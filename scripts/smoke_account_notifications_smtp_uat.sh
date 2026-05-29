#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUNTIME_DIR_INPUT="${PORTAL_ACCOUNT_NOTIFICATIONS_SMTP_UAT_RUNTIME_DIR:-.runtime-logs/account-notifications-smtp-uat}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"
SMTP_PASSWORD_FILE="${PORTAL_SMTP_PASSWORD_FILE:-}"
SMTP_UAT_RECIPIENT="${PORTAL_SMTP_UAT_RECIPIENT:-}"
SMTP_UAT_RECIPIENT_FILE="${PORTAL_SMTP_UAT_RECIPIENT_FILE:-/Users/billchen/Documents/cursor-project/HuaiRou-Agents/portal_smtp_uat_recipient.txt}"
SMTP_UAT_RECIPIENT_MASKED="${PORTAL_SMTP_UAT_RECIPIENT_MASKED:-}"
SMTP_UAT_CONFIRM_SEND="${PORTAL_SMTP_UAT_CONFIRM_SEND:-false}"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""

log() {
  echo "[account-notifications-smtp-uat] $*"
}

fail() {
  echo "[account-notifications-smtp-uat] ERROR: $*" >&2
  exit 1
}

python_minor() {
  local python_bin="$1"
  "${python_bin}" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
}

candidate_list() {
  if [ -n "${PYTHON_OVERRIDE}" ]; then
    echo "${PYTHON_OVERRIDE}"
    return 0
  fi
  printf '%s\n' python3.13 python3.12 python3.11
}

prepare_venv() {
  local python_bin="$1"
  local python_mm

  if ! command -v "${python_bin}" >/dev/null 2>&1; then
    log "skipping ${python_bin}: not found"
    return 1
  fi

  python_mm="$(python_minor "${python_bin}")"
  case "${python_mm}" in
    3.11|3.12|3.13) ;;
    *)
      log "skipping ${python_bin}: unsupported Python ${python_mm}"
      return 1
      ;;
  esac

  VENV_DIR="${RUNTIME_DIR}/backend-venv-py${python_mm//./}"
  mkdir -p "${RUNTIME_DIR}"

  if [ ! -x "${VENV_DIR}/bin/python" ]; then
    log "creating venv at ${VENV_DIR}"
    "${python_bin}" -m venv "${VENV_DIR}" || return 1
  fi

  log "installing backend requirements"
  "${VENV_DIR}/bin/python" -m pip install --upgrade pip >/dev/null
  "${VENV_DIR}/bin/python" -m pip install -r apps/api-server/requirements.txt >/dev/null
  return 0
}

require_inputs() {
  [ "${SMTP_UAT_CONFIRM_SEND}" = "true" ] || fail "set PORTAL_SMTP_UAT_CONFIRM_SEND=true to send real SMTP UAT email"
  [ -n "${SMTP_PASSWORD_FILE}" ] || fail "PORTAL_SMTP_PASSWORD_FILE is required"
  [ -s "${SMTP_PASSWORD_FILE}" ] || fail "SMTP password file is missing or empty"
  if [ -z "${SMTP_UAT_RECIPIENT}" ] && [ -s "${SMTP_UAT_RECIPIENT_FILE}" ]; then
    SMTP_UAT_RECIPIENT="$(tr -d '\r\n' < "${SMTP_UAT_RECIPIENT_FILE}")"
  fi
  [ -n "${SMTP_UAT_RECIPIENT}" ] || fail "PORTAL_SMTP_UAT_RECIPIENT is required"
  case "${SMTP_UAT_RECIPIENT}" in
    *@*) ;;
    *) fail "PORTAL_SMTP_UAT_RECIPIENT must be an email address" ;;
  esac
  if [ -z "${SMTP_UAT_RECIPIENT_MASKED}" ]; then
    SMTP_UAT_RECIPIENT_MASKED="$(
      RECIPIENT="${SMTP_UAT_RECIPIENT}" python3 - <<'PY'
import os
value = os.environ["RECIPIENT"]
name, domain = value.split("@", maxsplit=1)
if len(name) <= 2:
    print(f"{name[:1]}***@{domain}")
else:
    print(f"{name[:2]}***@{domain}")
PY
    )"
  fi

  local repo_realpath password_realpath recipient_realpath
  repo_realpath="$(
    python3 - <<'PY'
import os
print(os.path.realpath(os.getcwd()))
PY
  )"
  password_realpath="$(
    PASSWORD_FILE="${SMTP_PASSWORD_FILE}" python3 - <<'PY'
