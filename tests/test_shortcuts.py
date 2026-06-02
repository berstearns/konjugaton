"""Config-driven TUI shortcuts (text-based, remappable)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from konjugaton.settings import Settings
from konjugaton.settings.models import ShortcutSettings


def test_default_shortcuts() -> None:
    sc = Settings().shortcuts
    assert sc.next == "ctrl+right"
    assert sc.prev == "ctrl+left"
    assert sc.quit == "ctrl+q"


def test_shortcuts_remap_and_roundtrip() -> None:
    s = Settings()
    s.shortcuts.next = "ctrl+l"  # vim-like
    s.shortcuts.prev = "ctrl+h"
    restored = Settings.model_validate(s.model_dump())
    assert restored.shortcuts.next == "ctrl+l"
    assert restored.shortcuts.prev == "ctrl+h"


def test_shortcut_settings_strict() -> None:
    with pytest.raises(ValidationError):
        ShortcutSettings.model_validate({"bogus": "x"})
