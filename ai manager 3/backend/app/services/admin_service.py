import csv
import io
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from zoneinfo import ZoneInfo
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import NotFoundException
from app.models.models import User, Account, Transaction, Category, Budget, Consent, Import, AuditLog
from app.schemas.admin import (
    AdminOverviewResponse,
    AdminAnalyticsResponse,
    CustomerListResponse,
    CustomerSummaryItem,
    Customer360Response,
    CustomerProfile,
    AccountSummary,
    CustomerTransactionItem,
    CategorySpendSummary,
    MonthlySpendTrend,
    CustomerSegmentSummary,
    MerchantSummary,
    BudgetVsActual,
    PredictionBreakdown,
    ConsentSummary,
    ImportSummary,
    RiskAlert,
    AdminImportItem,
    AdminAuditLogItem,
)
from app.services.prediction_service import compute_monthly_prediction


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***@***.***"
    parts = email.split("@", 1)
    user_part, domain = parts[0], parts[1]
    if len(user_part) <= 2:
        masked_user = user_part[0] + "***"
    else:
        masked_user = user_part[0] + "***" + user_part[-1]
    return f"{masked_user}@{domain}"


def mask_account_number(last4: Optional[str]) -> str:
    if last4:
        return f"****{last4}"
    return "****0000"


def get_visible_customer_clause():
    """
    Returns an SQLAlchemy clause that filters for customers visible to admin:
    1. Role must be 'customer'
    2. Must be either is_demo == True OR have an active 'share_with_bank' consent
    """
    consented_subquery = (
        select(Consent.user_id)
        .where(
            Consent.consent_type == "share_with_bank",
            Consent.granted.is_(True),
            Consent.revoked_at.is_(None),
        )
    )
    return and_(
        User.role == "customer",
        or_(
            User.is_demo.is_(True),
            User.id.in_(consented_subquery),
        ),
    )


async def log_admin_audit(
    db: AsyncSession,
    admin_id: str,
    action: str,
    entity: str = "customer",
    entity_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    meta_data: Optional[Dict[str, Any]] = None,
) -> None:
    data = meta_data or {}
    if client_ip:
        data["ip"] = client_ip
    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=admin_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        meta_data=data,
        created_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    await db.commit()


async def get_visible_customer_or_404(db: AsyncSession, customer_id: str) -> User:
    stmt = select(User).where(
        User.id == customer_id,
        get_visible_customer_clause(),
    )
    res = await db.execute(stmt)
    customer = res.scalar_one_or_none()
    if not customer:
        raise NotFoundException("Customer not found or not visible")
    return customer


async def get_overview(db: AsyncSession) -> AdminOverviewResponse:
    vis_clause = get_visible_customer_clause()

    # Total visible customers
    tot_stmt = select(func.count(User.id)).where(vis_clause)
    total_customers = (await db.execute(tot_stmt)).scalar() or 0

    # Demo vs consented counts
    demo_stmt = select(func.count(User.id)).where(vis_clause, User.is_demo.is_(True))
    demo_count = (await db.execute(demo_stmt)).scalar() or 0
    consented_count = max(0, total_customers - demo_count)

    # Visible customer IDs subquery
    vis_cust_ids = select(User.id).where(vis_clause)

    # Active customers in last 30 days
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    act_stmt = select(func.count(func.distinct(Transaction.user_id))).where(
        Transaction.user_id.in_(vis_cust_ids),
        Transaction.txn_date >= thirty_days_ago,
        Transaction.deleted_at.is_(None),
    )
    active_customers_30d = (await db.execute(act_stmt)).scalar() or 0

    # Total tracked spend this month
    now = datetime.now(timezone.utc)
    first_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    spend_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
        Transaction.user_id.in_(vis_cust_ids),
        Transaction.direction == "debit",
        Transaction.deleted_at.is_(None),
        Transaction.txn_date >= first_of_month,
    )
    total_spend_this_month = (await db.execute(spend_stmt)).scalar() or 0

    avg_spend = int(total_spend_this_month / total_customers) if total_customers > 0 else 0

    # Total transactions
    tx_count_stmt = select(func.count(Transaction.id)).where(
        Transaction.user_id.in_(vis_cust_ids),
        Transaction.deleted_at.is_(None),
    )
    total_transactions = (await db.execute(tx_count_stmt)).scalar() or 0

    # Import success rate
    imp_done_stmt = select(func.count(Import.id)).where(
        Import.user_id.in_(vis_cust_ids),
        Import.status == "done",
    )
    imp_total_stmt = select(func.count(Import.id)).where(
        Import.user_id.in_(vis_cust_ids),
    )
    done_imports = (await db.execute(imp_done_stmt)).scalar() or 0
    total_imports = (await db.execute(imp_total_stmt)).scalar() or 0
    success_rate = round((done_imports / total_imports * 100.0), 1) if total_imports > 0 else 100.0

    # Top risk customers
    alerts = await get_risk_alerts(db)
    # Group by customer and take top 5 distinct
    seen_custs = set()
    top_risk = []
    for a in alerts:
        if a.customer_id not in seen_custs:
            seen_custs.add(a.customer_id)
            top_risk.append({
                "customer_id": a.customer_id,
                "name": a.customer_name,
                "masked_email": a.masked_email,
                "segment": a.segment,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "reason": a.reason,
            })
            if len(top_risk) >= 5:
                break

    return AdminOverviewResponse(
        total_customers=total_customers,
        active_customers_30d=active_customers_30d,
        total_tracked_spend_this_month=int(total_spend_this_month),
        avg_monthly_spend_per_customer=avg_spend,
        total_transactions=total_transactions,
        import_success_rate=success_rate,
        consented_customers_count=consented_count,
        demo_customers_count=demo_count,
        top_risk_customers=top_risk,
    )


