#!/usr/bin/env bash
#===============================================================================
# sync-ideas.sh — pull the (non-git) planning docs into this repo's docs/ so
# they travel through git to every clone (e.g. the cros-penguin executor).
#
# The planning docs are authored OUTSIDE any repo, under:
#   $DOCS_SRC/general/general-ideas.md     ← overall, cross-app ideas
#   $DOCS_SRC/<app>/ideas.md               ← this app's specific ideas
#
# This script makes a NAKED COPY (verbatim, no transformation) of both into the
# repo's flat docs/ as:
#   docs/ideas-general.md                  ← overall app ideas
#   docs/ideas-<app>.md                    ← this app's specific ideas
#
# So the flow you want becomes one command:
#   laptop:        scripts/sync-ideas.sh --push      (sync + commit + push)
#   cros-penguin:  git pull                          (gets the latest plans)
#
# Reuse for the sibling apps (verbion, namastion) by overriding APP:
#   APP=verbion DOCS_SRC=… scripts/sync-ideas.sh
#===============================================================================
set -euo pipefail

# Repo root = parent of this script's dir (scripts/ -> repo root).
REPO_ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
cd "$REPO_ROOT"

APP="${APP:-$(basename "$REPO_ROOT")}"                      # konjugaton by default
DOCS_SRC="${DOCS_SRC:-$HOME/projects/lang-pratice-docs}"    # external planning root
DEST="$REPO_ROOT/docs"

PUSH=0
[[ "${1:-}" == "--push" ]] && PUSH=1

# (source-relative-to-DOCS_SRC, dest-filename-in-docs/)
MAP=(
  "general/general-ideas.md   ideas-general.md"
  "$APP/ideas.md              ideas-$APP.md"
)

echo "sync-ideas: app=$APP"
echo "  src: $DOCS_SRC"
echo "  dst: $DEST"
mkdir -p "$DEST"

missing=0
for row in "${MAP[@]}"; do
  read -r src dst <<<"$row"
  if [[ -f "$DOCS_SRC/$src" ]]; then
    cp -f "$DOCS_SRC/$src" "$DEST/$dst"                     # naked copy, verbatim
    echo "  ✓ $src → docs/$dst"
  else
    echo "  ✗ MISSING source: $DOCS_SRC/$src" >&2
    missing=1
  fi
done
[[ "$missing" == 0 ]] || { echo "sync-ideas: aborting, a source was missing." >&2; exit 1; }

if [[ "$PUSH" == 0 ]]; then
  echo "sync-ideas: synced (no --push). Working-tree status:"
  git -C "$REPO_ROOT" status --short docs/ || true
  echo "sync-ideas: run with --push to commit + push these to origin."
  exit 0
fi

if git -C "$REPO_ROOT" diff --quiet -- docs/ && git -C "$REPO_ROOT" diff --cached --quiet -- docs/; then
  echo "sync-ideas: docs/ already up to date — nothing to commit."
  exit 0
fi

git -C "$REPO_ROOT" add docs/ideas-general.md "docs/ideas-$APP.md"
git -C "$REPO_ROOT" commit -m "docs: sync planning ideas ($APP) from lang-pratice-docs"
git -C "$REPO_ROOT" push
echo "sync-ideas: pushed. On cros-penguin run:  git -C <clone> pull --ff-only"
