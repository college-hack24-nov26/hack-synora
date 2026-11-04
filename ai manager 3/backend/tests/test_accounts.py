import pytest
from httpx import AsyncClient


async def get_auth_token(client: AsyncClient, email: str = "accuser@example.com") -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "name": "Account Tester"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    return login_resp.json()["access_token"]


@pytest.mark.asyncio
async def test_account_crud(client: AsyncClient):
    token = await get_auth_token(client, "crud_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Account
    create_payload = {
        "name": "HDFC Salary Account",
        "type": "savings",
        "last4": "4589",
        "opening_balance_minor": 5000000,  # ₹50,000.00
    }
    create_resp = await client.post("/api/v1/accounts", json=create_payload, headers=headers)
    assert create_resp.status_code == 201
    account = create_resp.json()
    account_id = account["id"]
    assert account["name"] == "HDFC Salary Account"
    assert account["opening_balance_minor"] == 5000000
    assert account["current_balance_minor"] == 5000000

    # 2. List Accounts
    list_resp = await client.get("/api/v1/accounts", headers=headers)
    assert list_resp.status_code == 200
    accounts = list_resp.json()
    assert len(accounts) == 1
    assert accounts[0]["id"] == account_id

    # 3. Update Account
    update_payload = {"name": "HDFC Main Savings"}
    update_resp = await client.patch(f"/api/v1/accounts/{account_id}", json=update_payload, headers=headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "HDFC Main Savings"

    # 4. Get Account by ID
    get_resp = await client.get(f"/api/v1/accounts/{account_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "HDFC Main Savings"

    # 5. Delete Account
    del_resp = await client.delete(f"/api/v1/accounts/{account_id}", headers=headers)
    assert del_resp.status_code == 204

    # 6. Verify Deletion
    get_after_del = await client.get(f"/api/v1/accounts/{account_id}", headers=headers)
    assert get_after_del.status_code == 404

