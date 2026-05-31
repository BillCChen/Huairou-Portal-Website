#!/usr/bin/env bash
set -euo pipefail

SERVER_HOST="${SERVER_HOST:-}"
SSH_USER="${SSH_USER:-root}"
SSH_KEY="${SSH_KEY:-}"
ACCESS_LOG="${ACCESS_LOG:-/var/log/nginx/access.log}"
ERROR_LOG="${ERROR_LOG:-/var/log/nginx/error.log}"
TAIL_LINES="${TAIL_LINES:-5000}"

redact() {
  sed -E \
    -e 's/([?&]([[:alnum:]_-]*token|code|passwd)=)[^&[:space:]]+/\1***REDACTED***/g' \
    -e 's/(Authorization:[[:space:]]+)[A-Za-z]+[[:space:]]+[A-Za-z0-9._-]+/\1***REDACTED***/g'
}

summary_script='
set -euo pipefail
ACCESS_LOG="${ACCESS_LOG:-/var/log/nginx/access.log}"
ERROR_LOG="${ERROR_LOG:-/var/log/nginx/error.log}"
TAIL_LINES="${TAIL_LINES:-5000}"

echo "== nginx access status summary =="
if [ -r "$ACCESS_LOG" ]; then
  tail -n "$TAIL_LINES" "$ACCESS_LOG" \
    | sed -E "s/([?&]([[:alnum:]_-]*token|code|passwd)=)[^&[:space:]]+/\1***REDACTED***/g" \
    | sed -nE "s/.*\" ([0-9]{3}) .*/\1/p" \
    | sort \
    | uniq -c \
    | awk '"'"'{ print $2, $1 }'"'"'
else
  echo "access log unavailable: $ACCESS_LOG"
fi

echo
echo "== nginx 5xx samples =="
if [ -r "$ACCESS_LOG" ]; then
  tail -n "$TAIL_LINES" "$ACCESS_LOG" \
    | sed -E "s/([?&]([[:alnum:]_-]*token|code|passwd)=)[^&[:space:]]+/\1***REDACTED***/g" \
    | grep -E "\" 5[0-9][0-9] " \
    | tail -40 || true
fi

echo
echo "== nginx error summary =="
if [ -r "$ERROR_LOG" ]; then
  tail -n "$TAIL_LINES" "$ERROR_LOG" \
    | sed -E "s/([?&]([[:alnum:]_-]*token|code|passwd)=)[^&[:space:]]+/\1***REDACTED***/g" \
    | grep -E "error|crit|alert|emerg|502|504|upstream|timeout|SSL" || true
else
  echo "error log unavailable: $ERROR_LOG"
fi
'

if [ -n "${SERVER_HOST}" ]; then
  if [ -z "${SSH_KEY}" ]; then
    echo "ERROR: SSH_KEY is required when SERVER_HOST is set." >&2
    exit 1
  fi
  ssh -i "${SSH_KEY}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${SSH_USER}@${SERVER_HOST}" \
    "ACCESS_LOG='${ACCESS_LOG}' ERROR_LOG='${ERROR_LOG}' TAIL_LINES='${TAIL_LINES}' bash -s" <<<"${summary_script}" | redact
else
  ACCESS_LOG="${ACCESS_LOG}" ERROR_LOG="${ERROR_LOG}" TAIL_LINES="${TAIL_LINES}" bash -s <<<"${summary_script}" | redact
fi
