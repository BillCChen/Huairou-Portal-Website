#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUNTIME_DIR_INPUT="${PORTAL_LOGIN_LOCKOUT_SMOKE_RUNTIME_DIR:-.runtime-logs/login-lockout-backend-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""

log() {
  echo "[login-lockout-smoke] $*"
}

fail() {
  echo "[login-lockout-smoke] ERROR: $*" >&2
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

DB_PATH="${RUNTIME_DIR}/portal_login_lockout_smoke.sqlite3"
OUTBOX_DIR="${RUNTIME_DIR}/mail_outbox"
UPLOAD_DIR="${RUNTIME_DIR}/uploads"

rm -f "${DB_PATH}"
rm -rf "${OUTBOX_DIR}"
mkdir -p "${OUTBOX_DIR}" "${UPLOAD_DIR}"

log "checking login lockout, notification, and unlock controls"
(
  cd apps/api-server
  exec env \
    DATABASE_URL="sqlite:///${DB_PATH}" \
    UPLOAD_DIR="${UPLOAD_DIR}" \
    EMAIL_PROVIDER="dev_outbox" \
    PASSWORD_RESET_DEV_OUTBOX_DIR="${OUTBOX_DIR}" \
    PUBLIC_FRONTEND_BASE_URL="http://127.0.0.1:3100" \
    INIT_SAMPLE_DATA="true" \
    LOGIN_LOCKOUT_ENABLED="true" \
    LOGIN_LOCKOUT_ACCOUNT_IP_FAILURES="10" \
    LOGIN_LOCKOUT_IP_FAILURES="30" \
    LOGIN_LOCKOUT_WINDOW_HOURS="24" \
    LOGIN_LOCKOUT_DURATION_HOURS="24" \
    LOGIN_LOCKOUT_EMAIL_COOLDOWN_HOURS="24" \
    "${VENV_DIR}/bin/python" - <<'PY'
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.api.routes import admin_login_lockouts, admin_unlock_login_lockout, login_password
from app.db.models import AuditLog, LoginLockout, Role, User
from app.db.seed import seed_database
from app.db.session import Base, SessionLocal, engine
from app.schemas import LoginLockoutUnlockIn, LoginRequest
from app.services.login_lockout import LOCKOUT_ACCOUNT_IP, LOCKOUT_IP


TRACE_UA = "Portal-P4B2-Lockout-Smoke/1.0"
ACCOUNT_IP = "203.0.113.60"
GLOBAL_IP = "203.0.113.61"
MISSING_IP = "203.0.113.62"
LOCKOUT_SUBJECT = "怀柔科学城门户网站：登录保护已触发"


def outbox_messages() -> list[str]:
    return [
        path.read_text(encoding="utf-8")
        for path in sorted(Path(settings.password_reset_dev_outbox_dir).glob("*.txt"))
    ]


def message_count() -> int:
    return sum(1 for text in outbox_messages() if f"Subject: {LOCKOUT_SUBJECT}" in text)


def make_request(path: str, ip: str, method: str = "POST") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [
                (b"x-forwarded-for", ip.encode("utf-8")),
                (b"user-agent", TRACE_UA.encode("utf-8")),
            ],
            "client": ("testclient", 50000),
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )


def request_login(username: str, password: str, ip: str, expected: int):
    with SessionLocal() as db:
        try:
            response = login_password(
                LoginRequest(username=username, password=password),
                make_request("/api/v1/auth/login/password", ip),
                db,
            )
        except HTTPException as error:
            assert error.status_code == expected, (username, error.status_code, error.detail)
            return error
        assert expected == 200, (username, expected, response)
        return response


def create_active_user(username: str, email: str | None, password_hash_value: str) -> None:
    with SessionLocal() as db:
        role = db.scalar(select(Role).where(Role.code == "registered_user"))
        assert role is not None
        db.add(
            User(
                username=username,
                mobile=None,
                email=email,
                password_hash=hash_password(password_hash_value),
                real_name="Login Lockout Smoke",
                organization="Lockout Smoke",
                expertise="Account Security",
                status="active",
                role_id=role.id,
            )
        )
        db.commit()


def active_lockout(lockout_type: str, ip_address: str, identifier: str | None = None) -> LoginLockout:
    with SessionLocal() as db:
        query = select(LoginLockout).where(
            LoginLockout.lockout_type == lockout_type,
            LoginLockout.ip_address == ip_address,
            LoginLockout.unlocked_at.is_(None),
        )
        if identifier:
            query = query.where(LoginLockout.normalized_identifier == identifier)
        item = db.scalar(query.order_by(LoginLockout.id.desc()).limit(1))
        assert item is not None
        return item


def assert_no_sensitive_audit() -> None:
    forbidden = ["WrongLockout", "LockoutPass", "Bearer "]
    with SessionLocal() as db:
        rows = db.scalars(select(AuditLog)).all()
        combined = "\n".join(str(row.detail_json) for row in rows)
    for value in forbidden:
        assert value not in combined


Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed_database(db)

suffix = uuid4().hex[:8]
locked_username = f"lockout-{suffix}"
locked_password = "LockoutPass1!"
create_active_user(locked_username, f"lockout-{suffix}@example.test", locked_password)

initial_messages = message_count()
for _ in range(settings.login_lockout_account_ip_failures):
    request_login(locked_username, "WrongLockout1!", ACCOUNT_IP, 400)

account_lockout = active_lockout(LOCKOUT_ACCOUNT_IP, ACCOUNT_IP, locked_username)
assert account_lockout.failure_count >= settings.login_lockout_account_ip_failures
assert message_count() == initial_messages + 1
request_login(locked_username, locked_password, ACCOUNT_IP, 429)
request_login(locked_username, "WrongLockout1!", ACCOUNT_IP, 429)
assert message_count() == initial_messages + 1

missing_messages = message_count()
missing_username = f"missing-{suffix}"
for _ in range(settings.login_lockout_account_ip_failures):
    request_login(missing_username, "WrongLockout1!", MISSING_IP, 400)
missing_lockout = active_lockout(LOCKOUT_ACCOUNT_IP, MISSING_IP, missing_username)
assert missing_lockout.user_id is None
assert message_count() == missing_messages

global_messages = message_count()
for index in range(settings.login_lockout_ip_failures):
    request_login(f"credential-{suffix}-{index}", "WrongLockout1!", GLOBAL_IP, 400)
ip_lockout = active_lockout(LOCKOUT_IP, GLOBAL_IP)
assert ip_lockout.failure_count >= settings.login_lockout_ip_failures
assert message_count() == global_messages
request_login(settings.admin_username, settings.admin_password, GLOBAL_IP, 429)

with SessionLocal() as db:
    admin = db.scalar(select(User).where(User.username == settings.admin_username))
    assert admin is not None

try:
    LoginLockoutUnlockIn(reason="too short")
except ValidationError:
    pass
else:
    raise AssertionError("short unlock reason was accepted")

unlock_reason = "测试误伤解锁说明，管理员已确认该来源可以恢复登录访问。"
with SessionLocal() as db:
    admin = db.scalar(select(User).where(User.username == settings.admin_username))
    assert admin is not None
    unlock_response = admin_unlock_login_lockout(
        account_lockout.id,
        LoginLockoutUnlockIn(reason=unlock_reason),
        make_request(f"/api/v1/admin/login-lockouts/{account_lockout.id}/unlock", "203.0.113.250"),
        admin,
        db,
    )
    assert unlock_response.data["id"] == account_lockout.id
request_login(locked_username, locked_password, ACCOUNT_IP, 200)

try:
    LoginLockoutUnlockIn(reason="too short")
except ValidationError:
    pass
else:
    raise AssertionError("short IP unlock reason was accepted")
with SessionLocal() as db:
    admin = db.scalar(select(User).where(User.username == settings.admin_username))
    assert admin is not None
    ip_unlock = admin_unlock_login_lockout(
        ip_lockout.id,
        LoginLockoutUnlockIn(reason="测试 IP 全局锁误伤解锁说明，管理员确认该来源不再异常。"),
        make_request(f"/api/v1/admin/login-lockouts/{ip_lockout.id}/unlock", "203.0.113.250"),
        admin,
        db,
    )
    assert ip_unlock.data["id"] == ip_lockout.id

with SessionLocal() as db:
    admin = db.scalar(select(User).where(User.username == settings.admin_username))
    assert admin is not None
    list_response = admin_login_lockouts(page=1, page_size=20, ip=ACCOUNT_IP, _=admin, db=db)
    assert list_response.data["total"] >= 1

with SessionLocal() as db:
    assert db.scalar(select(AuditLog).where(AuditLog.action == "login_lockout_created").limit(1)) is not None
    unlock_audit = db.scalar(select(AuditLog).where(AuditLog.action == "login_lockout_unlocked").limit(1))
    assert unlock_audit is not None
    assert unlock_audit.detail_json["reason"] == unlock_reason

assert_no_sensitive_audit()

print("account+IP lockout: PASS")
print("IP global lockout: PASS")
print("lockout notification sent once: PASS")
print("missing account email skipped: PASS")
print("IP global mass email skipped: PASS")
print("admin unlock reason gate: PASS")
print("token value printed: no")
print("password value printed: no")
PY
)

log "login lockout backend smoke passed"
