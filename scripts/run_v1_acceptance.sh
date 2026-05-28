#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_PYTHON="${PORTAL_BACKEND_PYTHON:-python3.11}"
STATUS_FILE="$(mktemp)"
trap 'rm -f "$STATUS_FILE"' EXIT

run_step() {
  local name="$1"
  shift
  echo
  echo "== ${name} =="
  "$@"
}

run_minimal_acceptance() {
  echo
  echo "== minimal acceptance =="
  git status --short > "$STATUS_FILE"
  if [ ! -s "$STATUS_FILE" ]; then
    ./scripts/portal_min_acceptance.sh
    return 0
  fi

  echo "working tree is not clean; running minimal acceptance component checks for pre-commit validation"
  cat "$STATUS_FILE"
  ./scripts/check_forbidden_artifacts.sh
  ./scripts/check_secrets_basic.sh
  python3 scripts/extract_api_routes.py
  ./scripts/check_docker_compose_config.sh
  python3 --version
}

echo "== Portal V1 acceptance =="
echo "backend python: ${BACKEND_PYTHON}"

run_minimal_acceptance
run_step "web typecheck" pnpm check:web
run_step "web build" pnpm build:web
run_step "admin typecheck" pnpm check:admin
run_step "admin build" pnpm build:admin
run_step "backend compileall" env BACKEND_PYTHON="${BACKEND_PYTHON}" bash -lc 'cd apps/api-server && "${BACKEND_PYTHON}" -m compileall app'
run_step "public API smoke" env PORTAL_BACKEND_PYTHON="${BACKEND_PYTHON}" ./scripts/run_local_public_api_smoke.sh
run_step "password reset backend smoke" env PORTAL_BACKEND_PYTHON="${BACKEND_PYTHON}" ./scripts/smoke_password_reset_backend.sh
run_step "user lifecycle smoke" env PORTAL_BACKEND_PYTHON="${BACKEND_PYTHON}" ./scripts/smoke_user_lifecycle_backend.sh
run_step "auth permission smoke" env PORTAL_BACKEND_PYTHON="${BACKEND_PYTHON}" ./scripts/smoke_auth_permission_backend.sh
run_step "V1 content smoke" env PORTAL_BACKEND_PYTHON="${BACKEND_PYTHON}" ./scripts/smoke_v1_content_backend.sh
run_step "diff check" git diff --check
run_step "forbidden artifacts" ./scripts/check_forbidden_artifacts.sh
run_step "basic secret scan" ./scripts/check_secrets_basic.sh

echo
echo "== Portal V1 acceptance completed =="
