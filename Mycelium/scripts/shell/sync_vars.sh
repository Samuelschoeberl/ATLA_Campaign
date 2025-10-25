#!/bin/bash
# Wrapper script to sync character sheets to variable files
# Usage: ./sync_vars.sh [options]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

cd "$PROJECT_ROOT"
python3 Mycelium/scripts/Python/sync_variables.py "$@"
