"""Async SMTP helper for email OTP delivery."""

from __future__ import annotations

import logging
import os

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _build_html_body(code: str) -> str:
    return f"""\
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Код подтверждения ICS</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f6f8;padding:32px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="480" cellspacing="0" cellpadding="0"
               style="background:#ffffff;border-radius:12px;padding:32px;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
          <tr>
            <td style="text-align:center;">
              <h1 style="margin:0 0 8px;font-size:22px;color:#111827;">ICS</h1>
              <p style="margin:0 0 24px;font-size:15px;color:#6b7280;line-height:1.5;">
                Ваш код подтверждения для входа в систему ics:
              </p>
              <div style="display:inline-block;padding:16px 32px;background:#eef2ff;border-radius:8px;
                          font-size:32px;font-weight:700;letter-spacing:8px;color:#3730a3;">
                {code}
              </div>
              <p style="margin:24px 0 0;font-size:13px;color:#9ca3af;line-height:1.5;">
                Код действителен 5 минут. Если вы не запрашивали вход — просто проигнорируйте это письмо.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


async def send_verification_email(to_email: str, code: str) -> bool:
    """Send a 4-digit verification code to the given email address."""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port_raw = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all([smtp_server, smtp_user, smtp_password]):
        logger.error("SMTP credentials are not fully configured (SMTP_SERVER/USER/PASSWORD).")
        return False

    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        logger.error("Invalid SMTP_PORT value: %r", smtp_port_raw)
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = "Код подтверждения ICS"
    message["From"] = smtp_user
    message["To"] = to_email

    plain_text = f"Ваш код подтверждения для входа в систему ics: {code}"
    message.attach(MIMEText(plain_text, "plain", "utf-8"))
    message.attach(MIMEText(_build_html_body(code), "html", "utf-8"))

    try:
        await aiosmtplib.send(
            message,
            hostname=smtp_server,
            port=smtp_port,
            username=smtp_user,
            password=smtp_password,
            start_tls=True,
        )
        logger.info("Verification email sent to %s", to_email)
        return True
    except aiosmtplib.SMTPException:
        logger.exception("SMTP error while sending verification email to %s", to_email)
        return False
    except OSError:
        logger.exception("Network error while sending verification email to %s", to_email)
        return False
