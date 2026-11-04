import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_transaction_has_all_six_fields(client: AsyncClient):
    """Verify a created transaction record contains all 6 required structured fields."""
    email = "sixfields_user@example.com"
    pwd = "Password123!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "Six Fields"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create account
    acc = (await client.post(
        "/api/v1/accounts",
        json={"name": "HDFC Savings", "type": "savings", "opening_balance_minor": 1000000},
        headers=headers,
    )).json()

    # Create custom category
    cat = (await client.post(
        "/api/v1/categories",
        json={"name": "Dining Out", "icon": "utensils", "color": "#f97316", "is_income": False},
        headers=headers,
    )).json()

    # Create transaction
    txn_res = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": acc["id"],
            "amount_minor": 45000,  # ₹450.00
            "direction": "debit",
            "merchant": "Swiggy Bangalore",
            "category_id": cat["id"],
            "txn_date": "2026-11-04T12:30:00Z",
            "description": "Lunch order",
        },
        headers=headers,
    )
    assert txn_res.status_code == 201
    txn = txn_res.json()

    # 1. Transaction ID (unique, UUID)
    assert "id" in txn and len(txn["id"]) >= 32
    # 2. User ID (owner, foreign key)
    assert "user_id" in txn and txn["user_id"]
    # 3. Merchant info (merchant_raw + merchant_normalized)
    assert txn["merchant"] == "Swiggy Bangalore"
    assert txn["merchant_normalized"] == "Swiggy Bangalore"
    assert txn["merchant_raw"] == "Swiggy Bangalore"
    # 4. Date of transaction (UTC datetime)
    assert "txn_date" in txn
    assert txn["txn_date"].startswith("2026-11-04")
    # 5. Category of expense (foreign key + category object)
    assert txn["category_id"] == cat["id"]
    assert txn["category"]["name"] == "Dining Out"
    assert txn["category"]["color"] == "#f97316"
    assert txn["category"]["icon"] == "utensils"
    # 6. Money sent (amount_minor in paise + direction 'debit' + currency)
    assert txn["amount_minor"] == 45000
    assert txn["direction"] == "debit"
    assert txn["currency"] == "INR"


@pytest.mark.asyncio
async def test_two_users_have_separate_histories_and_404_protection(client: AsyncClient):
    """Verify User A and User B cannot access each other's transactions."""
    # User A
    await client.post("/api/v1/auth/register", json={"email": "alice_hist@example.com", "password": "Password123!", "name": "Alice"})
    login_a = await client.post("/api/v1/auth/login", json={"email": "alice_hist@example.com", "password": "Password123!"})
    h_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

    acc_a = (await client.post("/api/v1/accounts", json={"name": "Alice Acc", "type": "savings"}, headers=h_a)).json()["id"]
    txn_a = (await client.post("/api/v1/transactions", json={
        "account_id": acc_a,
        "amount_minor": 120000,
        "direction": "debit",
        "merchant": "Alice Secret Shop",
    }, headers=h_a)).json()

    # User B
    await client.post("/api/v1/auth/register", json={"email": "bob_hist@example.com", "password": "Password123!", "name": "Bob"})
    login_b = await client.post("/api/v1/auth/login", json={"email": "bob_hist@example.com", "password": "Password123!"})
    h_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    acc_b = (await client.post("/api/v1/accounts", json={"name": "Bob Acc", "type": "current"}, headers=h_b)).json()["id"]
    txn_b = (await client.post("/api/v1/transactions", json={
        "account_id": acc_b,
        "amount_minor": 30000,
        "direction": "debit",
        "merchant": "Bob Grocery",
    }, headers=h_b)).json()

    # User B lists transactions -> only sees Bob's transaction
    b_list = await client.get("/api/v1/transactions", headers=h_b)
    assert b_list.status_code == 200
    b_data = b_list.json()
    assert b_data["total"] == 1
    assert b_data["items"][0]["id"] == txn_b["id"]
    assert b_data["items"][0]["merchant"] == "Bob Grocery"

    # User B probes User A's transaction -> strictly 404 Not Found
    get_cross = await client.get(f"/api/v1/transactions/{txn_a['id']}", headers=h_b)
    assert get_cross.status_code == 404

    patch_cross = await client.patch(f"/api/v1/transactions/{txn_a['id']}", json={"merchant": "Hacked"}, headers=h_b)
    assert patch_cross.status_code == 404

    del_cross = await client.delete(f"/api/v1/transactions/{txn_a['id']}", headers=h_b)
    assert del_cross.status_code == 404


