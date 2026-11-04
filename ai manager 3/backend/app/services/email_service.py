import asyncio
import logging
from email.message import EmailMessage
from typing import Optional, Tuple
import aiosmtplib
import httpx
from app.core.config import settings

logger = logging.getLogger("finance_app.email")


def mask_email(email: str) -> str:
    """Mask email for privacy, e.g. a***@gmail.com or j***e@domain.com."""
    if not email or "@" not in email:
        return "***@***.***"
    parts = email.split("@", 1)
    user, domain = parts[0], parts[1]
    if len(user) <= 2:
        masked_user = user[0] + "***"
    else:
        masked_user = user[0] + "***" + user[-1]
    return f"{masked_user}@{domain}"


def mask_phone(phone: Optional[str]) -> str:
    """Mask phone number for privacy, e.g. +91 ******3210."""
    if not phone:
        return "+91 ******0000"
    clean = phone.strip()
    if len(clean) >= 10:
        prefix = clean[:3] if clean.startswith("+") else ""
        last4 = clean[-4:]
        return f"{prefix} ******{last4}".strip()
    return "******" + clean[-2:] if len(clean) >= 2 else "******"


async def send_email(to: str, subject: str, html: str, text: str) -> bool:
    """
    Asynchronously send an email using the configured provider.
    Returns True if sent successfully, False otherwise.
    """
    success, _ = await send_email_detailed(to, subject, html, text)
    return success


async def send_email_detailed(to: str, subject: str, html: str, text: str) -> Tuple[bool, Optional[str]]:
    """
    Asynchronously send an email using the configured provider.
    Providers: console | smtp | resend | sendgrid | brevo.
    Returns: (success: bool, error_message: Optional[str])
    Includes retry with exponential backoff on transient network failures.
    """
    provider = settings.active_email_provider
    masked = mask_email(to)
    logger.info("Dispatching email via provider '%s' to %s", provider, masked)

    # 1. Console Provider (development / testing fallback)
    if provider == "console":
        separator = "=" * 64
        console_output = (
            f"\n{separator}\n"
            f"[CONSOLE EMAIL DISPATCH - DEV ONLY]\n"
            f"To:      {to}\n"
            f"Subject: {subject}\n"
            f"From:    {settings.EMAIL_FROM_NAME} <{settings.active_email_from}>\n"
            f"----------------------------------------------------------------\n"
            f"{text}\n"
            f"{separator}\n"
        )
        print(console_output)
        return True, None

    last_error: Optional[str] = None
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            if provider == "smtp":
                smtp_user = settings.active_smtp_user
                smtp_pass = settings.active_smtp_pass
                if not settings.SMTP_HOST:
                    return False, "SMTP_HOST is not configured."

                msg = EmailMessage()
                msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.active_email_from}>"
                msg["To"] = to
                msg["Subject"] = subject
                msg.set_content(text)
                msg.add_alternative(html, subtype="html")

                port = settings.SMTP_PORT
                # Handle Port 465 (Direct SSL) vs Port 587 (STARTTLS)
                use_tls = (port == 465)
                start_tls = (port == 587) if not use_tls else False
                if port not in (465, 587):
                    start_tls = settings.SMTP_USE_TLS

                await aiosmtplib.send(
                    msg,
                    hostname=settings.SMTP_HOST,
                    port=port,
                    username=smtp_user or None,
                    password=smtp_pass or None,
                    use_tls=use_tls,
                    start_tls=start_tls,
                    timeout=15,
                )
                logger.info("Successfully sent SMTP email to %s", masked)
                return True, None

            elif provider == "resend":
                if not settings.RESEND_API_KEY:
                    return False, "RESEND_API_KEY is not configured."
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        "https://api.resend.com/emails",
                        headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                        json={
                            "from": f"{settings.EMAIL_FROM_NAME} <{settings.active_email_from}>",
                            "to": [to],
                            "subject": subject,
                            "html": html,
                            "text": text,
                        },
                    )
                    if resp.status_code >= 400:
                        error_detail = resp.text
                        logger.error("Resend API returned status %d: %s", resp.status_code, error_detail)
                        return False, f"Resend error ({resp.status_code}): {error_detail}"
                logger.info("Successfully sent Resend email to %s", masked)
                return True, None

            elif provider == "sendgrid":
                if not settings.SENDGRID_API_KEY:
                    return False, "SENDGRID_API_KEY is not configured."
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        "https://api.sendgrid.com/v3/mail/send",
                        headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
                        json={
                            "personalizations": [{"to": [{"email": to}]}],
                            "from": {"email": settings.active_email_from, "name": settings.EMAIL_FROM_NAME},
                            "subject": subject,
                            "content": [
                                {"type": "text/plain", "value": text},
                                {"type": "text/html", "value": html},
                            ],
                        },
                    )
                    if resp.status_code >= 400:
                        error_detail = resp.text
                        logger.error("SendGrid API returned status %d: %s", resp.status_code, error_detail)
                        return False, f"SendGrid error ({resp.status_code}): {error_detail}"
                logger.info("Successfully sent SendGrid email to %s", masked)
                return True, None

            elif provider == "brevo":
                if not settings.BREVO_API_KEY:
                    return False, "BREVO_API_KEY is not configured."
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        "https://api.brevo.com/v3/smtp/email",
                        headers={"api-key": settings.BREVO_API_KEY},
                        json={
                            "sender": {"email": settings.active_email_from, "name": settings.EMAIL_FROM_NAME},
                            "to": [{"email": to}],
                            "subject": subject,
                            "htmlContent": html,
                            "textContent": text,
                        },
                    )
                    if resp.status_code >= 400:
                        error_detail = resp.text
                        logger.error("Brevo API returned status %d: %s", resp.status_code, error_detail)
                        return False, f"Brevo error ({resp.status_code}): {error_detail}"
                logger.info("Successfully sent Brevo email to %s", masked)
                return True, None

            else:
                logger.error("Unknown OTP_EMAIL_PROVIDER: %s. Defaulting to console log.", provider)
                print(f"[CONSOLE EMAIL FALLBACK] To: {to} | Code/Subject: {subject}\n{text}")
                return True, None

        except aiosmtplib.SMTPAuthenticationError as exc:
            last_error = f"SMTP Authentication failed (Check SMTP username & App Password): {exc}"
            logger.error("SMTP Auth Error for %s: %s", masked, last_error)
            return False, last_error
        except aiosmtplib.SMTPConnectError as exc:
            last_error = f"SMTP Connection failed to {settings.SMTP_HOST}:{settings.SMTP_PORT}: {exc}"
            logger.warning("Attempt %d failed to connect to SMTP: %s", attempt + 1, last_error)
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {str(exc)}"
            logger.warning("Attempt %d failed to send email to %s: %s", attempt + 1, masked, last_error)

        if attempt < max_retries:
            await asyncio.sleep(0.5 * (2 ** attempt))
        else:
            logger.error("All %d retries failed for email to %s: %s", max_retries + 1, masked, last_error)
            return False, last_error
    return False, last_error


