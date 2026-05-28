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
WORK_DIR="${RUNTIME_DIR}/requests"

rm -f "${DB_PATH}"
rm -rf "${WORK_DIR}"
mkdir -p "${UPLOAD_DIR}" "${WORK_DIR}"

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

json_field() {
  "${VENV_DIR}/bin/python" - "$1" "$2" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
value = payload
for part in sys.argv[2].split("."):
    value = value[part]
print(value)
PY
}

expect_http() {
  local expected="$1"
  local actual="$2"
  local label="$3"
  if [ "${actual}" != "${expected}" ]; then
    fail "${label} returned ${actual}, expected ${expected}"
  fi
}

request_json() {
  local method="$1"
  local path="$2"
  local body_file="$3"
  local output_file="$4"
  local token="${5:-}"
  if [ -n "${token}" ]; then
    curl -sS -o "${output_file}" -w "%{http_code}" \
      -X "${method}" "${BASE_URL}${path}" \
      -H 'Content-Type: application/json' \
      -H "Authorization: Bearer ${token}" \
      --data-binary @"${body_file}"
    return 0
  fi
  curl -sS -o "${output_file}" -w "%{http_code}" \
    -X "${method}" "${BASE_URL}${path}" \
    -H 'Content-Type: application/json' \
    --data-binary @"${body_file}"
}

get_json() {
  local path="$1"
  local output_file="$2"
  local token="${3:-}"
  if [ -n "${token}" ]; then
    curl -sS -o "${output_file}" -w "%{http_code}" \
      "${BASE_URL}${path}" \
      -H "Authorization: Bearer ${token}"
    return 0
  fi
  curl -sS -o "${output_file}" -w "%{http_code}" \
    "${BASE_URL}${path}"
}

suffix="$(date +%s)"
admin_login="${WORK_DIR}/admin-login.json"
user_register="${WORK_DIR}/user-register.json"
user_login="${WORK_DIR}/user-login.json"
empty_body="${WORK_DIR}/empty.json"
role_update="${WORK_DIR}/role-update.json"
response="${WORK_DIR}/response.json"
printf '{}' > "${empty_body}"
admin_password="$(
  cd apps/api-server
  "${VENV_DIR}/bin/python" - <<'PY'
from app.core.config import settings
print(settings.admin_password)
PY
)"
ordinary_password="$("${VENV_DIR}/bin/python" - <<'PY'
import secrets
print(f"Auth{secrets.token_urlsafe(12)}A1!")
PY
)"
ordinary_mobile="157${suffix: -8}"
ordinary_email="auth-${suffix}@example.com"

unauth_dashboard_code="$(get_json "/api/v1/admin/dashboard" "${response}")"
expect_http "401" "${unauth_dashboard_code}" "anonymous admin dashboard rejection"

TARGET_PATH="${admin_login}" ADMIN_PASSWORD="${admin_password}" "${VENV_DIR}/bin/python" - <<'PY'
import json
import os
from pathlib import Path

Path(os.environ["TARGET_PATH"]).write_text(
    json.dumps({"username": "admin", "password": os.environ["ADMIN_PASSWORD"]}, ensure_ascii=False),
    encoding="utf-8",
)
PY

admin_code="$(request_json POST "/api/v1/auth/login/password" "${admin_login}" "${response}")"
expect_http "200" "${admin_code}" "admin login"
admin_token="$(json_field "$(cat "${response}")" "data.access_token")"

admin_dashboard_code="$(get_json "/api/v1/admin/dashboard" "${response}" "${admin_token}")"
expect_http "200" "${admin_dashboard_code}" "admin dashboard access"
super_settings_code="$(get_json "/api/v1/admin/settings" "${response}" "${admin_token}")"
expect_http "200" "${super_settings_code}" "super admin settings access"

TARGET_PATH="${user_register}" ORDINARY_MOBILE="${ordinary_mobile}" ORDINARY_EMAIL="${ordinary_email}" ORDINARY_PASSWORD="${ordinary_password}" "${VENV_DIR}/bin/python" - <<'PY'
import json
import os
from pathlib import Path

Path(os.environ["TARGET_PATH"]).write_text(
    json.dumps(
        {
            "real_name": "权限边界用户",
            "organization": "P1-F Smoke Org",
            "mobile": os.environ["ORDINARY_MOBILE"],
            "email": os.environ["ORDINARY_EMAIL"],
            "expertise": "成果转化",
            "password": os.environ["ORDINARY_PASSWORD"],
        },
        ensure_ascii=False,
    ),
    encoding="utf-8",
)
PY
register_code="$(request_json POST "/api/v1/auth/register" "${user_register}" "${response}")"
expect_http "200" "${register_code}" "ordinary user registration"
ordinary_user_id="$(json_field "$(cat "${response}")" "data.user_id")"

approve_code="$(request_json POST "/api/v1/admin/users/${ordinary_user_id}/approve" "${empty_body}" "${response}" "${admin_token}")"
expect_http "200" "${approve_code}" "ordinary user approval"

TARGET_PATH="${user_login}" ORDINARY_MOBILE="${ordinary_mobile}" ORDINARY_PASSWORD="${ordinary_password}" "${VENV_DIR}/bin/python" - <<'PY'
import json
import os
from pathlib import Path

Path(os.environ["TARGET_PATH"]).write_text(
    json.dumps({"username": os.environ["ORDINARY_MOBILE"], "password": os.environ["ORDINARY_PASSWORD"]}, ensure_ascii=False),
    encoding="utf-8",
)
PY
ordinary_login_code="$(request_json POST "/api/v1/auth/login/password" "${user_login}" "${response}")"
expect_http "200" "${ordinary_login_code}" "ordinary user login"
ordinary_token="$(json_field "$(cat "${response}")" "data.access_token")"

ordinary_me_code="$(get_json "/api/v1/auth/me" "${response}" "${ordinary_token}")"
expect_http "200" "${ordinary_me_code}" "ordinary user me access"
ordinary_admin_code="$(get_json "/api/v1/admin/users" "${response}" "${ordinary_token}")"
expect_http "403" "${ordinary_admin_code}" "ordinary user admin list rejection"
ordinary_settings_code="$(get_json "/api/v1/admin/settings" "${response}" "${ordinary_token}")"
expect_http "403" "${ordinary_settings_code}" "ordinary user super admin settings rejection"

cat > "${role_update}" <<'JSON'
{"role_code":"registered_user"}
JSON
ordinary_role_code="$(request_json PUT "/api/v1/admin/users/1/role" "${role_update}" "${response}" "${ordinary_token}")"
expect_http "403" "${ordinary_role_code}" "ordinary user role assignment rejection"

"${VENV_DIR}/bin/python" - "${response}" "${admin_password}" "${ordinary_password}" <<'PY'
import json
import sys
from pathlib import Path

payload = Path(sys.argv[1]).read_text(encoding="utf-8")
for forbidden in [sys.argv[2], sys.argv[3]]:
    if forbidden in payload:
        raise SystemExit("permission smoke response contains a raw password")
try:
    json.loads(payload)
except json.JSONDecodeError as exc:
    raise SystemExit(f"last response was not JSON: {exc}") from exc
PY

log "auth permission smoke passed"
