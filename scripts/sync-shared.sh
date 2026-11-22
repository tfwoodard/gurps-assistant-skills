#!/usr/bin/env bash
# Copy shared/ into each skill (see sync_shared.py). --check fails on drift.
set -euo pipefail
py=python3
"$py" -c '' >/dev/null 2>&1 || py=python     # on Windows, python3 can be a stub that runs nothing
exec "$py" "$(dirname "$0")/sync_shared.py" "$@"
