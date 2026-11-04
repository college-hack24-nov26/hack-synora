import asyncio
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_multi_user_data_isolation(client: AsyncClient):
    # Register and login User A (Alice)
    await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "Password123!", "name": "Alice"},
    )
    res_a = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"},
    )
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register and login User B (Bob)
    await client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "Password123!", "name": "Bob"},
    )
    res_b = await client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "Password123!"},
    )
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates an account
    acc_a_resp = await client.post(
        "/api/v1/accounts",
        json={
            "name": "Alice's Secret Account",
            "type": "savings",
            "last4": "1111",
            "opening_balance_minor": 10000000,
        },
        headers=headers_a,
    )
    assert acc_a_resp.status_code == 201
    account_a_id = acc_a_resp.json()["id"]

    # User B creates an account
    acc_b_resp = await client.post(
        "/api/v1/accounts",
        json={
            "name": "Bob's Account",
            "type": "current",
            "last4": "2222",
            "opening_balance_minor": 500000,
        },
        headers=headers_b,
    )
    assert acc_b_resp.status_code == 201
    account_b_id = acc_b_resp.json()["id"]

    # 1. ACCOUNTS ISOLATION
    # User B lists accounts -> MUST ONLY see Bob's account
    list_b = await client.get("/api/v1/accounts", headers=headers_b)
    assert list_b.status_code == 200
    b_accounts = list_b.json()
    assert len(b_accounts) == 1
    assert b_accounts[0]["id"] == account_b_id
    assert b_accounts[0]["name"] == "Bob's Account"

    # User B tries to read User A's account by ID -> 404 Not Found (strict isolation)
    leak_get = await client.get(f"/api/v1/accounts/{account_a_id}", headers=headers_b)
    assert leak_get.status_code == 404

    # User B tries to update User A's account -> 404 Not Found
    leak_patch = await client.patch(
        f"/api/v1/accounts/{account_a_id}",
        json={"name": "Hacked Name"},
        headers=headers_b,
    )
    assert leak_patch.status_code == 404

    # User B tries to delete User A's account -> 404 Not Found
    leak_del = await client.delete(f"/api/v1/accounts/{account_a_id}", headers=headers_b)
    assert leak_del.status_code == 404

    # 2. CATEGORIES ISOLATION & SYSTEM CATEGORIES READ-ONLY
    # User A creates a custom category
    cat_a_resp = await client.post(
        "/api/v1/categories",
        json={"name": "Alice Specific Hobby", "icon": "star", "color": "#ff0000", "is_income": False},
        headers=headers_a,
    )
    assert cat_a_resp.status_code == 201
    cat_a_id = cat_a_resp.json()["id"]

    # User B lists categories -> does NOT include Alice's custom category
    cats_b = await client.get("/api/v1/categories", headers=headers_b)
    assert cats_b.status_code == 200
    b_cat_ids = [c["id"] for c in cats_b.json()]
    assert cat_a_id not in b_cat_ids

    # User B tries to update or delete User A's custom category -> 404
    assert (await client.patch(f"/api/v1/categories/{cat_a_id}", json={"name": "Hacked"}, headers=headers_b)).status_code == 404
    assert (await client.delete(f"/api/v1/categories/{cat_a_id}", headers=headers_b)).status_code == 404

    # Find a system default category (user_id is None)
    all_cats = cats_b.json()
    system_cat = next((c for c in all_cats if c.get("user_id") is None), None)
    if system_cat:
        # Modifying or deleting system default category must return 403 Forbidden
        sys_patch = await client.patch(f"/api/v1/categories/{system_cat['id']}", json={"name": "System Changed"}, headers=headers_a)
        assert sys_patch.status_code == 403
        sys_del = await client.delete(f"/api/v1/categories/{system_cat['id']}", headers=headers_a)
        assert sys_del.status_code == 403

    # 3. TRANSACTIONS ISOLATION
    # User A creates a transaction
    txn_a_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_a_id,
            "amount_minor": 150000,
            "direction": "debit",
            "merchant": "Alice Merchant",
            "category_id": cat_a_id,
            "description": "Alice Private Note",
        },
        headers=headers_a,
    )
    assert txn_a_resp.status_code == 201
    txn_a_id = txn_a_resp.json()["id"]

    # User B tries to read Alice's transaction -> 404
    assert (await client.get(f"/api/v1/transactions/{txn_a_id}", headers=headers_b)).status_code == 404

    # User B tries to patch Alice's transaction -> 404
    assert (await client.patch(f"/api/v1/transactions/{txn_a_id}", json={"merchant": "Hacked"}, headers=headers_b)).status_code == 404

    # User B tries to delete Alice's transaction -> 404
    assert (await client.delete(f"/api/v1/transactions/{txn_a_id}", headers=headers_b)).status_code == 404

    # User B tries to create a transaction using Alice's account -> 404
    cross_txn = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_a_id,
            "amount_minor": 5000,
            "direction": "debit",
            "merchant": "Cross Infiltration",
        },
        headers=headers_b,
    )
    assert cross_txn.status_code == 404

    # User B lists transactions -> 0 items
    list_txns_b = await client.get("/api/v1/transactions", headers=headers_b)
    assert list_txns_b.status_code == 200
    assert list_txns_b.json()["total"] == 0
    assert len(list_txns_b.json()["items"]) == 0

    # 4. IMPORTS & CONSENTS ISOLATION
    # User A grants consent and imports SMS
    await client.post(
        "/api/v1/consents",
        json={"consent_type": "sms_import", "policy_version": "1.0"},
        headers=headers_a,
    )
    import_a_resp = await client.post(
        "/api/v1/imports/sms",
        json={
            "account_id": account_a_id,
            "raw_text": "HDFC Bank: Rs 500.00 debited from a/c **1111 on 02-Nov-26 to SWIGGY.",
        },
        headers=headers_a,
    )
    assert import_a_resp.status_code == 200
    import_a_id = import_a_resp.json()["import_id"]

    # User B attempts to view User A's import status -> 404
    assert (await client.get(f"/api/v1/imports/{import_a_id}", headers=headers_b)).status_code == 404

    # User B lists consents -> 0 consents
    b_consents = await client.get("/api/v1/consents", headers=headers_b)
    assert b_consents.status_code == 200
    assert len(b_consents.json()) == 0

    # 5. BUDGETS ISOLATION
    # User A creates a budget
    cat_for_budget = system_cat["id"] if system_cat else cat_a_id
    bud_a_resp = await client.post(
        "/api/v1/budgets",
        json={"category_id": cat_for_budget, "month": "2026-11", "limit_minor": 2000000},
        headers=headers_a,
    )
    assert bud_a_resp.status_code == 201
    budget_a_id = bud_a_resp.json()["id"]

    # User B lists budgets -> 0 budgets
    list_bud_b = await client.get("/api/v1/budgets", headers=headers_b)
    assert list_bud_b.status_code == 200
    assert len(list_bud_b.json()) == 0

    # User B tries to read, update or delete Alice's budget -> 404
    assert (await client.get(f"/api/v1/budgets/{budget_a_id}", headers=headers_b)).status_code == 404
    assert (await client.patch(f"/api/v1/budgets/{budget_a_id}", json={"limit_minor": 999}, headers=headers_b)).status_code == 404
    assert (await client.delete(f"/api/v1/budgets/{budget_a_id}", headers=headers_b)).status_code == 404

    # 6. FORECASTS ISOLATION
    # User A creates a forecast
    fc_a_resp = await client.post(
        "/api/v1/forecasts",
        json={
            "target_month": "2026-12",
            "category_id": cat_for_budget,
            "predicted_minor": 1500000,
            "lower_bound_minor": 1200000,
            "upper_bound_minor": 1800000,
        },
        headers=headers_a,
    )
    assert fc_a_resp.status_code == 201
    fc_a_id = fc_a_resp.json()["id"]

    # User B lists forecasts -> 0 forecasts
    list_fc_b = await client.get("/api/v1/forecasts", headers=headers_b)
    assert list_fc_b.status_code == 200
    assert len(list_fc_b.json()) == 0

    # User B tries to read or delete Alice's forecast -> 404
    assert (await client.get(f"/api/v1/forecasts/{fc_a_id}", headers=headers_b)).status_code == 404
    assert (await client.delete(f"/api/v1/forecasts/{fc_a_id}", headers=headers_b)).status_code == 404

    # 7. ANALYTICS ISOLATION
    # User B creates their own transaction
    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_b_id,
            "amount_minor": 7500,
            "direction": "debit",
            "merchant": "Bob Coffee",
        },
        headers=headers_b,
    )

    summary_b = await client.get("/api/v1/analytics/summary", headers=headers_b)
    assert summary_b.status_code == 200
    b_data = summary_b.json()
    # Bob only has 1 transaction of 7500 paise, while Alice had multiple larger transactions
    assert b_data["transaction_count"] == 1
    assert b_data["total_expense_minor"] == 7500


