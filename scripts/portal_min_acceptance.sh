#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== Portal minimal acceptance =="

echo
echo "== Git status =="
git status --short

if [ -n "$(git status --short)" ]; then
  echo "ERROR: working tree is not clean before acceptance checks."
  echo "Run checks from a clean baseline, or commit intended script/doc changes first."
  exit 1
fi

echo
echo "== Forbidden artifacts =="
./scripts/check_forbidden_artifacts.sh

echo
echo "== Basic secret scan =="
./scripts/check_secrets_basic.sh

echo
echo "== API route map extraction =="
python3 scripts/extract_api_routes.py

echo
echo "== Frontend/admin command availability =="
if command -v pnpm >/dev/null 2>&1; then
  pnpm --version
else
  echo "WARN: pnpm is not installed or not in PATH"
fi

echo
echo "== Docker compose config =="
./scripts/check_docker_compose_config.sh

echo
echo "== Python availability =="
python3 --version

echo
echo "== Minimal acceptance completed =="
