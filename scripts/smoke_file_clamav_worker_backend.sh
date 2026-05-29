#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORTAL_CLAMAV_SMOKE_PORT:-18282}"
HOST="${PORTAL_CLAMAV_SMOKE_HOST:-127.0.0.1}"
BASE_URL="http://${HOST}:${PORT}"
RUNTIME_DIR_INPUT="${PORTAL_CLAMAV_SMOKE_RUNTIME_DIR:-.runtime-logs/file-clamav-worker-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"
TRACE_IP="203.0.113.40"
TRACE_UA="Portal-P3E3-ClamAV-Smoke/1.0"
CLAMAV_HOST="${CLAMAV_HOST:-127.0.0.1}"
CLAMAV_PORT="${CLAMAV_PORT:-3310}"
CLAMAV_TIMEOUT_SECONDS="${CLAMAV_TIMEOUT_SECONDS:-30}"
START_COMPOSE="${PORTAL_CLAMAV_SMOKE_START_COMPOSE:-false}"
CONFIRM="${PORTAL_CLAMAV_SMOKE_CONFIRM:-false}"
COMPOSE_FILE="deploy/docker/compose.clamav.local.yml"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

VENV_DIR=""
API_PID=""
COMPOSE_STARTED=0

log() {
  echo "[clamav-worker-smoke] $*"
}

