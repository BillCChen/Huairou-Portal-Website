#!/usr/bin/env bash
set -euo pipefail

echo "[docker-compose-config] checking deploy/docker/docker-compose.yml..."

if ! command -v docker >/dev/null 2>&1; then
  echo "WARN: docker is not installed or not in PATH"
  exit 0
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "WARN: docker compose is not available"
  exit 0
fi

docker compose --env-file deploy/docker/.env.example -f deploy/docker/docker-compose.yml config >/tmp/portal_docker_compose_config.out

echo "[docker-compose-config] passed"
