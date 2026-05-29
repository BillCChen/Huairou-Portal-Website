#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORTAL_PASSWORD_RESET_SMOKE_PORT:-18210}"
HOST="${PORTAL_PASSWORD_RESET_SMOKE_HOST:-127.0.0.1}"
BASE_URL="http://${HOST}:${PORT}"
RUNTIME_DIR_INPUT="${PORTAL_PASSWORD_RESET_SMOKE_RUNTIME_DIR:-.runtime-logs/password-reset-backend-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""
API_PID=""

log() {
  echo "[password-reset-smoke] $*"
}

fail() {
  echo "[password-reset-smoke] ERROR: $*" >&2
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

DB_PATH="${RUNTIME_DIR}/portal_password_reset_smoke.sqlite3"
DISABLED_DB_PATH="${RUNTIME_DIR}/portal_password_reset_disabled.sqlite3"
UPLOAD_DIR="${RUNTIME_DIR}/uploads"
OUTBOX_DIR="${RUNTIME_DIR}/mail_outbox"
DISABLED_OUTBOX_DIR="${RUNTIME_DIR}/disabled_mail_outbox"
LOG_PATH="${RUNTIME_DIR}/api.log"
PID_PATH="${RUNTIME_DIR}/api.pid"

rm -f "${DB_PATH}"
rm -f "${DISABLED_DB_PATH}"
rm -rf "${OUTBOX_DIR}" "${DISABLED_OUTBOX_DIR}"
mkdir -p "${UPLOAD_DIR}" "${OUTBOX_DIR}" "${DISABLED_OUTBOX_DIR}"

log "checking disabled email provider boundary"
(
  cd apps/api-server
  exec env \
    DATABASE_URL="sqlite:///${DISABLED_DB_PATH}" \
    EMAIL_PROVIDER="disabled" \
    PASSWORD_RESET_DEV_OUTBOX_DIR="${DISABLED_OUTBOX_DIR}" \
    INIT_SAMPLE_DATA="true" \
    "${VENV_DIR}/bin/python" - <<'PY'
from pathlib import Path

from app.db.seed import seed_database
from app.db.session import Base, SessionLocal, engine
from app.services.password_reset import PASSWORD_RESET_SAFE_MESSAGE, create_password_reset_request
from app.db.models import PasswordResetToken
from sqlalchemy import select

Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed_database(db)
    result = create_password_reset_request(db, email_or_username="partner.user", request_ip="127.0.0.1", user_agent="smoke")
    assert result["message"] == PASSWORD_RESET_SAFE_MESSAGE
    item = db.scalar(select(PasswordResetToken).order_by(PasswordResetToken.id.desc()).limit(1))
    assert item is not None
    assert item.consumed_at is not None

outbox = Path(__import__("os").environ["PASSWORD_RESET_DEV_OUTBOX_DIR"])
assert not list(outbox.glob("*.txt"))
PY
)

log "starting API at ${BASE_URL}"
(
  cd apps/api-server
  exec env \
    DATABASE_URL="sqlite:///${DB_PATH}" \
    UPLOAD_DIR="${UPLOAD_DIR}" \
    EMAIL_PROVIDER="dev_outbox" \
    PUBLIC_FRONTEND_BASE_URL="http://127.0.0.1:3100" \
    PASSWORD_RESET_DEV_OUTBOX_DIR="${OUTBOX_DIR}" \
    INIT_SAMPLE_DATA="true" \
    "${VENV_DIR}/bin/python" -m uvicorn app.main:app --host "${HOST}" --port "${PORT}"
) > "${LOG_PATH}" 2>&1 &

API_PID="$!"
echo "${API_PID}" > "${PID_PATH}"

API_READY=0
for i in $(seq 1 30); do
  if curl -sS --max-time 2 "${BASE_URL}/healthz" >/tmp/portal_password_reset_smoke_healthz.json 2>/dev/null; then
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

http_post() {
  local path="$1"
  local body_file="$2"
  local output_file="$3"
  curl -sS -o "${output_file}" -w "%{http_code}" \
    -X POST "${BASE_URL}${path}" \
    -H 'Content-Type: application/json' \
    --data-binary @"${body_file}"
}

request_existing="${RUNTIME_DIR}/request-existing.json"
request_missing="${RUNTIME_DIR}/request-missing.json"
confirm_body="${RUNTIME_DIR}/confirm.json"
replay_body="${RUNTIME_DIR}/replay.json"
expired_body="${RUNTIME_DIR}/expired.json"
login_old_body="${RUNTIME_DIR}/login-old.json"
login_new_body="${RUNTIME_DIR}/login-new.json"
response_file="${RUNTIME_DIR}/response.json"

printf '{"email_or_username":"partner.user"}' > "${request_existing}"
printf '{"email_or_username":"missing.user@example.test"}' > "${request_missing}"

existing_code="$(http_post "/api/v1/auth/password-reset/request" "${request_existing}" "${RUNTIME_DIR}/existing-response.json")"
missing_code="$(http_post "/api/v1/auth/password-reset/request" "${request_missing}" "${RUNTIME_DIR}/missing-response.json")"
[ "${existing_code}" = "200" ] || fail "existing user reset request returned ${existing_code}"
[ "${missing_code}" = "200" ] || fail "missing user reset request returned ${missing_code}"

existing_message="$(json_field "$(cat "${RUNTIME_DIR}/existing-response.json")" "data.message")"
missing_message="$(json_field "$(cat "${RUNTIME_DIR}/missing-response.json")" "data.message")"
[ "${existing_message}" = "${missing_message}" ] || fail "reset request messages differ"

token="$("${VENV_DIR}/bin/python" - "${OUTBOX_DIR}" <<'PY'
import re
import sys
from pathlib import Path
files = sorted(Path(sys.argv[1]).glob("*.txt"))
matches = []
for file in files:
    text = file.read_text(encoding="utf-8")
    if "Subject: Portal password reset" not in text:
        continue
    match = re.search(r"token=([A-Za-z0-9_\-]+)", text)
    if match:
        matches.append(match.group(1))
if len(matches) != 1:
    raise SystemExit(f"expected exactly one reset token message, found {len(matches)}")
print(matches[-1])
PY
)"

