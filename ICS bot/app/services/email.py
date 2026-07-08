"""Async SMTP helper for email OTP delivery."""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
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


def _send_via_smtp(
    *,
    smtp_server: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    message: MIMEMultipart,
) -> None:
    """Blocking SMTP send — SSL on 465, STARTTLS on other ports."""
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as smtp:
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(message)
        return

    with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)


async def send_verification_email(to_email: str, code: str) -> bool:
    """Send a 4-digit verification code to the given email address."""
    smtp_server = (os.getenv("SMTP_SERVER") or "").strip()
    smtp_port_raw = (os.getenv("SMTP_PORT") or "465").strip()
    smtp_user = (os.getenv("SMTP_USER") or "").strip()
    smtp_password = (os.getenv("SMTP_PASSWORD") or "").strip()

    if not all([smtp_server, smtp_user, smtp_password]):
        logger.error("SMTP credentials are not fully configured (SMTP_SERVER/USER/PASSWORD).")
        return False

    try:
        preferred_port = int(smtp_port_raw)
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

    alt_port = 587 if preferred_port == 465 else 465
    ports_to_try = [preferred_port]
    if alt_port not in ports_to_try:
        ports_to_try.append(alt_port)

    last_error: Exception | None = None
    for smtp_port in ports_to_try:
        logger.info(
            "Sending verification email via %s:%s as %s to %s",
            smtp_server,
            smtp_port,
            smtp_user,
            to_email,
        )
        try:
            await asyncio.to_thread(
                _send_via_smtp,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                message=message,
            )
            logger.info("Verification email sent to %s via port %s", to_email, smtp_port)
            return True
        except smtplib.SMTPAuthenticationError:
            logger.exception(
                "SMTP authentication failed for user=%s on %s:%s",
                smtp_user,
                smtp_server,
                smtp_port,
            )
            return False
        except (smtplib.SMTPException, OSError) as exc:
            last_error = exc
            logger.exception(
                "SMTP attempt failed on %s:%s for %s",
                smtp_server,
                smtp_port,
                to_email,
            )

    if last_error is not None:
        logger.error("All SMTP attempts failed for %s: %s", to_email, last_error)
    return False