import os
print(os.path.realpath(os.environ["PASSWORD_FILE"]))
PY
  )"
  case "${password_realpath}" in
    "${repo_realpath}"/*) fail "SMTP password file must stay outside the repository" ;;
  esac
  if [ -s "${SMTP_UAT_RECIPIENT_FILE}" ]; then
    recipient_realpath="$(
      RECIPIENT_FILE="${SMTP_UAT_RECIPIENT_FILE}" python3 - <<'PY'
import os
print(os.path.realpath(os.environ["RECIPIENT_FILE"]))
PY
    )"
    case "${recipient_realpath}" in
      "${repo_realpath}"/*) fail "SMTP recipient file must stay outside the repository" ;;
    esac
  fi
}

require_inputs

log "即将发送真实账号通知 UAT 邮件。"
log "Provider: smtp"
log "Recipient: ${SMTP_UAT_RECIPIENT_MASKED}"
log "预计邮件数量: 5"
log "不会输出 SMTP password / token / reset link / 明文密码。"

selected_python=""
for candidate in $(candidate_list); do
  if prepare_venv "${candidate}"; then
    selected_python="${candidate}"
    break
  fi
  if [ -n "${PYTHON_OVERRIDE}" ]; then
    fail "PORTAL_BACKEND_PYTHON=${PYTHON_OVERRIDE} failed"
  fi
done

if [ -z "${selected_python}" ]; then
  fail "no compatible Python interpreter could create a backend venv and install requirements"
fi

DB_PATH="${RUNTIME_DIR}/portal_account_notifications_smtp_uat.sqlite3"
UPLOAD_DIR="${RUNTIME_DIR}/uploads"
OUTBOX_DIR="${RUNTIME_DIR}/mail_outbox"

rm -f "${DB_PATH}"
mkdir -p "${UPLOAD_DIR}" "${OUTBOX_DIR}"

SMTP_PASSWORD_VALUE="$(tr -d '\r\n' < "${SMTP_PASSWORD_FILE}")"
[ -n "${SMTP_PASSWORD_VALUE}" ] || fail "SMTP password file is empty after normalization"

(
  cd apps/api-server
  exec env \
    DATABASE_URL="sqlite:///${DB_PATH}" \
    UPLOAD_DIR="${UPLOAD_DIR}" \
    EMAIL_PROVIDER="smtp" \
    PASSWORD_RESET_DEV_OUTBOX_DIR="${OUTBOX_DIR}" \
    PUBLIC_FRONTEND_BASE_URL="https://huairou.tech" \
    SMTP_HOST="smtpdm.aliyun.com" \
    SMTP_PORT="465" \
    SMTP_USERNAME="no-reply@notify.inside-chen.top" \
    SMTP_PASSWORD="${SMTP_PASSWORD_VALUE}" \
    SMTP_FROM_EMAIL="no-reply@notify.inside-chen.top" \
    SMTP_FROM_NAME="怀柔科学城门户网站" \
    SMTP_USE_TLS="true" \
    SMTP_USE_STARTTLS="false" \
    SMTP_TIMEOUT_SECONDS="10" \
    SMTP_REQUIRE_AUTH="true" \
    INIT_SAMPLE_DATA="true" \
    PORTAL_SMTP_UAT_RECIPIENT="${SMTP_UAT_RECIPIENT}" \
    PORTAL_SMTP_UAT_RECIPIENT_MASKED="${SMTP_UAT_RECIPIENT_MASKED}" \
    "${VENV_DIR}/bin/python" - <<'PY'
from datetime import timedelta
import os
import secrets
import time

from sqlalchemy import select

from app.api.routes import admin_approve_user, admin_create_user, admin_reject_user, register_user
from app.core.config import settings
from app.core.security import hash_password
from app.db.models import AuditLog, PasswordResetToken, RegistrationApplication, Role, User
from app.db.seed import seed_database
from app.db.session import Base, SessionLocal, engine
from app.schemas import AdminUserCreateIn, RegisterRequest, ReviewIn, UserRejectIn
from app.services.password_reset import confirm_password_reset, generate_reset_token, hash_reset_token, now_utc


recipient = os.environ["PORTAL_SMTP_UAT_RECIPIENT"]
recipient_masked = os.environ["PORTAL_SMTP_UAT_RECIPIENT_MASKED"]
run_id = str(int(time.time()))


def event_count(db) -> int:
    return len(db.scalars(select(AuditLog).where(AuditLog.module == "notifications")).all())


def require_new_sent_event(db, event: str, start_count: int) -> None:
    db.flush()
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.module == "notifications")
        .order_by(AuditLog.id.asc())
    ).all()[start_count:]
    matches = [row for row in rows if row.action == event]
    if not matches:
        raise AssertionError(f"missing notification event: {event}")
    latest = matches[-1]
    detail = latest.detail_json or {}
    if detail.get("provider") != "smtp" or detail.get("sent") is not True:
        raise AssertionError(f"notification not sent through smtp: {event}")
    if detail.get("recipient") != recipient_masked:
        raise AssertionError(f"unexpected recipient mask for {event}")


def role_by_code(db, code: str) -> Role:
    role = db.scalar(select(Role).where(Role.code == code))
    if role is None:
        raise AssertionError(f"missing role: {code}")
    return role


def create_pending_user(db, label: str) -> User:
    role = role_by_code(db, "registered_user")
    suffix = secrets.token_hex(3)
    user = User(
        username=f"uat_notify_{label}_{run_id}_{suffix}",
        mobile=f"17{run_id[-8:]}{suffix[:1]}{len(label)}",
        email=recipient,
        password_hash=hash_password("LocalOnly1!"),
        real_name=f"通知{label}用户",
        organization="Portal SMTP UAT",
        expertise="成果转化",
        status="pending",
        role_id=role.id,
    )
    db.add(user)
    db.flush()
    db.add(RegistrationApplication(user_id=user.id, review_status="pending"))
    db.flush()
    return user


def create_active_user(db, label: str) -> User:
    role = role_by_code(db, "registered_user")
    suffix = secrets.token_hex(3)
    user = User(
        username=f"uat_notify_{label}_{run_id}_{suffix}",
        mobile=f"18{run_id[-8:]}{suffix[:1]}{len(label)}",
        email=recipient,
        password_hash=hash_password("LocalOnly1!"),
        real_name=f"通知{label}用户",
        organization="Portal SMTP UAT",
        expertise="成果转化",
        status="active",
        role_id=role.id,
    )
    db.add(user)
    db.flush()
    return user


Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed_database(db)
    admin = db.scalar(select(User).where(User.username == settings.admin_username))
    if admin is None:
        raise AssertionError("missing seed admin")

    initial_password = f"AdminUat1!{secrets.token_hex(4)}"
    start = event_count(db)
    admin_create_user(
        AdminUserCreateIn(
            username=f"uat_notify_admin_created_{run_id}",
            email=recipient,
            mobile=f"15{run_id[-8:]}02",
            real_name="通知创建用户",
            organization="Portal SMTP UAT",
            expertise="成果转化",
            password=initial_password,
            role_code="institute_editor",
        ),
        admin,
        db,
    )
    require_new_sent_event(db, "admin_created_user", start)
    print("admin_created_user: sent")

    start = event_count(db)
    register_user(
        RegisterRequest(
            real_name="通知注册用户",
            organization="Portal SMTP UAT",
            mobile=f"16{run_id[-8:]}01",
            email=recipient,
            expertise="成果转化",
            password="Notify123!",
        ),
        db,
    )
    require_new_sent_event(db, "registration_submitted", start)
    print("registration_submitted: sent")

    pending_for_approval = create_pending_user(db, "approve")
    start = event_count(db)
    admin_approve_user(pending_for_approval.id, ReviewIn(review_comment="SMTP UAT approval"), admin, db)
    require_new_sent_event(db, "registration_approved", start)
    print("registration_approved: sent")

    rejection_reason = "申请资料暂不完整，请补充所在单位、联系方式和成果转化需求后重新提交。"
    pending_for_rejection = create_pending_user(db, "reject")
    start = event_count(db)
    admin_reject_user(pending_for_rejection.id, UserRejectIn(reason=rejection_reason), admin, db)
    require_new_sent_event(db, "registration_rejected", start)
    print("registration_rejected: sent")

    active_user = create_active_user(db, "changed")
    reset_token = generate_reset_token()
    db.add(
        PasswordResetToken(
            user_id=active_user.id,
            token_hash=hash_reset_token(reset_token),
            expires_at=now_utc() + timedelta(minutes=settings.password_reset_token_ttl_minutes),
            request_ip="127.0.0.1",
            user_agent="account-notifications-smtp-uat",
        )
    )
    db.flush()
    start = event_count(db)
    result = confirm_password_reset(db, token=reset_token, new_password="NotifyReset1!")
    if result["message"] != "Password has been reset":
        raise AssertionError("password reset confirm failed")
    require_new_sent_event(db, "password_changed", start)
    print("password_changed: sent")

print("account notification SMTP UAT sends completed")
PY
)

unset SMTP_PASSWORD_VALUE

log "真实 SMTP 账号通知 UAT 发送完成。"
