import datetime
import logging
from typing import Dict, Any, Optional
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Transaction, Account, Category, utc_now
from app.services.consent_service import has_active_consent
from app.services.llm.factory import get_llm_client, check_user_daily_ai_limit
from app.services.prediction_service import compute_monthly_prediction
from app.core.errors import BadRequestException, ForbiddenException

logger = logging.getLogger("finance_app.assistant")


# Predefined Safe SQL Aggregation Tools
async def tool_get_category_spending(db: AsyncSession, user_id: str, **kwargs) -> Dict[str, Any]:
    """Aggregates total debit spending grouped by category for the current month."""
    now = datetime.datetime.now(datetime.timezone.utc)
    start_of_month = datetime.datetime(now.year, now.month, 1, tzinfo=datetime.timezone.utc)

    stmt = (
        select(
            Category.name,
            func.sum(Transaction.amount_minor).label("total_minor"),
            func.count(Transaction.id).label("txn_count")
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.direction == "debit",
                Transaction.deleted_at.is_(None),
                Transaction.txn_date >= start_of_month,
            )
        )
        .group_by(Category.name)
        .order_by(desc("total_minor"))
    )
    res = await db.execute(stmt)
    rows = res.all()

    spending = [
        {
            "category": r[0] or "Uncategorized",
            "amount_inr": round((r[1] or 0) / 100, 2),
            "transactions": r[2],
        }
        for r in rows
    ]
    total_spent_inr = round(sum(item["amount_inr"] for item in spending), 2)
    return {
        "month": now.strftime("%B %Y"),
        "total_spent_inr": total_spent_inr,
        "categories": spending,
    }


async def tool_get_top_merchants(db: AsyncSession, user_id: str, limit: int = 5, **kwargs) -> Dict[str, Any]:
    """Retrieves top merchants by total spend in the current month."""
    now = datetime.datetime.now(datetime.timezone.utc)
    start_of_month = datetime.datetime(now.year, now.month, 1, tzinfo=datetime.timezone.utc)

    stmt = (
        select(
            Transaction.merchant_normalized,
            func.sum(Transaction.amount_minor).label("total_minor"),
            func.count(Transaction.id).label("txn_count")
        )
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.direction == "debit",
                Transaction.deleted_at.is_(None),
                Transaction.txn_date >= start_of_month,
            )
        )
        .group_by(Transaction.merchant_normalized)
        .order_by(desc("total_minor"))
        .limit(limit)
    )
    res = await db.execute(stmt)
    rows = res.all()

    merchants = [
        {
            "merchant": r[0] or "Unknown",
            "amount_inr": round((r[1] or 0) / 100, 2),
            "transactions": r[2],
        }
        for r in rows
    ]
    return {
        "month": now.strftime("%B %Y"),
        "top_merchants": merchants,
    }


async def tool_get_account_balances(db: AsyncSession, user_id: str, **kwargs) -> Dict[str, Any]:
    """Retrieves linked accounts with masked identifiers and current balances."""
    stmt = select(Account).where(Account.user_id == user_id)
    res = await db.execute(stmt)
    accounts = res.scalars().all()

    total_balance_minor = sum(a.opening_balance_minor for a in accounts)
    return {
        "account_count": len(accounts),
        "total_balance_inr": round(total_balance_minor / 100, 2),
        "accounts": [
            {
                "name": a.name,
                "account_type": a.type,
                "masked_number": f"••••{a.last4 or '0000'}",
                "balance_inr": round(a.opening_balance_minor / 100, 2),
            }
            for a in accounts
        ],
    }


async def tool_get_cashflow_summary(db: AsyncSession, user_id: str, **kwargs) -> Dict[str, Any]:
    """Calculates income vs expenses for the current month."""
    now = datetime.datetime.now(datetime.timezone.utc)
    start_of_month = datetime.datetime(now.year, now.month, 1, tzinfo=datetime.timezone.utc)

    stmt = (
        select(
            Transaction.direction,
            func.sum(Transaction.amount_minor).label("total_minor")
        )
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.deleted_at.is_(None),
                Transaction.txn_date >= start_of_month,
            )
        )
        .group_by(Transaction.direction)
    )
    res = await db.execute(stmt)
    rows = res.all()

    income_inr = 0.0
    expense_inr = 0.0
    for direction, total_minor in rows:
        if direction == "credit":
            income_inr = round((total_minor or 0) / 100, 2)
        elif direction == "debit":
            expense_inr = round((total_minor or 0) / 100, 2)

    net_savings_inr = round(income_inr - expense_inr, 2)
    savings_rate = round((net_savings_inr / income_inr * 100), 1) if income_inr > 0 else 0.0

    return {
        "month": now.strftime("%B %Y"),
        "total_income_inr": income_inr,
        "total_expense_inr": expense_inr,
        "net_savings_inr": net_savings_inr,
        "savings_rate_pct": savings_rate,
    }