# ------------------------------------------------------------------------------
# Email Templates (Responsive HTML + Plain Text Fallback)
# ------------------------------------------------------------------------------

def get_otp_email_template(
    code: str,
    purpose_line: str,
    request_time: str,
    device_ip: str = "127.0.0.1",
) -> Tuple[str, str, str]:
    """
    Returns (subject, html, text) for a 6-digit verification code.
    Strictly minimal context with no sensitive account or balance numbers.
    """
    subject = "Your FinTrack AI verification code"

    text = f"""FinTrack AI Verification Code
------------------------------------
Your one-time verification code is: {code}

Use this code {purpose_line}.
Valid for 5 minutes.

Request details:
- Time: {request_time}
- Approximate IP: {device_ip}

Security Warning:
Never share this code with anyone. Our team will never ask for it.
If this wasn't you, please change your password immediately.
"""

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; padding: 32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 520px; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
          <!-- Header -->
          <tr>
            <td style="padding: 28px 32px 20px; border-bottom: 1px solid #f1f5f9; text-align: left;">
              <span style="font-size: 20px; font-weight: 800; color: #2563eb; letter-spacing: -0.5px;">FinTrack AI</span>
              <span style="display: block; font-size: 12px; color: #64748b; margin-top: 2px;">Security & Verification Service</span>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding: 32px;">
              <h2 style="font-size: 18px; font-weight: 700; color: #0f172a; margin: 0 0 12px;">Verification Code</h2>
              <p style="font-size: 14px; line-height: 22px; color: #475569; margin: 0 0 24px;">
                Use the verification code below {purpose_line}. This code is valid for <strong>5 minutes</strong>.
              </p>

              <!-- Code Box -->
              <div style="background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 24px;">
                <span style="font-family: 'Courier New', Courier, monospace; font-size: 34px; font-weight: 800; letter-spacing: 8px; color: #1e293b; display: inline-block;">
                  {code}
                </span>
                <span style="display: block; font-size: 11px; text-transform: uppercase; font-weight: 700; color: #64748b; margin-top: 8px; letter-spacing: 1px;">
                  Expires in 5 minutes
                </span>
              </div>

              <!-- Request metadata -->
              <table role="presentation" width="100%" style="font-size: 12px; color: #64748b; margin-bottom: 24px; border-collapse: collapse;">
                <tr>
                  <td style="padding: 4px 0;"><strong>Request Time:</strong></td>
                  <td align="right" style="padding: 4px 0; color: #334155;">{request_time}</td>
                </tr>
                <tr>
                  <td style="padding: 4px 0;"><strong>Approximate IP:</strong></td>
                  <td align="right" style="padding: 4px 0; color: #334155;">{device_ip}</td>
                </tr>
              </table>

              <!-- Security Warning -->
              <div style="background-color: #fff1f2; border: 1px solid #fecdd3; border-radius: 10px; padding: 14px; font-size: 12px; line-height: 18px; color: #9f1239;">
                <strong>Security Alert:</strong> Never share this code. Our team will never ask for it. If this was not initiated by you, please change your account password immediately.
              </div>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background-color: #f8fafc; padding: 20px 32px; border-top: 1px solid #f1f5f9; font-size: 11px; color: #94a3b8; text-align: center; line-height: 16px;">
              FinTrack AI Manager • Zero Knowledge Financial Encryption & Multi-Tenant Isolation
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    return subject, html, text