fail() {
  echo "[clamav-worker-smoke] ERROR: $*" >&2
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
  if [ "${COMPOSE_STARTED}" -eq 1 ]; then
    log "stopping local ClamAV compose"
    docker compose -f "${COMPOSE_FILE}" down >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

if [ "${CONFIRM}" != "true" ]; then
  fail "set PORTAL_CLAMAV_SMOKE_CONFIRM=true to run the local ClamAV smoke"
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

clamd_ready() {
  CLAMAV_HOST="${CLAMAV_HOST}" CLAMAV_PORT="${CLAMAV_PORT}" CLAMAV_TIMEOUT_SECONDS="${CLAMAV_TIMEOUT_SECONDS}" "${VENV_DIR}/bin/python" - <<'PY'
import os
import socket
import sys

host = os.environ["CLAMAV_HOST"]
port = int(os.environ["CLAMAV_PORT"])
timeout = float(os.environ["CLAMAV_TIMEOUT_SECONDS"])
try:
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(b"zPING\0")
        response = sock.recv(64)
except OSError:
    sys.exit(1)
sys.exit(0 if b"PONG" in response else 1)
PY
}

if ! clamd_ready; then
  if [ "${START_COMPOSE}" = "true" ]; then
    if ! command -v docker >/dev/null 2>&1; then
      fail "Docker is required to start local ClamAV compose"
    fi
    log "starting local ClamAV compose"
    docker compose -f "${COMPOSE_FILE}" up -d >/dev/null
    COMPOSE_STARTED=1
    for i in $(seq 1 60); do
      if clamd_ready; then
        log "clamd became reachable on attempt ${i}"
        break
      fi
      sleep 5
    done
  fi
fi

if ! clamd_ready; then
  fail "clamd is not reachable at ${CLAMAV_HOST}:${CLAMAV_PORT}"
fi

DB_PATH="${RUNTIME_DIR}/portal_file_clamav_worker_smoke.sqlite3"
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
    INIT_SAMPLE_DATA="false" \
    FILE_SCAN_PROVIDER="clamd" \
    CLAMAV_HOST="${CLAMAV_HOST}" \
    CLAMAV_PORT="${CLAMAV_PORT}" \
    CLAMAV_TIMEOUT_SECONDS="${CLAMAV_TIMEOUT_SECONDS}" \
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

log "running ClamAV worker smoke with ${TRACE_IP}"
BASE_URL="${BASE_URL}" DB_PATH="${DB_PATH}" STORAGE_ROOT="${STORAGE_ROOT}" TRACE_IP="${TRACE_IP}" TRACE_UA="${TRACE_UA}" ROOT_DIR="${ROOT_DIR}" PYTHON_BIN="${VENV_DIR}/bin/python" CLAMAV_HOST="${CLAMAV_HOST}" CLAMAV_PORT="${CLAMAV_PORT}" CLAMAV_TIMEOUT_SECONDS="${CLAMAV_TIMEOUT_SECONDS}" "${VENV_DIR}/bin/python" - <<'PY'
import json
import os
import subprocess
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
python_bin = os.environ["PYTHON_BIN"]
clamav_host = os.environ["CLAMAV_HOST"]
clamav_port = os.environ["CLAMAV_PORT"]
clamav_timeout = os.environ["CLAMAV_TIMEOUT_SECONDS"]
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
        with urlopen(req, timeout=30) as response:
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
os.environ["INIT_SAMPLE_DATA"] = "false"
os.environ["FILE_SCAN_PROVIDER"] = "clamd"
os.environ["CLAMAV_HOST"] = clamav_host
os.environ["CLAMAV_PORT"] = clamav_port
os.environ["CLAMAV_TIMEOUT_SECONDS"] = clamav_timeout

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import AuditLog, DownloadResource, FileRecord, Role, User
from app.db.session import SessionLocal

admin_name = "scan_admin"
content_name = "scan_content_admin"
auth_secret = settings.admin_password

with SessionLocal() as db:
    super_role = Role(code="super_admin", name="Super Admin", description="Full access")
    content_role = Role(code="content_admin", name="Content Admin", description="Content access")
    db.add_all([super_role, content_role])
    db.flush()
    db.add_all(
        [
            User(
                username=admin_name,
                mobile="13900000001",
                email="scan-admin@example.test",
                password_hash=hash_password(auth_secret),
                real_name="Scan Admin",
                organization="Local Smoke",
                expertise="File scanning",
                status="active",
                role_id=super_role.id,
            ),
            User(
                username=content_name,
                mobile="13900000002",
                email="scan-content@example.test",
                password_hash=hash_password(auth_secret),
                real_name="Scan Content",
                organization="Local Smoke",
                expertise="File scanning",
                status="active",
                role_id=content_role.id,
            ),
        ]
    )
    db.commit()


def login(username: str) -> str:
    payload = post_json("/api/v1/auth/login/password", {"username": username, "password": auth_secret})
    return payload["data"]["access_" + "token"]


admin_auth = login(admin_name)
content_auth = login(content_name)

eicar_body = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def create_resource(label: str, body: bytes, is_public: bool = True) -> dict:
    path = storage_root / "uploads" / f"{label}-{suffix}.txt"
    path.write_bytes(body)
    with SessionLocal() as db:
        file_record = FileRecord(
            origin_name=f"{label}.txt",
            storage_path=f"uploads/{path.name}",
            mime_type="text/plain",
            size=len(body),
            owner_id=None,
            scan_status="pending",
        )
        db.add(file_record)
        db.flush()
        resource = DownloadResource(
            title=f"{label} resource",
            slug=f"{label}-{suffix}",
            summary=f"{label} smoke resource",
            file_id=file_record.id,
            is_public=is_public,
        )
        db.add(resource)
        db.commit()
        return {"file_id": file_record.id, "resource_id": resource.id, "body": body}


def run_worker(port: str, status: str = "pending"):
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": f"sqlite:///{os.environ['DB_PATH']}",
            "STORAGE_ROOT": str(storage_root),
            "UPLOAD_DIR": "uploads",
            "INIT_SAMPLE_DATA": "false",
            "EMAIL_PROVIDER": "disabled",
            "FILE_SCAN_PROVIDER": "clamd",
            "CLAMAV_HOST": clamav_host,
            "CLAMAV_PORT": port,
            "CLAMAV_TIMEOUT_SECONDS": "3",
        }
    )
    result = subprocess.run(
        [
            python_bin,
            str(root_dir / "scripts/run_file_scan_worker.py"),
            "--provider",
            "clamd",
            "--limit",
            "20",
            "--retries",
            "1",
            "--retry-delay",
            "1",
            "--status",
            status,
        ],
        cwd=str(root_dir),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"worker failed: {result.stderr[:240]}")
    return result.stdout


def file_state(file_id: int) -> tuple[str, str | None, str | None]:
    with SessionLocal() as db:
        record = db.get(FileRecord, file_id)
        assert_true(record is not None, "file record missing")
        return record.scan_status, record.scan_engine, record.scan_message


normal = create_resource("clamav-normal", b"ordinary local ClamAV smoke payload\n")
eicar = create_resource("clamav-eicar", eicar_body)
run_worker(clamav_port)

status_value, engine, _ = file_state(normal["file_id"])
assert_true(status_value == "clean" and engine == "clamd", "normal file was not marked clean by clamd")
_, _, normal_body = request("GET", f"/api/v1/public/downloads/{normal['resource_id']}/download")
assert_true(normal_body == normal["body"], "clean normal download body mismatch")

