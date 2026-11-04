import datetime
import logging
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import SavingsSuggestion, Transaction, Category, utc_now
from app.services.consent_service import has_active_consent
from app.services.llm.factory import get_llm_client, check_user_daily_ai_limit
from app.services.prediction_service import compute_monthly_prediction
from app.core.errors import NotFoundException, BadRequestException

logger = logging.getLogger("finance_app.insights")


async def compute_user_aggregates(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    """
    Computes purely numeric aggregated statistics in plain Python/SQL for the current and prior month.
    Sends ONLY aggregates (never raw SMS, balances, names, or accounts).
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    current_year = now.year
    current_month = now.month

    # Current month start / end
    current_start = datetime.datetime(current_year, current_month, 1, tzinfo=datetime.timezone.utc)
    if current_month == 12:
        next_start = datetime.datetime(current_year + 1, 1, 1, tzinfo=datetime.timezone.utc)
        prev_start = datetime.datetime(current_year, 11, 1, tzinfo=datetime.timezone.utc)
    elif current_month == 1:
        next_start = datetime.datetime(current_year, 2, 1, tzinfo=datetime.timezone.utc)
        prev_start = datetime.datetime(current_year - 1, 12, 1, tzinfo=datetime.timezone.utc)
    else:
        next_start = datetime.datetime(current_year, current_month + 1, 1, tzinfo=datetime.timezone.utc)
        prev_start = datetime.datetime(current_year, current_month - 1, 1, tzinfo=datetime.timezone.utc)

    # 1. Current month transactions
    stmt_curr = select(
        Transaction.category_id,
        Transaction.merchant_normalized,
        Transaction.amount_minor
    ).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
            Transaction.txn_date >= current_start,
            Transaction.txn_date < next_start,
        )
    )
    res_curr = await db.execute(stmt_curr)
    curr_txns = res_curr.all()

    # 2. Previous month transactions
    stmt_prev = select(
        Transaction.category_id,
        Transaction.amount_minor
    ).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
            Transaction.txn_date >= prev_start,
            Transaction.txn_date < current_start,
        )
    )
    res_prev = await db.execute(stmt_prev)
    prev_txns = res_prev.all()

    # Fetch category names
    cat_stmt = select(Category.id, Category.name)
    cat_res = await db.execute(cat_stmt)
    cat_names = {c.id: c.name for c in cat_res.all()}

    curr_total_minor = sum(t.amount_minor for t in curr_txns)
    prev_total_minor = sum(t.amount_minor for t in prev_txns)

    # Category breakdown for current month
    curr_by_cat: Dict[str, int] = {}
    merchant_spend: Dict[str, int] = {}
    for t in curr_txns:
        c_name = cat_names.get(t.category_id, "Other")
        curr_by_cat[c_name] = curr_by_cat.get(c_name, 0) + t.amount_minor
        m_name = t.merchant_normalized or "Unknown"
        merchant_spend[m_name] = merchant_spend.get(m_name, 0) + t.amount_minor

    # Category breakdown for prev month
    prev_by_cat: Dict[str, int] = {}
    for t in prev_txns:
        c_name = cat_names.get(t.category_id, "Other")
        prev_by_cat[c_name] = prev_by_cat.get(c_name, 0) + t.amount_minor

    # MoM changes
    mom_changes: Dict[str, float] = {}
    all_cat_names = set(curr_by_cat.keys()) | set(prev_by_cat.keys())
    for c_name in all_cat_names:
        c_curr = curr_by_cat.get(c_name, 0)
        c_prev = prev_by_cat.get(c_name, 0)
        if c_prev > 0:
            mom_changes[c_name] = round(((c_curr - c_prev) / c_prev) * 100, 1)
        else:
            mom_changes[c_name] = 100.0 if c_curr > 0 else 0.0

    # Top merchants
    top_merchants = sorted(merchant_spend.items(), key=lambda x: x[1], reverse=True)[:5]
    top_merchants_fmt = [{"merchant": m, "amount_inr": round(amt / 100, 2)} for m, amt in top_merchants]

    # Month-end predicted total
    try:
        pred_res = await compute_monthly_prediction(db, user_id)
        predicted_total_inr = round(pred_res.get("predicted_total_minor", curr_total_minor) / 100, 2)
    except Exception:
        predicted_total_inr = round(curr_total_minor / 100, 2)

    return {
        "current_month_spent_inr": round(curr_total_minor / 100, 2),
        "prev_month_spent_inr": round(prev_total_minor / 100, 2),
        "predicted_month_end_inr": predicted_total_inr,
        "category_spend_inr": {k: round(v / 100, 2) for k, v in curr_by_cat.items()},
        "mom_percentage_change": mom_changes,
        "top_merchants": top_merchants_fmt,
    }


def _get_fallback_suggestions(aggregates: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Deterministic fallback suggestions when LLM is unavailable or unconsented."""
    suggestions = []
    cat_spend = aggregates.get("category_spend_inr", {})
    top_merchants = aggregates.get("top_merchants", [])

    # Food & Dining suggestion
    food_spend = cat_spend.get("Food & Dining", 0)
    if food_spend > 2000:
        suggestions.append({
            "type": "dining_reduction",
            "title": "Optimize Food & Dining Expenses",
            "detail": f"You have spent ₹{food_spend:,.2f} on dining out and food deliveries this month. Preparing meals at home 2-3 times more each week could save up to 20%.",
            "estimated_saving_minor": int(food_spend * 0.20 * 100),
        })

    # Subscriptions check
    sub_spend = cat_spend.get("Entertainment", 0) + cat_spend.get("Subscriptions", 0)
    if sub_spend > 500:
        suggestions.append({
            "type": "subscription_cancel",
            "title": "Review Recurring Digital Subscriptions",
            "detail": f"Monthly entertainment and subscription outlays total ₹{sub_spend:,.2f}. Auditing active memberships and sharing family plans can cut overhead.",
            "estimated_saving_minor": int(sub_spend * 0.30 * 100),
        })

    # High utility MoM
    mom = aggregates.get("mom_percentage_change", {})
    util_mom = mom.get("Bills & Utilities", 0)
    if util_mom > 10:
        suggestions.append({
            "type": "utility_audit",
            "title": "Utility Bill Optimization",
            "detail": f"Utility expenses increased by {util_mom}% compared to last month. Review electricity usage and broadband plan tiers.",
            "estimated_saving_minor": 50000,
        })

    if not suggestions:
        suggestions.append({
            "type": "general_budget",
            "title": "Establish Category Spending Caps",
            "detail": "Setting spending limits on discretionary categories like shopping and dining can help retain an extra 10% of monthly income.",
            "estimated_saving_minor": 150000,
        })

    return suggestions[:5]


async def get_or_generate_insights(
    db: AsyncSession,
    user_id: str,
    force_refresh: bool = False,
) -> List[SavingsSuggestion]:
    """
    Returns active savings suggestions for the user.
    Uses cached records if generated within the last 24 hours unless force_refresh is True.
    """
    twenty_four_hours_ago = utc_now() - datetime.timedelta(hours=24)

    # 1. Check existing cached suggestions
    if not force_refresh:
        stmt = (
            select(SavingsSuggestion)
            .where(
                and_(
                    SavingsSuggestion.user_id == user_id,
                    SavingsSuggestion.created_at >= twenty_four_hours_ago,
                )
            )
            .order_by(desc(SavingsSuggestion.created_at))
        )
        res = await db.execute(stmt)
        cached = list(res.scalars().all())
        if cached:
            return cached

    # 2. Compute numeric aggregated statistics
    aggregates = await compute_user_aggregates(db, user_id)

    # 3. Privacy & Consent check
    has_ai_consent = await has_active_consent(db, user_id, "ai_processing")
    suggestions_data = []

    if has_ai_consent:
        try:
            await check_user_daily_ai_limit(user_id)
            llm = get_llm_client()
            system_prompt = (
                "You are an expert Indian personal finance advisor. Analyze the monthly spending aggregates "
                "and generate 3 to 5 realistic, actionable, and structured savings suggestions. "
                "Return pure JSON with key 'suggestions': "
                "[{\"type\": \"<subscription_cancel|dining_reduction|utility_audit|general_budget>\", "
                "\"title\": \"<clear title>\", \"detail\": \"<practical explanation>\", "
                "\"estimated_saving_minor\": <amount in paise as integer>}]."
            )
            user_prompt = (
                f"Financial Aggregates for User:\n"
                f"- Current Month Spent: ₹{aggregates['current_month_spent_inr']}\n"
                f"- Previous Month Spent: ₹{aggregates['prev_month_spent_inr']}\n"
                f"- Predicted Total: ₹{aggregates['predicted_month_end_inr']}\n"
                f"- Category Spend: {aggregates['category_spend_inr']}\n"
                f"- Month-over-Month %: {aggregates['mom_percentage_change']}\n"
                f"- Top Merchants: {aggregates['top_merchants']}\n"
            )

            res = await llm.complete_json(
                system=system_prompt,
                user=user_prompt,
                max_tokens=800,
                temperature=0.3,
                model_tier="smart",
            )
            suggestions_data = res.get("suggestions", [])
        except Exception as e:
            logger.warning("LLM smart tier suggestion generation failed: %s. Using fallbacks.", str(e))
            suggestions_data = _get_fallback_suggestions(aggregates)
    else:
        suggestions_data = _get_fallback_suggestions(aggregates)

    if not suggestions_data:
        suggestions_data = _get_fallback_suggestions(aggregates)

    # Persist suggestions in database
    created_records = []
    for item in suggestions_data[:5]:
        sugg = SavingsSuggestion(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=item.get("type", "general_budget")[:50],
            title=item.get("title", "Savings Opportunity")[:255],
            detail=item.get("detail", ""),
            estimated_saving_minor=int(item.get("estimated_saving_minor", 0)),
            status="new",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(sugg)
        created_records.append(sugg)

    await db.commit()
    for s in created_records:
        await db.refresh(s)

    return created_records


async def update_suggestion_status(
    db: AsyncSession,
    user_id: str,
    suggestion_id: str,
    new_status: str,
) -> SavingsSuggestion:
    """Updates status of a savings suggestion (new, accepted, dismissed)."""
    if new_status not in {"new", "accepted", "dismissed"}:
        raise BadRequestException("Invalid status. Must be one of: new, accepted, dismissed")

    stmt = select(SavingsSuggestion).where(
        and_(
            SavingsSuggestion.id == suggestion_id,
            SavingsSuggestion.user_id == user_id,
        )
    )
    res = await db.execute(stmt)
    sugg = res.scalar_one_or_none()
    if not sugg:
        raise NotFoundException("Savings suggestion not found")

    sugg.status = new_status
    sugg.updated_at = utc_now()
    await db.commit()
    await db.refresh(sugg)
    return sugg

