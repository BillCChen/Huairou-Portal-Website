#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORTAL_SESSION_EXPIRY_SMOKE_PORT:-18260}"
HOST="${PORTAL_SESSION_EXPIRY_SMOKE_HOST:-127.0.0.1}"
BASE_URL="http://${HOST}:${PORT}"
RUNTIME_DIR_INPUT="${PORTAL_SESSION_EXPIRY_SMOKE_RUNTIME_DIR:-.runtime-logs/session-expiry-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"
WAIT_SECONDS="${PORTAL_SESSION_EXPIRY_SMOKE_WAIT_SECONDS:-70}"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""
API_PID=""

log() {
  echo "[session-expiry-smoke] $*"
}

fail() {
  echo "[session-expiry-smoke] ERROR: $*" >&2
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

DB_PATH="${RUNTIME_DIR}/portal_session_expiry_smoke.sqlite3"
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
    ACCESS_TOKEN_EXPIRE_MINUTES="1" \
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

BASE_URL="${BASE_URL}" WAIT_SECONDS="${WAIT_SECONDS}" "${VENV_DIR}/bin/python" - <<'PY'
import json
import os
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import sys

sys.path.insert(0, "apps/api-server")
from app.core.config import settings

base_url = os.environ["BASE_URL"]
wait_seconds = int(os.environ["WAIT_SECONDS"])


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
    if status != expected:
        raise SystemExit(f"{method} {path} returned {status}, expected {expected}")
    return json.loads(text) if text else {}


login = request_json(
    "/api/v1/auth/login/password",
    method="POST",
    body={"username": settings.admin_username, "password": settings.admin_password},
)["data"]
access_token = login.get("access_token")
if not access_token:
    raise SystemExit("login response did not include an access token")

request_json("/api/v1/auth/me", token=access_token)
print("token issued: yes")
print("auth/me before expiry: PASS")
time.sleep(wait_seconds)
request_json("/api/v1/auth/me", token=access_token, expected=401)
print(f"waited seconds: {wait_seconds}")
print("auth/me after expiry rejected: PASS")
print("token value printed: no")
PY

log "session expiry smoke passed"
