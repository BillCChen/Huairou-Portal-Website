from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AuditLog, LoginLockout, LoginLog, User
from app.services.account_notifications import send_login_lockout_notification
from app.services.request_context import RequestMeta


LOGIN_LOCKOUT_GENERIC_MESSAGE = "登录失败次数过多或暂时受限，请稍后重试，或联系管理员。"
LOCKOUT_ACCOUNT_IP = "account_ip"
LOCKOUT_IP = "ip"


def now_utc() -> datetime:
    return datetime.now(UTC)


def as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_login_identifier(value: str | None) -> str:
    return (value or "").strip().lower()


def lockout_window_start(now: datetime) -> datetime:
    return now - timedelta(hours=settings.login_lockout_window_hours)


def lockout_until(now: datetime) -> datetime:
    return now + timedelta(hours=settings.login_lockout_duration_hours)


def lockout_active_clause(now: datetime):
    return LoginLockout.unlocked_at.is_(None), LoginLockout.locked_until > now


def active_ip_lockout(db: Session, ip_address: str | None, now: datetime) -> LoginLockout | None:
    if not ip_address:
        return None
    return db.scalar(
        select(LoginLockout)
        .where(
            LoginLockout.lockout_type == LOCKOUT_IP,
            LoginLockout.ip_address == ip_address,
            *lockout_active_clause(now),
        )
        .order_by(LoginLockout.id.desc())
        .limit(1)
    )


def active_account_ip_lockout(
    db: Session,
    identifier: str,
    ip_address: str | None,
    now: datetime,
) -> LoginLockout | None:
    if not identifier or not ip_address:
        return None
    return db.scalar(
        select(LoginLockout)
        .where(
            LoginLockout.lockout_type == LOCKOUT_ACCOUNT_IP,
            LoginLockout.normalized_identifier == identifier,
            LoginLockout.ip_address == ip_address,
            *lockout_active_clause(now),
        )
        .order_by(LoginLockout.id.desc())
        .limit(1)
    )


def audit_login_lockout(
    db: Session,
    *,
    action: str,
    lockout: LoginLockout | None,
    user_id: int | None,
    detail: dict,
    request_meta: RequestMeta,
    result: str = "failure",
    failure_reason: str | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            module="auth",
            action=action,
            object_type="login_lockout",
            object_id=str(lockout.id) if lockout and lockout.id else None,
            detail_json=detail,
            ip_address=request_meta.ip_address,
            user_agent=request_meta.user_agent,
            path=request_meta.path,
            method=request_meta.method,
            result=result,
            failure_reason=failure_reason,
        )
    )


def reject_locked_login(
    db: Session,
    *,
    lockout: LoginLockout,
    request_meta: RequestMeta,
) -> None:
    audit_login_lockout(
        db,
        action="login_lockout_blocked",
        lockout=lockout,
        user_id=lockout.user_id,
        detail={"lockout_type": lockout.lockout_type, "reason": "active_lockout"},
        request_meta=request_meta,
        failure_reason="active_lockout",
    )
    db.commit()
    raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=LOGIN_LOCKOUT_GENERIC_MESSAGE)


def enforce_login_not_locked(db: Session, *, identifier: str, request_meta: RequestMeta) -> None:
    if not settings.login_lockout_enabled:
        return
    now = now_utc()
    ip_lockout = active_ip_lockout(db, request_meta.ip_address, now)
    if ip_lockout is not None:
        reject_locked_login(db, lockout=ip_lockout, request_meta=request_meta)

    account_lockout = active_account_ip_lockout(db, normalize_login_identifier(identifier), request_meta.ip_address, now)
    if account_lockout is not None:
        reject_locked_login(db, lockout=account_lockout, request_meta=request_meta)


def account_ip_failure_count(db: Session, *, identifier: str, ip_address: str | None, since: datetime) -> int:
    if not identifier or not ip_address:
        return 0
    return int(
        db.scalar(
            select(func.count())
            .select_from(LoginLog)
            .where(
                LoginLog.success.is_(False),
                LoginLog.ip_address == ip_address,
                func.lower(LoginLog.username) == identifier,
                LoginLog.created_at >= since,
            )
        )
        or 0
    )


def ip_failure_count(db: Session, *, ip_address: str | None, since: datetime) -> int:
    if not ip_address:
        return 0
    return int(
        db.scalar(
            select(func.count())
            .select_from(LoginLog)
            .where(
                LoginLog.success.is_(False),
                LoginLog.ip_address == ip_address,
                LoginLog.created_at >= since,
            )
        )
        or 0
    )


