import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, or_, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_owned_or_404
from app.models.models import Transaction, Import, Category, Account, AuditLog, MerchantRule
from app.services.sms_parser import parse_sms_batch, compute_dedupe_hash
from app.services.statement_parser import parse_csv_statement, parse_pdf_statement
from app.services import prediction_service, categorization_service
from app.core.errors import NotFoundException, BadRequestException


async def get_or_create_category_map(db: AsyncSession, user_id: str) -> Dict[str, str]:
    stmt = select(Category).where(
        or_(Category.user_id.is_(None), Category.user_id == user_id)
    )
    res = await db.execute(stmt)
    categories = res.scalars().all()
    # Name -> id mapping (case insensitive)
    cat_map = {c.name.lower(): c.id for c in categories}
    return cat_map


async def process_sms_import(
    db: AsyncSession,
    user_id: str,
    account_id: str,
    raw_text: str,
) -> Dict[str, Any]:
    # Verify account belongs to user (404 if not found or cross-user)
    await get_owned_or_404(db, Account, account_id, user_id)

    parsed_txns, error_items = parse_sms_batch(raw_text, account_id)
    total_messages = len(parsed_txns) + len(error_items)

    cat_map = await get_or_create_category_map(db, user_id)
    uncategorized_id = cat_map.get("uncategorized")

    # Create Import Record
    import_id = str(uuid.uuid4())
    import_rec = Import(
        id=import_id,
        user_id=user_id,
        source_type="sms",
        file_name="Raw SMS Text",
        status="processing",
        total_rows=total_messages,
        parsed_rows=0,
        failed_rows=len(error_items),
        error_report=error_items,
    )
    db.add(import_rec)
    await db.flush()

    inserted_count = 0
    duplicate_count = 0

    for item in parsed_txns:
        # Check if dedupe_hash already exists for user
        dedupe_hash = item["dedupe_hash"]
        dup_stmt = select(Transaction.id).where(
            and_(Transaction.user_id == user_id, Transaction.dedupe_hash == dedupe_hash)
        )
        dup_res = await db.execute(dup_stmt)
        if dup_res.scalar_one_or_none():
            duplicate_count += 1
            continue

        # Use 3-step categorization engine (Rules -> Pluggable Model -> User)
        cat_res = await categorization_service.categorize_transaction_data(
            db=db,
            user_id=user_id,
            merchant=item["merchant_normalized"] or item["merchant_raw"],
            description=item["description"],
            amount_minor=item["amount_minor"],
            direction=item["direction"],
        )

        txn = Transaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            account_id=account_id,
            amount_minor=item["amount_minor"],
            direction=item["direction"],
            currency="INR",
            txn_date=item["txn_date"],
            merchant_raw=item["merchant_raw"],
            merchant_normalized=item["merchant_normalized"],
            description=item["description"],
            category_id=cat_res.category_id,
            category_source=cat_res.category_source,
            category_confidence=cat_res.category_confidence,
            needs_review=cat_res.needs_review,
            source="sms",
            import_id=import_id,
            dedupe_hash=dedupe_hash,
        )
        db.add(txn)
        inserted_count += 1

    import_rec.parsed_rows = inserted_count
    import_rec.status = "done"

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action="SMS_IMPORT_PROCESSED",
        entity="import",
        entity_id=import_id,
        meta_data={
            "total": total_messages,
            "inserted": inserted_count,
            "duplicates": duplicate_count,
            "failed": len(error_items),
        },
    )
    db.add(audit)

    await db.commit()
    await prediction_service.trigger_prediction_update(db, user_id)

    return {
        "import_id": import_id,
        "total_messages": total_messages,
        "inserted_transactions": inserted_count,
        "duplicates_skipped": duplicate_count,
        "unparsed_count": len(error_items),
        "status": "done",
    }


