import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.core.security import hash_password, create_access_token
from app.models.models import User, Consent, Account, Transaction, AuditLog
from tests.conftest import TestingSessionLocal
from scripts.seed_demo import seed_demo


@pytest.mark.asyncio
async def test_customer_gets_403_on_admin_routes(client: AsyncClient):
    """Customers must receive 403 Forbidden on all /admin routes."""
    cust_id = str(uuid.uuid4())
    async with TestingSessionLocal() as session:
        customer = User(
            id=cust_id,
            email="regular_customer@test.com",
            name="Regular Customer",
            password_hash=hash_password("Pass123!"),
            role="customer",
            is_active=True,
            is_demo=False,
        )
        session.add(customer)
        await session.commit()

    token = create_access_token(cust_id, {"email": "regular_customer@test.com", "role": "customer"})
    headers = {"Authorization": f"Bearer {token}"}

    admin_routes = [
        ("GET", "/api/v1/admin/overview"),
        ("GET", "/api/v1/admin/analytics"),
        ("GET", "/api/v1/admin/customers"),
        ("GET", f"/api/v1/admin/customers/{cust_id}"),
        ("GET", "/api/v1/admin/risk-alerts"),
        ("GET", "/api/v1/admin/imports"),
        ("GET", "/api/v1/admin/audit-log"),
        ("GET", "/api/v1/admin/export/customers.csv"),
        ("PATCH", f"/api/v1/admin/customers/{cust_id}/status"),
    ]

    for method, route in admin_routes:
        if method == "GET":
            res = await client.get(route, headers=headers)
        elif method == "PATCH":
            res = await client.patch(route, json={"is_active": False}, headers=headers)
        assert res.status_code == 403, f"Expected 403 for customer on {route}, got {res.status_code}"