def recent_email_sent_for_user(db: Session, *, user_id: int, now: datetime) -> bool:
    cooldown_start = now - timedelta(hours=settings.login_lockout_email_cooldown_hours)
    return bool(
        db.scalar(
            select(LoginLockout.id)
            .where(
                LoginLockout.user_id == user_id,
                LoginLockout.lockout_type == LOCKOUT_ACCOUNT_IP,
                LoginLockout.email_sent_at.is_not(None),
                LoginLockout.email_sent_at >= cooldown_start,
            )
            .limit(1)
        )
    )


def create_lockout(
    db: Session,
    *,
    lockout_type: str,
    identifier: str | None,
    user: User | None,
    ip_address: str | None,
    failure_count: int,
    reason: str,
    request_meta: RequestMeta,
    now: datetime,
) -> LoginLockout:
    item = LoginLockout(
        lockout_type=lockout_type,
        normalized_identifier=identifier,
        user_id=user.id if user else None,
        ip_address=ip_address,
        locked_until=lockout_until(now),
        reason=reason,
        failure_count=failure_count,
        window_started_at=lockout_window_start(now),
    )
    db.add(item)
    db.flush()
    audit_login_lockout(
        db,
        action="login_lockout_created",
        lockout=item,
        user_id=user.id if user else None,
        detail={
            "lockout_type": lockout_type,
            "failure_count": failure_count,
            "reason": reason,
            "has_user": user is not None,
        },
        request_meta=request_meta,
        failure_reason=reason,
    )
    return item


def maybe_send_lockout_email(db: Session, *, lockout: LoginLockout, user: User, request_meta: RequestMeta, now: datetime) -> None:
    if not user.email:
        return
    if recent_email_sent_for_user(db, user_id=user.id, now=now):
        audit_login_lockout(
            db,
            action="login_lockout_email_skipped",
            lockout=lockout,
            user_id=user.id,
            detail={"reason": "cooldown", "lockout_type": lockout.lockout_type},
            request_meta=request_meta,
            result="success",
        )
        return
    sent = send_login_lockout_notification(
        db,
        user,
        ip_address=lockout.ip_address,
        locked_until=lockout.locked_until,
        lockout_type=lockout.lockout_type,
    )
    if sent:
        lockout.email_sent_at = now


def update_login_lockouts_after_failure(
    db: Session,
    *,
    identifier: str,
    user: User | None,
    request_meta: RequestMeta,
) -> list[LoginLockout]:
    if not settings.login_lockout_enabled:
        return []
    now = now_utc()
    normalized_identifier = normalize_login_identifier(identifier)
    since = lockout_window_start(now)
    created: list[LoginLockout] = []

    if (
        active_account_ip_lockout(db, normalized_identifier, request_meta.ip_address, now) is None
        and account_ip_failure_count(db, identifier=normalized_identifier, ip_address=request_meta.ip_address, since=since)
        >= settings.login_lockout_account_ip_failures
    ):
        count = account_ip_failure_count(db, identifier=normalized_identifier, ip_address=request_meta.ip_address, since=since)
        lockout = create_lockout(
            db,
            lockout_type=LOCKOUT_ACCOUNT_IP,
            identifier=normalized_identifier,
            user=user,
            ip_address=request_meta.ip_address,
            failure_count=count,
            reason="account_ip_failure_threshold",
            request_meta=request_meta,
            now=now,
        )
        created.append(lockout)
        if user is not None:
            maybe_send_lockout_email(db, lockout=lockout, user=user, request_meta=request_meta, now=now)

    if (
        active_ip_lockout(db, request_meta.ip_address, now) is None
        and ip_failure_count(db, ip_address=request_meta.ip_address, since=since) >= settings.login_lockout_ip_failures
    ):
        count = ip_failure_count(db, ip_address=request_meta.ip_address, since=since)
        created.append(
            create_lockout(
                db,
                lockout_type=LOCKOUT_IP,
                identifier=None,
                user=None,
                ip_address=request_meta.ip_address,
                failure_count=count,
                reason="ip_failure_threshold",
                request_meta=request_meta,
                now=now,
            )
        )
    return created


def serialize_login_lockout(item: LoginLockout) -> dict:
    return {
        "id": item.id,
        "lockout_type": item.lockout_type,
        "normalized_identifier": item.normalized_identifier,
        "user_id": item.user_id,
        "ip_address": item.ip_address,
        "locked_until": item.locked_until,
        "reason": item.reason,
        "failure_count": item.failure_count,
        "window_started_at": item.window_started_at,
        "email_sent_at": item.email_sent_at,
        "unlocked_at": item.unlocked_at,
        "unlocked_by_user_id": item.unlocked_by_user_id,
        "unlock_reason": item.unlock_reason,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def lockout_is_active(item: LoginLockout, now: datetime | None = None) -> bool:
    current_time = now or now_utc()
    return item.unlocked_at is None and as_aware_utc(item.locked_until) > current_time
