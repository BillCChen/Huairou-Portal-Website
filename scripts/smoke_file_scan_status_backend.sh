#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORTAL_FILE_SCAN_SMOKE_PORT:-18281}"
HOST="${PORTAL_FILE_SCAN_SMOKE_HOST:-127.0.0.1}"
BASE_URL="http://${HOST}:${PORT}"
RUNTIME_DIR_INPUT="${PORTAL_FILE_SCAN_SMOKE_RUNTIME_DIR:-.runtime-logs/file-scan-status-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"
TRACE_IP="203.0.113.30"
TRACE_UA="Portal-P3E2-Scan-Smoke/1.0"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""
API_PID=""

log() {
  echo "[file-scan-smoke] $*"
}

fail() {
  echo "[file-scan-smoke] ERROR: $*" >&2
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

DB_PATH="${RUNTIME_DIR}/portal_file_scan_smoke.sqlite3"
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

log "checking file scan status gate with ${TRACE_IP}"
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
        raise AssertionError(f"{method} {path} expected {expected}, got {status}: {data[:160]!r}")
    return status, response_headers, data


def get_json(path: str, auth_value: str | None = None, params: dict | None = None, expected: int = 200):
    target = path
    if params:
        target = f"{path}?{urlencode(params)}"
    _, _, body = request("GET", target, auth_value=auth_value, expected=expected)
    return json.loads(body.decode("utf-8"))


def post_json(path: str, payload: dict | None = None, auth_value: str | None = None, expected: int = 200):
    _, _, body = request("POST", path, payload=payload or {}, auth_value=auth_value, expected=expected)
    return json.loads(body.decode("utf-8"))


sys.path.insert(0, str(root_dir / "apps/api-server"))
os.environ["DATABASE_URL"] = f"sqlite:///{os.environ['DB_PATH']}"
os.environ["STORAGE_ROOT"] = str(storage_root)
os.environ["UPLOAD_DIR"] = "uploads"
os.environ["EMAIL_PROVIDER"] = "disabled"
os.environ["INIT_SAMPLE_DATA"] = "true"

from app.core.config import settings
from app.db.models import DownloadResource, FileRecord
from app.db.session import SessionLocal

login_data = post_json(
    "/api/v1/auth/login/password",
    {"username": settings.admin_username, "password": settings.admin_password},
)
admin_auth = login_data["data"]["access_" + "token"]

public_body = b"public pending then clean payload\n"
protected_body = b"protected clean payload\n"
infected_body = b"this file contains an infected test signature\n"
failed_body = b"scan-fail simulated scanner error\n"
null_body = b"null scan status payload\n"
skipped_body = b"skipped scan status payload\n"

paths = {
    "public": storage_root / "uploads" / f"public-{suffix}.txt",
    "protected": storage_root / "uploads" / f"protected-{suffix}.txt",
    "infected": storage_root / "uploads" / f"infected-{suffix}.txt",
    "failed": storage_root / "uploads" / f"failed-{suffix}.txt",
    "null": storage_root / "uploads" / f"null-{suffix}.txt",
    "skipped": storage_root / "uploads" / f"skipped-{suffix}.txt",
}
paths["public"].write_bytes(public_body)
paths["protected"].write_bytes(protected_body)
paths["infected"].write_bytes(infected_body)
paths["failed"].write_bytes(failed_body)
paths["null"].write_bytes(null_body)
paths["skipped"].write_bytes(skipped_body)

with SessionLocal() as db:
    public_file = FileRecord(
        origin_name="public-pending.txt",
        storage_path=f"uploads/{paths['public'].name}",
        mime_type="text/plain",
        size=len(public_body),
        owner_id=None,
    )
    protected_file = FileRecord(
        origin_name="protected-clean.txt",
        storage_path=f"uploads/{paths['protected'].name}",
        mime_type="text/plain",
        size=len(protected_body),
        owner_id=None,
    )
    infected_file = FileRecord(
        origin_name="infected-sample.txt",
        storage_path=f"uploads/{paths['infected'].name}",
        mime_type="text/plain",
        size=len(infected_body),
        owner_id=None,
    )
    failed_file = FileRecord(
        origin_name="scan-fail-sample.txt",
        storage_path=f"uploads/{paths['failed'].name}",
        mime_type="text/plain",
        size=len(failed_body),
        owner_id=None,
    )
    null_file = FileRecord(
        origin_name="null-status.txt",
        storage_path=f"uploads/{paths['null'].name}",
        mime_type="text/plain",
        size=len(null_body),
        owner_id=None,
        scan_status=None,
    )
    skipped_file = FileRecord(
        origin_name="skipped-status.txt",
        storage_path=f"uploads/{paths['skipped'].name}",
        mime_type="text/plain",
        size=len(skipped_body),
        owner_id=None,
        scan_status="skipped",
    )
    db.add_all([public_file, protected_file, infected_file, failed_file, null_file, skipped_file])
    db.flush()
    public_resource = DownloadResource(
        title="Public scan smoke resource",
        slug=f"public-scan-smoke-{suffix}",
        summary="Public file scan status smoke",
        file_id=public_file.id,
        is_public=True,
    )
    protected_resource = DownloadResource(
        title="Protected scan smoke resource",
        slug=f"protected-scan-smoke-{suffix}",
        summary="Protected file scan status smoke",
        file_id=protected_file.id,
        is_public=False,
    )
    infected_resource = DownloadResource(
        title="Infected scan smoke resource",
        slug=f"infected-scan-smoke-{suffix}",
        summary="Infected file scan status smoke",
        file_id=infected_file.id,
        is_public=False,
    )
    failed_resource = DownloadResource(
        title="Failed scan smoke resource",
        slug=f"failed-scan-smoke-{suffix}",
        summary="Failed file scan status smoke",
        file_id=failed_file.id,
        is_public=True,
    )
    null_resource = DownloadResource(
        title="Null scan smoke resource",
        slug=f"null-scan-smoke-{suffix}",
        summary="Null scan status smoke",
        file_id=null_file.id,
        is_public=True,
    )
    skipped_resource = DownloadResource(
        title="Skipped scan smoke resource",
        slug=f"skipped-scan-smoke-{suffix}",
        summary="Skipped scan status smoke",
        file_id=skipped_file.id,
        is_public=True,
    )
    db.add_all([public_resource, protected_resource, infected_resource, failed_resource, null_resource, skipped_resource])
    db.commit()
    ids = {
        "public_file": public_file.id,
        "protected_file": protected_file.id,
        "infected_file": infected_file.id,
        "failed_file": failed_file.id,
        "public": public_resource.id,
        "protected": protected_resource.id,
        "infected": infected_resource.id,
        "failed": failed_resource.id,
        "null": null_resource.id,
        "skipped": skipped_resource.id,
    }

downloads = get_json("/api/v1/public/downloads")
serialized = json.dumps(downloads, ensure_ascii=False)
assert_true("storage_path" not in serialized, "public downloads API leaked storage_path")
items = downloads["data"]["items"]
public_item = next(item for item in items if item["id"] == ids["public"])
assert_true(public_item["file"]["scan_status"] == "pending", "default scan_status is not pending")

request("GET", f"/api/v1/public/downloads/{ids['public']}/download", expected=403)
post_json(f"/api/v1/admin/files/{ids['public_file']}/mock-scan", auth_value=admin_auth)
_, _, clean_public = request("GET", f"/api/v1/public/downloads/{ids['public']}/download")
assert_true(clean_public == public_body, "clean public download body mismatch")

request("GET", f"/api/v1/downloads/{ids['protected']}/download", auth_value=admin_auth, expected=403)
post_json(f"/api/v1/admin/files/{ids['infected_file']}/mock-scan", auth_value=admin_auth)
request("GET", f"/api/v1/downloads/{ids['infected']}/download", auth_value=admin_auth, expected=403)
post_json(f"/api/v1/admin/files/{ids['protected_file']}/mock-scan", auth_value=admin_auth)
_, _, clean_protected = request("GET", f"/api/v1/downloads/{ids['protected']}/download", auth_value=admin_auth)
assert_true(clean_protected == protected_body, "clean protected download body mismatch")

failed_scan = post_json(f"/api/v1/admin/files/{ids['failed_file']}/mock-scan", auth_value=admin_auth)
assert_true(failed_scan["data"]["scan_status"] == "failed", "mock scanner did not produce failed status")
request("GET", f"/api/v1/public/downloads/{ids['failed']}/download", expected=403)
request("GET", f"/api/v1/public/downloads/{ids['null']}/download", expected=403)
request("GET", f"/api/v1/public/downloads/{ids['skipped']}/download", expected=403)

admin_files = get_json("/api/v1/admin/files", admin_auth)
admin_serialized = json.dumps(admin_files, ensure_ascii=False)
assert_true("storage_path" not in admin_serialized, "admin files API leaked storage_path")
assert_true(any(item["id"] == ids["public_file"] and item["scan_status"] == "clean" for item in admin_files["data"]), "admin files scan_status missing")

audit = get_json("/api/v1/admin/audit-logs", admin_auth, {"ip": trace_ip, "module": "downloads", "page_size": 100})
rows = audit["data"]["items"]
assert_true(rows, "no download audit rows returned")
assert_true(all(row.get("ip_address") == trace_ip for row in rows), "audit IP mismatch")
assert_true(any(row.get("user_agent") == trace_ua for row in rows), "audit User-Agent missing")
assert_true(
    any(
        row["action"] == "file_download_denied"
        and row["detail_json"].get("reason") == "scan_status_not_clean"
        and row["detail_json"].get("scan_status") in {"pending", "infected", "failed", "skipped"}
        for row in rows
    ),
    "scan-status denial audit missing",
)
assert_true(any(row["action"] == "file_download_success" for row in rows), "download success audit missing")

audit_text = json.dumps(rows, ensure_ascii=False)
for forbidden in [settings.admin_password, "public pending then clean payload", "protected clean payload", str(storage_root), "Bea" + "rer "]:
    assert_true(forbidden not in audit_text, f"forbidden value leaked into audit rows: {forbidden[:12]}")

print("pending public download denied: PASS")
print("clean public download: PASS")
print("pending protected download denied: PASS")
print("infected protected download denied: PASS")
print("clean protected download: PASS")
print("failed/null/skipped scan status denied: PASS")
print("scan-status audit IP/User-Agent: PASS")
print("public/admin metadata storage_path hidden: PASS")
print("real scanner used: no")
print("token value printed: no")
print("password value printed: no")
PY

log "file scan status smoke passed"
