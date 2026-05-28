#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${PORTAL_API_BASE:-http://127.0.0.1:8000}"
ALLOW_UNAVAILABLE="${PORTAL_SMOKE_ALLOW_UNAVAILABLE:-0}"
TIMEOUT_SECONDS="${PORTAL_SMOKE_TIMEOUT_SECONDS:-5}"

if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: curl is not installed or not in PATH"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is not installed or not in PATH"
  exit 1
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

echo "[api-smoke] base url: ${BASE_URL}"

check_json_get() {
  local path="$1"
  local expected_status="${2:-200}"
  local body_file="${tmp_dir}/body_${path//\//_}.json"
  local status_file="${tmp_dir}/status_${path//\//_}.txt"

  echo "[api-smoke] GET ${path}"

  set +e
  local status
  status="$(curl \
    --silent \
    --show-error \
    --location \
    --max-time "${TIMEOUT_SECONDS}" \
    --output "${body_file}" \
    --write-out "%{http_code}" \
    "${BASE_URL}${path}" 2>"${body_file}.stderr")"
  local curl_exit="$?"
  set -e

  echo "${status}" > "${status_file}"

  if [ "${curl_exit}" -ne 0 ]; then
    echo "ERROR: curl failed for ${path}, exit=${curl_exit}"
    cat "${body_file}.stderr" || true
    return 2
  fi

  if [ "${status}" != "${expected_status}" ]; then
    echo "ERROR: unexpected HTTP status for ${path}: got ${status}, expected ${expected_status}"
    echo "--- response body ---"
    cat "${body_file}" || true
    echo
    return 1
  fi

  python3 - "$body_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8", errors="replace").strip()
if not text:
    print(f"ERROR: empty response body: {path}", file=sys.stderr)
    raise SystemExit(1)
try:
    json.loads(text)
except Exception as exc:
    print(f"ERROR: response is not valid JSON: {path}: {exc}", file=sys.stderr)
    print(text[:1000], file=sys.stderr)
    raise SystemExit(1)
PY
}

paths=(
  "/healthz"
  "/api/v1/public/categories"
  "/api/v1/public/home"
  "/api/v1/public/news"
  "/api/v1/public/cases"
  "/api/v1/public/leaders"
  "/api/v1/public/institutes"
  "/api/v1/public/settings"
  "/api/v1/public/downloads"
)

failed=0

for path in "${paths[@]}"; do
  if ! check_json_get "${path}" 200; then
    failed=1
    break
  fi
done

if [ "${failed}" -ne 0 ]; then
  if [ "${ALLOW_UNAVAILABLE}" = "1" ]; then
    echo "[api-smoke] BLOCKED: API is unavailable or smoke failed; allow-unavailable mode enabled"
    exit 0
  fi
  echo "[api-smoke] failed"
  exit 1
fi

echo "[api-smoke] passed"
