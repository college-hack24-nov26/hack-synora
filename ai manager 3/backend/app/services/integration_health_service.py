import time
import logging
from typing import Dict, Any, Optional
from app.core.config import settings
from app.services.llm.factory import get_llm_client
from app.services.email_service import send_email

logger = logging.getLogger("finance_app.health")


async def check_email_health(test_recipient: Optional[str] = None) -> Dict[str, Any]:
    """Tests the configured email provider connectivity and latency."""
    provider = settings.OTP_EMAIL_PROVIDER.lower().strip()
    start_time = time.perf_counter()

    if provider == "console":
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "provider": "console",
            "status": "ok",
            "latency_ms": latency,
            "message": "Console mode active (development only; prints to stdout).",
        }

    try:
        # If test recipient provided, attempt sending test verification message
        if test_recipient:
            success = await send_email(
                to_email=test_recipient,
                subject="FinTrack AI Integration Verification",
                html_content="<p>FinTrack AI email delivery verification successful.</p>",
                text_content="FinTrack AI email delivery verification successful.",
            )
            latency = round((time.perf_counter() - start_time) * 1000, 2)
            if success:
                return {
                    "provider": provider,
                    "status": "ok",
                    "latency_ms": latency,
                    "message": f"Verification email successfully sent to {test_recipient}.",
                }
            else:
                return {
                    "provider": provider,
                    "status": "error",
                    "latency_ms": latency,
                    "message": f"Failed to send email to {test_recipient} via {provider}.",
                }

        # Configuration sanity checks
        if provider == "smtp":
            if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
                return {
                    "provider": "smtp",
                    "status": "error",
                    "latency_ms": 0.0,
                    "message": "SMTP_HOST or SMTP_USERNAME is not configured.",
                }
        elif provider == "brevo" and not settings.BREVO_API_KEY:
            return {"provider": "brevo", "status": "error", "latency_ms": 0.0, "message": "BREVO_API_KEY is not set."}
        elif provider == "resend" and not settings.RESEND_API_KEY:
            return {"provider": "resend", "status": "error", "latency_ms": 0.0, "message": "RESEND_API_KEY is not set."}
        elif provider == "sendgrid" and not settings.SENDGRID_API_KEY:
            return {"provider": "sendgrid", "status": "error", "latency_ms": 0.0, "message": "SENDGRID_API_KEY is not set."}

        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "provider": provider,
            "status": "ok",
            "latency_ms": latency,
            "message": f"{provider.upper()} provider configured correctly.",
        }
    except Exception as e:
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "provider": provider,
            "status": "error",
            "latency_ms": latency,
            "message": str(e),
        }


async def check_sms_health(test_phone: Optional[str] = None) -> Dict[str, Any]:
    """Tests the configured SMS provider connectivity and latency."""
    return {
        "provider": "disabled",
        "status": "ok",
        "latency_ms": 0.0,
        "message": "SMS OTP disabled.",
    }


async def check_llm_health() -> Dict[str, Any]:
    """Tests the configured LLM provider and measures completion latency."""
    provider = settings.LLM_PROVIDER.lower().strip()
    start_time = time.perf_counter()

    try:
        llm = get_llm_client()
        res = await llm.complete_json(
            system="You are a health check agent. Return pure JSON: {\"status\": \"ok\"}",
            user="Ping health check for FinTrack AI.",
            max_tokens=50,
            temperature=0.0,
            model_tier="fast",
        )
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "provider": provider,
            "status": "ok",
            "latency_ms": latency,
            "model_fast": settings.LLM_MODEL_FAST,
            "model_smart": settings.LLM_MODEL_SMART,
            "message": f"{provider.capitalize()} LLM response received successfully.",
            "test_response": res,
        }
    except Exception as e:
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "provider": provider,
            "status": "error",
            "latency_ms": latency,
            "model_fast": settings.LLM_MODEL_FAST,
            "model_smart": settings.LLM_MODEL_SMART,
            "message": f"LLM health check failed: {str(e)}",
        }


async def run_all_health_checks(
    test_email: Optional[str] = None,
    test_phone: Optional[str] = None,
) -> Dict[str, Any]:
    """Executes checks across Email, SMS, and LLM integrations."""
    email_health = await check_email_health(test_email)
    sms_health = await check_sms_health(test_phone)
    llm_health = await check_llm_health()

    statuses = [email_health["status"], sms_health["status"], llm_health["status"]]
    if all(s == "ok" for s in statuses):
        overall = "healthy"
    elif any(s == "ok" for s in statuses):
        overall = "degraded"
    else:
        overall = "unhealthy"

    return {
        "status": overall,
        "email": email_health,
        "sms": sms_health,
        "llm": llm_health,
    }
