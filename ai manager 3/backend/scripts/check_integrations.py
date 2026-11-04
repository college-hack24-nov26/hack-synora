#!/usr/bin/env python3
"""
CLI Script to check external integration health and latency.
Usage:
    python -m scripts.check_integrations [--email user@example.com] [--phone +919876543210]
"""

import argparse
import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.integration_health_service import run_all_health_checks
from app.core.config import settings


def format_status(status_str: str) -> str:
    if status_str.lower() in ("ok", "healthy"):
        return f"\033[92m{status_str.upper()}\033[0m"
    elif status_str.lower() == "degraded":
        return f"\033[93m{status_str.upper()}\033[0m"
    else:
        return f"\033[91m{status_str.upper()}\033[0m"


async def main():
    parser = argparse.ArgumentParser(description="Check FinTrack AI Integrations Health (Email, SMS, LLM)")
    parser.add_argument("--email", type=str, help="Recipient email address to test sending verification email")
    parser.add_argument("--phone", type=str, help="Recipient phone number (E.164 e.g. +919876543210) to test sending SMS OTP")
    args = parser.parse_args()

    print("=" * 65)
    print(" FinTrack AI - External Integrations Health & Diagnostic Suite")
    print("=" * 65)
    print(f" Environment : {settings.ENVIRONMENT}")
    print(f" LLM Provider: {settings.LLM_PROVIDER}")
    print(f" Email OTP   : {settings.OTP_EMAIL_PROVIDER}")
    print(f" SMS OTP     : {settings.OTP_SMS_PROVIDER}")
    print("-" * 65)
    print("Running diagnostic tests...\n")

    report = await run_all_health_checks(test_email=args.email, test_phone=args.phone)

    # 1. Email Report
    email_res = report["email"]
    print(f"[EMAIL] Provider: {email_res['provider']} | Status: {format_status(email_res['status'])} | Latency: {email_res['latency_ms']}ms")
    print(f"        Message : {email_res['message']}")

    # 2. SMS Report
    sms_res = report["sms"]
    print(f"[SMS]   Provider: {sms_res['provider']} | Status: {format_status(sms_res['status'])} | Latency: {sms_res['latency_ms']}ms")
    print(f"        Message : {sms_res['message']}")

    # 3. LLM Report
    llm_res = report["llm"]
    print(f"[LLM]   Provider: {llm_res['provider']} | Status: {format_status(llm_res['status'])} | Latency: {llm_res['latency_ms']}ms")
    print(f"        Models  : Fast={llm_res.get('model_fast')} | Smart={llm_res.get('model_smart')}")
    print(f"        Message : {llm_res['message']}")

    print("-" * 65)
    print(f"OVERALL SYSTEM INTEGRATION STATUS: {format_status(report['status'])}")
    print("=" * 65)

    if report["status"] == "unhealthy":
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

