#!/usr/bin/env bash
# Install the sample pre-commit hook into .git/hooks
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK_SRC="$REPO_ROOT/.githooks/pre-commit"
HOOK_DST="$REPO_ROOT/.git/hooks/pre-commit"
if [ ! -f "$HOOK_SRC" ]; then
  echo "Hook source not found: $HOOK_SRC"
  exit 1
fi
cp "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_DST"
echo "Installed pre-commit hook to $HOOK_DST"
