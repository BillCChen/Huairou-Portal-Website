#!/usr/bin/env bash
set -euo pipefail

echo "[forbidden-artifacts] checking tracked files..."

forbidden_patterns=(
  '^\.runtime-logs/'
  '^outputs/'
  '^\.claude/settings\.local\.json$'
  '(^|/)\.env$'
  '(^|/)\.env\.local$'
  '(^|/)\.env\.production$'
  '(^|/)\.env\.development$'
  '\.db$'
  '\.sqlite$'
  '\.sqlite3$'
  '^uploads/'
  '^data/'
  '^\.nuxt/'
  '^\.output/'
  '^dist/'
  '^node_modules/'
)

tracked_files="$(git ls-files)"

failed=0
for pattern in "${forbidden_patterns[@]}"; do
  if echo "$tracked_files" | grep -E "$pattern" >/dev/null; then
    echo "ERROR: tracked forbidden artifact pattern matched: $pattern"
    echo "$tracked_files" | grep -E "$pattern" || true
    failed=1
  fi
done

if [ "$failed" -ne 0 ]; then
  echo "[forbidden-artifacts] failed"
  exit 1
fi

echo "[forbidden-artifacts] passed"
