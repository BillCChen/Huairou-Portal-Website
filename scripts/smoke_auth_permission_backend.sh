#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORTAL_AUTH_PERMISSION_SMOKE_PORT:-18250}"
HOST="${PORTAL_AUTH_PERMISSION_SMOKE_HOST:-127.0.0.1}"
BASE_URL="http://${HOST}:${PORT}"
RUNTIME_DIR_INPUT="${PORTAL_AUTH_PERMISSION_SMOKE_RUNTIME_DIR:-.runtime-logs/auth-permission-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""
API_PID=""

log() {
  echo "[auth-permission-smoke] $*"
}

fail() {
  echo "[auth-permission-smoke] ERROR: $*" >&2
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

DB_PATH="${RUNTIME_DIR}/portal_auth_permission_smoke.sqlite3"
UPLOAD_DIR="${RUNTIME_DIR}/uploads"
LOG_PATH="${RUNTIME_DIR}/api.log"
PID_PATH="${RUNTIME_DIR}/api.pid"

rm -f "${DB_PATH}"
rm -rf "${RUNTIME_DIR}/requests"
mkdir -p "${UPLOAD_DIR}"

log "starting API at ${BASE_URL}"
(
  cd apps/api-server
  exec env \
    DATABASE_URL="sqlite:///${DB_PATH}" \
    UPLOAD_DIR="${UPLOAD_DIR}" \
    EMAIL_PROVIDER="disabled" \
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

BASE_URL="${BASE_URL}" "${VENV_DIR}/bin/python" - <<'PY'
import json
import os
import secrets
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, "apps/api-server")
from app.core.config import settings

base_url = os.environ["BASE_URL"]
suffix = str(int(time.time()))
admin_password = settings.admin_password
ordinary_password = f"Auth{secrets.token_urlsafe(12)}A1!"
ordinary_mobile = f"157{suffix[-8:]}"
ordinary_email = f"auth-{suffix}@example.com"
responses: list[str] = []


def request_json(path: str, method: str = "GET", body: dict | None = None, token: str | None = None, expected: int = 200):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            status = response.status
            text = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        status = exc.code
        text = exc.read().decode("utf-8", errors="replace")
    responses.append(text)
    if status != expected:
        raise SystemExit(f"{method} {path} returned {status}, expected {expected}")
    return json.loads(text) if text else {}


request_json("/api/v1/admin/dashboard", expected=401)

admin_login = request_json(
    "/api/v1/auth/login/password",
    method="POST",
    body={"username": "admin", "password": admin_password},
)["data"]
admin_token = admin_login["access_token"]

request_json("/api/v1/admin/dashboard", token=admin_token)
request_json("/api/v1/admin/settings", token=admin_token)

registration = request_json(
    "/api/v1/auth/register",
    method="POST",
    body={
        "real_name": "权限边界用户",
        "organization": "P1-F Smoke Org",
        "mobile": ordinary_mobile,
        "email": ordinary_email,
        "expertise": "成果转化",
        "password": ordinary_password,
    },
)["data"]
ordinary_user_id = registration["user_id"]

request_json(f"/api/v1/admin/users/{ordinary_user_id}/approve", method="POST", body={}, token=admin_token)

ordinary_login = request_json(
    "/api/v1/auth/login/password",
    method="POST",
    body={"username": ordinary_mobile, "password": ordinary_password},
)["data"]
ordinary_token = ordinary_login["access_token"]

request_json("/api/v1/auth/me", token=ordinary_token)
request_json("/api/v1/admin/users", token=ordinary_token, expected=403)
request_json("/api/v1/admin/settings", token=ordinary_token, expected=403)
request_json(
    "/api/v1/admin/users/1/role",
    method="PUT",
    body={"role_code": "registered_user"},
    token=ordinary_token,
    expected=403,
)

serialized = " ".join(responses)
for forbidden in [admin_password, ordinary_password]:
    if forbidden in serialized:
        raise SystemExit("permission smoke response contains a raw password")
PY

log "auth permission smoke passed"
