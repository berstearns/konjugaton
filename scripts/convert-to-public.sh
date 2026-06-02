#!/usr/bin/env bash
#==============================================================================
# convert-to-public.sh  —  konjugaton's equivalent of app7's convert-dev-to-public.sh
#
# Produce a PUBLIC-SAFE clone of the konjugaton working tree in a sibling folder:
# no secrets, no caches, no runtime state, no .venv — ready to push to a public
# remote or hand to anyone. Then `release-e2e.sh` builds + deploys FROM that
# clean clone, from scratch.
#
# Usage:
#   scripts/convert-to-public.sh [dest-folder]
#
#   dest-folder   where to write the clone. Default: ../public-konjugaton-<TS>/
#                 (sibling of the repo, like app7's public-<dev>/).
#
# THE DIFFERENCE FROM app7:
#   app7 dev folders interleave REAL secrets (.env, JKS keystores,
#   server-config.yaml) that MUST be stripped. konjugaton currently has NONE —
#   it is already public-safe. So this script's job is inverted:
#     1. ASSERT no secret ever leaks (a scan gate — exit 5 if it finds one).
#     2. Export a clean tree (drop .venv/.git/dist/build/caches/runtime state).
#     3. Scaffold .env.template + PUBLIC.md + a fresh git repo.
#   The secret-STRIPPING steps below are CONDITIONAL: they fire only if/when
#   konjugaton grows the thing (an Android release keystore, a backend URL, …),
#   exactly like app7's `skip (not present)` branches. Nothing is invented.
#
# Hard guarantee: the SOURCE working tree is NEVER modified. An mtime manifest
# is captured up front and re-checked after every step; any drift aborts (99).
# Idempotency: refuses to overwrite an existing destination (exit 4).
#==============================================================================
set -euo pipefail

# ── STEP 1 — resolve paths ───────────────────────────────────────────────────
echo; echo "═══ STEP 1: resolve paths ═══"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "$SCRIPT_DIR/.." && pwd)"                 # repo root
TS="$(date +%Y%m%d_%H%M%S)"
DEST="${1:-$(dirname "$SRC")/public-konjugaton-$TS}"

if [[ -e "$DEST" ]]; then
    echo "FATAL: destination already exists: $DEST" >&2
    echo "       delete it manually if you want to redo." >&2
    exit 4
fi
echo "  source (read-only): $SRC"
echo "  destination:        $DEST"

# ── STEP 2 — snapshot source mtime manifest (tamper detection) ───────────────
echo; echo "═══ STEP 2: snapshot source mtime manifest ═══"
SRC_BEFORE="$(mktemp -t konjugaton-pub-before.XXXXXX)"
# Exclude volatile dirs from the manifest so editor/test churn there is ignored.
find "$SRC" -type f \
    -not -path '*/.git/*' -not -path '*/.venv/*' -not -path '*/build/*' \
    -not -path '*/dist/*' -not -path '*/__pycache__/*' \
    -not -path '*/.gradle/*' -not -path '*/.kotlin/*' \
    -not -path '*/.ruff_cache/*' -not -path '*/.pytest_cache/*' \
    -printf '%T@ %p\n' | LC_ALL=C sort > "$SRC_BEFORE"
echo "  manifest: $SRC_BEFORE  ($(wc -l < "$SRC_BEFORE") files)"

assert_source_untouched() {
    local label="$1" now
    now="$(mktemp -t konjugaton-pub-now.XXXXXX)"
    find "$SRC" -type f \
        -not -path '*/.git/*' -not -path '*/.venv/*' -not -path '*/build/*' \
        -not -path '*/dist/*' -not -path '*/__pycache__/*' \
        -not -path '*/.gradle/*' -not -path '*/.kotlin/*' \
        -not -path '*/.ruff_cache/*' -not -path '*/.pytest_cache/*' \
        -printf '%T@ %p\n' | LC_ALL=C sort > "$now"
    if ! diff -q "$SRC_BEFORE" "$now" >/dev/null; then
        echo "FATAL: source modified during $label" >&2
        diff "$SRC_BEFORE" "$now" | head -40 >&2
        exit 99
    fi
    rm -f "$now"
}

