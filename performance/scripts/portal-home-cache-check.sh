#!/usr/bin/env bash
set -euo pipefail

PORTAL_BASE_URL="${PORTAL_BASE_URL:-https://huairou.tech}"
PORTAL_ADMIN_BASE_URL="${PORTAL_ADMIN_BASE_URL:-https://portal-admin.huairou.tech}"
ACHIEVEMENT_BASE_URL="${ACHIEVEMENT_BASE_URL:-https://cg.huairou.tech}"

PORTAL_BASE_URL="${PORTAL_BASE_URL%/}"
PORTAL_ADMIN_BASE_URL="${PORTAL_ADMIN_BASE_URL%/}"
ACHIEVEMENT_BASE_URL="${ACHIEVEMENT_BASE_URL%/}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

failures=0

fetch_headers() {
  label="$1"
  url="$2"
  output_path="$3"

  echo "== ${label} =="
  if command -v curl >/dev/null 2>&1 && curl -sS --max-time 20 -D "${output_path}" -o /dev/null "${url}"; then
    sed -n '1,24p' "${output_path}" | tr -d '\r'
    return 0
  fi

  echo "curl unavailable or failed; falling back to python urllib"
  python3 - "${url}" "${output_path}" <<'PY'
import ssl
import sys
import urllib.request

url = sys.argv[1]
output_path = sys.argv[2]
request = urllib.request.Request(
    url,
    headers={"User-Agent": "portal-home-cache-check/1.0"},
    method="GET",
)

with urllib.request.urlopen(request, timeout=20, context=ssl.create_default_context()) as response:
    lines = [f"HTTP {response.status} {response.reason}"]
    for key, value in response.headers.items():
        lines.append(f"{key}: {value}")

with open(output_path, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines))
    handle.write("\n")
PY
  sed -n '1,24p' "${output_path}" | tr -d '\r'
}

header_value() {
  header_name="$1"
  file_path="$2"
  awk -v name="${header_name}" '
    BEGIN { target = tolower(name) ":" }
    {
      line = $0
      gsub(/\r/, "", line)
      lower = tolower(line)
      if (index(lower, target) == 1) {
        sub(/^[^:]+:[[:space:]]*/, "", line)
        print line
        exit
      }
    }
  ' "${file_path}"
}

expect_cache_status() {
  label="$1"
  file_path="$2"
  expected="$3"
  actual="$(header_value "X-Cache-Status" "${file_path}" || true)"

  if [ "${actual}" = "${expected}" ]; then
    echo "PASS: ${label} X-Cache-Status=${actual}"
    return 0
  fi

  echo "FAIL: ${label} expected X-Cache-Status=${expected}, got ${actual:-<missing>}"
  failures=$((failures + 1))
}

expect_not_cache_hit() {
  label="$1"
  file_path="$2"
  actual="$(header_value "X-Cache-Status" "${file_path}" || true)"

  if [ "${actual}" = "HIT" ]; then
    echo "FAIL: ${label} must not be served from cache"
    failures=$((failures + 1))
    return 0
  fi

  echo "PASS: ${label} is not cache HIT (${actual:-no cache header})"
}

root_first="${TMP_DIR}/root-first.headers"
root_second="${TMP_DIR}/root-second.headers"
query_headers="${TMP_DIR}/root-query.headers"
api_headers="${TMP_DIR}/api.headers"
admin_headers="${TMP_DIR}/admin.headers"
achievement_headers="${TMP_DIR}/achievement.headers"

fetch_headers "Portal root first request" "${PORTAL_BASE_URL}/" "${root_first}"
sleep 1
fetch_headers "Portal root second request" "${PORTAL_BASE_URL}/" "${root_second}"
fetch_headers "Portal root query bypass" "${PORTAL_BASE_URL}/?registered=pending" "${query_headers}"
fetch_headers "Portal public API" "${PORTAL_BASE_URL}/api/v1/public/home" "${api_headers}"
fetch_headers "Portal admin shell" "${PORTAL_ADMIN_BASE_URL}/" "${admin_headers}"
fetch_headers "Achievement shell" "${ACHIEVEMENT_BASE_URL}/" "${achievement_headers}"

expect_cache_status "Portal root second request" "${root_second}" "HIT"
expect_not_cache_hit "Portal root query request" "${query_headers}"
expect_not_cache_hit "Portal public API" "${api_headers}"
expect_not_cache_hit "Portal admin shell" "${admin_headers}"
expect_not_cache_hit "Achievement shell" "${achievement_headers}"

if [ "${failures}" -gt 0 ]; then
  echo "Portal home cache check failed: ${failures} issue(s)"
  exit 1
fi

echo "Portal home cache check passed"
