#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="${ROOT_DIR}/performance/reports/runtime"
SERVER_HOST="${SERVER_HOST:-47.94.240.154}"
SSH_USER="${SSH_USER:-root}"
SSH_KEY="${SSH_KEY:-}"
SNAPSHOT_TS="$(date +%Y%m%d_%H%M%S)"
SNAPSHOT_PATH="${RUNTIME_DIR}/server-readonly-snapshot-${SNAPSHOT_TS}.log"

if [ -z "${SSH_KEY}" ]; then
  echo "ERROR: SSH_KEY is required. Example: SSH_KEY=/path/to/key ${0}" >&2
  exit 1
fi

mkdir -p "${RUNTIME_DIR}"

redact() {
  sed -E \
    -e 's/(PASSWORD|SECRET|TOKEN|KEY|password|secret|token|key)=([^[:space:]]+)/\1=***REDACTED***/g' \
    -e 's/([[:alnum:]_-]*token)([\"=: ]+)[^\", ]+/\1\2***REDACTED***/g' \
    -e 's/(Authorization:[[:space:]]+)[A-Za-z]+[[:space:]]+[A-Za-z0-9._-]+/\1***REDACTED***/g' \
    -e 's/([0-9]{1,3}\.){3}[0-9]{1,3}/***IP***/g'
}

ssh -i "${SSH_KEY}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${SSH_USER}@${SERVER_HOST}" 'bash -s' <<'REMOTE' | redact | tee "${SNAPSHOT_PATH}"
set -euo pipefail

redact_remote() {
  sed -E \
    -e 's/(PASSWORD|SECRET|TOKEN|KEY|password|secret|token|key)=([^[:space:]]+)/\1=***REDACTED***/g' \
    -e 's/([[:alnum:]_-]*token)([\"=: ]+)[^\", ]+/\1\2***REDACTED***/g' \
    -e 's/([?&]([[:alnum:]_-]*token|code|passwd)=)[^&[:space:]]+/\1***REDACTED***/g' \
    -e 's/([0-9]{1,3}\.){3}[0-9]{1,3}/***IP***/g'
}

echo "== basic =="
hostname
date
uptime
df -h | sed -n '1,80p'
free -h

echo
echo "== docker containers =="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

echo
echo "== docker stats =="
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}'

echo
echo "== nginx =="
nginx -t
systemctl is-active nginx || true
ls -lah /etc/nginx/sites-enabled

echo
echo "== Portal compose =="
cd /opt/huairou/portal/repo/deploy/docker
sudo -u deploy docker compose -p portal-prod --env-file .env.production -f docker-compose.prod.yml ps

echo
echo "== Portal ClamAV compose =="
sudo -u deploy docker compose -p portal-clamav -f compose.clamav.local.yml ps || true

echo
echo "== Achievement compose =="
cd /opt/huairou/achievement/repo
sudo -u deploy docker compose -p achievement-prod --env-file deploy/docker/.env.production -f deploy/docker/compose.production.yml ps

echo
echo "== HTTPS smoke =="
curl -sS -I --max-time 15 https://huairou.tech/ | sed -n '1,40p'
curl -sS -o /dev/null -w "Portal public home API status: %{http_code}\n" --max-time 15 https://huairou.tech/api/v1/public/home
curl -sS -I --max-time 15 https://portal-admin.huairou.tech/ | sed -n '1,40p'
curl -sS -I --max-time 15 https://cg.huairou.tech/ | sed -n '1,40p'
curl -sS -o /dev/null -w "Achievement health API status: %{http_code}\n" --max-time 15 https://cg.huairou.tech/api/v1/health

echo
echo "== PostgreSQL connection count, safe best effort =="
cd /opt/huairou/portal/repo/deploy/docker
printf "Portal postgres active connections: "
sudo -u deploy docker compose -p portal-prod --env-file .env.production -f docker-compose.prod.yml exec -T postgres \
  sh -lc 'psql -U portal -d portal -Atc "select count(*) from pg_stat_activity;"' </dev/null 2>/dev/null || echo "Portal postgres count unavailable without secret"
cd /opt/huairou/achievement/repo
printf "Achievement postgres active connections: "
sudo -u deploy docker compose -p achievement-prod --env-file deploy/docker/.env.production -f deploy/docker/compose.production.yml exec -T postgres \
  sh -lc 'psql -U "${POSTGRES_USER:-achievement}" -d "${POSTGRES_DB:-achievement}" -Atc "select count(*) from pg_stat_activity;"' </dev/null 2>/dev/null || echo "Achievement postgres count unavailable without secret"

echo
echo "== Nginx recent errors =="
tail -120 /var/log/nginx/error.log 2>/dev/null | redact_remote || true

echo
echo "== Portal API recent warning/error scan =="
cd /opt/huairou/portal/repo/deploy/docker
sudo -u deploy docker compose -p portal-prod --env-file .env.production -f docker-compose.prod.yml logs --tail=220 api \
  | redact_remote \
  | grep -En "ERROR|Error|Traceback|Exception|missing column|migration|500|502|503|504|SECRET|PASSWORD|TOKEN|credential" || true

echo
echo "== Achievement backend recent warning/error scan =="
cd /opt/huairou/achievement/repo
sudo -u deploy docker compose -p achievement-prod --env-file deploy/docker/.env.production -f deploy/docker/compose.production.yml logs --tail=220 backend \
  | redact_remote \
  | grep -En "ERROR|Error|Traceback|Exception|missing column|migration|500|502|503|504|SECRET|PASSWORD|TOKEN|credential" || true
REMOTE

echo "Snapshot saved to ${SNAPSHOT_PATH}"
