#!/usr/bin/env bash
set -euo pipefail

COMMIT_MSG_FILE="${1:-}"

staged_files=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$staged_files" ]; then
  echo "No staged files detected."
  exit 0
fi

echo "Running lint checks for staged files..."
while IFS= read -r file; do
  case "$file" in
    *.js|*.cjs|*.mjs|*.ts|*.tsx|*.json|*.md|*.yml|*.yaml)
      npx --yes prettier --check "$file"
      ;;
    *.py)
      python -m py_compile "$file"
      ;;
  esac
done <<< "$staged_files"

echo "Scanning staged changes for potential secrets..."
if git diff --cached | rg -n --pcre2 '(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["\x27]?[A-Za-z0-9_\-]{16,}' >/dev/null; then
  echo "Potential secret detected in staged changes."
  exit 1
fi

if [ -z "$COMMIT_MSG_FILE" ] && [ -f .git/COMMIT_EDITMSG ]; then
  COMMIT_MSG_FILE=.git/COMMIT_EDITMSG
fi

if [ -n "$COMMIT_MSG_FILE" ] && [ -f "$COMMIT_MSG_FILE" ]; then
  message=$(head -n 1 "$COMMIT_MSG_FILE" | tr -d '\r')
  if ! [[ "$message" =~ ^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._/-]+\))?(!)?:\ .+ ]]; then
    echo "Commit message must follow conventional commits format."
    exit 1
  fi
fi

echo "Pre-commit checks passed."
