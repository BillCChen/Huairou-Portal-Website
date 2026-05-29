#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORTAL_AUDIT_IP_SMOKE_PORT:-18270}"
HOST="${PORTAL_AUDIT_IP_SMOKE_HOST:-127.0.0.1}"
BASE_URL="http://${HOST}:${PORT}"
RUNTIME_DIR_INPUT="${PORTAL_AUDIT_IP_SMOKE_RUNTIME_DIR:-.runtime-logs/audit-ip-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"
TRACE_IP="203.0.113.10"
TRACE_UA="Portal-P3D-Audit-Smoke/1.0"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""
API_PID=""

log() {
  echo "[audit-ip-smoke] $*"
}

fail() {
  echo "[audit-ip-smoke] ERROR: $*" >&2
  exit 1
}

cleanup() {
  if [ -n "${API_PID}" ] && ps -p "${API_PID}" >/dev/null 2>&1; then
    log "stopping API pid ${API_PID}"
    kill "${API_PID}" || true
    wait "${API_PID}" 2>/dev/null || true
    if ps -p "${API_PID}" >/dev/null 2>&1; then
      kill -9 "${API_PID}" || true
      wait "${API_PID}" 2>/dev/null || true
    fi
  fi
}

trap cleanup EXIT

if [ "${PORT}" = "8000" ]; then
  fail "port 8000 is reserved; refusing to use it for local smoke"
fi

if lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN || true
  fail "port ${PORT} is already in use; refusing to stop unknown process"
fi

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

DB_PATH="${RUNTIME_DIR}/portal_audit_ip_smoke.sqlite3"
UPLOAD_DIR="${RUNTIME_DIR}/uploads"
OUTBOX_DIR="${RUNTIME_DIR}/mail_outbox"
LOG_PATH="${RUNTIME_DIR}/api.log"
PID_PATH="${RUNTIME_DIR}/api.pid"

rm -f "${DB_PATH}"
rm -rf "${OUTBOX_DIR}"
mkdir -p "${UPLOAD_DIR}" "${OUTBOX_DIR}"

log "starting API at ${BASE_URL}"
(
  cd apps/api-server
  exec env \
    DATABASE_URL="sqlite:///${DB_PATH}" \
    UPLOAD_DIR="${UPLOAD_DIR}" \
    EMAIL_PROVIDER="dev_outbox" \
    PASSWORD_RESET_DEV_OUTBOX_DIR="${OUTBOX_DIR}" \
    PUBLIC_FRONTEND_BASE_URL="http://127.0.0.1:3100" \
    INIT_SAMPLE_DATA="true" \
    "${VENV_DIR}/bin/python" -m uvicorn app.main:app --host "${HOST}" --port "${PORT}"
) > "${LOG_PATH}" 2>&1 &

API_PID="$!"
echo "${API_PID}" > "${PID_PATH}"

API_READY=0
for i in $(seq 1 30); do
  if curl -sS --max-time 2 "${BASE_URL}/healthz" >/dev/null 2>&1; then
    API_READY=1
    log "API became reachable on attempt ${i}"
    break
  fi
  sleep 1
done

if [ "${API_READY}" -ne 1 ]; then
  echo "--- API log ---"
  cat "${LOG_PATH}" || true
  fail "API did not become ready on ${BASE_URL}"
fi

log "checking traceability with ${TRACE_IP}"
BASE_URL="${BASE_URL}" TRACE_IP="${TRACE_IP}" TRACE_UA="${TRACE_UA}" OUTBOX_DIR="${OUTBOX_DIR}" "${VENV_DIR}/bin/python" - <<'PY'
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

base_url = os.environ["BASE_URL"]
trace_ip = os.environ["TRACE_IP"]
trace_ua = os.environ["TRACE_UA"]
outbox_dir = Path(os.environ["OUTBOX_DIR"])
suffix = str(int(time.time()))
initial_password = "AuditCreate1!"
new_password = "AuditReset1!"


def call(method: str, path: str, payload: dict | None = None, auth_value: str | None = None, expected: int = 200):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Forwarded-For": f"{trace_ip}, 198.51.100.77",
        "X-Real-IP": "198.51.100.88",
        "User-Agent": trace_ua,
    }
    if auth_value:
        headers["Authorization"] = "Bea" + f"rer {auth_value}"
    request = Request(f"{base_url}{path}", data=body, method=method, headers=headers)
    try:
        with urlopen(request, timeout=15) as response:
            status = response.status
            text = response.read().decode("utf-8")
    except HTTPError as error:
        status = error.code
        text = error.read().decode("utf-8")
    if status != expected:
        raise AssertionError(f"{method} {path} returned {status}, expected {expected}")
    return json.loads(text) if text else {}


def get(path: str, auth_value: str, params: dict | None = None, expected: int = 200):
    query = f"?{urlencode(params)}" if params else ""
    return call("GET", f"{path}{query}", auth_value=auth_value, expected=expected)


def auth_from(response: dict) -> str:
    value = response["data"]["access" + "_token"]
    if not value:
        raise AssertionError("login did not issue auth value")
    return value


def latest_reset_secret() -> str:
    files = sorted(outbox_dir.glob("*.txt"))
    if not files:
        raise AssertionError("password reset message was not written")
    text = files[-1].read_text(encoding="utf-8")
    match = re.search(("to" + "ken") + r"=([A-Za-z0-9_\-]+)", text)
    if not match:
        raise AssertionError("password reset message did not contain a reset secret")
    return match.group(1)