# ── STEP 3 — SECRET-SCAN GATE (the "fully safe, no keys" guarantee) ──────────
echo; echo "═══ STEP 3: secret-scan gate ═══"
violations=0
scan() { find "$SRC" \
    -not -path '*/.git/*' -not -path '*/.venv/*' -not -path '*/build/*' \
    -not -path '*/dist/*' -not -path '*/.gradle/*' -not -path '*/.kotlin/*' \
    "$@"; }

# (a) a real .env (the template is allowed)
while IFS= read -r f; do
    [[ "$(basename "$f")" == ".env.template" ]] && continue
    echo "  ✗ secret file present: $f"; violations=$((violations+1))
done < <(scan -type f -name '.env' -o -type f -name '.env.*' ! -name '.env.template')

# (b) binary keystores / private keys
while IFS= read -r f; do
    echo "  ✗ key material present: $f"; violations=$((violations+1))
done < <(scan -type f \( -name '*.keystore' -o -name '*.jks' -o -name '*.p12' \
                          -o -name '*.pem' -o -name 'id_rsa' -o -name '*.key' \) ! -name '*.keystore.real')

# (c) inline private-key blocks. The class [A-Z ]* (not .*) matches real PEM
#     headers (RSA/EC/OPENSSH/empty) without matching this pattern's own text.
while IFS= read -r f; do
    echo "  ✗ inline PRIVATE KEY block: $f"; violations=$((violations+1))
done < <(scan -type f -exec grep -lIE -- '-----BEGIN [A-Z ]*PRIVATE KEY-----' {} + 2>/dev/null || true)

if (( violations > 0 )); then
    echo "FATAL: $violations secret(s) would leak into the public clone. Aborting (exit 5)." >&2
    echo "       Move them out of the tree (or .gitignore + delete from working dir) and re-run." >&2
    rm -f "$SRC_BEFORE"; exit 5
fi
echo "  ✅ no secrets found — konjugaton is public-safe as-is"
assert_source_untouched "secret scan"

# ── STEP 4 — clean export (rsync, dropping volatile + private paths) ─────────
echo; echo "═══ STEP 4: clean export → $DEST ═══"
rsync -a \
    --exclude='.git/' --exclude='.venv/' --exclude='venv/' \
    --exclude='build/' --exclude='dist/' \
    --exclude='__pycache__/' --exclude='*.py[cod]' --exclude='*.egg-info/' \
    --exclude='.gradle/' --exclude='.kotlin/' \
    --exclude='.ruff_cache/' --exclude='.pytest_cache/' --exclude='.coverage' \
    --exclude='.env' --exclude='.konjugaton/' --exclude='*.konjugaton-state.json' \
    "$SRC/" "$DEST/"
assert_source_untouched "rsync"
echo "  exported $(find "$DEST" -type f | wc -l) files"

# ── STEP 5 — .env.template (konjugaton's optional knobs + forward-looking keys) ──
echo; echo "═══ STEP 5: install .env.template ═══"
cat > "$DEST/.env.template" <<'EOF'
# konjugaton — environment template.  `cp .env.template .env` and edit as needed.
#
# konjugaton needs NO secrets to build or run; every key below is OPTIONAL.
# This file exists so the deploy pipeline has one documented place for config,
# and so future secrets have an obvious, gitignored home (never commit .env).

# ── Runtime / profile location (path overrides, not secrets) ──
# KONJUGATON_HOME=~/konjugaton       # profile root (config.yaml, state.json, events.*)
# KONJUGATON_USER=me                # default --user when unset
# XDG_STATE_HOME=~/.local/state    # where the CLI keeps state.json

# ── Deploy (leao remote) ──
# LEAO_REMOTE=ber:leao-bernardo/linguas/konjugaton/release   # rclone target; mirrors justfile

# ── Android signed release (FORWARD-LOOKING — none of this exists yet) ──
# The app currently ships debug-signed/minified APKs with NO signingConfig.
# When you add real release signing, fill these and generate the keystore at
# the declared path (keep the .keystore itself OUT of git — see .gitignore):
# ANDROID_RELEASE_KEYSTORE_PATH=./release-konjugaton.keystore
# ANDROID_RELEASE_STORE_PASSWORD=
# ANDROID_RELEASE_KEY_ALIAS=konjugaton
# ANDROID_RELEASE_KEY_PASSWORD=
EOF
rm -f "$DEST/.env"
echo "  $DEST/.env.template ($(wc -l < "$DEST/.env.template") lines)"
assert_source_untouched ".env.template"