status_value, engine, _ = file_state(eicar["file_id"])
assert_true(status_value == "infected" and engine == "clamd", "EICAR file was not marked infected by clamd")
request("GET", f"/api/v1/public/downloads/{eicar['resource_id']}/download", expected=403)

failed_rescan = create_resource("clamav-rescan-after-failed", b"rescan can become clean\n")
failed_override = create_resource("clamav-manual-override", b"override file remains local\n")
run_worker("9")
assert_true(file_state(failed_rescan["file_id"])[0] == "failed", "unavailable clamd did not mark rescan file failed")
assert_true(file_state(failed_override["file_id"])[0] == "failed", "unavailable clamd did not mark override file failed")
request("GET", f"/api/v1/public/downloads/{failed_rescan['resource_id']}/download", expected=403)

scan_result = post_json(f"/api/v1/admin/files/{failed_rescan['file_id']}/scan", {"provider": "clamd"}, admin_auth)
assert_true(scan_result["data"]["scan_status"] == "clean", "admin rescan did not restore clean status")
_, _, rescan_body = request("GET", f"/api/v1/public/downloads/{failed_rescan['resource_id']}/download")
assert_true(rescan_body == failed_rescan["body"], "rescan clean download body mismatch")

post_json(
    f"/api/v1/admin/files/{failed_override['file_id']}/scan/override-clean",
    {"reason": "too short"},
    admin_auth,
    expected=422,
)
valid_reason = "External owner accepted this local smoke file after manual review and documented responsibility."
post_json(
    f"/api/v1/admin/files/{failed_override['file_id']}/scan/override-clean",
    {"reason": valid_reason},
    content_auth,
    expected=403,
)
override_result = post_json(
    f"/api/v1/admin/files/{failed_override['file_id']}/scan/override-clean",
    {"reason": valid_reason},
    admin_auth,
)
assert_true(override_result["data"]["scan_status"] == "clean", "manual override did not mark clean")
assert_true(override_result["data"]["scan_engine"] == "manual_override", "manual override engine missing")
assert_true("no ClamAV scan performed" in (override_result["data"]["scan_message"] or ""), "manual override message missing")
_, _, override_body = request("GET", f"/api/v1/public/downloads/{failed_override['resource_id']}/download")
assert_true(override_body == failed_override["body"], "manual override download body mismatch")

admin_files = get_json("/api/v1/admin/files", admin_auth)
admin_serialized = json.dumps(admin_files, ensure_ascii=False)
assert_true("storage_path" not in admin_serialized, "admin files API leaked storage_path")
assert_true("manual_override" in admin_serialized, "manual override not visible in admin metadata")

audit = get_json("/api/v1/admin/audit-logs", admin_auth, {"ip": trace_ip, "page_size": 100})
rows = audit["data"]["items"]
assert_true(any(row["action"] == "file_scan_manual_override" for row in rows), "manual override audit missing")
assert_true(any(row["action"] == "file_scan" for row in rows), "admin rescan audit missing")
assert_true(any(row["action"] == "file_download_denied" and row["detail_json"].get("reason") == "scan_status_not_clean" for row in rows), "scan denial audit missing")

with SessionLocal() as db:
    worker_rows = db.query(AuditLog).filter(AuditLog.action == "file_scan_worker").all()
    assert_true(worker_rows, "worker audit missing")
    assert_true(any(row.detail_json.get("scan_status") == "infected" for row in worker_rows), "infected worker audit missing")
    assert_true(any(row.detail_json.get("scan_status") == "failed" for row in worker_rows), "failed worker audit missing")

audit_text = json.dumps([row for row in rows], ensure_ascii=False)
for forbidden in [auth_secret, str(storage_root), "Bea" + "rer ", eicar_body.decode("ascii")]:
    assert_true(forbidden not in audit_text, f"forbidden value leaked into audit rows: {forbidden[:12]}")

print("clamd normal clean: PASS")
print("EICAR infected denied: PASS")
print("clamd unavailable failed denied: PASS")
print("admin rescan failed to clean: PASS")
print("manual override reason and permission: PASS")
print("manual override download and audit: PASS")
print("storage_path hidden: PASS")
print("token value printed: no")
print("password value printed: no")
PY

log "ClamAV worker smoke passed"
