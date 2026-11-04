import pytest
from httpx import AsyncClient
from sqlalchemy import select, and_
from app.models.models import MerchantRule, Transaction, Category
from tests.conftest import TestingSessionLocal
from app.services.categorization_service import sanitize_minimal_model_payload


@pytest.mark.asyncio
async def test_minimal_data_sent_to_model_no_pii():
    """Verify that only minimal non-PII data is sent to the model.

    Account numbers, card masks, balances, and PII are strictly stripped.
    """
    raw_merchant = "Swiggy UPI-49102948 Card ••••4589"
    raw_desc = "Lunch order Rs 450.00 Avl Bal: Rs 45,000.00"
    amount_minor = 45000
    direction = "debit"

    payload = sanitize_minimal_model_payload(
        merchant=raw_merchant,
        description=raw_desc,
        amount_minor=amount_minor,
        direction=direction,
    )

    # 1. Contains only the minimal 4 required attributes
    assert set(payload.keys()) == {"merchant", "description", "amount", "direction"}

    # 2. Card numbers and digit sequences are redacted
    assert "4589" not in payload["merchant"]
    assert "[REDACTED_NUM]" in payload["merchant"]

    # 3. Balance disclosure is stripped from description
    assert "45,000" not in payload["description"]
    assert "Avl Bal" not in payload["description"]

    # 4. Correct numerical amount and direction
    assert payload["amount"] == 450.0
    assert payload["direction"] == "debit"


@pytest.mark.asyncio
async def test_rule_match_beats_model_and_builtins(client: AsyncClient):
    """Verify that predefined rules (built-in Indian rules and custom rules)

    beat model fallback with category_source="rule" and confidence 1.0.
    """
    email = "rule_user@example.com"
    pwd = "Password123!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "Rule User"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Grant SMS & statement consent
    await client.post("/api/v1/consents", json={"consent_type": "sms_import"}, headers=headers)

    acc = (await client.post("/api/v1/accounts", json={"name": "HDFC Checking", "type": "savings"}, headers=headers)).json()["id"]

    # 1. Swiggy matches built-in rule -> Food & Dining
    sms_text = "HDFC Bank: Rs 649.00 debited from a/c **4589 on 04-Nov-26 to SWIGGY BANGALORE."
    imp = await client.post("/api/v1/imports/sms", json={"account_id": acc, "raw_text": sms_text}, headers=headers)
    assert imp.status_code == 200

    txns = (await client.get("/api/v1/transactions", headers=headers)).json()["items"]
    assert len(txns) == 1
    t = txns[0]
    assert t["category"]["name"] == "Food & Dining"
    assert t["category_source"] == "rule"
    assert t["category_confidence"] == 1.0
    assert t["needs_review"] is False


@pytest.mark.asyncio
async def test_model_fallback_and_confidence_threshold(client: AsyncClient):
    """Verify that unseen or ambiguous merchants fall back to ML model.

    If confidence < 0.6, transaction is flagged with needs_review=True and
    category="Uncategorized".
    """
    email = "ml_user@example.com"
    pwd = "Password123!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "ML User"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    await client.post("/api/v1/consents", json={"consent_type": "sms_import"}, headers=headers)
    acc = (await client.post("/api/v1/accounts", json={"name": "Kotak Checking", "type": "savings"}, headers=headers)).json()["id"]

    # 1. High-confidence model pattern (e.g. "Coursera Course" -> Education)
    sms_high_conf = "HDFC Bank: Rs 2400.00 debited from a/c **4589 on 04-Nov-26 towards Coursera Online Course."
    await client.post("/api/v1/imports/sms", json={"account_id": acc, "raw_text": sms_high_conf}, headers=headers)

    # 2. Ambiguous merchant with low information ("UNKNOWN CORP MISC CHARGE") -> triggers needs_review
    sms_ambiguous = "HDFC Bank: Rs 999.00 debited from a/c **4589 on 04-Nov-26 towards UNKNOWN CORP MISC CHARGE."
    await client.post("/api/v1/imports/sms", json={"account_id": acc, "raw_text": sms_ambiguous}, headers=headers)

    # Fetch all transactions
    txns = (await client.get("/api/v1/transactions", headers=headers)).json()["items"]
    assert len(txns) == 2

    coursera_txn = next(t for t in txns if "coursera" in t["merchant"].lower())
    assert coursera_txn["category_source"] == "ml"
    assert coursera_txn["category_confidence"] >= 0.6
    assert coursera_txn["needs_review"] is False

    ambiguous_txn = next(t for t in txns if "unknown corp" in t["merchant"].lower())
    assert ambiguous_txn["category_source"] == "ml"
    assert ambiguous_txn["category_confidence"] < 0.6
    assert ambiguous_txn["needs_review"] is True
    assert ambiguous_txn["category"]["name"] == "Uncategorized"

    # Query GET /api/v1/transactions/needs-review
    needs_review_res = await client.get("/api/v1/transactions/needs-review", headers=headers)
    assert needs_review_res.status_code == 200
    nr_data = needs_review_res.json()
    assert nr_data["total"] == 1
    assert nr_data["items"][0]["id"] == ambiguous_txn["id"]


