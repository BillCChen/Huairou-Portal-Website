#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUNTIME_DIR_INPUT="${PORTAL_SMTP_CONFIG_SMOKE_RUNTIME_DIR:-.runtime-logs/password-reset-smtp-config-smoke}"
PYTHON_OVERRIDE="${PORTAL_BACKEND_PYTHON:-}"

case "$RUNTIME_DIR_INPUT" in
  /*) RUNTIME_DIR="$RUNTIME_DIR_INPUT" ;;
  *) RUNTIME_DIR="${ROOT_DIR}/${RUNTIME_DIR_INPUT}" ;;
esac

log() {
  echo "[smtp-config-smoke] $*"
}

fail() {
  echo "[smtp-config-smoke] ERROR: $*" >&2
  exit 1
}

python_minor() {
  local python_bin="$1"
  "${python_bin}" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
}

candidate_list() {
  if [ -n "${PYTHON_OVERRIDE}" ]; then
    echo "${PYTHON_OVERRIDE}"
    return 0
  fi
  printf '%s\n' python3.13 python3.12 python3.11
}

VENV_DIR=""
prepare_venv() {
  local python_bin="$1"
  local python_mm

  if ! command -v "${python_bin}" >/dev/null 2>&1; then
    log "skipping ${python_bin}: not found"
    return 1
  fi

  python_mm="$(python_minor "${python_bin}")"
  case "${python_mm}" in
    3.11|3.12|3.13) ;;
    *)
      log "skipping ${python_bin}: unsupported Python ${python_mm}"
      return 1
      ;;
  esac

  VENV_DIR="${RUNTIME_DIR}/backend-venv-py${python_mm//./}"
  mkdir -p "${RUNTIME_DIR}"

  if [ ! -x "${VENV_DIR}/bin/python" ]; then
    log "creating venv at ${VENV_DIR}"
    "${python_bin}" -m venv "${VENV_DIR}" || return 1
  fi

  log "installing backend requirements"
  "${VENV_DIR}/bin/python" -m pip install --upgrade pip >/dev/null
  "${VENV_DIR}/bin/python" -m pip install -r apps/api-server/requirements.txt >/dev/null
  return 0
}

selected_python=""
for candidate in $(candidate_list); do
  if prepare_venv "${candidate}"; then
    selected_python="${candidate}"
    break
  fi
  if [ -n "${PYTHON_OVERRIDE}" ]; then
    fail "PORTAL_BACKEND_PYTHON=${PYTHON_OVERRIDE} failed"
  fi
done

if [ -z "${selected_python}" ]; then
  fail "no compatible Python interpreter could create a backend venv and install requirements"
fi

SMTP_DB_PATH="${RUNTIME_DIR}/portal_smtp_config_smoke.sqlite3"
DISABLED_DB_PATH="${RUNTIME_DIR}/portal_smtp_disabled_smoke.sqlite3"
OUTBOX_DIR="${RUNTIME_DIR}/mail_outbox"
rm -f "${SMTP_DB_PATH}" "${DISABLED_DB_PATH}"
rm -rf "${OUTBOX_DIR}"
mkdir -p "${OUTBOX_DIR}"

log "checking disabled provider remains closed"
(
  cd apps/api-server
  exec env \
    DATABASE_URL="sqlite:///${DISABLED_DB_PATH}" \
    EMAIL_PROVIDER="disabled" \
    PASSWORD_RESET_DEV_OUTBOX_DIR="${OUTBOX_DIR}" \
    INIT_SAMPLE_DATA="true" \
    "${VENV_DIR}/bin/python" - <<'PY'
from app.db.seed import seed_database
from app.db.session import Base, SessionLocal, engine
from app.services.password_reset import PASSWORD_RESET_SAFE_MESSAGE, create_password_reset_request
from app.db.models import PasswordResetToken
from sqlalchemy import select

Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed_database(db)
    result = create_password_reset_request(
        db,
        email_or_username="partner.user",
        request_ip="127.0.0.1",
        user_agent="smtp-config-smoke",
    )
    assert result["message"] == PASSWORD_RESET_SAFE_MESSAGE
    item = db.scalar(select(PasswordResetToken).order_by(PasswordResetToken.id.desc()).limit(1))
    assert item is not None
    assert item.consumed_at is not None
PY
)

log "checking smtp provider fails closed without credentials"
(
  cd apps/api-server
  exec env \
    DATABASE_URL="sqlite:///${SMTP_DB_PATH}" \
    EMAIL_PROVIDER="smtp" \
    SMTP_HOST="smtp.example.invalid" \
    SMTP_PORT="465" \
    SMTP_FROM_EMAIL="no-reply@example.invalid" \
    SMTP_FROM_NAME="Portal Website" \
    SMTP_USE_TLS="true" \
    SMTP_USE_STARTTLS="false" \
    SMTP_REQUIRE_AUTH="true" \
    SMTP_TIMEOUT_SECONDS="1" \
    PASSWORD_RESET_DEV_OUTBOX_DIR="${OUTBOX_DIR}" \
    PUBLIC_FRONTEND_BASE_URL="https://portal.example.invalid" \
    INIT_SAMPLE_DATA="true" \
    "${VENV_DIR}/bin/python" - <<'PY'
from pathlib import Path
import os

from app.db.seed import seed_database
from app.db.session import Base, SessionLocal, engine
from app.services.password_reset import (
    PASSWORD_RESET_SAFE_MESSAGE,
    create_password_reset_request,
    email_delivery_configuration_issues,
)
from app.db.models import AuditLog, PasswordResetToken
from sqlalchemy import select

Base.metadata.create_all(bind=engine)
issues = email_delivery_configuration_issues(include_disabled=True)
assert "SMTP_AUTH_CREDENTIALS_REQUIRED" in issues, issues

with SessionLocal() as db:
    seed_database(db)
    result = create_password_reset_request(
        db,
        email_or_username="partner.user",
        request_ip="127.0.0.1",
        user_agent="smtp-config-smoke",
    )
    assert result["message"] == PASSWORD_RESET_SAFE_MESSAGE
    item = db.scalar(select(PasswordResetToken).order_by(PasswordResetToken.id.desc()).limit(1))
    assert item is not None
    assert item.consumed_at is not None
    audits = db.scalars(select(AuditLog).where(AuditLog.module == "auth")).all()
    combined = " ".join(str(audit.detail_json or {}) for audit in audits)
    assert "token=" not in combined

outbox = Path(os.environ["PASSWORD_RESET_DEV_OUTBOX_DIR"])
assert not list(outbox.glob("*.txt"))
PY
)

log "smtp provider configuration smoke passed"
