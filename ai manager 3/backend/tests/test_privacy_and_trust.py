import io
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from tests.conftest import TestingSessionLocal
from app.services.sms_parser import parse_single_sms, is_otp_or_promo, sanitize_financial_text


@pytest.mark.asyncio
async def test_consent_enforcement_and_revocation(client: AsyncClient):
    # 1. Register and login
    email = "trust_user@example.com"
    pwd = "Password123!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "Trust Tester"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create bank account
    acc_res = await client.post(
        "/api/v1/accounts",
        json={"name": "HDFC Savings", "type": "savings", "last4": "4589", "opening_balance_minor": 100000},
        headers=headers,
    )
    assert acc_res.status_code == 201
    account_id = acc_res.json()["id"]

    # 3. Test Promise 1 Enforcement: SMS import without consent MUST RETURN 403
    sms_payload = {
        "account_id": account_id,
        "raw_text": "HDFC Bank: Rs 550.00 debited from a/c **4589 on 03-Nov-26 to ZOMATO.",
    }
    sms_resp = await client.post("/api/v1/imports/sms", json=sms_payload, headers=headers)
    assert sms_resp.status_code == 403
    sms_err = sms_resp.json().get("error", {}).get("message") or sms_resp.json().get("detail", "")
    assert "Active consent for SMS import is required" in sms_err

    # 4. Test Statement upload without consent MUST RETURN 403
    csv_content = b"Date,Description,Debit,Credit\n03/11/2026,Swiggy Food,350.00,\n"
    csv_resp = await client.post(
        "/api/v1/imports/csv",
        data={"account_id": account_id},
        files={"file": ("statement.csv", io.BytesIO(csv_content), "text/csv")},
        headers=headers,
    )
    assert csv_resp.status_code == 403
    csv_err = csv_resp.json().get("error", {}).get("message") or csv_resp.json().get("detail", "")
    assert "Active consent for statement upload is required" in csv_err

    # 5. Grant SMS consent
    grant_sms_res = await client.post(
        "/api/v1/consents",
        json={"consent_type": "sms_import", "policy_version": "1.0"},
        headers=headers,
    )
    assert grant_sms_res.status_code == 201
    assert grant_sms_res.json()["granted"] is True

    # 6. Now SMS import MUST SUCCEED
    sms_success_resp = await client.post("/api/v1/imports/sms", json=sms_payload, headers=headers)
    assert sms_success_resp.status_code == 200
    assert sms_success_resp.json()["inserted_transactions"] == 1

    # 7. Grant Statement upload consent
    grant_stmt_res = await client.post(
        "/api/v1/consents",
        json={"consent_type": "statement_upload", "policy_version": "1.0"},
        headers=headers,
    )
    assert grant_stmt_res.status_code == 201
    assert grant_stmt_res.json()["granted"] is True

    # 8. CSV import MUST SUCCEED
    csv_success_resp = await client.post(
        "/api/v1/imports/csv",
        data={"account_id": account_id},
        files={"file": ("statement.csv", io.BytesIO(csv_content), "text/csv")},
        headers=headers,
    )
    assert csv_success_resp.status_code == 200
    assert csv_success_resp.json()["inserted_transactions"] == 1

    # Verify both transactions are in user's transaction list
    txns_res = await client.get("/api/v1/transactions", headers=headers)
    assert txns_res.status_code == 200
    assert txns_res.json()["total"] == 2

    # 9. Revoke SMS consent with delete_data=True
    revoke_res = await client.delete("/api/v1/consents/sms_import?delete_data=true", headers=headers)
    assert revoke_res.status_code == 200
    assert revoke_res.json()["data_deleted"] is True
    assert revoke_res.json()["deleted_transactions"] == 1

    # Verify SMS transaction was deleted, but CSV transaction remains
    txns_after = await client.get("/api/v1/transactions", headers=headers)
    assert txns_after.json()["total"] == 1
    assert txns_after.json()["items"][0]["source"] == "csv"

    # 10. Attempting SMS import again MUST RETURN 403
    retry_sms = await client.post("/api/v1/imports/sms", json=sms_payload, headers=headers)
    assert retry_sms.status_code == 403


