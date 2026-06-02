#!/usr/bin/env python3
"""Sync the konjugaton taxonomy (YAML) into Android assets (JSON).

This is the data pipeline that keeps konjugaton's promise — "adding a verb is a
data edit, not a code change" — alive on Android. You keep authoring in the
canonical YAML under ``src/konjugaton/_data/``; this script mirrors it verbatim
(same keys, same structure) into ``app/src/main/assets/*.json``, which the app
parses at startup.

Run it whenever you edit the taxonomy:

    python tools/sync_taxonomy.py        # from minimal-konjugaton-android/

No dependency on the app; only needs PyYAML (already in the konjugaton venv).
``ensure_ascii=False`` keeps Devanagari human-readable in the committed asset.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

# minimal-konjugaton-android/tools/sync_taxonomy.py -> repo root is two parents up.
HERE = Path(__file__).resolve()
ANDROID_ROOT = HERE.parent.parent
REPO_ROOT = ANDROID_ROOT.parent
SRC_DATA = REPO_ROOT / "src" / "konjugaton" / "_data"
ASSETS = ANDROID_ROOT / "app" / "src" / "main" / "assets"

FILES = ("verbs.yaml", "endings.yaml", "contexts.yaml")


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        data = yaml.safe_load((SRC_DATA / name).read_text(encoding="utf-8"))
        out = ASSETS / name.replace(".yaml", ".json")
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  {name:16} -> {out.relative_to(ANDROID_ROOT)}")
    print("taxonomy synced.")


if __name__ == "__main__":
    main()