@pytest.mark.asyncio
async def test_deduplication_prevents_duplicate_imports_and_allows_per_user(client: AsyncClient):
    """Verify deduplication constraint prevents identical imports for user A, but user B can have identical details."""
    # User A
    await client.post("/api/v1/auth/register", json={"email": "dedupe_a@example.com", "password": "Password123!", "name": "Dedupe A"})
    login_a = await client.post("/api/v1/auth/login", json={"email": "dedupe_a@example.com", "password": "Password123!"})
    h_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}
    acc_a = (await client.post("/api/v1/accounts", json={"name": "A Acc", "type": "savings"}, headers=h_a)).json()["id"]

    # Grant consent for SMS
    await client.post("/api/v1/consents", json={"consent_type": "sms_import", "policy_version": "1.0"}, headers=h_a)

    sms_text = "HDFC Bank: Rs 750.00 debited from a/c **1234 on 04-Nov-26 to ZOMATO."
    # First SMS import
    res1 = await client.post("/api/v1/imports/sms", json={"account_id": acc_a, "raw_text": sms_text}, headers=h_a)
    assert res1.status_code == 200
    assert res1.json()["inserted_transactions"] == 1

    # Second identical SMS import -> deduplication skips it
    res2 = await client.post("/api/v1/imports/sms", json={"account_id": acc_a, "raw_text": sms_text}, headers=h_a)
    assert res2.status_code == 200
    assert res2.json()["inserted_transactions"] == 0
    assert res2.json()["duplicates_skipped"] == 1

    # User B imports the same SMS into their own account -> allowed because dedupe constraint is per-user!
    await client.post("/api/v1/auth/register", json={"email": "dedupe_b@example.com", "password": "Password123!", "name": "Dedupe B"})
    login_b = await client.post("/api/v1/auth/login", json={"email": "dedupe_b@example.com", "password": "Password123!"})
    h_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
    acc_b = (await client.post("/api/v1/accounts", json={"name": "B Acc", "type": "savings"}, headers=h_b)).json()["id"]
    await client.post("/api/v1/consents", json={"consent_type": "sms_import", "policy_version": "1.0"}, headers=h_b)

    res_b = await client.post("/api/v1/imports/sms", json={"account_id": acc_b, "raw_text": sms_text}, headers=h_b)
    assert res_b.status_code == 200
    assert res_b.json()["inserted_transactions"] == 1


@pytest.mark.asyncio
async def test_pagination_and_filters(client: AsyncClient):
    """Test pagination, date range, search, category, and summary endpoints."""
    email = "filter_user@example.com"
    pwd = "Password123!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "Filter User"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    acc = (await client.post("/api/v1/accounts", json={"name": "Checking", "type": "savings"}, headers=headers)).json()["id"]

    cat_food = (await client.post("/api/v1/categories", json={"name": "Food & Grocery", "color": "#10b981"}, headers=headers)).json()["id"]
    cat_travel = (await client.post("/api/v1/categories", json={"name": "Travel & Commute", "color": "#3b82f6"}, headers=headers)).json()["id"]

    # Create 5 distinct transactions
    txns = [
        {"merchant": "Starbucks Coffee", "amount_minor": 35000, "direction": "debit", "category_id": cat_food, "txn_date": "2026-11-01T08:00:00Z"},
        {"merchant": "Uber Ride", "amount_minor": 45000, "direction": "debit", "category_id": cat_travel, "txn_date": "2026-11-02T09:00:00Z"},
        {"merchant": "Whole Foods", "amount_minor": 150000, "direction": "debit", "category_id": cat_food, "txn_date": "2026-11-03T18:00:00Z"},
        {"merchant": "Salary Credit", "amount_minor": 5000000, "direction": "credit", "category_id": None, "txn_date": "2026-11-04T05:00:00Z"},
        {"merchant": "Metro Recharge", "amount_minor": 20000, "direction": "debit", "category_id": cat_travel, "txn_date": "2026-11-04T12:00:00Z"},
    ]
    for t in txns:
        await client.post("/api/v1/transactions", json={"account_id": acc, **t}, headers=headers)

    # 1. Pagination: page=1, limit=2
    p1 = await client.get("/api/v1/transactions?page=1&limit=2", headers=headers)
    assert p1.status_code == 200
    p1_data = p1.json()
    assert p1_data["total"] == 5
    assert len(p1_data["items"]) == 2
    assert p1_data["page"] == 1
    assert p1_data["total_pages"] == 3

    # page=2, limit=2
    p2 = await client.get("/api/v1/transactions?page=2&limit=2", headers=headers)
    assert p2.status_code == 200
    assert len(p2.json()["items"]) == 2

    # 2. Category filter: cat_food
    f_cat = await client.get(f"/api/v1/transactions?category_id={cat_food}", headers=headers)
    assert f_cat.status_code == 200
    assert f_cat.json()["total"] == 2
    for item in f_cat.json()["items"]:
        assert item["category"]["id"] == cat_food

    # 3. Search filter: "Uber"
    f_search = await client.get("/api/v1/transactions?search=Uber", headers=headers)
    assert f_search.status_code == 200
    assert f_search.json()["total"] == 1
    assert "Uber" in f_search.json()["items"][0]["merchant"]

    # 4. Amount range filter: min 100000
    f_amt = await client.get("/api/v1/transactions?min_amount_minor=100000", headers=headers)
    assert f_amt.status_code == 200
    assert f_amt.json()["total"] == 2  # Whole Foods (150,000) and Salary (5,000,000)

    # 5. Summary Endpoint
    summary_res = await client.get("/api/v1/transactions/summary", headers=headers)
    assert summary_res.status_code == 200
    s_data = summary_res.json()
    assert s_data["transaction_count"] == 5
    # Total spent: 35000 + 45000 + 150000 + 20000 = 250000 paise (₹2,500)
    assert s_data["total_spent_minor"] == 250000
    # Total income: 5000000 paise (₹50,000)
    assert s_data["total_income_minor"] == 5000000
    assert len(s_data["top_categories"]) >= 1
