import calendar
import statistics
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from zoneinfo import ZoneInfo
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Transaction, Category, Budget, Forecast, User


def get_user_tz(user: Optional[User]) -> ZoneInfo:
    tz_str = user.timezone if user and user.timezone else "Asia/Kolkata"
    try:
        return ZoneInfo(tz_str)
    except Exception:
        return ZoneInfo("Asia/Kolkata")


async def compute_monthly_prediction(
    db: AsyncSession,
    user_id: str,
    as_of_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Deterministic, explainable statistical model for monthly spending prediction.
    
    ALGORITHM:
    1. Scope strictly to current user's non-deleted debit transactions (direction='debit').
    2. Convert transaction UTC dates to the user's local timezone.
    3. Separate completed calendar months (up to 6 previous months) from the current month.
    4. Outlier Filtering:
       - Detect any single past transaction exceeding mean + 3*std of past transactions.
       - Exclude abnormal one-off spikes from the baseline so regular habits are projected.
    5. Baseline Projection:
       - Weighted Moving Average (WMA) of completed months (weights 1, 2, ..., k, favoring recency).
    6. Run-Rate Projection:
       - (spent_so_far / days_elapsed) * days_in_month.
    7. Dynamic Blending:
       - alpha = days_elapsed / days_in_month.
       - Early month relies heavily on historical baseline; late month converges on run-rate.
    8. Recurring Expense Detection:
       - Detect merchants appearing in >= 2 completed months with consistent amounts (CV <= 0.25).
       - If a known recurring expense has not yet posted in the current month, ensure remaining
         projection covers it.
    9. Dynamic Uncertainty Range:
       - Standard deviation of past months, scaled by (days_remaining / days_in_month).
       - Lower bound >= spent_so_far, Upper bound >= predicted_total.
    10. Category Breakdown:
       - Project top categories and flag any that exceed the user's configured monthly budget.
    """
    # Load user for timezone & currency preferences
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    tz = get_user_tz(user)

    # Reference target date in user timezone
    if as_of_date:
        if as_of_date.tzinfo is None:
            now_local = as_of_date.replace(tzinfo=tz)
        else:
            now_local = as_of_date.astimezone(tz)
    else:
        now_local = datetime.now(tz)

    current_year = now_local.year
    current_month = now_local.month
    current_month_str = f"{current_year:04d}-{current_month:02d}"
    days_in_month = calendar.monthrange(current_year, current_month)[1]
    day_elapsed = max(1, min(now_local.day, days_in_month))
    days_remaining = days_in_month - day_elapsed

    # Query all user debit transactions
    stmt = (
        select(
            Transaction.id,
            Transaction.amount_minor,
            Transaction.txn_date,
            Transaction.merchant_normalized,
            Transaction.merchant_raw,
            Transaction.category_id,
        )
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.direction == "debit",
                Transaction.deleted_at.is_(None),
            )
        )
        .order_by(Transaction.txn_date.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    # Pre-fetch categories for display
    cat_stmt = select(Category).where(
        or_(Category.user_id.is_(None), Category.user_id == user_id)
    )
    cat_res = await db.execute(cat_stmt)
    cat_map = {c.id: c for c in cat_res.scalars().all()}

    # Group transactions by local calendar month
    month_txns: Dict[str, List[Any]] = {}
    current_month_txns: List[Any] = []

    for r in rows:
        txn_id, amount_minor, txn_dt, merch_norm, merch_raw, cat_id = r
        if txn_dt.tzinfo is None:
            txn_local = txn_dt.replace(tzinfo=timezone.utc).astimezone(tz)
        else:
            txn_local = txn_dt.astimezone(tz)

        m_str = txn_local.strftime("%Y-%m")
        item = {
            "id": txn_id,
            "amount_minor": amount_minor,
            "date": txn_local,
            "day": txn_local.day,
            "merchant": merch_norm or merch_raw or "Unknown",
            "category_id": cat_id,
            "month_str": m_str,
        }

        if m_str == current_month_str:
            # Only count transactions up to the current date/time
            if txn_local <= now_local:
                current_month_txns.append(item)
        elif m_str < current_month_str:
            month_txns.setdefault(m_str, []).append(item)

    spent_so_far_minor = sum(t["amount_minor"] for t in current_month_txns)

    # Sort completed months chronologically and keep the last 6
    completed_month_keys = sorted([m for m in month_txns.keys() if m < current_month_str])[-6:]
    completed_months_count = len(completed_month_keys)

    # COLD START HANDLING
    if completed_months_count == 0:
        return {
            "has_enough_data": False,
            "confidence": "none",
            "message": "Import at least 1 month of transactions to see predictions",
            "current_month": current_month_str,
            "days_elapsed": day_elapsed,
            "days_in_month": days_in_month,
            "days_remaining": days_remaining,
            "spent_so_far_minor": spent_so_far_minor,
            "predicted_total_minor": spent_so_far_minor,
            "lower_bound_minor": spent_so_far_minor,
            "upper_bound_minor": spent_so_far_minor,
            "projected_remaining_minor": 0,
            "daily_run_rate_minor": int(spent_so_far_minor / day_elapsed) if day_elapsed > 0 else 0,
            "historical_baseline_minor": 0,
            "completed_months_count": 0,
            "vs_last_month_pct": None,
            "vs_last_month_diff_minor": None,
            "last_month_total_minor": None,
            "drivers": ["Not enough past spending history to build an accurate predictive model."],
            "recurring_expenses_detected": [],
            "category_breakdown": [],
        }

    # Confidence rating based on completed historical months
    if completed_months_count in (1, 2):
        confidence = "low"
    elif completed_months_count in (3, 4):
        confidence = "medium"
    else:
        confidence = "high"

    # OUTLIER DETECTION ACROSS PAST MONTHS
    all_past_txns = [t for m in completed_month_keys for t in month_txns[m]]
    outlier_tx_ids = set()
    outliers_detected_count = 0
    if len(all_past_txns) >= 5:
        past_amounts = [t["amount_minor"] for t in all_past_txns]
        mean_tx = statistics.mean(past_amounts)
        std_tx = statistics.stdev(past_amounts)
        threshold = mean_tx + 3 * std_tx
        for t in all_past_txns:
            if t["amount_minor"] > threshold:
                outlier_tx_ids.add(t["id"])
                outliers_detected_count += 1

    # Compute filtered monthly totals for completed months
    completed_month_totals: List[int] = []
    for m in completed_month_keys:
        m_total = sum(t["amount_minor"] for t in month_txns[m] if t["id"] not in outlier_tx_ids)
        completed_month_totals.append(m_total)

    # HISTORICAL BASELINE: Weighted Moving Average
    k = len(completed_month_totals)
    weights = list(range(1, k + 1))
    weight_sum = sum(weights)
    baseline_minor = int(sum(w * tot for w, tot in zip(weights, completed_month_totals)) / weight_sum)

    # RUN-RATE PROJECTION
    daily_run_rate_minor = int(spent_so_far_minor / day_elapsed)
    run_rate_projection_minor = int(daily_run_rate_minor * days_in_month)

    # BLEND BASELINE AND RUN-RATE
    alpha = day_elapsed / days_in_month
    blended_total_minor = int((1.0 - alpha) * baseline_minor + alpha * run_rate_projection_minor)

    # RECURRING EXPENSES DETECTION
    merchant_past_records: Dict[str, List[Tuple[str, int, int]]] = {}
    for m in completed_month_keys:
        for t in month_txns[m]:
            merch_key = t["merchant"].strip().title()
            merchant_past_records.setdefault(merch_key, []).append((m, t["amount_minor"], t["day"]))

    current_month_merchants = {t["merchant"].strip().title() for t in current_month_txns}
    recurring_expenses_detected = []
    unbilled_recurring_minor = 0

    for merch, occurrences in merchant_past_records.items():
        distinct_months = {rec[0] for rec in occurrences}
        # Recurring if present in at least 2 distinct completed months
        if len(distinct_months) >= 2:
            amounts = [rec[1] for rec in occurrences]
            days = [rec[2] for rec in occurrences]
            avg_amt = int(statistics.mean(amounts))
            std_amt = statistics.stdev(amounts) if len(amounts) > 1 else 0
            cv = (std_amt / avg_amt) if avg_amt > 0 else 0

            # Consistent amounts (CV <= 0.25)
            if cv <= 0.25:
                typical_day = int(statistics.median(days))
                already_billed = merch in current_month_merchants
                rec_info = {
                    "merchant": merch,
                    "typical_amount_minor": avg_amt,
                    "typical_day": typical_day,
                    "already_billed_this_month": already_billed,
                }
                recurring_expenses_detected.append(rec_info)

                if not already_billed:
                    unbilled_recurring_minor += avg_amt

    # Ensure projected remaining accounts for unbilled recurring commitments
    remaining_blended = max(0, blended_total_minor - spent_so_far_minor)
    projected_remaining_minor = max(remaining_blended, unbilled_recurring_minor)
    predicted_total_minor = spent_so_far_minor + projected_remaining_minor

    # RANGE & UNCERTAINTY (Decreases as month ends)
    if k >= 2:
        month_std = statistics.stdev(completed_month_totals)
    else:
        month_std = baseline_minor * 0.15

    uncertainty_factor = days_remaining / days_in_month
    margin = int(month_std * uncertainty_factor)
    lower_bound_minor = max(spent_so_far_minor, predicted_total_minor - margin)
    upper_bound_minor = max(predicted_total_minor, predicted_total_minor + margin)

    # Enforce mathematical bounds: lower <= predicted <= upper
    if lower_bound_minor > predicted_total_minor:
        lower_bound_minor = predicted_total_minor
    if upper_bound_minor < predicted_total_minor:
        upper_bound_minor = predicted_total_minor

    # COMPARISON VS LAST MONTH
    last_month_total = completed_month_totals[-1] if completed_month_totals else None
    vs_last_month_pct = None
    vs_last_month_diff_minor = None
    if last_month_total and last_month_total > 0:
        vs_last_month_diff_minor = predicted_total_minor - last_month_total
        vs_last_month_pct = round(((predicted_total_minor - last_month_total) / last_month_total) * 100, 1)

    # EXPLAINABLE PLAIN-LANGUAGE DRIVERS
    drivers = []
    # 1. Baseline driver
    drivers.append(
        f"Based on your {completed_months_count}-month weighted average spending of ₹{baseline_minor / 100:,.0f}/month."
    )
    # 2. Run-rate pace driver
    drivers.append(
        f"Current pace of ₹{daily_run_rate_minor / 100:,.0f}/day across {day_elapsed} days elapsed in {now_local.strftime('%B')}."
    )
    # 3. Recurring expenses drivers
    unbilled_items = [r for r in recurring_expenses_detected if not r["already_billed_this_month"]]
    for item in unbilled_items[:3]:
        drivers.append(
            f"Upcoming commitment: {item['merchant']} (~₹{item['typical_amount_minor'] / 100:,.0f}) typically charged around day {item['typical_day']}."
        )
    # 4. Outlier driver
    if outliers_detected_count > 0:
        drivers.append(
            f"Filtered out {outliers_detected_count} one-off spending spike(s) from past baseline for a cleaner forecast."
        )
    # 5. Last month comparison driver
    if vs_last_month_pct is not None:
        direction_word = "higher" if vs_last_month_pct > 0 else "lower"
        drivers.append(
            f"Projected to be {abs(vs_last_month_pct)}% {direction_word} than last month (₹{last_month_total / 100:,.0f})."
        )

    # PER-CATEGORY BREAKDOWN & BUDGET CHECK
    category_past_totals: Dict[Optional[str], List[int]] = {}
    for m in completed_month_keys:
        cat_sums: Dict[Optional[str], int] = {}
        for t in month_txns[m]:
            if t["id"] not in outlier_tx_ids:
                cid = t["category_id"]
                cat_sums[cid] = cat_sums.get(cid, 0) + t["amount_minor"]
        for cid, val in cat_sums.items():
            category_past_totals.setdefault(cid, []).append(val)

    category_current_sums: Dict[Optional[str], int] = {}
    for t in current_month_txns:
        cid = t["category_id"]
        category_current_sums[cid] = category_current_sums.get(cid, 0) + t["amount_minor"]

    all_cat_ids = set(category_past_totals.keys()) | set(category_current_sums.keys())

    # Pre-fetch budgets for current month
    budget_stmt = select(Budget).where(
        and_(Budget.user_id == user_id, Budget.month == current_month_str)
    )
    b_res = await db.execute(budget_stmt)
    user_budgets = {b.category_id: b.limit_minor for b in b_res.scalars().all()}

    category_breakdown = []
    for cid in all_cat_ids:
        past_vals = category_past_totals.get(cid, [0])
        # Category baseline
        cat_base = int(statistics.mean(past_vals)) if past_vals else 0
        cat_spent = category_current_sums.get(cid, 0)
        cat_run_rate = (cat_spent / day_elapsed) * days_in_month
        cat_pred = int((1.0 - alpha) * cat_base + alpha * cat_run_rate)
        cat_pred = max(cat_spent, cat_pred)

        cat_obj = cat_map.get(cid) if cid else None
        cat_name = cat_obj.name if cat_obj else "Uncategorized"
        cat_color = cat_obj.color if cat_obj else "#6b7280"
        cat_icon = cat_obj.icon if cat_obj else "tag"

        b_limit = user_budgets.get(cid)
        budget_exceeded = bool(b_limit and cat_pred > b_limit)

        category_breakdown.append({
            "category_id": cid,
            "category_name": cat_name,
            "color": cat_color,
            "icon": cat_icon,
            "spent_so_far_minor": cat_spent,
            "predicted_minor": cat_pred,
            "percentage_of_total": round((cat_pred / predicted_total_minor) * 100, 1) if predicted_total_minor > 0 else 0,
            "budget_limit_minor": b_limit,
            "budget_exceeded": budget_exceeded,
        })

    # Sort categories by predicted spending descending
    category_breakdown.sort(key=lambda x: x["predicted_minor"], reverse=True)

    return {
        "has_enough_data": True,
        "confidence": confidence,
        "message": None,
        "current_month": current_month_str,
        "days_elapsed": day_elapsed,
        "days_in_month": days_in_month,
        "days_remaining": days_remaining,
        "spent_so_far_minor": spent_so_far_minor,
        "predicted_total_minor": predicted_total_minor,
        "lower_bound_minor": lower_bound_minor,
        "upper_bound_minor": upper_bound_minor,
        "projected_remaining_minor": projected_remaining_minor,
        "daily_run_rate_minor": daily_run_rate_minor,
        "historical_baseline_minor": baseline_minor,
        "completed_months_count": completed_months_count,
        "vs_last_month_pct": vs_last_month_pct,
        "vs_last_month_diff_minor": vs_last_month_diff_minor,
        "last_month_total_minor": last_month_total,
        "drivers": drivers,
        "recurring_expenses_detected": recurring_expenses_detected,
        "category_breakdown": category_breakdown[:8],
    }


async def persist_prediction(
    db: AsyncSession,
    user_id: str,
    prediction: Dict[str, Any],
) -> None:
    """
    Persist the current month prediction into the Forecast table.
    Upserts (user_id, target_month, category_id) for total and top categories.
    """
    if not prediction.get("has_enough_data"):
        return

    target_month = prediction["current_month"]
    pred_total = prediction["predicted_total_minor"]
    low_bound = prediction["lower_bound_minor"]
    up_bound = prediction["upper_bound_minor"]

    # 1. Upsert Total Forecast (category_id is None)
    stmt = select(Forecast).where(
        and_(
            Forecast.user_id == user_id,
            Forecast.target_month == target_month,
            Forecast.category_id.is_(None),
        )
    )
    res = await db.execute(stmt)
    existing_total = res.scalar_one_or_none()

    now_utc = datetime.now(timezone.utc)
    if existing_total:
        existing_total.predicted_minor = pred_total
        existing_total.lower_bound_minor = low_bound
        existing_total.upper_bound_minor = up_bound
        existing_total.model_version = "v1-stat"
        existing_total.created_at = now_utc
    else:
        import uuid
        fc = Forecast(
            id=str(uuid.uuid4()),
            user_id=user_id,
            target_month=target_month,
            category_id=None,
            predicted_minor=pred_total,
            lower_bound_minor=low_bound,
            upper_bound_minor=up_bound,
            model_version="v1-stat",
            created_at=now_utc,
        )
        db.add(fc)

    # 2. Upsert Category Forecasts
    for cat in prediction.get("category_breakdown", []):
        cid = cat.get("category_id")
        if not cid:
            continue
        c_pred = cat["predicted_minor"]

        c_stmt = select(Forecast).where(
            and_(
                Forecast.user_id == user_id,
                Forecast.target_month == target_month,
                Forecast.category_id == cid,
            )
        )
        c_res = await db.execute(c_stmt)
        existing_cat_fc = c_res.scalar_one_or_none()

        if existing_cat_fc:
            existing_cat_fc.predicted_minor = c_pred
            existing_cat_fc.lower_bound_minor = c_pred
            existing_cat_fc.upper_bound_minor = c_pred
            existing_cat_fc.model_version = "v1-stat"
            existing_cat_fc.created_at = now_utc
        else:
            import uuid
            cat_fc = Forecast(
                id=str(uuid.uuid4()),
                user_id=user_id,
                target_month=target_month,
                category_id=cid,
                predicted_minor=c_pred,
                lower_bound_minor=c_pred,
                upper_bound_minor=c_pred,
                model_version="v1-stat",
                created_at=now_utc,
            )
            db.add(cat_fc)

    await db.commit()


async def get_forecast_history(
    db: AsyncSession,
    user_id: str,
    months: int = 6,
    as_of_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Returns spending history for up to `months` past completed months plus the current month,
    comparing actual spending vs projected amount.
    """
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    tz = get_user_tz(user)

    ref_date = as_of_date or datetime.now(tz)
    current_month_str = ref_date.strftime("%Y-%m")

    # Fetch debit transactions
    stmt = (
        select(Transaction.amount_minor, Transaction.txn_date)
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.direction == "debit",
                Transaction.deleted_at.is_(None),
            )
        )
        .order_by(Transaction.txn_date.asc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    month_totals: Dict[str, int] = {}
    for amount_minor, txn_dt in rows:
        if txn_dt.tzinfo is None:
            txn_local = txn_dt.replace(tzinfo=timezone.utc).astimezone(tz)
        else:
            txn_local = txn_dt.astimezone(tz)
        m_str = txn_local.strftime("%Y-%m")
        month_totals[m_str] = month_totals.get(m_str, 0) + amount_minor

    # Fetch stored forecasts
    fc_stmt = select(Forecast).where(
        and_(
            Forecast.user_id == user_id,
            Forecast.category_id.is_(None),
        )
    )
    fc_res = await db.execute(fc_stmt)
    saved_forecasts = {f.target_month: f for f in fc_res.scalars().all()}

    # Compute current month prediction
    current_pred = await compute_monthly_prediction(db, user_id, as_of_date=ref_date)

    # Collect past months keys
    past_months = sorted([m for m in month_totals.keys() if m < current_month_str])[-months:]

    history = []
    for m in past_months:
        dt = datetime.strptime(m, "%Y-%m")
        label = dt.strftime("%b %y")
        fc = saved_forecasts.get(m)
        history.append({
            "month": m,
            "month_label": label,
            "actual_minor": month_totals[m],
            "predicted_minor": fc.predicted_minor if fc else month_totals[m],
            "lower_bound_minor": fc.lower_bound_minor if fc else None,
            "upper_bound_minor": fc.upper_bound_minor if fc else None,
            "is_current": False,
        })

    # Add current month
    cur_dt = datetime.strptime(current_month_str, "%Y-%m")
    history.append({
        "month": current_month_str,
        "month_label": f"{cur_dt.strftime('%b %y')} (Est)",
        "actual_minor": current_pred["spent_so_far_minor"],
        "predicted_minor": current_pred["predicted_total_minor"],
        "lower_bound_minor": current_pred["lower_bound_minor"],
        "upper_bound_minor": current_pred["upper_bound_minor"],
        "is_current": True,
    })

    return history


async def trigger_prediction_update(db: AsyncSession, user_id: str) -> None:
    """Safe helper to recompute and persist forecast after transaction changes."""
    try:
        pred = await compute_monthly_prediction(db, user_id)
        await persist_prediction(db, user_id, pred)
    except Exception:
        # Non-blocking: background recalculation should never block the primary transaction
        pass