@pytest.mark.asyncio
async def test_encryption_round_trip(client: AsyncClient):
    """Promise 3: Fields are encrypted at rest with Fernet and decrypted on read."""
    email = "crypto_user@example.com"
    pwd = "Password123!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "Crypto User"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    acc_res = await client.post(
        "/api/v1/accounts",
        json={"name": "ICICI Salary", "type": "savings", "last4": "1204", "opening_balance_minor": 500000},
        headers=headers,
    )
    account_id = acc_res.json()["id"]

    secret_merchant = "CONFIDENTIAL MEDICAL CLINIC"
    secret_desc = "Prescription medication payment 9876543210"

    create_txn = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "amount_minor": 185000,
            "direction": "debit",
            "merchant": secret_merchant,
            "description": secret_desc,
        },
        headers=headers,
    )
    assert create_txn.status_code == 201
    txn_id = create_txn.json()["id"]

    # 1. Verify that read via API decrypts correctly
    api_get = await client.get(f"/api/v1/transactions/{txn_id}", headers=headers)
    assert api_get.status_code == 200
    matched_txn = api_get.json()
    assert matched_txn["merchant_raw"] == secret_merchant
    assert matched_txn["description"] == secret_desc

    # 2. Inspect raw database column to verify it is encrypted ciphertext at rest
    async with TestingSessionLocal() as session:
        raw_res = await session.execute(
            text("SELECT merchant_raw, description FROM transactions WHERE id = :id"),
            {"id": txn_id},
        )
        row = raw_res.first()
        raw_db_merchant, raw_db_desc = row[0], row[1]

        # Fernet ciphertexts start with 'gAAAAA'
        assert raw_db_merchant != secret_merchant
        assert raw_db_merchant.startswith("gAAAAA")
        assert raw_db_desc != secret_desc
        assert raw_db_desc.startswith("gAAAAA")


@pytest.mark.asyncio
async def test_data_minimization():
    """Promise 2: Discard OTPs, mask card numbers, strip balances."""
    # Test OTP filtering
    assert is_otp_or_promo("Your OTP is 492019. Do not share this with anyone.") is True
    assert is_otp_or_promo("Congratulations! You are pre-approved for a personal loan of 5 lakhs.") is True
    assert is_otp_or_promo("Your e-statement has been generated for month October.") is True
    assert is_otp_or_promo("Rs 450 debited to Swiggy on 03-Nov-26.") is False

    # Test sensitive text sanitization & balance stripping
    dirty_text = "Paid to merchant via card 4532 0192 8841 9012. Avl Bal: Rs 42,150.00."
    clean = sanitize_financial_text(dirty_text)
    assert "42,150" not in clean
    assert "4532 0192 8841 9012" not in clean
    assert "••••9012" in clean

    # Test parsing single SMS
    parsed = parse_single_sms(
        "HDFC Bank: Rs 849.00 debited from a/c **4589 on 03-Nov-26 to SWIGGY. Avl bal: Rs 42,150.00.",
        "acc-123",
    )
    assert parsed is not None
    assert parsed["amount_minor"] == 84900
    assert parsed["direction"] == "debit"
    assert parsed["last4"] == "4589"
    assert "42,150" not in parsed["merchant_raw"]


@pytest.mark.asyncio
async def test_user_data_export_and_wipe(client: AsyncClient):
    """Promise 4 & Data Control: GET /users/me/export and DELETE /users/me/data."""
    email = "wipe_user@example.com"
    pwd = "SecurePassword123!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "Wipe User"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create account and consent
    acc_res = await client.post(
        "/api/v1/accounts",
        json={"name": "SBI Savings", "type": "savings", "last4": "9901", "opening_balance_minor": 200000},
        headers=headers,
    )
    account_id = acc_res.json()["id"]

    await client.post(
        "/api/v1/consents",
        json={"consent_type": "statement_upload", "policy_version": "1.0"},
        headers=headers,
    )

    # Export my data
    export_res = await client.get("/api/v1/users/me/export", headers=headers)
    assert export_res.status_code == 200
    export_data = export_res.json()
    assert export_data["export_metadata"]["user_email"] == email
    assert len(export_data["accounts"]) == 1
    assert export_data["accounts"][0]["id"] == account_id
    assert len(export_data["consents"]) == 1

    # Attempt wipe with invalid password
    bad_wipe = await client.request("DELETE", "/api/v1/users/me/data", json={"password": "WrongPassword"}, headers=headers)
    assert bad_wipe.status_code == 401

    # Wipe with correct password
    good_wipe = await client.request("DELETE", "/api/v1/users/me/data", json={"password": pwd}, headers=headers)
    assert good_wipe.status_code == 200

    # Verify accounts are wiped
    acc_check = await client.get("/api/v1/accounts", headers=headers)
    assert acc_check.status_code == 200
    assert len(acc_check.json()) == 0