async def tool_get_monthly_forecast(db: AsyncSession, user_id: str, **kwargs) -> Dict[str, Any]:
    """Runs statistical forecast model for current month."""
    return await compute_monthly_prediction(db, user_id)


# Safe tool registry mapping
SAFE_TOOLS = {
    "category_spending": tool_get_category_spending,
    "top_merchants": tool_get_top_merchants,
    "account_balances": tool_get_account_balances,
    "cashflow_summary": tool_get_cashflow_summary,
    "monthly_forecast": tool_get_monthly_forecast,
}


async def answer_financial_query(
    db: AsyncSession,
    user_id: str,
    question: str,
) -> Dict[str, Any]:
    """
    Answers user natural language financial questions strictly via safe predefined SQL tools.
    Never allows raw or free-form SQL generation.
    """
    clean_q = question.strip()
    if not clean_q:
        raise BadRequestException("Question cannot be empty")

    has_consent = await has_active_consent(db, user_id, "ai_processing")
    if not has_consent:
        raise ForbiddenException(
            "AI processing consent is required to use the financial assistant. "
            "Please grant 'ai_processing' consent in Security Settings."
        )

    await check_user_daily_ai_limit(user_id)

    # Keyword / intent matching to pick safe predefined tool
    q_lower = clean_q.lower()
    selected_tool = "category_spending"

    if any(k in q_lower for k in ["balance", "account", "bank", "how much money", "total money"]):
        selected_tool = "account_balances"
    elif any(k in q_lower for k in ["merchant", "store", "swiggy", "zomato", "amazon", "who did i pay", "top spending", "vendors"]):
        selected_tool = "top_merchants"
    elif any(k in q_lower for k in ["cashflow", "income", "salary", "saved", "saving", "net"]):
        selected_tool = "cashflow_summary"
    elif any(k in q_lower for k in ["forecast", "predict", "end of month", "will i spend", "next month"]):
        selected_tool = "monthly_forecast"
    else:
        selected_tool = "category_spending"

    # Execute deterministic safe SQL tool
    tool_func = SAFE_TOOLS[selected_tool]
    tool_data = await tool_func(db, user_id)

    # Use LLM smart tier to synthesize helpful answer from tool data
    try:
        llm = get_llm_client()
        system_prompt = (
            "You are a helpful, trustworthy personal financial assistant for Indian users. "
            "Explain the user's financial query accurately based strictly on the provided structured data. "
            "All amounts are in Indian Rupees (₹). Keep explanations concise, polite, and actionable."
        )
        user_prompt = (
            f"User Question: \"{clean_q}\"\n"
            f"Tool Used: {selected_tool}\n"
            f"Verified Aggregate Data: {tool_data}\n"
            f"Return JSON format: {{\"answer\": \"<Clear concise response addressing user's question>\"}}"
        )

        res = await llm.complete_json(
            system=system_prompt,
            user=user_prompt,
            max_tokens=500,
            temperature=0.2,
            model_tier="smart",
        )
        answer_text = res.get("answer")
        if not answer_text:
            answer_text = f"Here is your financial summary based on verified records: {tool_data}"
    except Exception:
        # Deterministic conversational summary fallback
        if selected_tool == "account_balances":
            answer_text = f"You have {tool_data.get('account_count', 0)} active account(s) with a total combined balance of ₹{tool_data.get('total_balance_inr', 0):,.2f}."
        elif selected_tool == "cashflow_summary":
            answer_text = f"This month your income is ₹{tool_data.get('total_income_inr', 0):,.2f} and your expenses are ₹{tool_data.get('total_expense_inr', 0):,.2f}, resulting in net savings of ₹{tool_data.get('net_savings_inr', 0):,.2f}."
        elif selected_tool == "top_merchants":
            top_list = [f"{m['merchant']} (₹{m['amount_inr']:,.2f})" for m in tool_data.get("top_merchants", [])]
            answer_text = f"Your top merchants this month are: {', '.join(top_list)}."
        else:
            answer_text = f"Your total recorded spending for this month is ₹{tool_data.get('total_spent_inr', 0):,.2f}."

    return {
        "question": clean_q,
        "tool_used": selected_tool,
        "data": tool_data,
        "answer": answer_text,
    }
