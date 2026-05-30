from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import secrets

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import AuditLog, PasswordResetToken, User
from app.services.account_notifications import send_password_changed_notification
from app.services.email_notifications import email_delivery_configuration_issues, ensure_email_delivery_ready, mask_email, send_plaintext_email
from app.services.password_policy import PASSWORD_UNCHANGED_MESSAGE, ensure_password_not_current, validate_password_policy
from app.services.request_context import current_request_meta


PASSWORD_RESET_SAFE_MESSAGE = "If the account can receive password reset email, instructions will be sent."
PASSWORD_RESET_LINK_PATH = "/password-reset/confirm"
ACTIVE_USER_STATUS = "active"


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


def truncate_user_agent(value: str | None) -> str | None:
    if not value:
        return None
    return value[:255]


def reset_link(token: str) -> str:
    base_url = settings.public_frontend_base_url.rstrip("/")
    return f"{base_url}{PASSWORD_RESET_LINK_PATH}?token={token}"


def ensure_password_reset_email_ready() -> None:
    ensure_email_delivery_ready(message="Password reset delivery is not configured")


def write_auth_audit(
    db: Session,
    *,
    action: str,
    user_id: int | None = None,
    object_id: str | None = None,
    detail: dict | None = None,
) -> None:
    meta = current_request_meta()
    db.add(
        AuditLog(
            user_id=user_id,
            module="auth",
            action=action,
            object_type="password_reset",
            object_id=object_id,
            detail_json=detail or {},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
            path=meta.path,
            method=meta.method,
            result="failure" if action.endswith("_failed") else "success",
            failure_reason=(detail or {}).get("reason") if action.endswith("_failed") else None,
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
    subject = "Portal password reset"
    body = (
        "A password reset was requested for your Portal account.\n\n"
        f"Reset link: {reset_link(token)}\n\n"
        f"This link expires in {settings.password_reset_token_ttl_minutes} minutes.\n"
        "If you did not request this change, ignore this email and keep your current password.\n"
    )
    return send_plaintext_email(recipient, subject, body)


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
        ensure_password_not_current(new_password, user.password_hash)
        validate_password_policy(new_password, username=user.username, email=user.email, mobile=user.mobile)
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
    send_password_changed_notification(db, user)
    write_auth_audit(db, action="password_reset_confirm", user_id=user.id, object_id=str(item.id), detail={"result": "success"})
    db.commit()
    return {"message": "Password has been reset"}