async def get_analytics(db: AsyncSession) -> AdminAnalyticsResponse:
    vis_clause = get_visible_customer_clause()
    vis_cust_ids = select(User.id).where(vis_clause)

    now = datetime.now(timezone.utc)
    first_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # 1. Spend by Category (current month)
    cat_stmt = (
        select(
            Category.id,
            Category.name,
            Category.icon,
            Category.color,
            func.coalesce(func.sum(Transaction.amount_minor), 0).label("spend"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id.in_(vis_cust_ids),
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
            Transaction.txn_date >= first_of_month,
        )
        .group_by(Category.id, Category.name, Category.icon, Category.color)
        .order_by(desc("spend"))
    )
    cat_rows = (await db.execute(cat_stmt)).all()
    total_cat_spend = sum(r.spend for r in cat_rows) or 1
    spend_by_cat = [
        CategorySpendSummary(
            category_id=r.id,
            category_name=r.name or "Uncategorized",
            icon=r.icon or "Tag",
            color=r.color or "#3B82F6",
            total_spend_minor=int(r.spend),
            percentage=round((r.spend / total_cat_spend * 100.0), 1),
        )
        for r in cat_rows
    ]

    # 2. Monthly Spend Trend (last 6 calendar months)
    monthly_trend: List[MonthlySpendTrend] = []
    for i in range(5, -1, -1):
        target_year = now.year
        target_month = now.month - i
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        m_str = f"{target_year:04d}-{target_month:02d}"
        start_dt = datetime(target_year, target_month, 1, tzinfo=timezone.utc)
        if target_month == 12:
            end_dt = datetime(target_year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_dt = datetime(target_year, target_month + 1, 1, tzinfo=timezone.utc)

        m_stmt = select(
            func.coalesce(func.sum(Transaction.amount_minor), 0),
            func.count(Transaction.id),
        ).where(
            Transaction.user_id.in_(vis_cust_ids),
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
            Transaction.txn_date >= start_dt,
            Transaction.txn_date < end_dt,
        )
        m_res = (await db.execute(m_stmt)).one()
        monthly_trend.append(
            MonthlySpendTrend(
                month=m_str,
                spend_minor=int(m_res[0]),
                transactions_count=int(m_res[1]),
            )
        )

    # 3. Customer Segments
    seg_stmt = (
        select(
            func.coalesce(User.segment, "general").label("seg"),
            func.count(User.id),
        )
        .where(vis_clause)
        .group_by("seg")
    )
    seg_counts = (await db.execute(seg_stmt)).all()
    customer_segments = []
    for row in seg_counts:
        seg_name = row[0]
        cnt = row[1]
        # Sum spend this month for this segment
        seg_spend_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
            Transaction.user_id.in_(
                select(User.id).where(vis_clause, func.coalesce(User.segment, "general") == seg_name)
            ),
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
            Transaction.txn_date >= first_of_month,
        )
        seg_spend = (await db.execute(seg_spend_stmt)).scalar() or 0
        customer_segments.append(
            CustomerSegmentSummary(
                segment=seg_name.title(),
                customer_count=cnt,
                total_spend_minor=int(seg_spend),
            )
        )

    # 4. Top Merchants (last 30 days)
    merchant_stmt = (
        select(
            Transaction.merchant_normalized,
            func.coalesce(func.sum(Transaction.amount_minor), 0).label("merch_spend"),
            func.count(Transaction.id).label("cnt"),
        )
        .where(
            Transaction.user_id.in_(vis_cust_ids),
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
            Transaction.txn_date >= (now - timedelta(days=30)),
            Transaction.merchant_normalized.is_not(None),
        )
        .group_by(Transaction.merchant_normalized)
        .order_by(desc("merch_spend"))
        .limit(8)
    )
    merchant_rows = (await db.execute(merchant_stmt)).all()
    top_merchants = [
        MerchantSummary(
            merchant=r[0] or "Unknown",
            total_spend_minor=int(r[1]),
            transaction_count=int(r[2]),
        )
        for r in merchant_rows
    ]

    return AdminAnalyticsResponse(
        spend_by_category=spend_by_cat,
        monthly_spend_trend=monthly_trend,
        customer_segments=customer_segments,
        top_merchants=top_merchants,
    )


async def list_customers(
    db: AsyncSession,
    q: Optional[str] = None,
    segment: Optional[str] = None,
    status: Optional[str] = None,
    risk_filter: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
) -> CustomerListResponse:
    vis_clause = get_visible_customer_clause()
    conditions = [vis_clause]

    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        conditions.append(or_(
            func.lower(User.name).like(term),
            func.lower(User.email).like(term),
        ))

    if segment and segment != "all":
        conditions.append(User.segment == segment.lower())

    if status and status != "all":
        if status == "active":
            conditions.append(User.is_active.is_(True))
        elif status == "inactive":
            conditions.append(User.is_active.is_(False))

    stmt = select(User).where(and_(*conditions)).order_by(User.name)
    all_users = (await db.execute(stmt)).scalars().all()

    # Pre-fetch all risk alerts so we can filter by risk flag if requested
    alerts_map: Dict[str, List[str]] = {}
    all_alerts = await get_risk_alerts(db)
    for a in all_alerts:
        alerts_map.setdefault(a.customer_id, []).append(a.alert_type)

    filtered_users = []
    now = datetime.now(timezone.utc)
    first_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    for u in all_users:
        u_flags = alerts_map.get(u.id, [])
        if risk_filter and risk_filter != "all":
            if risk_filter == "flagged" and not u_flags:
                continue
            if risk_filter == "clean" and u_flags:
                continue
        filtered_users.append((u, u_flags))

    total = len(filtered_users)
    start_idx = (page - 1) * limit
    page_users = filtered_users[start_idx : start_idx + limit]

    items: List[CustomerSummaryItem] = []
    for u, u_flags in page_users:
        # Accounts count
        acc_cnt_stmt = select(func.count(Account.id)).where(Account.user_id == u.id)
        accounts_count = (await db.execute(acc_cnt_stmt)).scalar() or 0

        # This month spend
        spend_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
            Transaction.user_id == u.id,
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
            Transaction.txn_date >= first_of_month,
        )
        this_month_spend = (await db.execute(spend_stmt)).scalar() or 0

        # Last activity
        last_act_stmt = select(func.max(Transaction.txn_date)).where(
            Transaction.user_id == u.id,
            Transaction.deleted_at.is_(None),
        )
        last_activity = (await db.execute(last_act_stmt)).scalar()

        # Prediction (lightweight estimate)
        try:
            pred = await compute_monthly_prediction(db, u.id)
            pred_spend = pred.get("predicted_total_minor", this_month_spend)
        except Exception:
            pred_spend = this_month_spend

        items.append(
            CustomerSummaryItem(
                id=u.id,
                name=u.name,
                masked_email=mask_email(u.email),
                segment=u.segment,
                accounts_count=accounts_count,
                this_month_spend_minor=int(this_month_spend),
                predicted_month_end_spend_minor=int(pred_spend),
                last_activity=last_activity,
                is_active=u.is_active,
                is_demo=u.is_demo,
                consent_type="share_with_bank" if not u.is_demo else "demo",
                risk_flags=u_flags,
            )
        )

    return CustomerListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