"${VENV_DIR}/bin/python" - "${DB_PATH}" "${token}" <<'PY'
import sqlite3
import sys
db_path, token = sys.argv[1], sys.argv[2]
conn = sqlite3.connect(db_path)
rows = conn.execute("select token_hash, consumed_at from password_reset_tokens").fetchall()
assert len(rows) == 1, rows
token_hash, consumed_at = rows[0]
assert token_hash != token
assert len(token_hash) == 64
assert consumed_at is None
conn.close()
PY

new_password="PortalReset123!"
printf '{"token":"%s","new_password":"%s"}' "${token}" "${new_password}" > "${confirm_body}"
confirm_code="$(http_post "/api/v1/auth/password-reset/confirm" "${confirm_body}" "${response_file}")"
[ "${confirm_code}" = "200" ] || fail "valid reset confirm returned ${confirm_code}"

printf '{"username":"partner.user","password":"Partner123!"}' > "${login_old_body}"
printf '{"username":"partner.user","password":"%s"}' "${new_password}" > "${login_new_body}"

old_login_code="$(http_post "/api/v1/auth/login/password" "${login_old_body}" "${response_file}")"
new_login_code="$(http_post "/api/v1/auth/login/password" "${login_new_body}" "${response_file}")"
[ "${old_login_code}" = "400" ] || fail "old password login returned ${old_login_code}"
[ "${new_login_code}" = "200" ] || fail "new password login returned ${new_login_code}"

printf '{"token":"%s","new_password":"PortalReset456!"}' "${token}" > "${replay_body}"
replay_code="$(http_post "/api/v1/auth/password-reset/confirm" "${replay_body}" "${response_file}")"
[ "${replay_code}" = "400" ] || fail "consumed token replay returned ${replay_code}"

printf '{"email_or_username":"partner.user"}' > "${request_existing}"
second_request_code="$(http_post "/api/v1/auth/password-reset/request" "${request_existing}" "${response_file}")"
[ "${second_request_code}" = "200" ] || fail "second reset request returned ${second_request_code}"

second_token="$("${VENV_DIR}/bin/python" - "${OUTBOX_DIR}" <<'PY'
import re
import sys
from pathlib import Path
files = sorted(Path(sys.argv[1]).glob("*.txt"))
matches = []
for file in files:
    text = file.read_text(encoding="utf-8")
    if "Subject: Portal password reset" not in text:
        continue
    match = re.search(r"token=([A-Za-z0-9_\-]+)", text)
    if match:
        matches.append(match.group(1))
if len(matches) != 2:
    raise SystemExit(f"expected two reset token messages, found {len(matches)}")
print(matches[-1])
PY
)"

"${VENV_DIR}/bin/python" - "${DB_PATH}" <<'PY'
import sqlite3
conn = sqlite3.connect(__import__("sys").argv[1])
latest_id = conn.execute("select max(id) from password_reset_tokens").fetchone()[0]
conn.execute("update password_reset_tokens set expires_at = '2000-01-01 00:00:00' where id = ?", (latest_id,))
conn.commit()
conn.close()
PY

printf '{"token":"%s","new_password":"PortalReset789!"}' "${second_token}" > "${expired_body}"
expired_code="$(http_post "/api/v1/auth/password-reset/confirm" "${expired_body}" "${response_file}")"
[ "${expired_code}" = "400" ] || fail "expired token confirm returned ${expired_code}"

"${VENV_DIR}/bin/python" - "${DB_PATH}" "${OUTBOX_DIR}" <<'PY'
import sqlite3
import sys
from pathlib import Path
db_path, outbox_dir = sys.argv[1], Path(sys.argv[2])
conn = sqlite3.connect(db_path)
audit_count = conn.execute("select count(*) from audit_logs where module = 'auth' and object_type = 'password_reset'").fetchone()[0]
assert audit_count >= 4, audit_count
combined = " ".join((row[0] or "") for row in conn.execute("select coalesce(detail_json, '') from audit_logs"))
for file in outbox_dir.glob("*.txt"):
    text = file.read_text(encoding="utf-8")
    token_fragment = "token="
    if token_fragment not in text:
        continue
    assert token_fragment in text
    token = text.split(token_fragment, 1)[1].split()[0]
    assert token not in combined
conn.close()
PY

log "password reset backend smoke passed"
