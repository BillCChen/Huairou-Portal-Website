#!/usr/bin/env bash
set -euo pipefail

SERVER_HOST="${SERVER_HOST:-}"
SSH_USER="${SSH_USER:-root}"
SSH_KEY="${SSH_KEY:-}"

stats_script='
set -euo pipefail
echo "== docker ps =="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo
echo "== docker stats =="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
echo
echo "== host resources =="
uptime
free -h
df -h | sed -n "1,80p"
'

if [ -n "${SERVER_HOST}" ]; then
  if [ -z "${SSH_KEY}" ]; then
    echo "ERROR: SSH_KEY is required when SERVER_HOST is set." >&2
    exit 1
  fi
  ssh -i "${SSH_KEY}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${SSH_USER}@${SERVER_HOST}" "bash -s" <<<"${stats_script}"
else
  bash -s <<<"${stats_script}"
fi
