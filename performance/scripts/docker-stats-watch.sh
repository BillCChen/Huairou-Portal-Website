#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="${ROOT_DIR}/performance/reports/runtime"
SERVER_HOST="${SERVER_HOST:-}"
SSH_USER="${SSH_USER:-root}"
SSH_KEY="${SSH_KEY:-}"
DURATION_SECONDS="${DURATION_SECONDS:-600}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-5}"
OUTPUT_FILE="${OUTPUT_FILE:-${RUNTIME_DIR}/docker-stats-watch-$(date +%Y%m%d_%H%M%S).log}"

if [ -z "${SERVER_HOST}" ]; then
  echo "ERROR: SERVER_HOST is required." >&2
  exit 1
fi

if [ -z "${SSH_KEY}" ]; then
  echo "ERROR: SSH_KEY is required." >&2
  exit 1
fi

mkdir -p "$(dirname "${OUTPUT_FILE}")"

redact() {
  sed -E \
    -e 's/(PASSWORD|SECRET|TOKEN|KEY|password|secret|token|key)=([^[:space:]]+)/\1=***REDACTED***/g' \
    -e 's/([[:alnum:]_-]*token)([\"=: ]+)[^\", ]+/\1\2***REDACTED***/g'
}

ssh -i "${SSH_KEY}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${SSH_USER}@${SERVER_HOST}" \
  "DURATION_SECONDS='${DURATION_SECONDS}' INTERVAL_SECONDS='${INTERVAL_SECONDS}' bash -s" <<'REMOTE' | redact > "${OUTPUT_FILE}"
set -euo pipefail

end_time=$((SECONDS + DURATION_SECONDS))

while [ "${SECONDS}" -le "${end_time}" ]; do
  echo "== sample $(date -Is) =="
  uptime
  free -h | sed -n '1,3p'
  docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}'
  echo
  sleep "${INTERVAL_SECONDS}"
done
REMOTE

echo "Docker stats watch saved to ${OUTPUT_FILE}"
