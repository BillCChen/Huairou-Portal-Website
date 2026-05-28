#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORTAL_USER_LIFECYCLE_SMOKE_PORT:-18230}"
HOST="${PORTAL_USER_LIFECYCLE_SMOKE_HOST:-127.0.0.1}"
BASE_URL="http://${HOST}:${PORT}"
RUNTIME_DIR_INPUT="${PORTAL_USER_LIFECYCLE_SMOKE_RUNTIME_DIR:-.runtime-logs/user-lifecycle-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""
API_PID=""

log() {
  echo "[user-lifecycle-smoke] $*"
}

fail() {
  echo "[user-lifecycle-smoke] ERROR: $*" >&2
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

DB_PATH="${RUNTIME_DIR}/portal_user_lifecycle_smoke.sqlite3"
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
pending_register="${WORK_DIR}/pending-register.json"
pending_login="${WORK_DIR}/pending-login.json"
new_login="${WORK_DIR}/new-login.json"
create_institution="${WORK_DIR}/create-institution.json"
institution_login="${WORK_DIR}/institution-login.json"
role_update="${WORK_DIR}/role-update.json"
reject_register="${WORK_DIR}/reject-register.json"
reject_login="${WORK_DIR}/reject-login.json"
empty_body="${WORK_DIR}/empty.json"
response="${WORK_DIR}/response.json"
printf '{}' > "${empty_body}"

cat > "${admin_login}" <<'JSON'
{"username":"admin","password":"ChangeMe123!"}
JSON

admin_code="$(request_json POST "/api/v1/auth/login/password" "${admin_login}" "${response}")"
expect_http "200" "${admin_code}" "admin login"
admin_token="$(json_field "$(cat "${response}")" "data.access_token")"
admin_id="$(json_field "$(cat "${response}")" "data.user.id")"

cat > "${pending_register}" <<JSON
{"real_name":"生命周期待审用户","organization":"P1-D Smoke Org","mobile":"155${suffix: -8}","email":"p1d-${suffix}@example.com","expertise":"成果转化","password":"PendingUser123!"}
JSON
register_code="$(request_json POST "/api/v1/auth/register" "${pending_register}" "${response}")"
expect_http "200" "${register_code}" "pending registration"
pending_user_id="$(json_field "$(cat "${response}")" "data.user_id")"

cat > "${pending_login}" <<JSON
{"username":"155${suffix: -8}","password":"PendingUser123!"}
JSON
pending_login_code="$(request_json POST "/api/v1/auth/login/password" "${pending_login}" "${response}")"
expect_http "400" "${pending_login_code}" "pending user login rejection"

approve_code="$(request_json POST "/api/v1/admin/users/${pending_user_id}/approve" "${empty_body}" "${response}" "${admin_token}")"
expect_http "200" "${approve_code}" "approve pending user"

active_login_code="$(request_json POST "/api/v1/auth/login/password" "${pending_login}" "${response}")"
expect_http "200" "${active_login_code}" "approved user login"
approved_token="$(json_field "$(cat "${response}")" "data.access_token")"

disable_code="$(request_json POST "/api/v1/admin/users/${pending_user_id}/disable" "${empty_body}" "${response}" "${admin_token}")"
expect_http "200" "${disable_code}" "disable active user"
disabled_login_code="$(request_json POST "/api/v1/auth/login/password" "${pending_login}" "${response}")"
expect_http "400" "${disabled_login_code}" "disabled user login rejection"
disabled_me_code="$(get_json "/api/v1/auth/me" "${response}" "${approved_token}")"
expect_http "401" "${disabled_me_code}" "disabled user token rejection"

enable_code="$(request_json POST "/api/v1/admin/users/${pending_user_id}/enable" "${empty_body}" "${response}" "${admin_token}")"
expect_http "200" "${enable_code}" "enable disabled user"
enabled_login_code="$(request_json POST "/api/v1/auth/login/password" "${pending_login}" "${response}")"
expect_http "200" "${enabled_login_code}" "enabled user login"

self_disable_code="$(request_json POST "/api/v1/admin/users/${admin_id}/disable" "${empty_body}" "${response}" "${admin_token}")"
expect_http "400" "${self_disable_code}" "self disable protection"

cat > "${create_institution}" <<JSON
{"username":"inst_${suffix}","email":"inst-${suffix}@example.com","mobile":"166${suffix: -8}","real_name":"机构用户","organization":"P1-D Institution","expertise":"机构协作","password":"InstitutionUser123!","role_code":"institute_editor"}
JSON
create_code="$(request_json POST "/api/v1/admin/users" "${create_institution}" "${response}" "${admin_token}")"
expect_http "200" "${create_code}" "create institution user"
institution_id="$(json_field "$(cat "${response}")" "data.id")"
institution_role="$(json_field "$(cat "${response}")" "data.role_code")"
[ "${institution_role}" = "institute_editor" ] || fail "institution user role mismatch"

cat > "${institution_login}" <<JSON
{"username":"inst_${suffix}","password":"InstitutionUser123!"}
JSON
institution_login_code="$(request_json POST "/api/v1/auth/login/password" "${institution_login}" "${response}")"
expect_http "200" "${institution_login_code}" "institution user login"

cat > "${role_update}" <<'JSON'
{"role_code":"registered_user"}
JSON
role_code="$(request_json PUT "/api/v1/admin/users/${institution_id}/role" "${role_update}" "${response}" "${admin_token}")"
expect_http "200" "${role_code}" "role assignment"
updated_role="$(json_field "$(cat "${response}")" "data.role_code")"
[ "${updated_role}" = "registered_user" ] || fail "role assignment did not update role"

self_role_code="$(request_json PUT "/api/v1/admin/users/${admin_id}/role" "${role_update}" "${response}" "${admin_token}")"
expect_http "400" "${self_role_code}" "self demotion protection"

cat > "${reject_register}" <<JSON
{"real_name":"生命周期驳回用户","organization":"P1-D Rejected Org","mobile":"156${suffix: -8}","email":"reject-${suffix}@example.com","expertise":"成果转化","password":"RejectedUser123!"}
JSON
reject_register_code="$(request_json POST "/api/v1/auth/register" "${reject_register}" "${response}")"
expect_http "200" "${reject_register_code}" "reject registration"
rejected_user_id="$(json_field "$(cat "${response}")" "data.user_id")"

cat > "${WORK_DIR}/reject-reason.json" <<'JSON'
{"reason":"Smoke review rejection"}
JSON
reject_code="$(request_json POST "/api/v1/admin/users/${rejected_user_id}/reject" "${WORK_DIR}/reject-reason.json" "${response}" "${admin_token}")"
expect_http "200" "${reject_code}" "reject pending user"

cat > "${reject_login}" <<JSON
{"username":"156${suffix: -8}","password":"RejectedUser123!"}
JSON
rejected_login_code="$(request_json POST "/api/v1/auth/login/password" "${reject_login}" "${response}")"
expect_http "400" "${rejected_login_code}" "rejected user login rejection"

audit_code="$(get_json "/api/v1/admin/audit-logs?page=1&page_size=100" "${response}" "${admin_token}")"
expect_http "200" "${audit_code}" "audit log listing"
"${VENV_DIR}/bin/python" - "${response}" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
actions = {item["action"] for item in payload["data"]["items"] if item["module"] == "users"}
required = {"approve", "reject", "disable", "enable", "create", "assign_role"}
missing = sorted(required - actions)
if missing:
    raise SystemExit(f"missing user audit actions: {missing}")
serialized = json.dumps(payload, ensure_ascii=False)
for forbidden in ["PendingUser123!", "InstitutionUser123!", "RejectedUser123!"]:
    if forbidden in serialized:
        raise SystemExit("audit response contains a raw smoke password")
PY

log "user lifecycle smoke passed"