@pytest.mark.asyncio
async def test_user_correction_creates_merchant_rule_and_isolation(client: AsyncClient):
    """Step 3 & 4: User correction sets category_source='user'.

    With 'create_rule=True', it creates a MerchantRule for this user only, which
    subsequently beats model suggestions for future transactions without
    influencing other users.
    """
    # User A
    user_a_email = "usera_rules@example.com"
    pwd = "Password123!"
    await client.post("/api/v1/auth/register", json={"email": user_a_email, "password": pwd, "name": "User A"})
    login_a = await client.post("/api/v1/auth/login", json={"email": user_a_email, "password": pwd})
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}
    await client.post("/api/v1/consents", json={"consent_type": "sms_import"}, headers=headers_a)
    acc_a = (await client.post("/api/v1/accounts", json={"name": "Account A", "type": "savings"}, headers=headers_a)).json()["id"]

    # User B
    user_b_email = "userb_rules@example.com"
    await client.post("/api/v1/auth/register", json={"email": user_b_email, "password": pwd, "name": "User B"})
    login_b = await client.post("/api/v1/auth/login", json={"email": user_b_email, "password": pwd})
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
    await client.post("/api/v1/consents", json={"consent_type": "sms_import"}, headers=headers_b)
    acc_b = (await client.post("/api/v1/accounts", json={"name": "Account B", "type": "savings"}, headers=headers_b)).json()["id"]

    # Categories
    cat_books = (await client.post("/api/v1/categories", json={"name": "Books & Learning", "color": "#10b981"}, headers=headers_a)).json()["id"]
    cat_hobbies = (await client.post("/api/v1/categories", json={"name": "Hobbies", "color": "#f59e0b"}, headers=headers_b)).json()["id"]

    # User A imports transaction for custom merchant "ACME Bookstore"
    sms_a = "HDFC Bank: Rs 550.00 debited from a/c **4589 on 04-Nov-26 towards ACME Bookstore."
    await client.post("/api/v1/imports/sms", json={"account_id": acc_a, "raw_text": sms_a}, headers=headers_a)
    txn_a = (await client.get("/api/v1/transactions", headers=headers_a)).json()["items"][0]

    # User A updates category with create_rule=True
    patch_res = await client.patch(
        f"/api/v1/transactions/{txn_a['id']}",
        json={"category_id": cat_books, "create_rule": True},
        headers=headers_a,
    )
    assert patch_res.status_code == 200
    patched_txn = patch_res.json()
    assert patched_txn["category_source"] == "user"
    assert patched_txn["category_confidence"] == 1.0
    assert patched_txn["needs_review"] is False

    # Verify MerchantRule was created in database under User A's ID
    async with TestingSessionLocal() as session:
        rule_stmt = select(MerchantRule).where(MerchantRule.pattern.ilike("%ACME Bookstore%"))
        rule = (await session.execute(rule_stmt)).scalar_one_or_none()
        assert rule is not None
        assert rule.category_id == cat_books

    # Future transaction from User A for "ACME Bookstore" should now be categorized via the Rule!
    sms_a_future = "HDFC Bank: Rs 900.00 debited from a/c **4589 on 05-Nov-26 towards ACME Bookstore."
    await client.post("/api/v1/imports/sms", json={"account_id": acc_a, "raw_text": sms_a_future}, headers=headers_a)
    txns_a_all = (await client.get("/api/v1/transactions", headers=headers_a)).json()["items"]
    new_txn_a = next(t for t in txns_a_all if t["id"] != txn_a["id"])
    assert new_txn_a["category"]["id"] == cat_books
    assert new_txn_a["category_source"] == "rule"

    # User B imports the same merchant "ACME Bookstore": User A's rule MUST NOT affect User B!
    sms_b = "HDFC Bank: Rs 550.00 debited from a/c **4589 on 04-Nov-26 towards ACME Bookstore."
    await client.post("/api/v1/imports/sms", json={"account_id": acc_b, "raw_text": sms_b}, headers=headers_b)
    txn_b = (await client.get("/api/v1/transactions", headers=headers_b)).json()["items"][0]

    # User B's transaction does NOT have User A's custom category
    assert txn_b["category"]["id"] != cat_books


@pytest.mark.asyncio
async def test_recategorization_endpoint(client: AsyncClient):
    """Step 5: Verify POST /api/v1/transactions/recategorize re-evaluates

    transactions after new rules are added, preserving user-locked categories.
    """
    email = "recat_user@example.com"
    pwd = "Password123!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "Recat User"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    await client.post("/api/v1/consents", json={"consent_type": "sms_import"}, headers=headers)
    acc = (await client.post("/api/v1/accounts", json={"name": "Axis Checking", "type": "savings"}, headers=headers)).json()["id"]

    cat_coffee = (await client.post("/api/v1/categories", json={"name": "Artisan Coffee", "color": "#78350f"}, headers=headers)).json()["id"]

    # Import ambiguous/unrecognized merchant
    sms = "HDFC Bank: Rs 300.00 debited from a/c **4589 on 04-Nov-26 towards BlueTokaiCoffee Roasters."
    await client.post("/api/v1/imports/sms", json={"account_id": acc, "raw_text": sms}, headers=headers)
    txns = (await client.get("/api/v1/transactions", headers=headers)).json()["items"]
    assert len(txns) == 1
    t_id = txns[0]["id"]

    # Now user adds a MerchantRule for "BlueTokai"
    await client.post(
        "/api/v1/merchant-rules",
        json={"pattern": "BlueTokai", "category_id": cat_coffee, "priority": 10},
        headers=headers,
    )

    # Call POST /api/v1/transactions/recategorize
    recat_res = await client.post("/api/v1/transactions/recategorize", headers=headers)
    assert recat_res.status_code == 200
    recat_data = recat_res.json()
    assert recat_data["updated_count"] >= 1

    # Verify transaction is now categorized under "Artisan Coffee" via rule
    updated_txn = (await client.get(f"/api/v1/transactions/{t_id}", headers=headers)).json()
    assert updated_txn["category"]["id"] == cat_coffee
    assert updated_txn["category_source"] == "rule"
