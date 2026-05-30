from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AuditLog, User
from app.services.email_notifications import mask_email, safe_delivery_error, send_plaintext_email


def display_name(user: User) -> str:
    return user.real_name or user.username or "用户"


def portal_url() -> str:
    return settings.public_frontend_base_url.rstrip("/")


def send_account_notification(
    db: Session,
    *,
    user: User,
    event: str,
    subject: str,
    body: str,
) -> bool:
    if not user.email:
        record_notification_audit(db, user=user, event=event, sent=False, reason="missing_email")
        return False

    try:
        sent = send_plaintext_email(user.email, subject, body)
    except HTTPException as error:
        record_notification_audit(db, user=user, event=event, sent=False, reason=notification_error_code(error))
        return False
    except Exception as error:
        record_notification_audit(db, user=user, event=event, sent=False, reason=safe_delivery_error(error))
        return False

    record_notification_audit(db, user=user, event=event, sent=sent, reason=None)
    return sent


def record_notification_audit(
    db: Session,
    *,
    user: User,
    event: str,
    sent: bool,
    reason: str | None,
) -> None:
    detail = {
        "event": event,
        "provider": settings.email_provider,
        "recipient": mask_email(user.email),
        "sent": sent,
    }
    if reason:
        detail["reason"] = reason
    db.add(
        AuditLog(
            user_id=user.id,
            module="notifications",
            action=event,
            object_type="user",
            object_id=str(user.id),
            detail_json=detail,
        )
    )


def notification_error_code(error: HTTPException) -> str:
    detail = error.detail
    if isinstance(detail, dict):
        code = detail.get("code") or detail.get("message")
        return str(code or "email_delivery_failed")
    return str(detail or "email_delivery_failed")


def send_registration_submitted_notification(db: Session, user: User) -> bool:
    subject = "怀柔科学城门户网站：注册申请已提交"
    body = (
        f"{display_name(user)}，您好：\n\n"
        "您的注册申请已提交。\n"
        "当前状态：等待审核。\n"
        "审核完成后，平台会另行发送通知。\n\n"
        "如非本人操作，可忽略本邮件或联系平台管理员。\n\n"
        "怀柔科学城门户网站\n"
    )
    return send_account_notification(db, user=user, event="registration_submitted", subject=subject, body=body)


def send_registration_approved_notification(db: Session, user: User) -> bool:
    subject = "怀柔科学城门户网站：账号审核已通过"
    body = (
        f"{display_name(user)}，您好：\n\n"
        "您的账号审核已通过，账号已激活。\n"
        f"登录地址：{portal_url()}\n"
        "如忘记密码，可通过登录页的“忘记密码”完成重置。\n\n"
        "怀柔科学城门户网站\n"
    )
    return send_account_notification(db, user=user, event="registration_approved", subject=subject, body=body)


def send_registration_rejected_notification(db: Session, user: User, reason: str) -> bool:
    subject = "怀柔科学城门户网站：注册申请审核未通过"
    body = (
        f"{display_name(user)}，您好：\n\n"
        "审核结果：未通过\n"
        f"审核说明：{reason}\n"
        "后续建议：如需补充材料，请联系平台管理员。\n\n"
        "怀柔科学城门户网站\n"
    )
    return send_account_notification(db, user=user, event="registration_rejected", subject=subject, body=body)


def send_admin_created_user_notification(db: Session, user: User) -> bool:
    subject = "怀柔科学城门户网站：账号已创建"
    body = (
        f"{display_name(user)}，您好：\n\n"
        "管理员已为您创建怀柔科学城门户网站账号。\n"
        f"用户名：{user.username or '-'}\n"
        f"登录地址：{portal_url()}\n"
        "邮件不包含初始密码。请访问门户网站登录页，通过“忘记密码”设置或重置登录密码。\n"
        "如非本人相关，请联系平台管理员。\n\n"
        "怀柔科学城门户网站\n"
    )
    return send_account_notification(db, user=user, event="admin_created_user", subject=subject, body=body)


def send_password_changed_notification(db: Session, user: User) -> bool:
    subject = "怀柔科学城门户网站：密码已修改"
    body = (
        f"{display_name(user)}，您好：\n\n"
        "您的账号密码已成功修改。\n"
        "如果这是本人操作，无需处理。\n"
        "如果不是本人操作，请立即联系平台管理员。\n\n"
        "怀柔科学城门户网站\n"
    )
    return send_account_notification(db, user=user, event="password_changed", subject=subject, body=body)


def send_login_lockout_notification(
    db: Session,
    user: User,
    *,
    ip_address: str | None,
    locked_until,
    lockout_type: str,
) -> bool:
    subject = "怀柔科学城门户网站：登录保护已触发"
    body = (
        f"{display_name(user)}，您好：\n\n"
        "您的账号出现多次登录失败，系统已临时限制该来源的登录。\n"
        "限制时间：24 小时。\n"
        f"触发 IP：{ip_address or 'unknown'}\n"
        f"限制到期时间：{locked_until}\n\n"
        "如果这是本人操作，请稍后重试或联系管理员解锁。\n"
        "如果不是本人操作，请尽快联系平台管理员。\n\n"
        "怀柔科学城门户网站\n"
    )
    return send_account_notification(
        db,
        user=user,
        event=f"login_lockout_{lockout_type}",
        subject=subject,
        body=body,
    )
