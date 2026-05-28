#!/usr/bin/env bash
set -euo pipefail

echo "[secrets-basic] scanning tracked text files..."

patterns='(AKIA[0-9A-Z]{16}|BEGIN PRIVATE KEY|sk-[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]+|ghp_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9_]{20,}|AIza[0-9A-Za-z_-]{35}|access_key_secret\s*=\s*[^#[:space:]]+|accessKeySecret\s*=\s*[^#[:space:]]+|secret_access_key\s*=\s*[^#[:space:]]+)'

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

git ls-files > "$tmp_file"

# Keep this basic and conservative. It is not a replacement for gitleaks/trufflehog.
if xargs -a "$tmp_file" rg -n --hidden --no-ignore-vcs "$patterns" 2>/dev/null; then
  echo "[secrets-basic] possible secret-like pattern found"
  exit 1
fi

echo "[secrets-basic] passed"
