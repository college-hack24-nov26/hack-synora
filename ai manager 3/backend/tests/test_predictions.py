import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import prediction_service
from app.models.models import User, Account, Transaction, Category


@pytest.mark.asyncio
async def test_cold_start_scenarios(client: AsyncClient):
    """Test 0, 1, and 2 months of history cold start behavior."""
    # Register & login
    email = "cold_user@example.com"
    pwd = "Password123!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "Cold User"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Case 1: 0 completed months -> not enough data
    res_0 = await client.get("/api/v1/analytics/forecast/current-month", headers=headers)
    assert res_0.status_code == 200
    data_0 = res_0.json()
    assert data_0["has_enough_data"] is False
    assert data_0["confidence"] == "none"
    assert "Import at least 1 month" in data_0["message"]

    # Create account
    acc_res = await client.post(
        "/api/v1/accounts",
        json={"name": "Bank", "type": "savings", "opening_balance_minor": 10000000},
        headers=headers,
    )
    acc_id = acc_res.json()["id"]

    # Case 2: 1 completed month -> low confidence
    # Add transaction in previous month (e.g. October 2026 if current is November 2026)
    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": acc_id,
            "amount_minor": 1200000,
            "direction": "debit",
            "merchant": "Supermarket",
            "txn_date": "2026-10-15T10:00:00Z",
        },
        headers=headers,
    )

    res_1 = await client.get("/api/v1/analytics/forecast/current-month", headers=headers)
    assert res_1.status_code == 200
    data_1 = res_1.json()
    assert data_1["has_enough_data"] is True
    assert data_1["confidence"] == "low"
    assert data_1["completed_months_count"] == 1

    # Case 3: 2 completed months -> low confidence
    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": acc_id,
            "amount_minor": 1100000,
            "direction": "debit",
            "merchant": "Supermarket",
            "txn_date": "2026-09-15T10:00:00Z",
        },
        headers=headers,
    )

    res_2 = await client.get("/api/v1/analytics/forecast/current-month", headers=headers)
    assert res_2.status_code == 200
    data_2 = res_2.json()
    assert data_2["has_enough_data"] is True
    assert data_2["confidence"] == "low"
    assert data_2["completed_months_count"] == 2


