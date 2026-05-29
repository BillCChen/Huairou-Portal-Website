from __future__ import annotations

from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import formataddr
from hashlib import sha256
from pathlib import Path
import smtplib
import socket

from fastapi import HTTPException, status

from app.core.config import settings


SMTP_SAFE_ERROR_MAP = {
    smtplib.SMTPAuthenticationError: "smtp_authentication_failed",
    smtplib.SMTPConnectError: "smtp_connect_failed",
    smtplib.SMTPServerDisconnected: "smtp_disconnected",
    smtplib.SMTPRecipientsRefused: "smtp_recipient_refused",
    smtplib.SMTPSenderRefused: "smtp_sender_refused",
    smtplib.SMTPDataError: "smtp_data_rejected",
    smtplib.SMTPException: "smtp_error",
    TimeoutError: "smtp_timeout",
    socket.timeout: "smtp_timeout",
    OSError: "smtp_network_error",
}


def now_utc() -> datetime:
    return datetime.now(UTC)


def mask_email(value: str | None) -> str:
    if not value or "@" not in value:
        return "***"
    name, domain = value.split("@", maxsplit=1)
    if len(name) <= 2:
        return f"{name[:1]}***@{domain}"
    return f"{name[:2]}***@{domain}"


def email_delivery_configuration_issues(*, include_disabled: bool = True) -> list[str]:
    provider = settings.email_provider.strip().lower()
    issues: list[str] = []
    if provider == "disabled":
        if include_disabled:
            issues.append("EMAIL_PROVIDER_DISABLED")
        return issues
    if provider == "dev_outbox":
        return issues
    if provider != "smtp":
        issues.append("EMAIL_PROVIDER_UNSUPPORTED")
        return issues

    if not settings.smtp_host:
        issues.append("SMTP_HOST_REQUIRED")
    if not settings.smtp_from_email:
        issues.append("SMTP_FROM_EMAIL_REQUIRED")
    if settings.smtp_use_tls and settings.smtp_use_starttls:
        issues.append("SMTP_TLS_MODE_CONFLICT")
    if settings.smtp_require_auth and (not settings.smtp_username or not settings.smtp_password):
        issues.append("SMTP_AUTH_CREDENTIALS_REQUIRED")
    if not settings.public_frontend_base_url:
        issues.append("PUBLIC_FRONTEND_BASE_URL_REQUIRED")
    return issues


def ensure_email_delivery_ready(*, message: str = "Email delivery is not configured") -> None:
    issues = email_delivery_configuration_issues(include_disabled=True)
    if not issues:
        return
    code = "EMAIL_PROVIDER_NOT_CONFIGURED"
    if "EMAIL_PROVIDER_DISABLED" in issues:
        code = "EMAIL_PROVIDER_DISABLED"
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": code, "message": message},
    )


def write_dev_outbox(recipient: str, subject: str, body: str) -> None:
    outbox_dir = Path(settings.password_reset_dev_outbox_dir)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{now_utc().strftime('%Y%m%d%H%M%S%f')}-{sha256(recipient.encode('utf-8')).hexdigest()}.txt"
    (outbox_dir / safe_name).write_text(f"To: {recipient}\nSubject: {subject}\n\n{body}", encoding="utf-8")


def build_email_message(recipient: str, subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    sender = settings.smtp_from_email or ""
    message["From"] = formataddr((settings.smtp_from_name, sender)) if settings.smtp_from_name else sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    return message


def safe_delivery_error(error: BaseException) -> str:
    for error_type, code in SMTP_SAFE_ERROR_MAP.items():
        if isinstance(error, error_type):
            return code
    return error.__class__.__name__


def send_smtp_message(recipient: str, subject: str, body: str) -> None:
    ensure_email_delivery_ready()
    message = build_email_message(recipient, subject, body)
    timeout = settings.smtp_timeout_seconds
    smtp_class = smtplib.SMTP_SSL if settings.smtp_use_tls else smtplib.SMTP
    try:
        with smtp_class(settings.smtp_host, settings.smtp_port, timeout=timeout) as client:
            if getattr(client, "sock", None) is not None:
                client.sock.settimeout(timeout)
            if settings.smtp_use_starttls and not settings.smtp_use_tls:
                client.starttls()
                if getattr(client, "sock", None) is not None:
                    client.sock.settimeout(timeout)
            if settings.smtp_require_auth:
                client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "EMAIL_DELIVERY_FAILED", "message": safe_delivery_error(error)},
        ) from None


def send_plaintext_email(recipient: str, subject: str, body: str) -> bool:
    provider = settings.email_provider.strip().lower()
    if provider == "disabled":
        return False
    if provider == "dev_outbox":
        write_dev_outbox(recipient, subject, body)
        return True
    if provider == "smtp":
        send_smtp_message(recipient, subject, body)
        return True
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Email delivery is not configured")
