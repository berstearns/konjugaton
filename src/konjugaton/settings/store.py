"""Per-user profile locations + load/save of config.yaml.

Profile layout (default):

    ~/konjugaton/{userid}/
        config.yaml      # the Settings, editable by hand or via the TUI
        state.json       # learner state
        events.jsonl     # learner output (see konjugaton.services.output)
        ...

The base ``~/konjugaton`` can be overridden with ``$KONJUGATON_HOME`` (used by
tests). Saving and loading the same path is the bidirectional bridge the TUI
relies on.
"""

from __future__ import annotations

import getpass
import os
from pathlib import Path

import yaml

from konjugaton.settings.models import Settings


def base_root() -> Path:
    override = os.environ.get("KONJUGATON_HOME")
    return Path(override).expanduser() if override else Path.home() / "konjugaton"


def default_user() -> str:
    return os.environ.get("KONJUGATON_USER") or getpass.getuser()


def profile_root(user: str) -> Path:
    return base_root() / user


def config_path(user: str) -> Path:
    return profile_root(user) / "config.yaml"


def state_path(user: str) -> Path:
    return profile_root(user) / "state.json"


#: The schema default for output.dir; when unchanged we route outputs to the
#: profile root so $KONJUGATON_HOME governs config and outputs together.
_DEFAULT_OUTPUT_DIR = "~/konjugaton/{userid}"


def resolve_output_dir(settings: Settings, user: str) -> Path:
    if settings.output.dir == _DEFAULT_OUTPUT_DIR:
        return profile_root(user)
    return Path(settings.output.dir.replace("{userid}", user)).expanduser()


def load_settings(user: str, *, create: bool = True) -> Settings:
    """Load settings for ``user``; write defaults on first run if ``create``."""
    path = config_path(user)
    if not path.exists():
        settings = Settings()
        if create:
            save_settings(settings, user)
        return settings
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Settings.model_validate(data)


def save_settings(settings: Settings, user: str) -> Path:
    """Persist settings to the user's config.yaml (UTF-8, key order preserved)."""
    path = config_path(user)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = yaml.safe_dump(
        settings.model_dump(), allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    path.write_text(payload, encoding="utf-8")
    return path