async def get_customer_360(
    db: AsyncSession,
    customer_id: str,
    page: int = 1,
    limit: int = 20,
) -> Customer360Response:
    customer = await get_visible_customer_or_404(db, customer_id)

    # Profile
    profile = CustomerProfile(
        id=customer.id,
        name=customer.name,
        masked_email=mask_email(customer.email),
        currency=customer.currency,
        timezone=customer.timezone,
        segment=customer.segment,
        is_active=customer.is_active,
        is_demo=customer.is_demo,
        created_at=customer.created_at,
    )

    # Accounts
    acc_stmt = select(Account).where(Account.user_id == customer.id).order_by(Account.created_at)
    acc_rows = (await db.execute(acc_stmt)).scalars().all()
    accounts: List[AccountSummary] = []
    for a in acc_rows:
        # Calculate current balance = opening + credits - debits
        creds_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
            Transaction.account_id == a.id,
            Transaction.direction == "credit",
            Transaction.deleted_at.is_(None),
        )
        debs_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
            Transaction.account_id == a.id,
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
        )
        c_val = (await db.execute(creds_stmt)).scalar() or 0
        d_val = (await db.execute(debs_stmt)).scalar() or 0
        current_bal = a.opening_balance_minor + c_val - d_val
        accounts.append(
            AccountSummary(
                id=a.id,
                name=a.name,
                type=a.type,
                masked_account_number=mask_account_number(a.last4),
                opening_balance_minor=a.opening_balance_minor,
                current_balance_minor=current_bal,
            )
        )

    # Transactions (paginated, with masked details only)
    tx_total_stmt = select(func.count(Transaction.id)).where(
        Transaction.user_id == customer.id,
        Transaction.deleted_at.is_(None),
    )
    total_tx = (await db.execute(tx_total_stmt)).scalar() or 0

    tx_stmt = (
        select(Transaction, Category)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == customer.id,
            Transaction.deleted_at.is_(None),
        )
        .order_by(desc(Transaction.txn_date))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    tx_rows = (await db.execute(tx_stmt)).all()
    transactions = [
        CustomerTransactionItem(
            id=tx.id,
            txn_date=tx.txn_date,
            merchant_normalized=tx.merchant_normalized or "Unknown",
            amount_minor=tx.amount_minor,
            direction=tx.direction,
            currency=tx.currency,
            category_name=cat.name if cat else "Uncategorized",
            category_icon=cat.icon if cat else "Tag",
            category_color=cat.color if cat else "#6B7280",
            category_source=tx.category_source or "rule",
            category_confidence=float(tx.category_confidence or 1.0),
            source=tx.source,
            needs_review=tx.needs_review,
        )
        for tx, cat in tx_rows
    ]

    now = datetime.now(timezone.utc)
    first_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # Category breakdown (current month)
    cat_stmt = (
        select(
            Category.id,
            Category.name,
            Category.icon,
            Category.color,
            func.coalesce(func.sum(Transaction.amount_minor), 0).label("cat_spend"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == customer.id,
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
            Transaction.txn_date >= first_of_month,
        )
        .group_by(Category.id, Category.name, Category.icon, Category.color)
        .order_by(desc("cat_spend"))
    )
    cat_rows = (await db.execute(cat_stmt)).all()
    tot_cat_spend = sum(r[4] for r in cat_rows) or 1
    category_breakdown = [
        CategorySpendSummary(
            category_id=r[0],
            category_name=r[1] or "Uncategorized",
            icon=r[2] or "Tag",
            color=r[3] or "#3B82F6",
            total_spend_minor=int(r[4]),
            percentage=round(r[4] / tot_cat_spend * 100.0, 1),
        )
        for r in cat_rows
    ]

    # Monthly Trend (last 6 months)
    monthly_trend: List[MonthlySpendTrend] = []
    for i in range(5, -1, -1):
        ty = now.year
        tm = now.month - i
        while tm <= 0:
            tm += 12
            ty -= 1
        m_str = f"{ty:04d}-{tm:02d}"
        s_dt = datetime(ty, tm, 1, tzinfo=timezone.utc)
        e_dt = datetime(ty + 1, 1, 1, tzinfo=timezone.utc) if tm == 12 else datetime(ty, tm + 1, 1, tzinfo=timezone.utc)

        m_stmt = select(
            func.coalesce(func.sum(Transaction.amount_minor), 0),
            func.count(Transaction.id),
        ).where(
            Transaction.user_id == customer.id,
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
            Transaction.txn_date >= s_dt,
            Transaction.txn_date < e_dt,
        )
        m_res = (await db.execute(m_stmt)).one()
        monthly_trend.append(
            MonthlySpendTrend(
                month=m_str,
                spend_minor=int(m_res[0]),
                transactions_count=int(m_res[1]),
            )
        )

    # Budgets vs Actual
    cur_month_str = f"{now.year:04d}-{now.month:02d}"
    b_stmt = (
        select(Budget, Category)
        .join(Category, Budget.category_id == Category.id)
        .where(
            Budget.user_id == customer.id,
            Budget.month == cur_month_str,
        )
    )
    b_rows = (await db.execute(b_stmt)).all()
    budgets: List[BudgetVsActual] = []
    for b, cat in b_rows:
        act_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
            Transaction.user_id == customer.id,
            Transaction.category_id == cat.id,
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
            Transaction.txn_date >= first_of_month,
        )
        spent = (await db.execute(act_stmt)).scalar() or 0
        if spent > b.limit_minor:
            b_status = "exceeded"
        elif spent >= b.limit_minor * 0.85:
            b_status = "warning"
        else:
            b_status = "normal"
        budgets.append(
            BudgetVsActual(
                category_id=cat.id,
                category_name=cat.name,
                month=b.month,
                limit_minor=b.limit_minor,
                actual_spent_minor=int(spent),
                status=b_status,
            )
        )

    # Prediction
    prediction: Optional[PredictionBreakdown] = None
    try:
        p_res = await compute_monthly_prediction(db, customer.id)
        prediction = PredictionBreakdown(
            predicted_month_end_minor=p_res.get("predicted_total_minor", 0),
            spent_so_far_minor=p_res.get("spent_so_far_minor", 0),
            days_elapsed=p_res.get("days_elapsed", 1),
            days_in_month=p_res.get("days_in_month", 30),
            confidence_level=p_res.get("confidence_level", "medium"),
            historical_baseline_minor=p_res.get("baseline_wma_minor", 0),
            run_rate_projection_minor=p_res.get("run_rate_projection_minor", 0),
        )
    except Exception:
        pass

    # Consents
    cons_stmt = select(Consent).where(Consent.user_id == customer.id).order_by(Consent.created_at)
    cons_rows = (await db.execute(cons_stmt)).scalars().all()
    consent_status = [
        ConsentSummary(
            id=c.id,
            consent_type=c.consent_type,
            granted=c.granted,
            granted_at=c.granted_at,
            revoked_at=c.revoked_at,
            policy_version=c.policy_version,
        )
        for c in cons_rows
    ]

    # Imports
    imp_stmt = (
        select(Import)
        .where(Import.user_id == customer.id)
        .order_by(desc(Import.created_at))
        .limit(10)
    )
    imp_rows = (await db.execute(imp_stmt)).scalars().all()
    imports = [
        ImportSummary(
            id=im.id,
            source_type=im.source_type,
            status=im.status,
            total_rows=im.total_rows,
            parsed_rows=im.parsed_rows,
            failed_rows=im.failed_rows,
            error_summary=str(im.error_report[0]) if im.error_report and len(im.error_report) > 0 else None,
            created_at=im.created_at,
        )
        for im in imp_rows
    ]

    return Customer360Response(
        profile=profile,
        accounts=accounts,
        transactions=transactions,
        total_transactions=total_tx,
        category_breakdown=category_breakdown,
        monthly_trend=monthly_trend,
        budgets=budgets,
        prediction=prediction,
        consent_status=consent_status,
        imports=imports,
    )


