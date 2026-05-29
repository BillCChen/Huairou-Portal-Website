#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORTAL_FILE_DOWNLOAD_SMOKE_PORT:-18280}"
HOST="${PORTAL_FILE_DOWNLOAD_SMOKE_HOST:-127.0.0.1}"
BASE_URL="http://${HOST}:${PORT}"
RUNTIME_DIR_INPUT="${PORTAL_FILE_DOWNLOAD_SMOKE_RUNTIME_DIR:-.runtime-logs/file-download-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"
TRACE_IP="203.0.113.20"
TRACE_UA="Portal-P3E1-File-Smoke/1.0"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""
API_PID=""

log() {
  echo "[file-download-smoke] $*"
}

fail() {
  echo "[file-download-smoke] ERROR: $*" >&2
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

DB_PATH="${RUNTIME_DIR}/portal_file_download_smoke.sqlite3"
STORAGE_ROOT="${RUNTIME_DIR}/storage"
LOG_PATH="${RUNTIME_DIR}/api.log"
PID_PATH="${RUNTIME_DIR}/api.pid"

rm -f "${DB_PATH}"
rm -rf "${STORAGE_ROOT}"
mkdir -p "${STORAGE_ROOT}/uploads"

log "starting API at ${BASE_URL}"
(
  cd apps/api-server
  exec env \
    DATABASE_URL="sqlite:///${DB_PATH}" \
    STORAGE_ROOT="${STORAGE_ROOT}" \
    UPLOAD_DIR="uploads" \
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

log "checking file download security with ${TRACE_IP}"
BASE_URL="${BASE_URL}" DB_PATH="${DB_PATH}" STORAGE_ROOT="${STORAGE_ROOT}" TRACE_IP="${TRACE_IP}" TRACE_UA="${TRACE_UA}" ROOT_DIR="${ROOT_DIR}" "${VENV_DIR}/bin/python" - <<'PY'
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

base_url = os.environ["BASE_URL"]
db_path = os.environ["DB_PATH"]
storage_root = Path(os.environ["STORAGE_ROOT"])
trace_ip = os.environ["TRACE_IP"]
trace_ua = os.environ["TRACE_UA"]
root_dir = Path(os.environ["ROOT_DIR"])
suffix = str(int(time.time()))


def assert_true(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def request(method: str, path: str, payload: dict | None = None, auth_value: str | None = None, expected: int = 200):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Forwarded-For": f"{trace_ip}, 198.51.100.77",
        "X-Real-IP": "198.51.100.88",
        "User-Agent": trace_ua,
    }
    if auth_value:
        headers["Authorization"] = "Bea" + f"rer {auth_value}"
    req = Request(f"{base_url}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=15) as response:
            status = response.status
            data = response.read()
            response_headers = dict(response.headers.items())
    except HTTPError as exc:
        status = exc.code
        data = exc.read()
        response_headers = dict(exc.headers.items())
    if status != expected:
        raise AssertionError(f"{method} {path} returned {status}, expected {expected}")
    return status, response_headers, data


def request_json(method: str, path: str, payload: dict | None = None, auth_value: str | None = None, expected: int = 200):
    status, headers, data = request(method, path, payload, auth_value, expected)
    text = data.decode("utf-8")
    return json.loads(text) if text else {}


def get_json(path: str, auth_value: str | None = None, params: dict | None = None, expected: int = 200):
    query = f"?{urlencode(params)}" if params else ""
    return request_json("GET", f"{path}{query}", auth_value=auth_value, expected=expected)


def auth_from(response: dict) -> str:
    value = response["data"]["access" + "_token"]
    if not value:
        raise AssertionError("login did not issue auth value")
    return value


sys.path.insert(0, str(root_dir / "apps/api-server"))
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
os.environ["STORAGE_ROOT"] = str(storage_root)
os.environ["UPLOAD_DIR"] = "uploads"

from app.core.config import settings
from app.db.models import DownloadResource, FileRecord
from app.db.session import SessionLocal

public_body = b"public download smoke payload\n"
protected_body = b"protected download smoke payload\n"
public_path = storage_root / "uploads" / f"public-{suffix}.txt"
protected_path = storage_root / "uploads" / f"protected-{suffix}.txt"
public_path.write_bytes(public_body)
protected_path.write_bytes(protected_body)

with SessionLocal() as db:
    public_file = FileRecord(
        origin_name="public-smoke.txt",
        storage_path=f"uploads/{public_path.name}",
        mime_type="text/plain",
        size=len(public_body),
        owner_id=None,
    )
    protected_file = FileRecord(
        origin_name="protected-smoke.txt",
        storage_path=f"uploads/{protected_path.name}",
        mime_type="text/plain",
        size=len(protected_body),
        owner_id=None,
    )
    invalid_file = FileRecord(
        origin_name="invalid-path.txt",
        storage_path="../outside.txt",
        mime_type="text/plain",
        size=12,
        owner_id=None,
    )
    db.add_all([public_file, protected_file, invalid_file])
    db.flush()
    public_resource = DownloadResource(
        title="Public smoke resource",
        slug=f"public-smoke-{suffix}",
        summary="Public file download smoke",
        file_id=public_file.id,
        is_public=True,
    )
    protected_resource = DownloadResource(
        title="Protected smoke resource",
        slug=f"protected-smoke-{suffix}",
        summary="Protected file download smoke",
        file_id=protected_file.id,
        is_public=False,
    )
    invalid_resource = DownloadResource(
        title="Invalid path smoke resource",
        slug=f"invalid-path-smoke-{suffix}",
        summary="Invalid path smoke",
        file_id=invalid_file.id,
        is_public=True,
    )
    db.add_all([public_resource, protected_resource, invalid_resource])
    db.commit()
    ids = {
        "public": public_resource.id,
        "protected": protected_resource.id,
        "invalid": invalid_resource.id,
    }

admin_auth = auth_from(
    request_json(
        "POST",
        "/api/v1/auth/login/password",
        {"username": settings.admin_username, "password": settings.admin_password},
    )
)

downloads = get_json("/api/v1/public/downloads")
serialized = json.dumps(downloads, ensure_ascii=False)
assert_true("storage_path" not in serialized, "public downloads API leaked storage_path")
items = downloads["data"]["items"]
public_item = next((item for item in items if item["id"] == ids["public"]), None)
assert_true(public_item is not None, "public resource missing from public list")
assert_true(public_item.get("download_url") == f"/api/v1/public/downloads/{ids['public']}/download", "public download_url mismatch")

_, headers, body = request("GET", f"/api/v1/public/downloads/{ids['public']}/download")
assert_true(body == public_body, "public download response body mismatch")
assert_true(headers.get("content-type", "").startswith("text/plain"), "public download MIME type mismatch")

request("GET", f"/api/v1/public/downloads/{ids['protected']}/download", expected=403)
request("GET", f"/api/v1/downloads/{ids['protected']}/download", expected=401)
_, _, protected_download = request("GET", f"/api/v1/downloads/{ids['protected']}/download", auth_value=admin_auth)
assert_true(protected_download == protected_body, "protected download response body mismatch")
request("GET", "/api/v1/public/downloads/99999999/download", expected=404)
request("GET", f"/api/v1/public/downloads/{ids['invalid']}/download", expected=403)

audit = get_json("/api/v1/admin/audit-logs", admin_auth, {"ip": trace_ip, "module": "downloads", "page_size": 100})
rows = audit["data"]["items"]
actions = {row["action"] for row in rows}
for action in [
    "file_download_success",
    "file_download_denied",
    "file_download_not_found",
    "file_download_path_invalid",
]:
    assert_true(action in actions, f"missing audit action {action}")

assert_true(all(row.get("ip_address") == trace_ip for row in rows), "audit IP mismatch")
assert_true(all(row.get("user_agent") == trace_ua for row in rows), "audit User-Agent mismatch")
assert_true(any(row["action"] == "file_download_success" and row["detail_json"].get("actor_type") == "anonymous" for row in rows), "anonymous public success audit missing")
assert_true(any(row["action"] == "file_download_success" and row["detail_json"].get("actor_type") == "user" and row.get("user_id") for row in rows), "user protected success audit missing")
assert_true(any(row["action"] == "file_download_denied" and row["detail_json"].get("reason") in {"protected_resource", "missing_credentials"} for row in rows), "denied audit missing")
assert_true(any(row["action"] == "file_download_not_found" and row["detail_json"].get("reason") == "resource_not_found" for row in rows), "not-found audit missing")
assert_true(any(row["action"] == "file_download_path_invalid" and row["detail_json"].get("reason") == "path_invalid" for row in rows), "path-invalid audit missing")

audit_text = json.dumps(rows, ensure_ascii=False)
for forbidden in [settings.admin_password, "public download smoke payload", "protected download smoke payload", str(storage_root), "Bea" + "rer "]:
    assert_true(forbidden not in audit_text, f"audit output leaked forbidden fragment: {forbidden}")

print("public anonymous download: PASS")
print("protected anonymous denial: PASS")
print("protected active user download: PASS")
print("not-found audit: PASS")
print("path traversal guard: PASS")
print("public metadata storage_path hidden: PASS")
print("download audit IP/User-Agent: PASS")
print("token value printed: no")
print("password value printed: no")
PY

log "file download security smoke passed"
