#!/usr/bin/env bash
# Track RAM while building the Nuitka standalone binary (dist/konjugaton).
# Run from any directory; paths are resolved relative to this script.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

exec python3 "$SCRIPT_DIR/track.py" "$@" \
    -- bash -c "cd '$PROJECT_DIR' && just build"