async def get_risk_alerts(db: AsyncSession) -> List[RiskAlert]:
    vis_clause = get_visible_customer_clause()
    users = (await db.execute(select(User).where(vis_clause))).scalars().all()

    alerts: List[RiskAlert] = []
    now = datetime.now(timezone.utc)
    first_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # 3-month window for baseline
    three_months_ago = first_of_month - timedelta(days=90)

    for u in users:
        masked = mask_email(u.email)

        # 1. Spend this month & credits this month
        debs_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
            Transaction.user_id == u.id,
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
            Transaction.txn_date >= first_of_month,
        )
        creds_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
            Transaction.user_id == u.id,
            Transaction.direction == "credit",
            Transaction.deleted_at.is_(None),
            Transaction.txn_date >= first_of_month,
        )
        cur_debits = (await db.execute(debs_stmt)).scalar() or 0
        cur_credits = (await db.execute(creds_stmt)).scalar() or 0

        # Historical monthly average
        hist_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
            Transaction.user_id == u.id,
            Transaction.direction == "debit",
            Transaction.deleted_at.is_(None),
            Transaction.txn_date >= three_months_ago,
            Transaction.txn_date < first_of_month,
        )
        hist_spend_total = (await db.execute(hist_stmt)).scalar() or 0
        hist_monthly_avg = int(hist_spend_total / 3) if hist_spend_total > 0 else 0

        # Check 1: Spending spike (> 1.5x of 3-month average)
        if hist_monthly_avg > 0 and cur_debits > int(1.5 * hist_monthly_avg) and cur_debits > 500000:
            ratio = round(cur_debits / hist_monthly_avg, 1)
            alerts.append(
                RiskAlert(
                    id=f"{u.id}-spending-spike",
                    customer_id=u.id,
                    customer_name=u.name,
                    masked_email=masked,
                    segment=u.segment,
                    alert_type="spending_spike",
                    severity="high",
                    reason=f"Current spend of ₹{cur_debits / 100:,.0f} is {ratio}x the 3-month baseline average (₹{hist_monthly_avg / 100:,.0f}).",
                    detected_at=now,
                )
            )

        # Check 2: Budget overshoot
        cur_m_str = f"{now.year:04d}-{now.month:02d}"
        b_stmt = (
            select(Budget, Category)
            .join(Category, Budget.category_id == Category.id)
            .where(
                Budget.user_id == u.id,
                Budget.month == cur_m_str,
            )
        )
        budgets_res = (await db.execute(b_stmt)).all()
        for b, cat in budgets_res:
            cat_spend_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
                Transaction.user_id == u.id,
                Transaction.category_id == cat.id,
                Transaction.direction == "debit",
                Transaction.deleted_at.is_(None),
                Transaction.txn_date >= first_of_month,
            )
            cat_spend = (await db.execute(cat_spend_stmt)).scalar() or 0
            if cat_spend > b.limit_minor:
                overshoot = cat_spend - b.limit_minor
                alerts.append(
                    RiskAlert(
                        id=f"{u.id}-budget-overshoot-{b.id}",
                        customer_id=u.id,
                        customer_name=u.name,
                        masked_email=masked,
                        segment=u.segment,
                        alert_type="budget_overshoot",
                        severity="high",
                        reason=f"Exceeded '{cat.name}' monthly budget by ₹{overshoot / 100:,.0f} (Budget: ₹{b.limit_minor / 100:,.0f}, Spent: ₹{cat_spend / 100:,.0f}).",
                        detected_at=now,
                    )
                )

        # Check 3: Spend greater than income this month
        if cur_debits > cur_credits and cur_debits > 200000 and cur_credits > 0:
            diff = cur_debits - cur_credits
            alerts.append(
                RiskAlert(
                    id=f"{u.id}-spend-exceeds-income",
                    customer_id=u.id,
                    customer_name=u.name,
                    masked_email=masked,
                    segment=u.segment,
                    alert_type="spend_exceeds_income",
                    severity="medium",
                    reason=f"Monthly spend (₹{cur_debits / 100:,.0f}) exceeds incoming credits (₹{cur_credits / 100:,.0f}) by ₹{diff / 100:,.0f}.",
                    detected_at=now,
                )
            )

        # Check 4: Sudden spike in a single category (> 50% of monthly spend)
        if cur_debits > 100000:
            top_cat_stmt = (
                select(
                    Category.name,
                    func.sum(Transaction.amount_minor).label("cat_amt"),
                )
                .join(Category, Transaction.category_id == Category.id)
                .where(
                    Transaction.user_id == u.id,
                    Transaction.direction == "debit",
                    Transaction.deleted_at.is_(None),
                    Transaction.txn_date >= first_of_month,
                )
                .group_by(Category.name)
                .order_by(desc("cat_amt"))
                .limit(1)
            )
            top_cat_row = (await db.execute(top_cat_stmt)).first()
            if top_cat_row and top_cat_row[1] > (cur_debits * 0.55):
                cat_pct = round((top_cat_row[1] / cur_debits) * 100, 1)
                alerts.append(
                    RiskAlert(
                        id=f"{u.id}-category-spike-{top_cat_row[0]}",
                        customer_id=u.id,
                        customer_name=u.name,
                        masked_email=masked,
                        segment=u.segment,
                        alert_type="category_spike",
                        severity="medium",
                        reason=f"Single category '{top_cat_row[0]}' accounts for {cat_pct}% of total monthly spend (₹{top_cat_row[1] / 100:,.0f}).",
                        detected_at=now,
                    )
                )

    return alerts


