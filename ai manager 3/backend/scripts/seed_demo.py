#!/usr/bin/env python3
"""
seed_demo.py - Seed realistic demo data for FinTrack AI Manager

Creates:
- 1 Admin user (admin@demo.com)
- 5 Diverse Demo Customers with 6 months of historical transactions:
  1. Student (Aarav Sharma - student@demo.com)
  2. Working Professional (Priya Nair - professional@demo.com)
  3. Small Business Owner (Rajesh Gupta - business@demo.com)
  4. Freelancer (Ananya Iyer - freelancer@demo.com)
  5. Family Household (Vikram Deshmukh - family@demo.com)

Idempotent: Safe to re-run.
Safety: Refuses to run if ENVIRONMENT=production unless --force is passed.
"""

import asyncio
import hashlib
import os
import random
import sys
import uuid
from datetime import datetime, timezone, timedelta

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, func, and_
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine, Base
from app.db.seed import seed_default_categories
from app.models.models import User, Account, Transaction, Category, Budget, Forecast, Consent, Import


ADMIN_EMAIL = "admin@demo.com"
ADMIN_PASSWORD = os.environ.get("DEMO_ADMIN_PASSWORD", "AdminDemo@123!")
CUSTOMER_PASSWORD = os.environ.get("DEMO_CUSTOMER_PASSWORD", "Customer@123!")

DEMO_PERSONAS = [
    {
        "email": "student@demo.com",
        "name": "Aarav Sharma",
        "segment": "student",
        "account_types": [("Student Campus Savings", "savings", "4412", 1500000)],
        "monthly_pocket_money_minor": 1500000,  # ₹15,000 / month
        "has_laptop_spike": True,
    },
    {
        "email": "professional@demo.com",
        "name": "Priya Nair",
        "segment": "professional",
        "account_types": [
            ("Salary Account - HDFC", "savings", "9821", 8500000),
            ("Millennia Credit Card", "credit_card", "3104", 0),
        ],
        "monthly_salary_minor": 12000000,  # ₹1,20,000 / month
        "has_dining_overshoot": True,
    },
    {
        "email": "business@demo.com",
        "name": "Rajesh Gupta",
        "segment": "business",
        "account_types": [
            ("Current Account - ICICI", "current", "7719", 25000000),
            ("Business UPI Wallet", "wallet", "1200", 2000000),
        ],
        "monthly_revenue_minor": 35000000,  # ₹3,50,000 / month
    },
    {
        "email": "freelancer@demo.com",
        "name": "Ananya Iyer",
        "segment": "freelancer",
        "account_types": [
            ("Freelance Primary - Axis", "savings", "6530", 4000000),
        ],
        "has_deficit_anomaly": True,
    },
    {
        "email": "family@demo.com",
        "name": "Vikram Deshmukh",
        "segment": "family",
        "account_types": [
            ("Family Joint Account - SBI", "savings", "5012", 12000000),
            ("Household Credit Card", "credit_card", "8841", 0),
        ],
        "monthly_salary_minor": 18000000,  # ₹1,80,000 / month
        "has_health_spike": True,
    },
]


def gen_dedupe_hash(user_id: str, date_str: str, amount: int, merchant: str) -> str:
    seed_str = f"{user_id}:{date_str}:{amount}:{merchant}"
    return hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:32]


