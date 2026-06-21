import logging
import smtplib
from email.mime.text import MIMEText

from app.core.config import Settings


logger = logging.getLogger(__name__)


def send_email(
    *,
    to: str,
    subject: str,
    body: str,
    settings: Settings,
) -> None:
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to

    if not settings.smtp_host or settings.smtp_host == "localhost":
        logger.info("DEV MODE: Email suppressed. Contents:\nTo: %s\nSubject: %s\nBody:\n%s", to, subject, body)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password or "")
        server.send_message(msg)