async def process_file_import(
    db: AsyncSession,
    user_id: str,
    account_id: str,
    file_bytes: bytes,
    file_name: str,
    source_type: str,
) -> Dict[str, Any]:
    # Verify account belongs to user (404 if not found or cross-user)
    await get_owned_or_404(db, Account, account_id, user_id)

    if source_type == "csv":
        parsed_txns, error_items = parse_csv_statement(file_bytes, account_id)
    elif source_type == "pdf":
        parsed_txns, error_items = parse_pdf_statement(file_bytes, account_id)
    else:
        raise BadRequestException(f"Unsupported statement source type: {source_type}")

    total_rows = len(parsed_txns) + len(error_items)
    cat_map = await get_or_create_category_map(db, user_id)
    uncategorized_id = cat_map.get("uncategorized")

    # Create Import Record
    import_id = str(uuid.uuid4())
    import_rec = Import(
        id=import_id,
        user_id=user_id,
        source_type=source_type,
        file_name=file_name,
        status="processing",
        total_rows=total_rows,
        parsed_rows=0,
        failed_rows=len(error_items),
        error_report=error_items,
    )
    db.add(import_rec)
    await db.flush()

    inserted_count = 0
    duplicate_count = 0

    for item in parsed_txns:
        dedupe_hash = item["dedupe_hash"]
        dup_stmt = select(Transaction.id).where(
            and_(Transaction.user_id == user_id, Transaction.dedupe_hash == dedupe_hash)
        )
        dup_res = await db.execute(dup_stmt)
        if dup_res.scalar_one_or_none():
            duplicate_count += 1
            continue

        # Use 3-step categorization engine (Rules -> Pluggable Model -> User)
        cat_res = await categorization_service.categorize_transaction_data(
            db=db,
            user_id=user_id,
            merchant=item["merchant_normalized"] or item["merchant_raw"],
            description=item["description"],
            amount_minor=item["amount_minor"],
            direction=item["direction"],
        )

        txn = Transaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            account_id=account_id,
            amount_minor=item["amount_minor"],
            direction=item["direction"],
            currency="INR",
            txn_date=item["txn_date"],
            merchant_raw=item["merchant_raw"],
            merchant_normalized=item["merchant_normalized"],
            description=item["description"],
            category_id=cat_res.category_id,
            category_source=cat_res.category_source,
            category_confidence=cat_res.category_confidence,
            needs_review=cat_res.needs_review,
            source=source_type,
            import_id=import_id,
            dedupe_hash=dedupe_hash,
        )
        db.add(txn)
        inserted_count += 1

    import_rec.parsed_rows = inserted_count
    import_rec.status = "done"

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action=f"{source_type.upper()}_IMPORT_PROCESSED",
        entity="import",
        entity_id=import_id,
        meta_data={
            "total": total_rows,
            "inserted": inserted_count,
            "duplicates": duplicate_count,
            "failed": len(error_items),
        },
    )
    db.add(audit)
    await db.commit()
    await prediction_service.trigger_prediction_update(db, user_id)

    return {
        "import_id": import_id,
        "total_rows": total_rows,
        "inserted_transactions": inserted_count,
        "duplicates_skipped": duplicate_count,
        "failed_rows": len(error_items),
        "status": "done",
    }


