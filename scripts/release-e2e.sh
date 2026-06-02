#!/usr/bin/env bash
#==============================================================================
# release-e2e.sh  —  konjugaton's equivalent of app7's e2e.sh
#
# Build + deploy FROM a public-safe clone, FROM SCRATCH, in an ephemeral folder,
# so the build is proven to work with nothing but the public tree + a .env.
# Never touches your working tree or the canonical public clone.
#
# Usage:
#   scripts/release-e2e.sh <public-folder> [feature] [--with-apk]
#
#   <public-folder>  a folder produced by convert-to-public.sh
#                    (default: newest ../public-konjugaton-* sibling)
#   feature          kebab label baked into the artifact name (default: latest)
#   --with-apk       also build + upload the Android release APK (needs ANDROID_HOME + JDK 17)
#
# Pipeline (mirrors app7's e2e.sh, minus the secret-injection app7 needs):
#   1. cp -R <public>/ <public>_e2e_<RUN_TS>/      (canonical clone stays clean)
#   2. seed .env from .env.template if absent       (konjugaton builds without one)
#   3. uv venv + uv pip install -e ".[dev,build]"   (from scratch, no reuse)
#   4. just deploy-leao <feature>                   (GATED by binary-smoke)
#   5. [--with-apk] just deploy-leao-apk <feature>
#   6. print the remote listing
#==============================================================================
set -euo pipefail

PUBLIC="${1:-}"
FEATURE="latest"
WITH_APK=0
shift || true
for a in "$@"; do
    case "$a" in
        --with-apk) WITH_APK=1 ;;
        *) FEATURE="$a" ;;
    esac
done

# Resolve the public folder (default: newest sibling public-konjugaton-*).
if [[ -z "$PUBLIC" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PARENT="$(dirname "$(cd "$SCRIPT_DIR/.." && pwd)")"
    PUBLIC="$(find "$PARENT" -maxdepth 1 -type d -name 'public-konjugaton-*' \
              ! -name '*_e2e_*' -printf '%T@ %p\n' | LC_ALL=C sort -nr | head -1 | cut -d' ' -f2-)"
    [[ -n "$PUBLIC" ]] || { echo "FATAL: no public-konjugaton-* folder; run convert-to-public.sh first" >&2; exit 1; }
fi
PUBLIC="$(cd "$PUBLIC" && pwd)"
[[ -f "$PUBLIC/.env.template" && -f "$PUBLIC/justfile" ]] \
    || { echo "FATAL: $PUBLIC is not a konjugaton public clone (no .env.template / justfile)" >&2; exit 2; }

command -v uv     >/dev/null || { echo "FATAL: uv not on PATH"     >&2; exit 3; }
command -v just   >/dev/null || { echo "FATAL: just not on PATH"   >&2; exit 3; }
command -v rclone >/dev/null || { echo "FATAL: rclone not on PATH" >&2; exit 3; }

RUN_TS="$(date +%Y%m%d_%H%M%S)"
E2E="${PUBLIC}_e2e_${RUN_TS}"
echo "═══ konjugaton release e2e ═══"
echo "  public source: $PUBLIC"
echo "  e2e clone:     $E2E"
echo "  feature:       $FEATURE   (artifact prefix: $RUN_TS)"
echo "  with apk:      $WITH_APK"

# 1. ephemeral clone
cp -R "$PUBLIC" "$E2E"
cd "$E2E"

# 2. seed .env (konjugaton needs none, but the pipeline keeps the app7 shape)
[[ -f .env ]] || cp .env.template .env

# 3. from-scratch toolchain
echo "── installing toolchain (uv venv + .[dev,build]) ──"
uv venv .venv
uv pip install --python .venv -e ".[dev,build]" patchelf

# 4. gated binary deploy (deploy-leao depends on binary-smoke)
echo "── build + deploy binary (gated) ──"
just deploy-leao "$FEATURE"

# 5. optional Android APK
if (( WITH_APK )); then
    echo "── build + deploy Android APK ──"
    just deploy-leao-apk "$FEATURE"
fi

# 6. report
REMOTE="$(just --evaluate leao_remote 2>/dev/null || echo 'ber:leao-bernardo/linguas/konjugaton/release')"
echo
echo "──────────────────────────────────────────────────────────────────"
echo "DONE — artifacts on ${REMOTE}/ (prefix ${RUN_TS}-${FEATURE}-…)"
rclone ls "$REMOTE" 2>/dev/null | grep -E "${RUN_TS}|${FEATURE}" || true
echo "──────────────────────────────────────────────────────────────────"