def get_new_login_alert(
    device_ip: str,
    login_time: str,
) -> Tuple[str, str, str]:
    """Informational security alert email for new login."""
    subject = "Security Alert: New Sign-In to your FinTrack AI Account"
    text = f"""FinTrack AI Security Alert: New Sign-In Detected
-------------------------------------------------------
We detected a new sign-in to your FinTrack AI account.

Sign-in details:
- Time: {login_time}
- Approximate IP: {device_ip}

Was this you?
If you just signed in, you can safely ignore this email.
If this wasn't you, your account may be compromised. Please sign in immediately and change your password.
"""
    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; background-color: #f8fafc; padding: 24px; color: #1e293b;">
  <div style="max-width: 500px; margin: auto; background: #ffffff; border-radius: 12px; padding: 24px; border: 1px solid #e2e8f0;">
    <h3 style="color: #2563eb; margin-top: 0;">FinTrack AI Security Alert</h3>
    <p>A new sign-in to your account was detected.</p>
    <ul>
      <li><strong>Time:</strong> {login_time}</li>
      <li><strong>Approximate IP:</strong> {device_ip}</li>
    </ul>
    <p style="font-size: 12px; color: #64748b;">If this was you, you can safely ignore this alert. If you did not sign in, change your password immediately.</p>
  </div>
</body>
</html>"""
    return subject, html, text


def get_account_change_alert(
    action: str,
    account_name: str,
    last4: Optional[str],
    action_time: str,
) -> Tuple[str, str, str]:
    """Informational alert when a bank account is linked or unlinked."""
    masked_acc = f"ending in {last4}" if last4 else ""
    subject = f"Security Alert: Bank Account {action.title()} on FinTrack AI"
    text = f"""FinTrack AI Security Alert: Bank Account {action.title()}
-----------------------------------------------------------
A bank account was {action} on your profile.

Details:
- Account: {account_name} {masked_acc}
- Time: {action_time}

If you made this change, no action is needed. If you did not make this change, please log in and contact support immediately.
"""
    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; background-color: #f8fafc; padding: 24px; color: #1e293b;">
  <div style="max-width: 500px; margin: auto; background: #ffffff; border-radius: 12px; padding: 24px; border: 1px solid #e2e8f0;">
    <h3 style="color: #2563eb; margin-top: 0;">FinTrack AI Security Alert</h3>
    <p>A bank account was <strong>{action}</strong> on your profile.</p>
    <ul>
      <li><strong>Account:</strong> {account_name} {masked_acc}</li>
      <li><strong>Time:</strong> {action_time}</li>
    </ul>
    <p style="font-size: 12px; color: #64748b;">If you made this change, no action is needed. If not, secure your account immediately.</p>
  </div>
</body>
</html>"""
    return subject, html, text


def get_security_settings_alert(
    setting_name: str,
    action_time: str,
) -> Tuple[str, str, str]:
    """Informational alert when security settings or password change."""
    subject = f"Security Alert: Your FinTrack AI {setting_name} was updated"
    text = f"""FinTrack AI Security Alert: Setting Updated
---------------------------------------------------
Your {setting_name} was recently modified.

- Time: {action_time}

If this was you, no action is required. If you did not authorize this, please reset your password immediately.
"""
    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; background-color: #f8fafc; padding: 24px; color: #1e293b;">
  <div style="max-width: 500px; margin: auto; background: #ffffff; border-radius: 12px; padding: 24px; border: 1px solid #e2e8f0;">
    <h3 style="color: #2563eb; margin-top: 0;">FinTrack AI Security Alert</h3>
    <p>Your <strong>{setting_name}</strong> was recently updated on {action_time}.</p>
    <p style="font-size: 12px; color: #64748b;">If you made this update, no action is needed. If not, please reset your password immediately.</p>
  </div>
</body>
</html>"""
    return subject, html, text

