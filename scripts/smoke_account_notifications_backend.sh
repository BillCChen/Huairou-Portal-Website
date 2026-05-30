#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUNTIME_DIR_INPUT="${PORTAL_ACCOUNT_NOTIFICATIONS_SMOKE_RUNTIME_DIR:-.runtime-logs/account-notifications-backend-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""

log() {
  echo "[account-notifications-smoke] $*"
}

fail() {
  echo "[account-notifications-smoke] ERROR: $*" >&2
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

DB_PATH="${RUNTIME_DIR}/portal_account_notifications_smoke.sqlite3"
DISABLED_DB_PATH="${RUNTIME_DIR}/portal_account_notifications_disabled_smoke.sqlite3"
OUTBOX_DIR="${RUNTIME_DIR}/mail_outbox"
DISABLED_OUTBOX_DIR="${RUNTIME_DIR}/disabled_mail_outbox"
UPLOAD_DIR="${RUNTIME_DIR}/uploads"

rm -f "${DB_PATH}" "${DISABLED_DB_PATH}"
rm -rf "${OUTBOX_DIR}" "${DISABLED_OUTBOX_DIR}"
mkdir -p "${OUTBOX_DIR}" "${DISABLED_OUTBOX_DIR}" "${UPLOAD_DIR}"

log "checking account notification events"
(
  cd apps/api-server
  exec env \
    DATABASE_URL="sqlite:///${DB_PATH}" \
    UPLOAD_DIR="${UPLOAD_DIR}" \
    EMAIL_PROVIDER="dev_outbox" \
    PASSWORD_RESET_DEV_OUTBOX_DIR="${OUTBOX_DIR}" \
    PUBLIC_FRONTEND_BASE_URL="http://127.0.0.1:3100" \
    INIT_SAMPLE_DATA="true" \
    "${VENV_DIR}/bin/python" - <<'PY'
import json
import re
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select

from app.api.routes import admin_approve_user, admin_create_user, admin_reject_user, register_user
from app.core.config import settings
from app.db.models import AuditLog, User
from app.db.seed import seed_database
from app.db.session import Base, SessionLocal, engine
from app.schemas import AdminUserCreateIn, RegisterRequest, ReviewIn, UserRejectIn
from app.services.password_reset import confirm_password_reset, create_password_reset_request


def outbox_files() -> list[Path]:
    return sorted(Path(settings.password_reset_dev_outbox_dir).glob("*.txt"))


def require_new_message(subject: str, start_index: int) -> str:
    for file in outbox_files()[start_index:]:
        text = file.read_text(encoding="utf-8")
        if f"Subject: {subject}" in text:
            return text
    raise AssertionError(f"missing outbox subject: {subject}")


def assert_no_sensitive_fragments(text: str, fragments: list[str]) -> None:
    for fragment in fragments:
        assert fragment not in text, "message contains a forbidden fragment"


Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed_database(db)
    admin = db.scalar(select(User).where(User.username == settings.admin_username))
    partner = db.scalar(select(User).where(User.username == "partner.user"))
    assert admin is not None
    assert partner is not None

    start = len(outbox_files())
    submitted = register_user(
        RegisterRequest(
            real_name="通知待审用户",
            organization="Account Notification Smoke",
            mobile="18700000001",
            email="notify-submitted@example.com",
            expertise="成果转化",
            password="Notify123!",
        ),
        db,
    )
    submitted_text = require_new_message("怀柔科学城门户网站：注册申请已提交", start)
    assert "当前状态：等待审核" in submitted_text
    submitted_user_id = submitted.data["user_id"]

    start = len(outbox_files())
    admin_approve_user(submitted_user_id, ReviewIn(review_comment="审核通过"), admin, db)
    approved_text = require_new_message("怀柔科学城门户网站：账号审核已通过", start)
    assert "账号已激活" in approved_text

    rejected = register_user(
        RegisterRequest(
            real_name="通知驳回用户",
            organization="Account Notification Smoke",
            mobile="18700000002",
            email="notify-rejected@example.com",
            expertise="成果转化",
            password="Notify456!",
        ),
        db,
    )
    rejected_user_id = rejected.data["user_id"]

    try:
        UserRejectIn(reason="too short")
    except ValidationError:
        pass
    else:
        raise AssertionError("short rejection reason was accepted")

    rejection_reason = "资料说明不足，请补充单位证明材料后重新提交审核。"
    start = len(outbox_files())
    admin_reject_user(rejected_user_id, UserRejectIn(reason=rejection_reason), admin, db)
    rejected_text = require_new_message("怀柔科学城门户网站：注册申请审核未通过", start)
    assert "审核结果：未通过" in rejected_text
    assert rejection_reason in rejected_text

    initial_password = "NotifyCreate1!"
    start = len(outbox_files())
    created = admin_create_user(
        AdminUserCreateIn(
            username="notify_created_user",
            email="notify-created@example.com",
            mobile="18700000003",
            real_name="通知创建用户",
            organization="Account Notification Smoke",
            expertise="成果转化",
            password=initial_password,
            role_code="institute_editor",
        ),
        admin,
        db,
    )
    assert created.data["status"] == "active"
    created_text = require_new_message("怀柔科学城门户网站：账号已创建", start)
    assert "忘记密码" in created_text
    assert_no_sensitive_fragments(created_text, [initial_password, "password_hash"])

    start = len(outbox_files())
    create_password_reset_request(
        db,
        email_or_username="partner.user",
        request_ip="127.0.0.1",
        user_agent="account-notifications-smoke",
    )
    reset_request_text = require_new_message("Portal password reset", start)
    match = re.search(r"token=([A-Za-z0-9_\-]+)", reset_request_text)
    assert match is not None
    reset_token = match.group(1)

    start = len(outbox_files())
    result = confirm_password_reset(db, token=reset_token, new_password="NotifyReset1!")
    assert result["message"] == "Password has been reset"
    changed_text = require_new_message("怀柔科学城门户网站：密码已修改", start)
    assert "如不是本人操作" not in changed_text
    assert "如果不是本人操作，请立即联系平台管理员。" in changed_text
    assert_no_sensitive_fragments(changed_text, [reset_token, "token=", "/password-reset/confirm"])

    audits = db.scalars(select(AuditLog).where(AuditLog.module == "notifications")).all()
    events = {audit.action for audit in audits}
    expected = {
        "registration_submitted",
        "registration_approved",
        "registration_rejected",
        "admin_created_user",
        "password_changed",
    }
    assert expected <= events, sorted(expected - events)
    audit_payload = json.dumps([audit.detail_json for audit in audits], ensure_ascii=False)
    assert_no_sensitive_fragments(audit_payload, [initial_password, reset_token])

print("account notification backend smoke passed")
PY
)

log "checking disabled provider does not block account workflow"
(
  cd apps/api-server
  exec env \
    DATABASE_URL="sqlite:///${DISABLED_DB_PATH}" \
    UPLOAD_DIR="${UPLOAD_DIR}" \
    EMAIL_PROVIDER="disabled" \
    PASSWORD_RESET_DEV_OUTBOX_DIR="${DISABLED_OUTBOX_DIR}" \
    PUBLIC_FRONTEND_BASE_URL="http://127.0.0.1:3100" \
    INIT_SAMPLE_DATA="true" \
    "${VENV_DIR}/bin/python" - <<'PY'
from pathlib import Path

from sqlalchemy import select

from app.api.routes import admin_approve_user, register_user
from app.core.config import settings
from app.db.models import AuditLog, User
from app.db.seed import seed_database
from app.db.session import Base, SessionLocal, engine
from app.schemas import RegisterRequest, ReviewIn


Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed_database(db)
    admin = db.scalar(select(User).where(User.username == settings.admin_username))
    assert admin is not None

    disabled_password = "Notify789!"
    submitted = register_user(
        RegisterRequest(
            **{
                "real_name": "通知关闭用户",
                "organization": "Account Notification Disabled Smoke",
                "mobile": "18700000004",
                "email": "notify-disabled@example.com",
                "expertise": "成果转化",
                "password": disabled_password,
            }
        ),
        db,
    )
    user_id = submitted.data["user_id"]
    admin_approve_user(user_id, ReviewIn(review_comment="disabled provider approval"), admin, db)

    assert not list(Path(settings.password_reset_dev_outbox_dir).glob("*.txt"))
    audits = db.scalars(select(AuditLog).where(AuditLog.module == "notifications")).all()
    assert {audit.action for audit in audits} >= {"registration_submitted", "registration_approved"}
    assert all(audit.detail_json.get("provider") == "disabled" for audit in audits)
    assert all(audit.detail_json.get("sent") is False for audit in audits)

print("disabled provider main workflow: PASS")
PY
)
