#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORTAL_LOCAL_SMOKE_PORT:-18200}"
HOST="${PORTAL_LOCAL_SMOKE_HOST:-127.0.0.1}"
BASE_URL="http://${HOST}:${PORT}"
RUNTIME_DIR_INPUT="${PORTAL_LOCAL_SMOKE_RUNTIME_DIR:-.runtime-logs/local-public-api-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""
API_PID=""

log() {
  echo "[local-api-smoke] $*"
}

fail() {
  echo "[local-api-smoke] ERROR: $*" >&2
  exit 1
}

cleanup() {
  if [ -n "${API_PID}" ] && ps -p "${API_PID}" >/dev/null 2>&1; then
    log "stopping API pid ${API_PID}"
    kill "${API_PID}" || true
    sleep 2
    if ps -p "${API_PID}" >/dev/null 2>&1; then
      kill -9 "${API_PID}" || true
    fi
  fi
}

trap cleanup EXIT

if [ ! -f "apps/api-server/requirements.txt" ]; then
  fail "missing apps/api-server/requirements.txt"
fi

if [ ! -x "scripts/smoke_api_public.sh" ]; then
  fail "missing executable scripts/smoke_api_public.sh"
fi

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

python_version() {
  local python_bin="$1"
  "${python_bin}" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
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
  local python_ver

  if ! command -v "${python_bin}" >/dev/null 2>&1; then
    log "skipping ${python_bin}: not found"
    return 1
  fi

  python_mm="$(python_minor "${python_bin}")"
  python_ver="$(python_version "${python_bin}")"

  if [ "${python_mm}" = "3.14" ]; then
    log "skipping ${python_bin}: Python 3.14 is not accepted for current psycopg lock"
    return 1
  fi

  case "${python_mm}" in
    3.11|3.12|3.13) ;;
    *)
      log "skipping ${python_bin}: unsupported Python ${python_ver}"
      return 1
      ;;
  esac

  VENV_DIR="${RUNTIME_DIR}/backend-venv-py${python_mm//./}"
  mkdir -p "${RUNTIME_DIR}"

  if [ ! -x "${VENV_DIR}/bin/python" ]; then
    log "creating venv at ${VENV_DIR} with ${python_bin} ${python_ver}"
    if ! "${python_bin}" -m venv "${VENV_DIR}"; then
      log "failed to create venv with ${python_bin} ${python_ver}"
      return 1
    fi
  fi

  "${VENV_DIR}/bin/python" --version

  log "upgrading pip"
  if ! "${VENV_DIR}/bin/python" -m pip install --upgrade pip; then
    log "failed to upgrade pip with ${python_bin} ${python_ver}"
    return 1
  fi

  log "installing backend requirements"
  if ! "${VENV_DIR}/bin/python" -m pip install -r apps/api-server/requirements.txt; then
    log "failed to install backend requirements with ${python_bin} ${python_ver}"
    return 1
  fi

  log "using Python ${python_ver} via ${python_bin}"
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

log "verifying key imports"
"${VENV_DIR}/bin/python" - <<'PY'
import sys
import fastapi
import uvicorn
import sqlalchemy
import psycopg
print("python", sys.version)
print("fastapi", getattr(fastapi, "__version__", "unknown"))
print("uvicorn", getattr(uvicorn, "__version__", "unknown"))
print("sqlalchemy", getattr(sqlalchemy, "__version__", "unknown"))
print("psycopg", getattr(psycopg, "__version__", "unknown"))
PY

DB_PATH="${RUNTIME_DIR}/portal_local_smoke.sqlite3"
UPLOAD_DIR="${RUNTIME_DIR}/uploads"
LOG_PATH="${RUNTIME_DIR}/api.log"
PID_PATH="${RUNTIME_DIR}/api.pid"

mkdir -p "${UPLOAD_DIR}"

log "starting API at ${BASE_URL}"
(
  cd apps/api-server
  exec env \
    DATABASE_URL="sqlite:///${DB_PATH}" \
    UPLOAD_DIR="${UPLOAD_DIR}" \
    "${VENV_DIR}/bin/python" -m uvicorn app.main:app --host "${HOST}" --port "${PORT}"
) > "${LOG_PATH}" 2>&1 &

API_PID="$!"
echo "${API_PID}" > "${PID_PATH}"

API_READY=0
for i in $(seq 1 30); do
  if curl -sS --max-time 2 "${BASE_URL}/healthz" >/tmp/portal_local_smoke_healthz.json; then
    API_READY=1
    log "API became reachable on attempt ${i}"
    cat /tmp/portal_local_smoke_healthz.json
    echo
    break
  fi
  sleep 1
done

if [ "${API_READY}" -ne 1 ]; then
  echo "--- API log ---"
  cat "${LOG_PATH}" || true
  fail "API did not become ready on ${BASE_URL}"
fi

log "running public API smoke"
PORTAL_API_BASE="${BASE_URL}" ./scripts/smoke_api_public.sh

log "real public API smoke passed"
