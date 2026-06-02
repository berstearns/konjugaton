"""User settings: the config.yaml schema, per-user store, and preset bundles."""

from __future__ import annotations

from konjugaton.settings.models import DEFAULT_TRANSLITERATION, Settings, ShortcutSettings
from konjugaton.settings.presets import PRESET_NAMES, apply_preset
from konjugaton.settings.store import (
    config_path,
    default_user,
    load_settings,
    profile_root,
    resolve_output_dir,
    save_settings,
    state_path,
)

__all__ = [
    "DEFAULT_TRANSLITERATION",
    "PRESET_NAMES",
    "Settings",
    "ShortcutSettings",
    "apply_preset",
    "config_path",
    "default_user",
    "load_settings",
    "profile_root",
    "resolve_output_dir",
    "save_settings",
    "state_path",
]
