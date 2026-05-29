from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr
from hashlib import sha256
from pathlib import Path
import secrets
import smtplib
import socket

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import AuditLog, PasswordResetToken, User
from app.services.password_policy import PASSWORD_UNCHANGED_MESSAGE, ensure_password_not_current, validate_password_policy


PASSWORD_RESET_SAFE_MESSAGE = "If the account can receive password reset email, instructions will be sent."
PASSWORD_RESET_LINK_PATH = "/password-reset/confirm"
ACTIVE_USER_STATUS = "active"
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


def as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def mask_email(value: str | None) -> str:
    if not value or "@" not in value:
        return "***"
    name, domain = value.split("@", maxsplit=1)
    if len(name) <= 2:
        return f"{name[:1]}***@{domain}"
    return f"{name[:2]}***@{domain}"


def truncate_user_agent(value: str | None) -> str | None:
    if not value:
        return None
    return value[:255]


def reset_link(token: str) -> str:
    base_url = settings.public_frontend_base_url.rstrip("/")
    return f"{base_url}{PASSWORD_RESET_LINK_PATH}?token={token}"


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


def ensure_password_reset_email_ready() -> None:
    issues = email_delivery_configuration_issues(include_disabled=True)
    if not issues:
        return
    code = "EMAIL_PROVIDER_NOT_CONFIGURED"
    if "EMAIL_PROVIDER_DISABLED" in issues:
        code = "EMAIL_PROVIDER_DISABLED"
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": code, "message": "Password reset delivery is not configured"},
    )


def write_auth_audit(
    db: Session,
    *,
    action: str,
    user_id: int | None = None,
    object_id: str | None = None,
    detail: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            module="auth",
            action=action,
            object_type="password_reset",
            object_id=object_id,
            detail_json=detail or {},
        )
    )


def find_reset_user(db: Session, email_or_username: str) -> User | None:
    identifier = email_or_username.strip()
    if not identifier:
        return None
    email_identifier = identifier.lower()
    return db.scalar(
        select(User)
        .where(or_(User.username == identifier, func.lower(User.email) == email_identifier))
        .order_by(User.id.asc())
        .limit(1)
    )


def can_reset_password(user: User | None) -> bool:
    return bool(user and user.status == ACTIVE_USER_STATUS and user.email)


def send_password_reset_notification(recipient: str, token: str) -> bool:
    provider = settings.email_provider.strip().lower()
    if provider == "disabled":
        return False
    subject = "Portal password reset"
    body = (
        "A password reset was requested for your Portal account.\n\n"
        f"Reset link: {reset_link(token)}\n\n"
        f"This link expires in {settings.password_reset_token_ttl_minutes} minutes.\n"
        "If you did not request this change, ignore this email and keep your current password.\n"
    )
    if provider == "dev_outbox":
        write_dev_outbox(recipient, subject, body)
        return True
    if provider == "smtp":
        send_smtp_message(recipient, subject, body)
        return True
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Password reset delivery is not configured")


def write_dev_outbox(recipient: str, subject: str, body: str) -> None:
    outbox_dir = Path(settings.password_reset_dev_outbox_dir)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{now_utc().strftime('%Y%m%d%H%M%S%f')}-{hash_reset_token(recipient)}.txt"
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
    ensure_password_reset_email_ready()
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


def create_password_reset_request(
    db: Session,
    *,
    email_or_username: str,
    request_ip: str | None,
    user_agent: str | None,
) -> dict[str, str]:
    if not settings.password_reset_enabled:
        return {"message": PASSWORD_RESET_SAFE_MESSAGE}

    user = find_reset_user(db, email_or_username)
    if not can_reset_password(user):
        write_auth_audit(db, action="password_reset_request", detail={"eligible": False})
        db.commit()
        return {"message": PASSWORD_RESET_SAFE_MESSAGE}

    assert user is not None
    token = generate_reset_token()
    expires_at = now_utc() + timedelta(minutes=settings.password_reset_token_ttl_minutes)
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.consumed_at.is_(None))
        .values(consumed_at=now_utc())
    )
    item = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(token),
        expires_at=expires_at,
        request_ip=request_ip,
        user_agent=truncate_user_agent(user_agent),
    )
    db.add(item)
    db.flush()

    try:
        sent = send_password_reset_notification(user.email or "", token)
    except HTTPException:
        item.consumed_at = now_utc()
        write_auth_audit(
            db,
            action="password_reset_delivery_failed",
            user_id=user.id,
            object_id=str(item.id),
            detail={"provider": settings.email_provider},
        )
        db.commit()
        return {"message": PASSWORD_RESET_SAFE_MESSAGE}

    if not sent:
        item.consumed_at = now_utc()

    write_auth_audit(
        db,
        action="password_reset_request",
        user_id=user.id,
        object_id=str(item.id),
        detail={"recipient": mask_email(user.email), "provider": settings.email_provider, "sent": sent},
    )
    db.commit()
    return {"message": PASSWORD_RESET_SAFE_MESSAGE}


def confirm_password_reset(db: Session, *, token: str, new_password: str) -> dict[str, str]:
    token_hash = hash_reset_token(token.strip())
    item = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash).limit(1))
    if not item or item.consumed_at is not None:
        write_auth_audit(db, action="password_reset_confirm_failed", detail={"reason": "invalid"})
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password reset token")

    if as_aware_utc(item.expires_at) <= now_utc():
        item.consumed_at = now_utc()
        write_auth_audit(db, action="password_reset_confirm_failed", user_id=item.user_id, object_id=str(item.id), detail={"reason": "expired"})
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password reset token expired")

    user = db.get(User, item.user_id)
    if not can_reset_password(user):
        item.consumed_at = now_utc()
        write_auth_audit(db, action="password_reset_confirm_failed", user_id=item.user_id, object_id=str(item.id), detail={"reason": "account_unavailable"})
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password reset token")

    assert user is not None
    try:
        validate_password_policy(new_password)
        ensure_password_not_current(new_password, user.password_hash)
    except HTTPException as error:
        reason = "same_current_password" if error.detail == PASSWORD_UNCHANGED_MESSAGE else "password_policy"
        write_auth_audit(db, action="password_reset_confirm_failed", user_id=user.id, object_id=str(item.id), detail={"reason": reason})
        db.commit()
        raise

    user.password_hash = hash_password(new_password)
    item.consumed_at = now_utc()
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != item.id,
            PasswordResetToken.consumed_at.is_(None),
        )
        .values(consumed_at=now_utc())
    )
    write_auth_audit(db, action="password_reset_confirm", user_id=user.id, object_id=str(item.id), detail={"result": "success"})
    db.commit()
    return {"message": "Password has been reset"}
