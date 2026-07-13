"""
Transactional email via Resend.

When `RESEND_API_KEY` is unset the sender falls back to logging the message
instead of sending it, so password reset works end-to-end in local development
without an email provider. Outside DEBUG that fallback is a misconfiguration —
it is logged as an error, not silently ignored.
"""

import httpx

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_RESEND_API = "https://api.resend.com/emails"


async def send_email(to: str, subject: str, html: str, text: str) -> bool:
    """
    Send one email. Returns True if it was handed to the provider.

    Never raises: callers (password reset) must not leak provider failures to
    the client, and must not fail the request because mail is down.
    """
    settings = get_settings()

    if not settings.RESEND_API_KEY:
        log = logger.info if settings.DEBUG else logger.error
        log(
            "email_not_sent_no_provider_configured",
            to=to,
            subject=subject,
            # In dev this is how you get the reset link; in prod it's a red flag.
            body_preview=text,
        )
        return False

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                _RESEND_API,
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={
                    "from": settings.EMAIL_FROM,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "text": text,
                },
            )
        if response.status_code >= 400:
            logger.error(
                "email_send_failed",
                to=to,
                status=response.status_code,
                body=response.text[:300],
            )
            return False

        logger.info("email_sent", to=to, subject=subject)
        return True

    except Exception as e:
        logger.error("email_send_error", to=to, error=str(e))
        return False


async def send_password_reset(to: str, name: str, reset_url: str) -> bool:
    """Send the password-reset link."""
    settings = get_settings()
    minutes = settings.PASSWORD_RESET_EXPIRE_MINUTES

    subject = "Reset your Exyst password"
    text = (
        f"Hi {name},\n\n"
        f"Use the link below to choose a new Exyst password. "
        f"It expires in {minutes} minutes and can only be used once.\n\n"
        f"{reset_url}\n\n"
        "If you didn't request this, you can ignore this email — your password "
        "will stay the same.\n"
    )
    html = f"""\
<div style="font-family:system-ui,sans-serif;line-height:1.6;color:#111">
  <h2 style="margin:0 0 16px">Reset your Exyst password</h2>
  <p>Hi {name},</p>
  <p>Use the button below to choose a new password. It expires in
     {minutes} minutes and can only be used once.</p>
  <p style="margin:24px 0">
    <a href="{reset_url}"
       style="background:#6366f1;color:#fff;padding:12px 20px;border-radius:8px;
              text-decoration:none;font-weight:600">Reset password</a>
  </p>
  <p style="color:#666;font-size:14px">
    If you didn't request this, you can ignore this email — your password will
    stay the same.
  </p>
</div>"""

    return await send_email(to=to, subject=subject, html=html, text=text)
