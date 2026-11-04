import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # 1. Register a new user
    reg_payload = {
        "email": "user1@example.com",
        "password": "StrongPassword123!",
        "name": "Arjun Sharma",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
    }
    resp = await client.post("/api/v1/auth/register", json=reg_payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["email"] == "user1@example.com"
    assert data["name"] == "Arjun Sharma"
    assert data["currency"] == "INR"

    # 2. Try registering duplicate email -> 409 Conflict
    dup_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"]["code"] == "CONFLICT"

    # 3. Login with valid credentials
    login_payload = {
        "email": "user1@example.com",
        "password": "StrongPassword123!",
    }
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    token = login_data["access_token"]
    assert "refresh_token" in login_resp.cookies

    # 4. Login with invalid password -> 401
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "user1@example.com", "password": "WrongPassword"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["error"]["code"] == "UNAUTHORIZED"

    # 5. Access /auth/me with Bearer token
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "user1@example.com"

    # 6. Access /auth/me without token -> 401
    no_token_resp = await client.get("/api/v1/auth/me")
    assert no_token_resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "refreshtest@example.com",
            "password": "Password123!",
            "name": "Priya Patel",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "refreshtest@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    refresh_cookie = login_resp.cookies.get("refresh_token")
    assert refresh_cookie is not None

    # Refresh using the cookie
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": refresh_cookie},
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()

