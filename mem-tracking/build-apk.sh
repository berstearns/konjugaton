#!/usr/bin/env bash
# Track RAM while building the Android release APK.
# Run from any directory; paths are resolved relative to this script.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANDROID_DIR="$(cd "$SCRIPT_DIR/../minimal-konjugaton-android" && pwd)"

exec python3 "$SCRIPT_DIR/track.py" "$@" \
    -- bash -c "cd '$ANDROID_DIR' && ./gradlew :app:assembleRelease"
