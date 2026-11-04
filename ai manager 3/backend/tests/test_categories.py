import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_categories_and_system_defaults(client: AsyncClient):
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"email": "catuser@example.com", "password": "Password123!", "name": "Category User"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "catuser@example.com", "password": "Password123!"},
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List categories -> should contain seeded default categories
    list_resp = await client.get("/api/v1/categories", headers=headers)
    assert list_resp.status_code == 200
    categories = list_resp.json()
    category_names = [c["name"] for c in categories]
    assert "Food & Dining" in category_names
    assert "Groceries" in category_names
    assert "Salary" in category_names
    assert "Uncategorized" in category_names

    # 2. Try deleting a system default category -> 403 Forbidden
    system_cat = next(c for c in categories if c["user_id"] is None)
    del_system_resp = await client.delete(f"/api/v1/categories/{system_cat['id']}", headers=headers)
    assert del_system_resp.status_code == 403

    # 3. Create a custom category
    create_resp = await client.post(
        "/api/v1/categories",
        json={
            "name": "Cricket Club",
            "icon": "trophy",
            "color": "#10b981",
            "is_income": False,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    custom_cat = create_resp.json()
    assert custom_cat["name"] == "Cricket Club"
    assert custom_cat["user_id"] is not None

    # 4. Delete the custom category -> 204
    del_custom_resp = await client.delete(f"/api/v1/categories/{custom_cat['id']}", headers=headers)
    assert del_custom_resp.status_code == 204