async def seed_demo():
    # 1. Environment Safety Check
    if getattr(settings, "ENVIRONMENT", "").lower() == "production" and "--force" not in sys.argv:
        print("\n[ERROR] Refusing to run seed_demo in PRODUCTION environment without --force flag!")
        sys.exit(1)

    print("==================================================")
    print("   FinTrack AI Manager - Demo Data Seed Script    ")
    print("==================================================")

    async with AsyncSessionLocal() as session:
        # Seed categories first
        await seed_default_categories(session)

        # Cache category map
        cat_res = await session.execute(select(Category).where(Category.user_id.is_(None)))
        categories = {c.name: c for c in cat_res.scalars().all()}

        # 2. Seed Admin User
        admin_res = await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        admin_user = admin_res.scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                id=str(uuid.uuid4()),
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                name="Bank Staff Admin",
                role="admin",
                is_active=True,
                is_demo=False,
                segment="staff",
                currency="INR",
                timezone="Asia/Kolkata",
            )
            session.add(admin_user)
            await session.commit()
            print(f"[+] Admin created: {ADMIN_EMAIL}")
        else:
            # Ensure admin role
            admin_user.role = "admin"
            admin_user.is_active = True
            await session.commit()
            print(f"[i] Admin exists: {ADMIN_EMAIL}")

        # 3. Seed Demo Personas
        now = datetime.now(timezone.utc)
        cur_year = now.year
        cur_month = now.month

        for persona in DEMO_PERSONAS:
            email = persona["email"]
            user_res = await session.execute(select(User).where(User.email == email))
            user = user_res.scalar_one_or_none()

            if not user:
                user = User(
                    id=str(uuid.uuid4()),
                    email=email,
                    password_hash=hash_password(CUSTOMER_PASSWORD),
                    name=persona["name"],
                    role="customer",
                    is_active=True,
                    is_demo=True,
                    segment=persona["segment"],
                    phone="+919876543210",
                    phone_verified=True,
                    email_verified=True,
                    preferred_otp_channel="email",
                    alert_preferences={"new_login": True, "account_changes": True, "security_settings": True, "consent_changes": True},
                    currency="INR",
                    timezone="Asia/Kolkata",
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                print(f"[+] Created Demo Customer: {persona['name']} ({email})")
            else:
                user.is_demo = True
                user.role = "customer"
                user.segment = persona["segment"]
                user.email_verified = True
                user.phone = user.phone or "+919876543210"
                user.phone_verified = True
                user.preferred_otp_channel = user.preferred_otp_channel or "email"
                user.alert_preferences = user.alert_preferences or {"new_login": True, "account_changes": True, "security_settings": True, "consent_changes": True}
                await session.commit()
                print(f"[i] Demo Customer exists: {persona['name']} ({email})")

            # Seed Consents (active share_with_bank, sms_import, statement_upload)
            for c_type in ["share_with_bank", "sms_import", "statement_upload"]:
                c_stmt = select(Consent).where(Consent.user_id == user.id, Consent.consent_type == c_type)
                c_row = (await session.execute(c_stmt)).scalar_one_or_none()
                if not c_row:
                    consent = Consent(
                        id=str(uuid.uuid4()),
                        user_id=user.id,
                        consent_type=c_type,
                        granted=True,
                        granted_at=now - timedelta(days=180),
                        policy_version="1.0",
                    )
                    session.add(consent)
                else:
                    c_row.granted = True
                    c_row.revoked_at = None
            await session.commit()

            # Seed Accounts
            accounts_map = {}
            for acc_name, acc_type, last4, op_bal in persona["account_types"]:
                a_stmt = select(Account).where(Account.user_id == user.id, Account.name == acc_name)
                acc = (await session.execute(a_stmt)).scalar_one_or_none()
                if not acc:
                    acc = Account(
                        id=str(uuid.uuid4()),
                        user_id=user.id,
                        name=acc_name,
                        type=acc_type,
                        last4=last4,
                        opening_balance_minor=op_bal,
                    )
                    session.add(acc)
                    await session.commit()
                    await session.refresh(acc)
                accounts_map[acc_name] = acc

            primary_acc = list(accounts_map.values())[0]

            # Check if transactions already exist
            tx_cnt_stmt = select(func.count(Transaction.id)).where(Transaction.user_id == user.id)
            existing_tx_count = (await session.execute(tx_cnt_stmt)).scalar() or 0

            if existing_tx_count >= 100:
                print(f"    [-] Already has {existing_tx_count} transactions. Skipping transaction re-generation.")
            else:
                print(f"    [*] Generating 6 months of realistic transactions...")
                random.seed(persona["email"])

                # Persona spending templates
                if persona["segment"] == "student":
                    expense_templates = [
                        ("Food & Dining", "Swiggy", 18000, 45000, "rule", 1.0),
                        ("Food & Dining", "Zomato", 22000, 52000, "rule", 1.0),
                        ("Food & Dining", "Campus Canteen", 8000, 15000, "user", 1.0),
                        ("Transport", "Uber", 9000, 25000, "rule", 1.0),
                        ("Transport", "Metro SmartCard Recharge", 50000, 50000, "ml", 0.85),
                        ("Entertainment", "PVR Cinemas", 35000, 75000, "rule", 1.0),
                        ("Subscriptions", "Spotify Student", 5900, 5900, "rule", 1.0),
                        ("Subscriptions", "YouTube Premium", 12900, 12900, "rule", 1.0),
                        ("Shopping", "Amazon.in Books", 45000, 120000, "ml", 0.78),
                    ]
                elif persona["segment"] == "professional":
                    expense_templates = [
                        ("Rent", "House Rent NEFT", 2500000, 2500000, "user", 1.0),
                        ("EMI/Loans", "HDFC Car Loan EMI", 1450000, 1450000, "rule", 1.0),
                        ("Groceries", "Blinkit", 45000, 185000, "rule", 1.0),
                        ("Groceries", "BigBasket", 150000, 420000, "rule", 1.0),
                        ("Food & Dining", "Zomato", 45000, 125000, "rule", 1.0),
                        ("Food & Dining", "Starbucks Coffee", 38000, 85000, "rule", 1.0),
                        ("Fuel", "Shell Petrol Pump", 250000, 450000, "rule", 1.0),
                        ("Bills & Utilities", "Tata Power Mumbai", 280000, 420000, "rule", 1.0),
                        ("Bills & Utilities", "Airtel Fiber", 119900, 119900, "rule", 1.0),
                        ("Investments", "Zerodha Coin SIP", 1500000, 2000000, "rule", 1.0),
                        ("Shopping", "Amazon India", 85000, 350000, "ml", 0.88),
                    ]
                elif persona["segment"] == "business":
                    expense_templates = [
                        ("Bills & Utilities", "Commercial Electricity BESCOM", 1500000, 2800000, "rule", 1.0),
                        ("Shopping", "Raw Material Supplier", 4500000, 9500000, "user", 1.0),
                        ("Shopping", "Packaging Vendor Ltd", 2200000, 4800000, "ml", 0.82),
                        ("Bills & Utilities", "GST Payment Portal", 3500000, 7500000, "rule", 1.0),
                        ("Transport", "Logistics Delivery Hub", 1800000, 3200000, "ml", 0.75),
                        ("Food & Dining", "Client Lunch Cafe", 180000, 450000, "rule", 1.0),
                        ("Subscriptions", "Tally Cloud Server", 250000, 250000, "rule", 1.0),
                    ]
                elif persona["segment"] == "freelancer":
                    expense_templates = [
                        ("Rent", "WeWork HotDesk Access", 950000, 950000, "rule", 1.0),
                        ("Subscriptions", "Figma Professional", 120000, 120000, "rule", 1.0),
                        ("Subscriptions", "GitHub Copilot", 85000, 85000, "rule", 1.0),
                        ("Subscriptions", "Adobe Creative Cloud", 420000, 420000, "rule", 1.0),
                        ("Food & Dining", "Third Wave Coffee", 32000, 65000, "rule", 1.0),
                        ("Food & Dining", "Swiggy Daily", 25000, 75000, "rule", 1.0),
                        ("Shopping", "Amazon Tech Accessories", 150000, 650000, "ml", 0.8),
                        ("Bills & Utilities", "ACT Fibernet 300Mbps", 125000, 125000, "rule", 1.0),
                    ]
                else:  # family
                    expense_templates = [
                        ("Rent", "Society Maintenance & Rent", 3200000, 3200000, "user", 1.0),
                        ("Education", "Delhi Public School Fees", 1850000, 2500000, "rule", 1.0),
                        ("Groceries", "DMart Supermarket", 650000, 1450000, "rule", 1.0),
                        ("Groceries", "Nature's Basket", 250000, 580000, "rule", 1.0),
                        ("Health", "Apollo Pharmacy Medicines", 120000, 380000, "rule", 1.0),
                        ("Bills & Utilities", "Mahanagar Gas PNG", 95000, 165000, "rule", 1.0),
                        ("Bills & Utilities", "Adani Electricity", 350000, 620000, "rule", 1.0),
                        ("Transport", "Indian Oil Fuel", 350000, 550000, "rule", 1.0),
                        ("Entertainment", "Netflix & Disney Hotstar", 115000, 115000, "rule", 1.0),
                    ]

                # Generate across 6 calendar months (m=0 is current month, m=5 is 5 months ago)
                batch_txs = []
                for m_offset in range(5, -1, -1):
                    # Compute month
                    yr = cur_year
                    mo = cur_month - m_offset
                    while mo <= 0:
                        mo += 12
                        yr -= 1

                    # Monthly income credit
                    if persona["segment"] == "student":
                        inc_date = datetime(yr, mo, 1, 10, 0, tzinfo=timezone.utc)
                        batch_txs.append(
                            Transaction(
                                id=str(uuid.uuid4()),
                                user_id=user.id,
                                account_id=primary_acc.id,
                                amount_minor=persona["monthly_pocket_money_minor"],
                                direction="credit",
                                currency="INR",
                                txn_date=inc_date,
                                merchant_normalized="Monthly Pocket Money (Parents)",
                                category_id=categories["Other Income"].id if "Other Income" in categories else None,
                                category_source="rule",
                                category_confidence=1.0,
                                source="sms",
                                dedupe_hash=gen_dedupe_hash(user.id, inc_date.isoformat(), persona["monthly_pocket_money_minor"], "Pocket Money"),
                            )
                        )
                    elif persona["segment"] in ["professional", "family"]:
                        sal_amt = persona.get("monthly_salary_minor", 10000000)
                        sal_date = datetime(yr, mo, 1, 9, 30, tzinfo=timezone.utc)
                        batch_txs.append(
                            Transaction(
                                id=str(uuid.uuid4()),
                                user_id=user.id,
                                account_id=primary_acc.id,
                                amount_minor=sal_amt,
                                direction="credit",
                                currency="INR",
                                txn_date=sal_date,
                                merchant_normalized="Infosys Technologies Payroll",
                                category_id=categories["Salary"].id if "Salary" in categories else None,
                                category_source="rule",
                                category_confidence=1.0,
                                source="csv",
                                dedupe_hash=gen_dedupe_hash(user.id, sal_date.isoformat(), sal_amt, "Salary"),
                            )
                        )
                    elif persona["segment"] == "business":
                        # 2 client revenue credits per month
                        for d_day, amt in [(5, 18500000), (20, 16500000)]:
                            c_dt = datetime(yr, mo, d_day, 14, 0, tzinfo=timezone.utc)
                            batch_txs.append(
                                Transaction(
                                    id=str(uuid.uuid4()),
                                    user_id=user.id,
                                    account_id=primary_acc.id,
                                    amount_minor=amt,
                                    direction="credit",
                                    currency="INR",
                                    txn_date=c_dt,
                                    merchant_normalized="Client Payment RTGS",
                                    category_id=categories["Other Income"].id if "Other Income" in categories else None,
                                    category_source="rule",
                                    category_confidence=1.0,
                                    source="statement",
                                    dedupe_hash=gen_dedupe_hash(user.id, c_dt.isoformat(), amt, f"Client-{d_day}"),
                                )
                            )
                    elif persona["segment"] == "freelancer":
                        # Irregular credits
                        if m_offset == 0 and persona.get("has_deficit_anomaly"):
                            # Current month deficit anomaly: low income (only ₹35k) vs ₹75k spend
                            c_dt = datetime(yr, mo, 8, 11, 0, tzinfo=timezone.utc)
                            batch_txs.append(
                                Transaction(
                                    id=str(uuid.uuid4()),
                                    user_id=user.id,
                                    account_id=primary_acc.id,
                                    amount_minor=3500000,
                                    direction="credit",
                                    currency="INR",
                                    txn_date=c_dt,
                                    merchant_normalized="Upwork Escrow Payout",
                                    category_id=categories["Other Income"].id if "Other Income" in categories else None,
                                    category_source="rule",
                                    category_confidence=1.0,
                                    source="csv",
                                    dedupe_hash=gen_dedupe_hash(user.id, c_dt.isoformat(), 3500000, "Upwork"),
                                )
                            )
                        else:
                            for d_day, amt in [(4, 5500000), (18, 4800000)]:
                                c_dt = datetime(yr, mo, d_day, 11, 0, tzinfo=timezone.utc)
                                batch_txs.append(
                                    Transaction(
                                        id=str(uuid.uuid4()),
                                        user_id=user.id,
                                        account_id=primary_acc.id,
                                        amount_minor=amt,
                                        direction="credit",
                                        currency="INR",
                                        txn_date=c_dt,
                                        merchant_normalized="Design Client Wire Transfer",
                                        category_id=categories["Other Income"].id if "Other Income" in categories else None,
                                        category_source="rule",
                                        category_confidence=1.0,
                                        source="csv",
                                        dedupe_hash=gen_dedupe_hash(user.id, c_dt.isoformat(), amt, f"Wire-{d_day}"),
                                    )
                                )

                    # 40-60 debits per month
                    max_day = now.day if m_offset == 0 else 28
                    num_txs = random.randint(35, 50) if m_offset > 0 else max(15, int(35 * (max_day / 28)))

                    for _ in range(num_txs):
                        cat_name, merch, min_a, max_a, c_src, c_conf = random.choice(expense_templates)
                        tx_amt = random.randint(min_a, max_a)
                        tx_day = random.randint(1, max(1, max_day))
                        tx_hour = random.randint(8, 22)
                        tx_min = random.randint(0, 59)
                        tx_dt = datetime(yr, mo, tx_day, tx_hour, tx_min, tzinfo=timezone.utc)

                        cat_obj = categories.get(cat_name)
                        acc_target = random.choice(list(accounts_map.values()))

                        batch_txs.append(
                            Transaction(
                                id=str(uuid.uuid4()),
                                user_id=user.id,
                                account_id=acc_target.id,
                                amount_minor=tx_amt,
                                direction="debit",
                                currency="INR",
                                txn_date=tx_dt,
                                merchant_normalized=merch,
                                category_id=cat_obj.id if cat_obj else None,
                                category_source=c_src,
                                category_confidence=c_conf,
                                needs_review=(c_conf < 0.6),
                                source=random.choice(["sms", "csv", "pdf"]),
                                dedupe_hash=gen_dedupe_hash(user.id, tx_dt.isoformat(), tx_amt, merch),
                            )
                        )

                    # Anomaly 1: Student laptop spike in current month (> 1.5x average)
                    if m_offset == 0 and persona.get("has_laptop_spike"):
                        sp_dt = datetime(yr, mo, 2, 16, 20, tzinfo=timezone.utc)
                        laptop_amt = 6500000  # ₹65,000
                        batch_txs.append(
                            Transaction(
                                id=str(uuid.uuid4()),
                                user_id=user.id,
                                account_id=primary_acc.id,
                                amount_minor=laptop_amt,
                                direction="debit",
                                currency="INR",
                                txn_date=sp_dt,
                                merchant_normalized="Apple Store BKC (MacBook Air)",
                                category_id=categories["Shopping"].id if "Shopping" in categories else None,
                                category_source="user",
                                category_confidence=1.0,
                                source="csv",
                                dedupe_hash=gen_dedupe_hash(user.id, sp_dt.isoformat(), laptop_amt, "Apple Store"),
                            )
                        )

                    # Anomaly 2: Professional dining out overshoot
                    if m_offset == 0 and persona.get("has_dining_overshoot"):
                        # Extra high dining spends
                        for d_day in [2, 3]:
                            ov_dt = datetime(yr, mo, d_day, 21, 0, tzinfo=timezone.utc)
                            d_amt = 850000  # ₹8,500 each
                            batch_txs.append(
                                Transaction(
                                    id=str(uuid.uuid4()),
                                    user_id=user.id,
                                    account_id=primary_acc.id,
                                    amount_minor=d_amt,
                                    direction="debit",
                                    currency="INR",
                                    txn_date=ov_dt,
                                    merchant_normalized="Bastian At The Top (Celebration)",
                                    category_id=categories["Food & Dining"].id if "Food & Dining" in categories else None,
                                    category_source="rule",
                                    category_confidence=1.0,
                                    source="sms",
                                    dedupe_hash=gen_dedupe_hash(user.id, ov_dt.isoformat(), d_amt, f"Bastian-{d_day}"),
                                )
                            )

                    # Anomaly 4: Family health spike anomaly
                    if m_offset == 0 and persona.get("has_health_spike"):
                        h_dt = datetime(yr, mo, 3, 11, 45, tzinfo=timezone.utc)
                        h_amt = 9500000  # ₹95,000
                        batch_txs.append(
                            Transaction(
                                id=str(uuid.uuid4()),
                                user_id=user.id,
                                account_id=primary_acc.id,
                                amount_minor=h_amt,
                                direction="debit",
                                currency="INR",
                                txn_date=h_dt,
                                merchant_normalized="Max Healthcare Hospital (Knee Surgery)",
                                category_id=categories["Health"].id if "Health" in categories else None,
                                category_source="user",
                                category_confidence=1.0,
                                source="pdf",
                                dedupe_hash=gen_dedupe_hash(user.id, h_dt.isoformat(), h_amt, "Max Hospital"),
                            )
                        )

                session.add_all(batch_txs)
                await session.commit()
                print(f"    [+] Created {len(batch_txs)} transactions across 6 months.")

            # Seed Budgets for current month
            cur_m_str = f"{cur_year:04d}-{cur_month:02d}"
            budget_targets = [
                ("Food & Dining", 1200000 if persona["segment"] != "student" else 600000),
                ("Groceries", 1500000 if persona["segment"] != "student" else 300000),
                ("Shopping", 800000 if persona["segment"] != "student" else 400000),
            ]
            for b_cat_name, b_limit in budget_targets:
                if b_cat_name in categories:
                    b_cat = categories[b_cat_name]
                    b_stmt = select(Budget).where(
                        Budget.user_id == user.id,
                        Budget.category_id == b_cat.id,
                        Budget.month == cur_m_str,
                    )
                    b_ex = (await session.execute(b_stmt)).scalar_one_or_none()
                    if not b_ex:
                        b_rec = Budget(
                            id=str(uuid.uuid4()),
                            user_id=user.id,
                            category_id=b_cat.id,
                            month=cur_m_str,
                            limit_minor=b_limit,
                        )
                        session.add(b_rec)
            await session.commit()

            # Seed Sample Import Record
            imp_stmt = select(Import).where(Import.user_id == user.id)
            if not (await session.execute(imp_stmt)).first():
                sample_import = Import(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    source_type="csv",
                    status="done",
                    total_rows=65,
                    parsed_rows=65,
                    failed_rows=0,
                    error_report=[],
                    created_at=now - timedelta(days=5),
                )
                session.add(sample_import)
                await session.commit()

    print("==================================================")
    print("   Demo Seeding Completed Successfully!           ")
    print("==================================================")
    print("\nLogins Available:")
    print(f"  [Admin Portal Staff]: {ADMIN_EMAIL}  /  {ADMIN_PASSWORD}")
    for p in DEMO_PERSONAS:
        print(f"  [{p['segment'].title()} Customer]: {p['email']}  /  {CUSTOMER_PASSWORD}")
    print("\nRun Pytest to verify test suite.")


if __name__ == "__main__":
    asyncio.run(seed_demo())

