#!/usr/bin/env bash
# Build the player and GM skill zips in dist/ (see package-skills.py).
set -euo pipefail
py=python3
"$py" -c '' >/dev/null 2>&1 || py=python     # on Windows, python3 can be a stub that runs nothing
exec "$py" "$(dirname "$0")/package-skills.py" "$@"
