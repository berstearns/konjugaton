# konjugaton — task runner.  Run `just` (or `just --list`) to see everything.
#
# The headline recipe is `just build`: it compiles a fully standalone native
# binary with Nuitka (Python → C), so end users run ./dist/konjugaton with no
# Python, no venv, no pip — just the file.

set shell := ["bash", "-uc"]

venv      := ".venv"
py        := venv / "bin" / "python"
konjugaton := py + " -m konjugaton"
bin       := "dist/konjugaton"

# Deploy target — the SAME rclone scheme as app7/app11/verbion ("leao"):
#   ber:leao-bernardo/<subpath>/release/   (app7 → manga-reading, app11 → paper-reading)
# konjugaton lives under the languages folder, beside verbion.  Override with: just leao_remote=… …
leao_remote := "ber:leao-bernardo/linguas/konjugaton/release"

# Show all recipes
default:
    @just --list --unsorted

# ─────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────

# Create the venv and install the project with dev extras (textual + nuitka + tools)
install:
    uv venv {{venv}}
    uv pip install --python {{venv}} -e ".[dev]"

# ─────────────────────────────────────────────────────────────────────────
# Quality gates (mirror CI)
# ─────────────────────────────────────────────────────────────────────────

# Lint with ruff
lint:
    {{venv}}/bin/ruff check .

# Auto-format with ruff
fmt:
    {{venv}}/bin/ruff format .

# Check formatting without writing
fmt-check:
    {{venv}}/bin/ruff format --check .

# Strict type check (basedpyright)
typecheck:
    {{venv}}/bin/basedpyright

# Run the test suite
test:
    {{py}} -m pytest

# Everything CI runs, in order
check: lint fmt-check typecheck test

# ─────────────────────────────────────────────────────────────────────────
# BUILD — the fully standalone native binary (Nuitka)
# ─────────────────────────────────────────────────────────────────────────

# Compile a single-file native binary → dist/konjugaton (no Python needed to run)
build:
    {{py}} -m nuitka \
      --onefile --standalone \
      --output-dir=dist --output-filename=konjugaton \
      --include-package=konjugaton \
      --include-package-data=konjugaton \
      --lto=no --jobs=$(nproc) \
      --assume-yes-for-downloads --remove-output \
      --company-name=konjugaton --product-name=konjugaton --file-version=0.1.0 \
      entrypoint.py
    @echo "→ built {{bin}}  ($(du -h {{bin}} | cut -f1))"

# Same, but bundle the Textual TUI into the binary as well (larger)
build-tui:
    {{py}} -m nuitka \
      --onefile --standalone \
      --output-dir=dist --output-filename=konjugaton \
      --include-package=konjugaton --include-package-data=konjugaton \
      --include-package=textual --include-package-data=textual \
      --lto=no --jobs=$(nproc) \
      --assume-yes-for-downloads --remove-output \
      entrypoint.py
    @echo "→ built {{bin}} (with TUI)"

# Build wheel + sdist (the pip/pipx/uv install path)
build-wheel:
    uv build
    @echo "→ wheel + sdist in dist/"

# Build, then self-check the binary in a CLEAN env (no Python) — the deploy gate
binary-smoke: build
    ./{{bin}} version
    env -i ./{{bin}} selfcheck
    env -i ./{{bin}} catalog | tail -3
    env -i ./{{bin}} practice --tense perfekt --no-interactive -n 3 --seed 1

# ─────────────────────────────────────────────────────────────────────────
# DEPLOY — upload artifacts to the leao remote (ber:), same scheme as app7
# For a real (public-safe, from-scratch) release, use scripts/release-e2e.sh —
# see RELEASE.md.  These recipes ship straight from the working tree.
# ─────────────────────────────────────────────────────────────────────────

# List what's currently on the leao remote
leao-list:
    rclone ls "{{leao_remote}}" 2>/dev/null || echo "  (empty / unreachable)"

# Gate the binary, then upload it to leao as <TS>-<feature>-linux
deploy-leao feature="latest": binary-smoke
    #!/usr/bin/env bash
    set -euo pipefail
    command -v rclone >/dev/null || { echo "rclone not installed"; exit 1; }
    TS=$(date +%Y%m%d_%H%M%S)
    NAME="${TS}-{{feature}}-linux"
    echo "→ {{bin}} ($(du -h {{bin}} | cut -f1))  →  {{leao_remote}}/${NAME}"
    rclone copyto "{{bin}}" "{{leao_remote}}/${NAME}" --progress
    echo "── remote now ──"
    rclone ls "{{leao_remote}}" | tail -6