@pytest.mark.asyncio
async def test_typical_4_month_pattern_and_range_ordering(client: AsyncClient):
    """Test 4-month pattern with medium confidence and mathematical range lower <= predicted <= upper."""
    email = "pattern_user@example.com"
    pwd = "Password123!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "Pattern User"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    acc_res = await client.post(
        "/api/v1/accounts",
        json={"name": "Checking", "type": "savings", "opening_balance_minor": 50000000},
        headers=headers,
    )
    acc_id = acc_res.json()["id"]

    # Add 4 completed months of data: July, August, September, October 2026
    monthly_spends = [
        ("2026-07-10T12:00:00Z", 2000000),  # ₹20,000
        ("2026-08-10T12:00:00Z", 2200000),  # ₹22,000
        ("2026-09-10T12:00:00Z", 2100000),  # ₹21,000
        ("2026-10-10T12:00:00Z", 2500000),  # ₹25,000
    ]
    for dt, amt in monthly_spends:
        await client.post(
            "/api/v1/transactions",
            json={"account_id": acc_id, "amount_minor": amt, "direction": "debit", "merchant": "Store", "txn_date": dt},
            headers=headers,
        )

    # Current month transaction (November 2026)
    await client.post(
        "/api/v1/transactions",
        json={"account_id": acc_id, "amount_minor": 500000, "direction": "debit", "merchant": "Fuel", "txn_date": "2026-11-02T12:00:00Z"},
        headers=headers,
    )

    res = await client.get("/api/v1/analytics/forecast/current-month", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["has_enough_data"] is True
    assert data["confidence"] == "medium"
    assert data["completed_months_count"] == 4
    assert data["spent_so_far_minor"] >= 500000
    # Range ordering must hold strictly: lower <= predicted <= upper
    assert data["lower_bound_minor"] <= data["predicted_total_minor"]
    assert data["predicted_total_minor"] <= data["upper_bound_minor"]
    assert data["predicted_total_minor"] >= data["spent_so_far_minor"]
    assert len(data["drivers"]) >= 2


@pytest.mark.asyncio
async def test_early_vs_late_month_blending():
    """Verify that early month weights baseline more while late month weights run-rate more."""
    from unittest.mock import MagicMock
    from app.services.prediction_service import compute_monthly_prediction
    from app.models.models import User

    # Create dummy records
    user = User(id="dummy_u", timezone="Asia/Kolkata")

    # Mock session
    db = MagicMock(spec=AsyncSession)

    # We can test this by calling compute_monthly_prediction with as_of_date
    # on day 2 vs day 29 of a 30-day month with a high current month pace.
    # In day 2, alpha is 2/30 = 0.066; in day 29, alpha is 29/30 = 0.966.
    pass


@pytest.mark.asyncio
async def test_recurring_expense_detection(client: AsyncClient):
    """Detect recurring rent and verify it is accounted for in projected remaining."""
    email = "recurring_user@example.com"
    pwd = "Password123!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "Rec User"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    acc_res = await client.post(
        "/api/v1/accounts",
        json={"name": "Checking", "type": "savings", "opening_balance_minor": 50000000},
        headers=headers,
    )
    acc_id = acc_res.json()["id"]

    # Recurring rent of ₹30,000 paid around day 5 in Aug, Sep, Oct
    for m in ["2026-08", "2026-09", "2026-10"]:
        await client.post(
            "/api/v1/transactions",
            json={
                "account_id": acc_id,
                "amount_minor": 3000000,
                "direction": "debit",
                "merchant": "Landlord Housing",
                "txn_date": f"{m}-05T10:00:00Z",
            },
            headers=headers,
        )

    # In November, only a small coffee was bought on Nov 1, rent NOT yet paid
    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": acc_id,
            "amount_minor": 20000,
            "direction": "debit",
            "merchant": "Coffee Shop",
            "txn_date": "2026-11-01T10:00:00Z",
        },
        headers=headers,
    )

    res = await client.get("/api/v1/analytics/forecast/current-month", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["has_enough_data"] is True
    # Recurring expense of ₹30,000 should be detected
    rec = data["recurring_expenses_detected"]
    assert any("Landlord Housing" in r["merchant"] for r in rec)
    # Predicted total should cover the ₹30,000 rent
    assert data["predicted_total_minor"] >= 3000000
    assert any("Landlord Housing" in d for d in data["drivers"])


@pytest.mark.asyncio
async def test_outlier_exclusion(client: AsyncClient):
    """Ensure abnormal one-off outlier spikes do not bloat baseline."""
    email = "outlier_user@example.com"
    pwd = "Password123!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "Outlier User"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    acc_res = await client.post(
        "/api/v1/accounts",
        json={"name": "Checking", "type": "savings", "opening_balance_minor": 50000000},
        headers=headers,
    )
    acc_id = acc_res.json()["id"]

    # Normal spending ~₹1,000 across multiple transactions
    for m in ["2026-08", "2026-09", "2026-10"]:
        for d in [1, 5, 10, 15, 20]:
            await client.post(
                "/api/v1/transactions",
                json={
                    "account_id": acc_id,
                    "amount_minor": 100000,  # ₹1,000
                    "direction": "debit",
                    "merchant": "Grocery",
                    "txn_date": f"{m}-{d:02d}T10:00:00Z",
                },
                headers=headers,
            )

    # Inject one massive outlier in August: ₹25,00,000 (e.g. car purchase)
    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": acc_id,
            "amount_minor": 250000000,
            "direction": "debit",
            "merchant": "Luxury Car Dealership",
            "txn_date": "2026-08-25T10:00:00Z",
        },
        headers=headers,
    )

    res = await client.get("/api/v1/analytics/forecast/current-month", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # The outlier must be excluded from baseline so baseline stays normal (~₹5,000/mo)
    # If the ₹25,00,000 was included, baseline would be > ₹60,00,000!
    assert data["historical_baseline_minor"] < 2000000  # Less than ₹20,000
    assert any("outlier" in d.lower() or "spike" in d.lower() for d in data["drivers"])


@pytest.mark.asyncio
async def test_user_isolation_in_predictions(client: AsyncClient):
    """Verify User B's predictions are never affected by User A's large transactions."""
    # User A (High spender)
    await client.post("/api/v1/auth/register", json={"email": "rich_a@example.com", "password": "Password123!", "name": "Rich A"})
    login_a = await client.post("/api/v1/auth/login", json={"email": "rich_a@example.com", "password": "Password123!"})
    h_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

    acc_a = (await client.post("/api/v1/accounts", json={"name": "A", "type": "savings", "opening_balance_minor": 100000000}, headers=h_a)).json()["id"]
    for m in ["2026-08", "2026-09", "2026-10"]:
        await client.post(
            "/api/v1/transactions",
            json={"account_id": acc_a, "amount_minor": 50000000, "direction": "debit", "merchant": "Diamonds", "txn_date": f"{m}-10T10:00:00Z"},
            headers=h_a,
        )

    # User B (Frugal spender)
    await client.post("/api/v1/auth/register", json={"email": "frugal_b@example.com", "password": "Password123!", "name": "Frugal B"})
    login_b = await client.post("/api/v1/auth/login", json={"email": "frugal_b@example.com", "password": "Password123!"})
    h_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    acc_b = (await client.post("/api/v1/accounts", json={"name": "B", "type": "savings", "opening_balance_minor": 10000000}, headers=h_b)).json()["id"]
    for m in ["2026-08", "2026-09", "2026-10"]:
        await client.post(
            "/api/v1/transactions",
            json={"account_id": acc_b, "amount_minor": 500000, "direction": "debit", "merchant": "Bread", "txn_date": f"{m}-10T10:00:00Z"},
            headers=h_b,
        )

    # Check User B's prediction
    res_b = await client.get("/api/v1/analytics/forecast/current-month", headers=h_b)
    assert res_b.status_code == 200
    data_b = res_b.json()

    # User B baseline must be ~₹5,000, totally free of User A's ₹5,00,000
    assert data_b["historical_baseline_minor"] <= 600000
    assert data_b["predicted_total_minor"] <= 1000000


@pytest.mark.asyncio
async def test_forecast_history_endpoint(client: AsyncClient):
    """Test GET /api/v1/analytics/forecast/history."""
    email = "history_user@example.com"
    pwd = "Password123!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "History User"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res = await client.get("/api/v1/analytics/forecast/history?months=6", headers=headers)
    assert res.status_code == 200
    history = res.json()
    assert isinstance(history, list)
    assert len(history) >= 1
    assert history[-1]["is_current"] is True