async def get_admin_imports(
    db: AsyncSession,
    status_filter: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> Tuple[List[AdminImportItem], int]:
    vis_clause = get_visible_customer_clause()

    conditions = [
        Import.user_id.in_(select(User.id).where(vis_clause)),
    ]
    if status_filter and status_filter != "all":
        conditions.append(Import.status == status_filter.lower())

    tot_stmt = select(func.count(Import.id)).where(and_(*conditions))
    total = (await db.execute(tot_stmt)).scalar() or 0

    stmt = (
        select(Import, User)
        .join(User, Import.user_id == User.id)
        .where(and_(*conditions))
        .order_by(desc(Import.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    items = [
        AdminImportItem(
            id=im.id,
            customer_id=u.id,
            customer_name=u.name,
            masked_email=mask_email(u.email),
            source_type=im.source_type,
            status=im.status,
            total_rows=im.total_rows,
            parsed_rows=im.parsed_rows,
            failed_rows=im.failed_rows,
            error_summary=str(im.error_report[0]) if im.error_report and len(im.error_report) > 0 else None,
            created_at=im.created_at,
        )
        for im, u in rows
    ]
    return items, total


async def get_admin_audit_logs(
    db: AsyncSession,
    action_filter: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> Tuple[List[AdminAuditLogItem], int]:
    conditions = [
        or_(
            AuditLog.action.like("ADMIN_%"),
            AuditLog.action.like("admin_%"),
        )
    ]
    if action_filter and action_filter != "all":
        conditions.append(AuditLog.action == action_filter)

    tot_stmt = select(func.count(AuditLog.id)).where(and_(*conditions))
    total = (await db.execute(tot_stmt)).scalar() or 0

    stmt = (
        select(AuditLog, User)
        .join(User, AuditLog.user_id == User.id)
        .where(and_(*conditions))
        .order_by(desc(AuditLog.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    items: List[AdminAuditLogItem] = []
    for audit, admin_user in rows:
        cust_name = None
        if audit.entity_id:
            c_res = await db.execute(select(User.name).where(User.id == audit.entity_id))
            cust_name = c_res.scalar_one_or_none()

        items.append(
            AdminAuditLogItem(
                id=audit.id,
                admin_id=admin_user.id,
                admin_email=mask_email(admin_user.email),
                action=audit.action,
                customer_id=audit.entity_id,
                customer_name=cust_name,
                timestamp=audit.created_at,
                ip_address=audit.meta_data.get("ip") if audit.meta_data else None,
                details=audit.meta_data,
            )
        )

    return items, total


async def generate_customers_csv(db: AsyncSession) -> str:
    res = await list_customers(db, page=1, limit=1000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Customer ID",
        "Name",
        "Masked Email",
        "Segment",
        "Accounts Count",
        "Status",
        "Type",
        "This Month Spend (INR)",
        "Predicted Month End Spend (INR)",
        "Last Activity",
        "Risk Flags",
    ])
    for item in res.items:
        writer.writerow([
            item.id,
            item.name,
            item.masked_email,
            item.segment or "General",
            item.accounts_count,
            "Active" if item.is_active else "Inactive",
            "Demo" if item.is_demo else "Consented",
            f"{item.this_month_spend_minor / 100:.2f}",
            f"{item.predicted_month_end_spend_minor / 100:.2f}",
            item.last_activity.isoformat() if item.last_activity else "No activity",
            "; ".join(item.risk_flags) if item.risk_flags else "None",
        ])
    return output.getvalue()


async def update_customer_status(
    db: AsyncSession,
    customer_id: str,
    is_active: bool,
    admin_id: str,
    client_ip: Optional[str] = None,
) -> User:
    customer = await get_visible_customer_or_404(db, customer_id)
    old_status = customer.is_active
    customer.is_active = is_active
    await db.commit()
    await db.refresh(customer)

    await log_admin_audit(
        db,
        admin_id=admin_id,
        action="ADMIN_UPDATE_CUSTOMER_STATUS",
        entity="customer",
        entity_id=customer.id,
        client_ip=client_ip,
        meta_data={
            "customer_id": customer.id,
            "previous_status": old_status,
            "new_status": is_active,
        },
    )

    return customer

