import uuid
import datetime
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from tests.conftest import TestingSessionLocal
from app.models.models import User, Account, Category, Transaction, Consent, SavingsSuggestion, utc_now
from app.core.security import hash_password
from app.services.categorization_service import (
    categorize_transaction_data,
    batch_categorize_transactions,
    get_amount_bucket,
    sanitize_minimal_model_payload,
)
from app.services.insight_service import compute_user_aggregates, get_or_generate_insights, update_suggestion_status
from app.services.financial_assistant_service import answer_financial_query
from app.services.integration_health_service import run_all_health_checks
from app.core.config import settings


async def create_helper_user(session, email="ai_user@example.com") -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=hash_password("SecretPassword123!"),
        name="AI Tester",
        role="customer",
        is_active=True,
        email_verified=True,
        phone="+919876543210",
        phone_verified=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_amount_bucket_and_sanitizer():
    """Verifies privacy-preserving amount bucketing and non-PII sanitization."""
    assert get_amount_bucket(15000) == "< ₹500"
    assert get_amount_bucket(100000) == "₹500 - ₹2,000"
    assert get_amount_bucket(500000) == "₹2,000 - ₹10,000"
    assert get_amount_bucket(2500000) == "> ₹10,000"

    # Redaction of long numbers and balances
    sanitized = sanitize_minimal_model_payload(
        merchant="SBI Card ••••1234",
        description="Swiggy Order #987654321 Avl Bal INR 45,000.00",
        amount_minor=35000,
        direction="debit",
    )
    assert "[REDACTED_NUM]" in sanitized["merchant"]
    assert "[REDACTED_NUM]" in sanitized["description"]
    assert "45,000" not in sanitized["description"]
    assert sanitized["amount"] == 350.0
    assert sanitized["direction"] == "debit"


@pytest.mark.asyncio
async def test_categorization_consent_and_ai_fallback():
    """Verifies that without 'ai_processing' consent, unmapped transactions default to Uncategorized needs_review."""
    async with TestingSessionLocal() as session:
        test_user = await create_helper_user(session, "noconsent_user@example.com")
        result = await categorize_transaction_data(
            db=session,
            user_id=test_user.id,
            merchant="Random Unmapped Store XYZ",
            description="POS payment",
            amount_minor=120000,
            direction="debit",
        )
        assert result.needs_review is True
        assert result.category_confidence < 0.6
        assert result.category_source == "ml"


@pytest.mark.asyncio
async def test_categorization_with_ai_consent_and_mock_llm():
    """Verifies AI categorization works when 'ai_processing' consent is granted."""
    async with TestingSessionLocal() as session:
        test_user = await create_helper_user(session, "aiconsent_user@example.com")
        # Grant ai_processing consent
        ai_consent = Consent(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            consent_type="ai_processing",
            granted=True,
            granted_at=utc_now(),
            policy_version="1.0",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(ai_consent)
        await session.commit()

        # Food & Dining merchant
        res_food = await categorize_transaction_data(
            db=session,
            user_id=test_user.id,
            merchant="Swiggy Food Delivery",
            description="Order lunch",
            amount_minor=45000,
            direction="debit",
        )
        assert res_food.category_name in ("Food & Dining", "Food")
        assert res_food.needs_review is False

        # Low confidence trigger
        res_unknown = await categorize_transaction_data(
            db=session,
            user_id=test_user.id,
            merchant="low_confidence ambiguous store",
            description="charge misc",
            amount_minor=10000,
            direction="debit",
        )
        assert res_unknown.needs_review is True
        assert res_unknown.category_confidence < 0.6


@pytest.mark.asyncio
async def test_batch_categorization():
    """Verifies batch categorization processes items correctly in chunks up to 20."""
    async with TestingSessionLocal() as session:
        test_user = await create_helper_user(session, "batch_user@example.com")
        items = [
            {"merchant_raw": "Zomato", "description": "Dinner", "amount_minor": 42000, "direction": "debit"},
            {"merchant_raw": "Blinkit", "description": "Milk and bread", "amount_minor": 18000, "direction": "debit"},
            {"merchant_raw": "Uber India", "description": "Cab ride", "amount_minor": 25000, "direction": "debit"},
        ]
        results = await batch_categorize_transactions(session, test_user.id, items)
        assert len(results) == 3
        for r in results:
            assert r.category_name != "Uncategorized"


@pytest.mark.asyncio
async def test_savings_insights_and_status():
    """Verifies plain Python aggregates and savings suggestion generation and status update."""
    async with TestingSessionLocal() as session:
        test_user = await create_helper_user(session, "insights_user@example.com")
        acc = Account(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            name="Primary Savings",
            type="savings",
            last4="1234",
            opening_balance_minor=1000000,
        )
        session.add(acc)
        await session.commit()

        # Seed transactions
        now = utc_now()
        txn = Transaction(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            account_id=acc.id,
            amount_minor=500000,  # ₹5,000.00
            direction="debit",
            currency="INR",
            source="manual",
            dedupe_hash=str(uuid.uuid4()),
            txn_date=now,
            merchant_raw="Swiggy",
            merchant_normalized="Swiggy",
            description="Food deliveries",
        )
        session.add(txn)
        await session.commit()

        aggregates = await compute_user_aggregates(session, test_user.id)
        assert aggregates["current_month_spent_inr"] >= 5000.0

        # Generate insights
        suggestions = await get_or_generate_insights(session, test_user.id, force_refresh=True)
        assert len(suggestions) > 0
        sugg = suggestions[0]
        assert sugg.status == "new"

        # Update status to accepted
        updated = await update_suggestion_status(session, test_user.id, sugg.id, "accepted")
        assert updated.status == "accepted"


@pytest.mark.asyncio
async def test_financial_assistant_query():
    """Verifies safe SQL aggregation queries via assistant."""
    async with TestingSessionLocal() as session:
        test_user = await create_helper_user(session, "assistant_user@example.com")
        # Grant consent
        ai_consent = Consent(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            consent_type="ai_processing",
            granted=True,
            granted_at=utc_now(),
            policy_version="1.0",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(ai_consent)
        await session.commit()

        res = await answer_financial_query(
            db=session,
            user_id=test_user.id,
            question="How much did I spend this month?",
        )
        assert "answer" in res
        assert res["tool_used"] in ("category_spending", "cashflow_summary")
        assert "data" in res


@pytest.mark.asyncio
async def test_integration_health_diagnostic():
    """Verifies integration health check runner returns structured health status."""
    report = await run_all_health_checks()
    assert report["status"] in ("healthy", "degraded", "unhealthy")
    assert "email" in report
    assert "sms" in report
    assert "llm" in report
    assert report["llm"]["provider"] == settings.LLM_PROVIDER