# Build the Android release APK, then upload it to leao as <TS>-<feature>-release.apk
deploy-leao-apk feature="latest":
    #!/usr/bin/env bash
    set -euo pipefail
    command -v rclone >/dev/null || { echo "rclone not installed"; exit 1; }
    ( cd minimal-konjugaton-android && ./gradlew :app:assembleRelease )
    APK=$(find minimal-konjugaton-android/app/build/outputs/apk/release \
            -type f \( -name "*-release.apk" -o -name "*-release-unsigned.apk" \) | head -1)
    [[ -n "$APK" ]] || { echo "no release APK found"; exit 1; }
    TS=$(date +%Y%m%d_%H%M%S)
    NAME="${TS}-{{feature}}-release.apk"
    echo "→ ${APK} ($(du -h "$APK" | cut -f1))  →  {{leao_remote}}/${NAME}"
    rclone copyto "$APK" "{{leao_remote}}/${NAME}" --progress
    echo "── remote now ──"
    rclone ls "{{leao_remote}}" | tail -6

# Ship BOTH artifacts (Linux binary + Android APK) to leao in one go
deploy-leao-all feature="latest": (deploy-leao feature) (deploy-leao-apk feature)

# ─────────────────────────────────────────────────────────────────────────
# Usage
# ─────────────────────────────────────────────────────────────────────────

# Describe the combinatorial space and its size
catalog:
    {{konjugaton}} catalog

# List the verb inventory (optionally one class:  just verbs irregular)
verbs verb_class="":
    {{konjugaton}} verbs {{ if verb_class == "" { "" } else { "--class " + verb_class } }}

# Generic drill — pass any flags:  just drill --tense praeteritum --register du -n 5
drill *ARGS:
    {{konjugaton}} practice {{ARGS}}

# Mastery + IRT-ability report
report:
    {{konjugaton}} report

# Exhaustively validate engine + data over the whole space (every coordinate)
selfcheck:
    {{konjugaton}} selfcheck

# User settings:  just config show | just config preset gentle | just config set grading.ignore_accents true
config *ARGS:
    {{konjugaton}} config {{ARGS}}

# Launch the Textual TUI (needs the [tui] extra / `just build-tui`)
tui:
    {{konjugaton}} tui

# ─────────────────────────────────────────────────────────────────────────
# Combinatorial workflows
# ─────────────────────────────────────────────────────────────────────────

# One tense-mood across the space (sample):  just tense perfekt
tense TENSE n="6":
    {{konjugaton}} practice --tense {{TENSE}} --no-interactive -n {{n}} --order easy-first

# One register across the space:  just register du
register REGISTER n="6":
    {{konjugaton}} practice --register {{REGISTER}} --no-interactive -n {{n}}

# Negation drill — exercises nicht placement
negatives n="8":
    {{konjugaton}} practice --polarity negative --no-interactive -n {{n}}

# The werden-passive (transitive verbs)
passive n="8":
    {{konjugaton}} practice --voice passiv --no-interactive -n {{n}}

# The formal Sie register
formal n="8":
    {{konjugaton}} practice --register sie_formal --no-interactive -n {{n}}

# Strong-verb perfect — the haben/sein auxiliary split
perfekt n="8":
    {{konjugaton}} practice --tense perfekt --no-interactive -n {{n}}

# Multiple-choice only (no typing)
mcq n="8":
    {{konjugaton}} practice --only-mcq --no-interactive -n {{n}}

# SWEEP — sample every (tense × voice) cell: the full combinatorial tour
sweep n="2":
    #!/usr/bin/env bash
    set -euo pipefail
    for t in praesens praeteritum perfekt plusquamperfekt futur1 konjunktiv2 imperativ; do
      for v in aktiv passiv; do
        echo "═══ $t · $v ═══"
        {{konjugaton}} practice --tense "$t" --voice "$v" --no-interactive -n {{n}} \
          --order easy-first 2>/dev/null | grep -E '^[0-9]+\.|→' \
          || echo "  (no realizable items)"
      done
    done

# ─────────────────────────────────────────────────────────────────────────
# Housekeeping
# ─────────────────────────────────────────────────────────────────────────

# Remove build artifacts and caches
clean:
    rm -rf dist build ./*.egg-info .pytest_cache .ruff_cache
    find . -type d -name __pycache__ -prune -exec rm -rf {} +

# Wipe the saved learner state (XDG)
reset-state:
    rm -f "${XDG_STATE_HOME:-$HOME/.local/state}/konjugaton/state.json"
