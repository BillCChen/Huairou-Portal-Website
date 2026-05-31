#!/usr/bin/env bash
set -euo pipefail

SERVER_HOST="${SERVER_HOST:-}"
SSH_USER="${SSH_USER:-root}"
SSH_KEY="${SSH_KEY:-}"
ACCESS_LOG="${ACCESS_LOG:-/var/log/nginx/access.log}"

if [ -z "${SERVER_HOST}" ]; then
  echo "ERROR: SERVER_HOST is required." >&2
  exit 1
fi

if [ -z "${SSH_KEY}" ]; then
  echo "ERROR: SSH_KEY is required." >&2
  exit 1
fi

redact() {
  sed -E \
    -e 's/([?&]([[:alnum:]_-]*token|code|passwd)=)[^&[:space:]]+/\1***REDACTED***/g' \
    -e 's/([0-9]{1,3}\.){3}[0-9]{1,3}/***IP***/g'
}

ssh -i "${SSH_KEY}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${SSH_USER}@${SERVER_HOST}" \
  "ACCESS_LOG='${ACCESS_LOG}' bash -s" <<'REMOTE' | redact
set -euo pipefail

echo "== nginx timing log_format capability =="
if nginx -T 2>/dev/null | grep -En 'log_format|access_log|request_time|upstream_response_time' | sed -n '1,120p'; then
  true
else
  echo "no log_format/access_log timing lines found through nginx -T"
fi

echo
echo "== timing fields present in config =="
if nginx -T 2>/dev/null | grep -Eq '\$request_time|\$upstream_response_time'; then
  echo "timing_fields_in_config=yes"
else
  echo "timing_fields_in_config=no"
fi

echo
echo "== recent access log timing markers =="
if [ -r "${ACCESS_LOG}" ]; then
  recent_lines="$(tail -n 200 "${ACCESS_LOG}" 2>/dev/null || true)"
  if printf '%s\n' "${recent_lines}" | grep -Eq 'request_time=|upstream_response_time=| rt=| urt='; then
    echo "named_timing_markers_in_access_log=yes"
  else
    echo "named_timing_markers_in_access_log=no"
  fi
  printf '%s\n' "${recent_lines}" \
    | sed -E 's/([?&]([[:alnum:]_-]*token|code|passwd)=)[^&[:space:]]+/\1***REDACTED***/g' \
    | awk '{$1="***IP***"; print}' \
    | tail -3
else
  echo "access log unavailable: ${ACCESS_LOG}"
fi
REMOTE