async def list_transactions(
    db: AsyncSession,
    user_id: str,
    account_id: Optional[str] = None,
    category_id: Optional[str] = None,
    direction: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_amount_minor: Optional[int] = None,
    max_amount_minor: Optional[int] = None,
    needs_review: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    if account_id:
        await get_owned_or_404(db, Account, account_id, user_id)
    if category_id:
        await get_owned_or_404(db, Category, category_id, user_id, allow_system_read=True)

    base_conditions = [Transaction.user_id == user_id, Transaction.deleted_at.is_(None)]

    if account_id:
        base_conditions.append(Transaction.account_id == account_id)
    if category_id:
        base_conditions.append(Transaction.category_id == category_id)
    if direction:
        base_conditions.append(Transaction.direction == direction)
    if start_date:
        base_conditions.append(Transaction.txn_date >= start_date)
    if end_date:
        base_conditions.append(Transaction.txn_date <= end_date)
    if min_amount_minor is not None:
        base_conditions.append(Transaction.amount_minor >= min_amount_minor)
    if max_amount_minor is not None:
        base_conditions.append(Transaction.amount_minor <= max_amount_minor)
    if needs_review is not None:
        base_conditions.append(Transaction.needs_review == needs_review)
    if search:
        term = f"%{search.strip()}%"
        base_conditions.append(
            or_(
                Transaction.merchant_normalized.ilike(term),
                Transaction.merchant_raw.ilike(term),
                Transaction.description.ilike(term),
            )
        )

    # Count total
    count_stmt = select(func.count(Transaction.id)).where(and_(*base_conditions))
    total = (await db.execute(count_stmt)).scalar_one()

    # Query rows joined with Account and Category
    stmt = (
        select(
            Transaction,
            Account.name.label("account_name"),
            Category.name.label("category_name"),
            Category.color.label("category_color"),
            Category.icon.label("category_icon"),
        )
        .outerjoin(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(and_(*base_conditions))
        .order_by(desc(Transaction.txn_date), desc(Transaction.created_at))
        .limit(limit)
        .offset(offset)
    )

    res = await db.execute(stmt)
    rows = res.all()

    txns = []
    for txn, acc_name, cat_name, cat_color, cat_icon in rows:
        cat_info = None
        if txn.category_id:
            cat_info = {
                "id": txn.category_id,
                "name": cat_name or "Uncategorized",
                "icon": cat_icon or "tag",
                "color": cat_color or "#6b7280",
            }

        txns.append({
            "id": txn.id,
            "account_id": txn.account_id,
            "account_name": acc_name or "Unknown Account",
            "amount_minor": txn.amount_minor,
            "direction": txn.direction,
            "currency": txn.currency or "INR",
            "txn_date": txn.txn_date,
            "merchant": txn.merchant_normalized or txn.merchant_raw or "Unknown Merchant",
            "merchant_raw": txn.merchant_raw,
            "merchant_normalized": txn.merchant_normalized,
            "description": txn.description,
            "category": cat_info,
            "category_id": txn.category_id,
            "category_name": cat_name or "Uncategorized",
            "category_color": cat_color or "#6b7280",
            "category_icon": cat_icon or "tag",
            "category_source": txn.category_source or "rule",
            "category_confidence": float(txn.category_confidence) if txn.category_confidence is not None else 1.0,
            "needs_review": bool(txn.needs_review),
            "source": txn.source,
            "created_at": txn.created_at,
        })

    return txns, total


async def get_transaction_by_id(db: AsyncSession, user_id: str, txn_id: str) -> Transaction:
    txn = await get_owned_or_404(db, Transaction, txn_id, user_id)
    if txn.deleted_at is not None:
        raise NotFoundException("Transaction not found")
    return txn


async def get_transaction_detail(db: AsyncSession, user_id: str, txn_id: str) -> Dict[str, Any]:
    txn = await get_transaction_by_id(db, user_id, txn_id)

    acc_name = "Unknown Account"
    if txn.account_id:
        acc = await db.get(Account, txn.account_id)
        if acc:
            acc_name = acc.name

    cat_info = None
    if txn.category_id:
        cat = await db.get(Category, txn.category_id)
        if cat:
            cat_info = {
                "id": cat.id,
                "name": cat.name,
                "icon": cat.icon or "tag",
                "color": cat.color or "#6b7280",
            }

    return {
        "id": txn.id,
        "user_id": txn.user_id,
        "account_id": txn.account_id,
        "account_name": acc_name,
        "amount_minor": txn.amount_minor,
        "direction": txn.direction,
        "currency": txn.currency or "INR",
        "txn_date": txn.txn_date,
        "merchant": txn.merchant_normalized or txn.merchant_raw or "Unknown Merchant",
        "merchant_raw": txn.merchant_raw,
        "merchant_normalized": txn.merchant_normalized,
        "description": txn.description,
        "category": cat_info,
        "category_id": txn.category_id,
        "category_source": txn.category_source,
        "category_confidence": float(txn.category_confidence) if txn.category_confidence else 1.0,
        "needs_review": bool(txn.needs_review),
        "source": txn.source,
        "import_id": txn.import_id,
        "dedupe_hash": txn.dedupe_hash,
        "created_at": txn.created_at,
        "updated_at": txn.updated_at,
    }


async def get_transactions_summary(
    db: AsyncSession,
    user_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    base_conditions = [Transaction.user_id == user_id, Transaction.deleted_at.is_(None)]
    if account_id:
        await get_owned_or_404(db, Account, account_id, user_id)
        base_conditions.append(Transaction.account_id == account_id)
    if start_date:
        base_conditions.append(Transaction.txn_date >= start_date)
    if end_date:
        base_conditions.append(Transaction.txn_date <= end_date)

    # 1. Total Spent (Debits)
    spent_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
        and_(*base_conditions, Transaction.direction == "debit")
    )
    total_spent_minor = (await db.execute(spent_stmt)).scalar_one()

    # 2. Total Income (Credits)
    income_stmt = select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
        and_(*base_conditions, Transaction.direction == "credit")
    )
    total_income_minor = (await db.execute(income_stmt)).scalar_one()

    # 3. Transaction Count
    count_stmt = select(func.count(Transaction.id)).where(and_(*base_conditions))
    transaction_count = (await db.execute(count_stmt)).scalar_one()

    # 4. Top Categories for Debits
    cat_stmt = (
        select(
            Category.id,
            Category.name,
            Category.icon,
            Category.color,
            func.sum(Transaction.amount_minor).label("cat_total"),
            func.count(Transaction.id).label("cat_count"),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .where(and_(*base_conditions, Transaction.direction == "debit"))
        .group_by(Category.id, Category.name, Category.icon, Category.color)
        .order_by(func.sum(Transaction.amount_minor).desc())
        .limit(5)
    )
    cat_res = await db.execute(cat_stmt)
    cat_rows = cat_res.all()

    top_categories = []
    for cid, cname, cicon, ccolor, ctotal, ccount in cat_rows:
        pct = round((ctotal / total_spent_minor) * 100, 1) if total_spent_minor > 0 else 0.0
        top_categories.append({
            "category_id": cid,
            "name": cname or "Uncategorized",
            "icon": cicon or "tag",
            "color": ccolor or "#6b7280",
            "total_minor": ctotal,
            "count": ccount,
            "percentage": pct,
        })

    return {
        "total_spent_minor": total_spent_minor,
        "total_income_minor": total_income_minor,
        "transaction_count": transaction_count,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "top_categories": top_categories,
    }


async def update_transaction(
    db: AsyncSession,
    user_id: str,
    txn_id: str,
    merchant: Optional[str] = None,
    category_id: Optional[str] = None,
    description: Optional[str] = None,
    amount_minor: Optional[int] = None,
    direction: Optional[str] = None,
    txn_date: Optional[datetime] = None,
    create_rule: bool = False,
) -> Transaction:
    txn = await get_transaction_by_id(db, user_id, txn_id)
    if category_id is not None:
        if category_id != "":
            await get_owned_or_404(db, Category, category_id, user_id, allow_system_read=True)
            txn.category_id = category_id
        else:
            txn.category_id = None
        # User manual correction wins!
        txn.category_source = "user"
        txn.category_confidence = 1.0
        txn.needs_review = False

        # If user selected "Always use this category for this merchant", persist a user-scoped rule
        if create_rule and txn.category_id:
            rule_pattern = (txn.merchant_normalized or txn.merchant_raw or merchant or "").strip()
            if rule_pattern:
                rule_stmt = select(MerchantRule).where(
                    and_(
                        MerchantRule.user_id == user_id,
                        MerchantRule.pattern.ilike(rule_pattern),
                    )
                )
                existing_rule = (await db.execute(rule_stmt)).scalar_one_or_none()
                if existing_rule:
                    existing_rule.category_id = txn.category_id
                    existing_rule.priority = 10
                else:
                    new_rule = MerchantRule(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        pattern=rule_pattern,
                        category_id=txn.category_id,
                        priority=10,
                    )
                    db.add(new_rule)

                audit = AuditLog(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    action="MERCHANT_RULE_CREATED_FROM_CORRECTION",
                    entity="merchant_rule",
                    meta_data={
                        "pattern": rule_pattern,
                        "category_id": txn.category_id,
                        "transaction_id": txn.id,
                    },
                )
                db.add(audit)
    if merchant is not None:
        txn.merchant_raw = merchant
        txn.merchant_normalized = merchant.strip().title()
    if description is not None:
        txn.description = description
    if amount_minor is not None:
        txn.amount_minor = amount_minor
    if direction is not None:
        txn.direction = direction
    if txn_date is not None:
        txn.txn_date = txn_date

    await db.commit()
    await db.refresh(txn)
    await prediction_service.trigger_prediction_update(db, user_id)
    return txn


async def create_manual_transaction(
    db: AsyncSession,
    user_id: str,
    account_id: str,
    amount_minor: int,
    direction: str,
    merchant: str,
    category_id: Optional[str] = None,
    txn_date: Optional[datetime] = None,
    description: Optional[str] = None,
) -> Transaction:
    # Verify account ownership (returns 404 if not found or cross-user)
    await get_owned_or_404(db, Account, account_id, user_id)

    # Verify category ownership if provided (returns 404 if cross-user)
    if category_id:
        await get_owned_or_404(db, Category, category_id, user_id, allow_system_read=True)

    if amount_minor <= 0:
        raise BadRequestException("Amount must be greater than zero")

    date_obj = txn_date or datetime.now(timezone.utc)
    dedupe_hash = compute_dedupe_hash(
        account_id,
        date_obj.strftime("%Y-%m-%d"),
        amount_minor,
        direction,
        merchant,
    )

    # Check dedupe
    dup_stmt = select(Transaction).where(
        and_(Transaction.user_id == user_id, Transaction.dedupe_hash == dedupe_hash)
    )
    if (await db.execute(dup_stmt)).scalar_one_or_none():
        raise BadRequestException("A duplicate transaction with the same details already exists")

    txn = Transaction(
        id=str(uuid.uuid4()),
        user_id=user_id,
        account_id=account_id,
        amount_minor=amount_minor,
        direction=direction,
        currency="INR",
        txn_date=date_obj,
        merchant_raw=merchant,
        merchant_normalized=merchant.strip().title(),
        description=description or f"Manual: {merchant}",
        category_id=category_id,
        category_source="user",
        category_confidence=1.0,
        source="manual",
        dedupe_hash=dedupe_hash,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    await prediction_service.trigger_prediction_update(db, user_id)
    return txn


async def soft_delete_transaction(db: AsyncSession, user_id: str, txn_id: str) -> None:
    txn = await get_owned_or_404(db, Transaction, txn_id, user_id)
    if txn.deleted_at is not None:
        raise NotFoundException("Transaction not found")

    txn.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await prediction_service.trigger_prediction_update(db, user_id)