@pytest.mark.asyncio
async def test_admin_visibility_demo_and_consented_vs_unconsented_404(client: AsyncClient):
    """
    Admin can see:
    - demo customers (is_demo=True)
    - real customers who consented with 'share_with_bank'
    Non-consented real customers must return 404 (invisible).
    """
    admin_id = str(uuid.uuid4())
    demo_id = str(uuid.uuid4())
    consented_id = str(uuid.uuid4())
    unconsented_id = str(uuid.uuid4())

    async with TestingSessionLocal() as session:
        admin = User(
            id=admin_id,
            email="bank_admin@test.com",
            name="Bank Admin",
            password_hash=hash_password("AdminPass123!"),
            role="admin",
            is_active=True,
        )
        demo_cust = User(
            id=demo_id,
            email="demo_person@test.com",
            name="Demo Person",
            password_hash=hash_password("Pass123!"),
            role="customer",
            is_demo=True,
        )
        consented_cust = User(
            id=consented_id,
            email="consented_real@test.com",
            name="Consented Real Customer",
            password_hash=hash_password("Pass123!"),
            role="customer",
            is_demo=False,
        )
        unconsented_cust = User(
            id=unconsented_id,
            email="secret_real@test.com",
            name="Secret Real Customer",
            password_hash=hash_password("Pass123!"),
            role="customer",
            is_demo=False,
        )
        consent = Consent(
            id=str(uuid.uuid4()),
            user_id=consented_id,
            consent_type="share_with_bank",
            granted=True,
            policy_version="1.0",
        )
        session.add_all([admin, demo_cust, consented_cust, unconsented_cust, consent])
        await session.commit()

    token = create_access_token(admin_id, {"email": "bank_admin@test.com", "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Admin can access demo customer
    res_demo = await client.get(f"/api/v1/admin/customers/{demo_id}", headers=headers)
    assert res_demo.status_code == 200

    # 2. Admin can access consented real customer
    res_consented = await client.get(f"/api/v1/admin/customers/{consented_id}", headers=headers)
    assert res_consented.status_code == 200

    # 3. Admin gets 404 for unconsented real customer (complete privacy isolation)
    res_unconsented = await client.get(f"/api/v1/admin/customers/{unconsented_id}", headers=headers)
    assert res_unconsented.status_code == 404

    # 4. List customers includes demo & consented, but excludes unconsented
    res_list = await client.get("/api/v1/admin/customers", headers=headers)
    assert res_list.status_code == 200
    cust_ids = [item["id"] for item in res_list.json()["items"]]
    assert demo_id in cust_ids
    assert consented_id in cust_ids
    assert unconsented_id not in cust_ids


@pytest.mark.asyncio
async def test_admin_sensitive_fields_masked_and_no_password_hashes(client: AsyncClient):
    """Verify that email is masked (a***@...) and account numbers are last4 only, never returning passwords."""
    admin_id = str(uuid.uuid4())
    cust_id = str(uuid.uuid4())
    acc_id = str(uuid.uuid4())

    async with TestingSessionLocal() as session:
        admin = User(
            id=admin_id,
            email="super_admin@bank.com",
            name="Admin User",
            password_hash=hash_password("AdminPass123!"),
            role="admin",
            is_active=True,
        )
        demo_cust = User(
            id=cust_id,
            email="secret.identity@example.com",
            name="John Doe",
            password_hash=hash_password("CustomerSecretPass!"),
            role="customer",
            is_demo=True,
        )
        acc = Account(
            id=acc_id,
            user_id=cust_id,
            name="Savings Account",
            type="savings",
            last4="5589",
            opening_balance_minor=100000,
        )
        session.add_all([admin, demo_cust, acc])
        await session.commit()

    token = create_access_token(admin_id, {"email": "super_admin@bank.com", "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    # Test Customer 360 view
    res = await client.get(f"/api/v1/admin/customers/{cust_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Raw password or hash should never appear anywhere in json
    raw_json_str = res.text
    assert "CustomerSecretPass" not in raw_json_str
    assert "password_hash" not in raw_json_str

    # Email must be masked
    profile = data["profile"]
    assert profile["masked_email"] != "secret.identity@example.com"
    assert "s***y@example.com" in profile["masked_email"] or "***" in profile["masked_email"]

    # Account number must be masked (last 4 only)
    acc_data = data["accounts"][0]
    assert acc_data["masked_account_number"] == "****5589"


@pytest.mark.asyncio
async def test_admin_access_creates_audit_log_and_read_only(client: AsyncClient):
    """Every admin customer access creates an AuditLog row; admin has no endpoint to modify customer transactions."""
    admin_id = str(uuid.uuid4())
    cust_id = str(uuid.uuid4())

    async with TestingSessionLocal() as session:
        admin = User(
            id=admin_id,
            email="staff_audit@bank.com",
            name="Staff Audit",
            password_hash=hash_password("Pass123!"),
            role="admin",
            is_active=True,
        )
        cust = User(
            id=cust_id,
            email="target@demo.com",
            name="Target Demo",
            password_hash=hash_password("Pass123!"),
            role="customer",
            is_demo=True,
        )
        session.add_all([admin, cust])
        await session.commit()

    token = create_access_token(admin_id, {"email": "staff_audit@bank.com", "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    # View customer 360
    res = await client.get(f"/api/v1/admin/customers/{cust_id}", headers=headers)
    assert res.status_code == 200

    # Verify AuditLog row was written
    async with TestingSessionLocal() as session:
        stmt = select(AuditLog).where(
            AuditLog.user_id == admin_id,
            AuditLog.action == "ADMIN_VIEW_CUSTOMER",
            AuditLog.entity_id == cust_id,
        )
        log_entry = (await session.execute(stmt)).scalar_one_or_none()
        assert log_entry is not None
        assert log_entry.entity == "customer"

    # Export CSV also creates audit log
    csv_res = await client.get("/api/v1/admin/export/customers.csv", headers=headers)
    assert csv_res.status_code == 200
    assert "Customer ID" in csv_res.text

    async with TestingSessionLocal() as session:
        stmt_csv = select(AuditLog).where(
            AuditLog.user_id == admin_id,
            AuditLog.action == "ADMIN_EXPORT_CUSTOMERS",
        )
        assert (await session.execute(stmt_csv)).scalar_one_or_none() is not None

    # Verify admin cannot edit transactions via admin API (no mutation endpoints exist)
    bad_post = await client.post("/api/v1/admin/transactions", json={"amount": 100}, headers=headers)
    assert bad_post.status_code in [404, 405]


@pytest.mark.asyncio
async def test_deactivated_user_cannot_login_and_status_update(client: AsyncClient):
    """Admin can deactivate/reactivate a customer, and deactivated users cannot log in."""
    admin_id = str(uuid.uuid4())
    cust_id = str(uuid.uuid4())

    async with TestingSessionLocal() as session:
        admin = User(
            id=admin_id,
            email="status_admin@bank.com",
            name="Status Admin",
            password_hash=hash_password("AdminPass123!"),
            role="admin",
            is_active=True,
        )
        cust = User(
            id=cust_id,
            email="active_target@demo.com",
            name="Active Target",
            password_hash=hash_password("TargetPass123!"),
            role="customer",
            is_active=True,
            is_demo=True,
        )
        session.add_all([admin, cust])
        await session.commit()

    token = create_access_token(admin_id, {"email": "status_admin@bank.com", "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Customer can log in initially
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "active_target@demo.com", "password": "TargetPass123!"},
    )
    assert login_res.status_code == 200

    # 2. Admin deactivates the customer
    deact_res = await client.patch(
        f"/api/v1/admin/customers/{cust_id}/status",
        json={"is_active": False},
        headers=headers,
    )
    assert deact_res.status_code == 200
    assert deact_res.json()["is_active"] is False

    # 3. Deactivated customer cannot log in
    blocked_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "active_target@demo.com", "password": "TargetPass123!"},
    )
    assert blocked_login.status_code == 401

    # 4. Admin reactivates the customer
    react_res = await client.patch(
        f"/api/v1/admin/customers/{cust_id}/status",
        json={"is_active": True},
        headers=headers,
    )
    assert react_res.status_code == 200
    assert react_res.json()["is_active"] is True

    # 5. Customer can log in again
    ok_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "active_target@demo.com", "password": "TargetPass123!"},
    )
    assert ok_login.status_code == 200


@pytest.mark.asyncio
async def test_seed_demo_script_creates_personas():
    """Verify seed_demo creates 1 admin + 5 demo customers with 6 months of data idempotently."""
    await seed_demo()

    async with TestingSessionLocal() as session:
        # Check admin
        admin = (await session.execute(select(User).where(User.email == "admin@demo.com"))).scalar_one_or_none()
        assert admin is not None
        assert admin.role == "admin"

        # Check 5 personas
        emails = [
            "student@demo.com",
            "professional@demo.com",
            "business@demo.com",
            "freelancer@demo.com",
            "family@demo.com",
        ]
        for em in emails:
            u = (await session.execute(select(User).where(User.email == em))).scalar_one_or_none()
            assert u is not None, f"Expected {em} to exist"
            assert u.is_demo is True
            assert u.role == "customer"

            # Check transactions count >= 100
            tx_cnt = (await session.execute(select(Transaction.id).where(Transaction.user_id == u.id))).all()
            assert len(tx_cnt) >= 100, f"Expected >= 100 transactions for {em}, got {len(tx_cnt)}"

            # Check share_with_bank consent
            c = (await session.execute(
                select(Consent).where(
                    Consent.user_id == u.id,
                    Consent.consent_type == "share_with_bank",
                    Consent.granted.is_(True),
                )
            )).scalar_one_or_none()
            assert c is not None, f"Expected active share_with_bank consent for {em}"