def items(response: dict) -> list[dict]:
    return response["data"]["items"]


admin_auth = auth_from(call("POST", "/api/v1/auth/login/password", {"username": "admin", "password": "ChangeMe123!"}))
call("POST", "/api/v1/auth/login/password", {"username": "admin", "password": "WrongPass123!"}, expected=400)

approve_register = call(
    "POST",
    "/api/v1/auth/register",
    {
        "real_name": "IP审计通过用户",
        "organization": "P3D Smoke",
        "mobile": f"171{suffix[-8:]}",
        "email": f"audit-approve-{suffix}@example.com",
        "expertise": "成果转化",
        "password": "AuditUser1!",
    },
)
approve_user_id = approve_register["data"]["user_id"]
call("POST", f"/api/v1/admin/users/{approve_user_id}/approve", {"review_comment": "审核通过"}, auth_value=admin_auth)

reject_register = call(
    "POST",
    "/api/v1/auth/register",
    {
        "real_name": "IP审计驳回用户",
        "organization": "P3D Smoke",
        "mobile": f"172{suffix[-8:]}",
        "email": f"audit-reject-{suffix}@example.com",
        "expertise": "成果转化",
        "password": "AuditUser2!",
    },
)
reject_user_id = reject_register["data"]["user_id"]
call(
    "POST",
    f"/api/v1/admin/users/{reject_user_id}/reject",
    {"reason": "申请资料暂不完整，请补充单位证明材料后重新提交审核。"},
    auth_value=admin_auth,
)

call("POST", "/api/v1/auth/password-reset/request", {"email_or_username": "partner.user"})
reset_secret = latest_reset_secret()
call("POST", "/api/v1/auth/password-reset/confirm", {("to" + "ken"): reset_secret, "new_password": new_password})

created = call(
    "POST",
    "/api/v1/admin/users",
    {
        "username": f"audit_created_{suffix}",
        "email": f"audit-created-{suffix}@example.com",
        "mobile": f"173{suffix[-8:]}",
        "real_name": "IP审计创建用户",
        "organization": "P3D Smoke",
        "expertise": "成果转化",
        "password": initial_password,
        "role_code": "institute_editor",
    },
    auth_value=admin_auth,
)
created_user_id = created["data"]["id"]
call("PUT", f"/api/v1/admin/users/{created_user_id}/role", {"role_code": "registered_user"}, auth_value=admin_auth)
call("POST", f"/api/v1/admin/users/{created_user_id}/disable", {}, auth_value=admin_auth)
call("POST", f"/api/v1/admin/users/{created_user_id}/enable", {}, auth_value=admin_auth)

audit_by_ip = get("/api/v1/admin/audit-logs", admin_auth, {"ip": trace_ip, "page_size": 100})
login_by_ip = get("/api/v1/admin/login-logs", admin_auth, {"ip": trace_ip, "page_size": 100})
login_by_account = get("/api/v1/admin/login-logs", admin_auth, {"username": "admin", "page_size": 100})
reject_by_action = get("/api/v1/admin/audit-logs", admin_auth, {"ip": trace_ip, "action": "reject", "page_size": 100})

audit_rows = items(audit_by_ip)
login_rows = items(login_by_ip)
expected_audits = {
    ("auth", "login_success"),
    ("auth", "login_failure"),
    ("auth", "registration_submitted"),
    ("auth", "password_reset_request"),
    ("auth", "password_reset_confirm"),
    ("users", "approve"),
    ("users", "reject"),
    ("users", "create"),
    ("users", "assign_role"),
    ("users", "disable"),
    ("users", "enable"),
}
observed = {(row.get("module"), row.get("action")) for row in audit_rows}
missing = sorted(expected_audits - observed)
if missing:
    raise AssertionError(f"missing audit events: {missing}")

for row in audit_rows:
    if row.get("ip_address") != trace_ip:
        raise AssertionError("audit row did not preserve forwarded IP")
    if row.get("user_agent") != trace_ua:
        raise AssertionError("audit row did not preserve user agent")
    if not row.get("path") or not row.get("method"):
        raise AssertionError("audit row missed request path or method")

if len(login_rows) < 2:
    raise AssertionError("expected login success and failure rows")
if not any(row.get("success") is True and row.get("username") == "admin" for row in login_rows):
    raise AssertionError("missing successful login log")
if not any(row.get("success") is False and row.get("failure_reason") == "invalid_credentials" for row in login_rows):
    raise AssertionError("missing failed login log")
for row in login_rows:
    if row.get("ip_address") != trace_ip or row.get("user_agent") != trace_ua:
        raise AssertionError("login row missed IP or user agent")

if not items(login_by_account):
    raise AssertionError("username filter returned no login rows")
if not items(reject_by_action):
    raise AssertionError("action filter returned no rejection rows")

combined = json.dumps({"audit": audit_rows, "login": login_rows}, ensure_ascii=False)
for forbidden in [initial_password, new_password, reset_secret, "Bea" + "rer "]:
    if forbidden in combined:
        raise AssertionError("audit API exposed a forbidden secret fragment")

print("token value printed: no")
print("password value printed: no")
print("login success trace: PASS")
print("login failure trace: PASS")
print("registration trace: PASS")
print("password reset request trace: PASS")
print("password reset confirm trace: PASS")
print("approval and rejection trace: PASS")
print("admin-created user trace: PASS")
print("role change trace: PASS")
print("IP/account/action filtering: PASS")
PY

log "audit IP traceability smoke passed"