@pytest.mark.asyncio
async def test_concurrent_requests_isolation(client: AsyncClient):
    """Verify that simultaneous asynchronous requests from multiple users never leak data."""
    # Register User 1 & User 2
    await client.post(
        "/api/v1/auth/register",
        json={"email": "u1@example.com", "password": "Password123!", "name": "User 1"},
    )
    u1_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "u1@example.com", "password": "Password123!"},
    )
    h1 = {"Authorization": f"Bearer {u1_login.json()['access_token']}"}

    await client.post(
        "/api/v1/auth/register",
        json={"email": "u2@example.com", "password": "Password123!", "name": "User 2"},
    )
    u2_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "u2@example.com", "password": "Password123!"},
    )
    h2 = {"Authorization": f"Bearer {u2_login.json()['access_token']}"}

    # Concurrent account creation
    r1, r2 = await asyncio.gather(
        client.post(
            "/api/v1/accounts",
            json={"name": "U1 Account", "type": "savings", "opening_balance_minor": 1000},
            headers=h1,
        ),
        client.post(
            "/api/v1/accounts",
            json={"name": "U2 Account", "type": "current", "opening_balance_minor": 2000},
            headers=h2,
        ),
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    u1_acc_id = r1.json()["id"]
    u2_acc_id = r2.json()["id"]

    # Concurrent transactions creation
    t1, t2 = await asyncio.gather(
        client.post(
            "/api/v1/transactions",
            json={"account_id": u1_acc_id, "amount_minor": 500, "direction": "debit", "merchant": "M1"},
            headers=h1,
        ),
        client.post(
            "/api/v1/transactions",
            json={"account_id": u2_acc_id, "amount_minor": 800, "direction": "debit", "merchant": "M2"},
            headers=h2,
        ),
    )
    assert t1.status_code == 201
    assert t2.status_code == 201

    # Concurrent listing & cross-reading verification
    list1, list2, probe_cross1, probe_cross2 = await asyncio.gather(
        client.get("/api/v1/accounts", headers=h1),
        client.get("/api/v1/accounts", headers=h2),
        client.get(f"/api/v1/accounts/{u2_acc_id}", headers=h1),  # U1 probes U2's account
        client.get(f"/api/v1/accounts/{u1_acc_id}", headers=h2),  # U2 probes U1's account
    )

    # U1 accounts list must contain only U1
    assert len(list1.json()) == 1
    assert list1.json()[0]["id"] == u1_acc_id

    # U2 accounts list must contain only U2
    assert len(list2.json()) == 1
    assert list2.json()[0]["id"] == u2_acc_id

    # Cross probes must both return 404
    assert probe_cross1.status_code == 404
    assert probe_cross2.status_code == 404
