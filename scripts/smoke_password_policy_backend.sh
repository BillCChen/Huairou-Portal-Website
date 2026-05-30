#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUNTIME_DIR_INPUT="${PORTAL_PASSWORD_POLICY_SMOKE_RUNTIME_DIR:-.runtime-logs/password-policy-backend-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""

log() {
  echo "[password-policy-smoke] $*"
}

fail() {
  echo "[password-policy-smoke] ERROR: $*" >&2
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

DB_PATH="${RUNTIME_DIR}/portal_password_policy_smoke.sqlite3"
OUTBOX_DIR="${RUNTIME_DIR}/mail_outbox"
UPLOAD_DIR="${RUNTIME_DIR}/uploads"

rm -f "${DB_PATH}"
rm -rf "${OUTBOX_DIR}"
mkdir -p "${OUTBOX_DIR}" "${UPLOAD_DIR}"

log "checking password policy entrypoints"
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
import re
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select

from app.api.routes import admin_create_user, register_user
from app.core.config import settings
from app.core.security import verify_password
from app.db.models import PasswordResetToken, User
from app.db.seed import seed_database
from app.db.session import Base, SessionLocal, engine
from app.schemas import AdminUserCreateIn, RegisterRequest
from app.services.password_policy import PASSWORD_ACCOUNT_SIMILAR_MESSAGE, PASSWORD_COMMON_MESSAGE
from app.services.password_reset import confirm_password_reset, create_password_reset_request


def expect_http_error(label: str, func, expected_detail: str | None = None) -> None:
    try:
        func()
    except HTTPException as error:
        assert error.status_code == 400, (label, error.status_code)
        if expected_detail is not None:
            assert error.detail == expected_detail, (label, error.detail)
        return
    raise AssertionError(f"{label} did not fail")


Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed_database(db)
    admin = db.scalar(select(User).where(User.username == settings.admin_username))
    partner = db.scalar(select(User).where(User.username == "partner.user"))
    assert admin is not None
    assert partner is not None

    expect_http_error(
        "basic weak registration password",
        lambda: register_user(
            RegisterRequest(
                real_name="弱密码注册用户",
                organization="Password Policy Smoke",
                mobile="18800000001",
                email="policy-weak@example.com",
                expertise="成果转化",
                password="abcdefgh",
            ),
            db,
        ),
    )

    expect_http_error(
        "common registration password",
        lambda: register_user(
            RegisterRequest(
                real_name="常见弱密码注册用户",
                organization="Password Policy Smoke",
                mobile="18800000005",
                email="policy-common@example.com",
                expertise="成果转化",
                password="Password123",
            ),
            db,
        ),
        PASSWORD_COMMON_MESSAGE,
    )

    expect_http_error(
        "mobile-similar registration password",
        lambda: register_user(
            RegisterRequest(
                real_name="手机号相似密码注册用户",
                organization="Password Policy Smoke",
                mobile="18800000006",
                email="policy-mobile-similar@example.com",
                expertise="成果转化",
                password="Tail0006!",
            ),
            db,
        ),
        PASSWORD_ACCOUNT_SIMILAR_MESSAGE,
    )

    strong_registration = register_user(
        RegisterRequest(
            real_name="合规密码注册用户",
            organization="Password Policy Smoke",
            mobile="18800000002",
            email="policy-strong@example.com",
            expertise="成果转化",
            password="Policy123!",
        ),
        db,
    )
    assert strong_registration.data["status"] == "pending_review"

    expect_http_error(
        "weak admin-created user password",
        lambda: admin_create_user(
            AdminUserCreateIn(
                username="policy_weak_user",
                email="policy-admin-weak@example.com",
                mobile="18800000003",
                real_name="弱密码后台用户",
                organization="Password Policy Smoke",
                expertise="成果转化",
                password="abcdefgh",
                role_code="institute_editor",
            ),
            admin,
            db,
        ),
    )

    expect_http_error(
        "username-similar admin-created user password",
        lambda: admin_create_user(
            AdminUserCreateIn(
                username="similar_user",
                email="policy-admin-username-similar@example.com",
                mobile="18800000005",
                real_name="用户名相似密码后台用户",
                organization="Password Policy Smoke",
                expertise="成果转化",
                password="Similar_user1!",
                role_code="institute_editor",
            ),
            admin,
            db,
        ),
        PASSWORD_ACCOUNT_SIMILAR_MESSAGE,
    )

    expect_http_error(
        "email-local-similar admin-created user password",
        lambda: admin_create_user(
            AdminUserCreateIn(
                username="policy_email_user",
                email="localpart@example.com",
                mobile="18800000006",
                real_name="邮箱相似密码后台用户",
                organization="Password Policy Smoke",
                expertise="成果转化",
                password="Localpart1!",
                role_code="institute_editor",
            ),
            admin,
            db,
        ),
        PASSWORD_ACCOUNT_SIMILAR_MESSAGE,
    )

    created = admin_create_user(
        AdminUserCreateIn(
            username="policy_strong_user",
            email="policy-admin-strong@example.com",
            mobile="18800000004",
            real_name="合规密码后台用户",
            organization="Password Policy Smoke",
            expertise="成果转化",
            password="Policy456!",
            role_code="institute_editor",
        ),
        admin,
        db,
    )
    assert created.data["status"] == "active"

    create_password_reset_request(
        db,
        email_or_username="partner.user",
        request_ip="127.0.0.1",
        user_agent="password-policy-smoke",
    )
    reset_messages = [
        file.read_text(encoding="utf-8")
        for file in sorted(Path(settings.password_reset_dev_outbox_dir).glob("*.txt"))
        if "Subject: Portal password reset" in file.read_text(encoding="utf-8")
    ]
    assert len(reset_messages) == 1
    outbox_text = reset_messages[0]
    match = re.search(r"token=([A-Za-z0-9_\-]+)", outbox_text)
    assert match is not None
    reset_token = match.group(1)

    expect_http_error(
        "weak reset password",
        lambda: confirm_password_reset(db, token=reset_token, new_password="abcdefgh"),
    )
    expect_http_error(
        "same reset password",
        lambda: confirm_password_reset(db, token=reset_token, new_password="Partner123!"),
        "新密码不能与当前密码相同。",
    )

    result = confirm_password_reset(db, token=reset_token, new_password="PolicyReset1!")
    assert result["message"] == "Password has been reset"

    db.refresh(partner)
    assert not verify_password("Partner123!", partner.password_hash)
    assert verify_password("PolicyReset1!", partner.password_hash)
    item = db.scalar(select(PasswordResetToken).where(PasswordResetToken.user_id == partner.id).order_by(PasswordResetToken.id.desc()).limit(1))
    assert item is not None
    assert item.consumed_at is not None

print("password policy backend smoke passed")
PY
)