# ── STEP 6 — ensure public .gitignore covers secrets ─────────────────────────
echo; echo "═══ STEP 6: harden .gitignore ═══"
# konjugaton's .gitignore is already clean; append the secret patterns idempotently.
for pat in '.env' '*.keystore' '*.keystore.real' '*.jks' '*.p12' '*.pem'; do
    grep -qxF "$pat" "$DEST/.gitignore" 2>/dev/null || echo "$pat" >> "$DEST/.gitignore"
done
echo "  $DEST/.gitignore hardened"
assert_source_untouched ".gitignore"

# ── STEP 7 — (CONDITIONAL) strip Android release signing, if it ever exists ──
echo; echo "═══ STEP 7: Android signing (conditional) ═══"
GRADLE="$DEST/minimal-konjugaton-android/app/build.gradle.kts"
if [[ -f "$GRADLE" ]] && grep -q 'signingConfigs' "$GRADLE"; then
    python3 - "$GRADLE" <<'PY'
import re, sys
p = sys.argv[1]; s = open(p).read()
# Rewrite any hardcoded passwords to env-var-with-PLACEHOLDER, app7-style.
block = '''    signingConfigs {
        create("release") {
            storeFile = file(System.getenv("ANDROID_RELEASE_KEYSTORE_PATH") ?: "release-konjugaton.keystore")
            storePassword = System.getenv("ANDROID_RELEASE_STORE_PASSWORD") ?: "PLACEHOLDER"
            keyAlias = System.getenv("ANDROID_RELEASE_KEY_ALIAS") ?: "konjugaton"
            keyPassword = System.getenv("ANDROID_RELEASE_KEY_PASSWORD") ?: "PLACEHOLDER"
        }
    }
'''
s = re.sub(r'    signingConfigs \{.*?\n    \}\n', block, s, count=1, flags=re.S)
open(p,"w").write(s)
print("  patched signingConfigs → env vars + PLACEHOLDER")
PY
else
    echo "  skip (not present): no signingConfigs in Android build — nothing to strip"
fi
assert_source_untouched "android signing"

# ── STEP 8 — PUBLIC.md (konjugaton's equivalent of app7's STRATEGY.md) ─────────
echo; echo "═══ STEP 8: install PUBLIC.md ═══"
cat > "$DEST/PUBLIC.md" <<EOF
# Public clone of konjugaton

Generated $TS by \`scripts/convert-to-public.sh\` from the private working tree.

- **No secrets.** A scan gate refused to run if any \`.env\`/keystore/private key
  was present. \`.env.template\` documents the (currently all-optional) knobs.
- **Clean export.** No \`.venv/\`, \`.git/\` (a fresh one was initialised here),
  \`dist/\`, \`build/\`, caches, or runtime state.
- **Build it from scratch:**

      cp .env.template .env        # optional — konjugaton builds without it
      uv venv && uv pip install -e ".[dev,build]"
      just binary-smoke            # clean-env self-check
      ./dist/konjugaton practice -n 5

See \`RELEASE.md\` in the upstream repo for the full convert → e2e → deploy runbook.
EOF
echo "  $DEST/PUBLIC.md"
assert_source_untouched "PUBLIC.md"

# ── STEP 9 — fresh git repo ──────────────────────────────────────────────────
echo; echo "═══ STEP 9: git init + initial commit ═══"
( cd "$DEST"
  git init -q
  git add .
  git -c user.name="convert-to-public" -c user.email="local@local" \
      commit -q -m "Initial public clone of konjugaton ($TS)"
  git log --oneline -1 )
assert_source_untouched "git init"

# ── STEP 10 — final check + banner ───────────────────────────────────────────
echo; echo "═══ STEP 10: final source-untouched check ═══"
assert_source_untouched "final"
echo "  ✅ source $SRC unchanged"
rm -f "$SRC_BEFORE"
cat <<EOF

──────────────────────────────────────────────────────────────────
DONE: $DEST
next:
  scripts/release-e2e.sh "$DEST" <feature>   # build + deploy FROM this clone
or build by hand:
  cd "$DEST" && uv venv && uv pip install -e ".[dev,build]" && just binary-smoke
──────────────────────────────────────────────────────────────────
EOF
