"""Settings: load/save round-trip, presets, profile isolation."""

from __future__ import annotations

from pathlib import Path

import pytest

from konjugaton.settings import (
    PRESET_NAMES,
    Settings,
    apply_preset,
    config_path,
    load_settings,
    save_settings,
)


@pytest.fixture(autouse=True)
def _isolated_home(  # pyright: ignore[reportUnusedFunction]
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KONJUGATON_HOME", str(tmp_path))


def test_first_load_writes_defaults() -> None:
    settings = load_settings("alice")
    assert settings.preset == "custom"
    assert config_path("alice").exists()


def test_roundtrip_preserves_changes() -> None:
    settings = load_settings("bob")
    settings.grading.similarity_tolerance = 4
    settings.grading.transliteration["a"] = ["a", "aa"]
    save_settings(settings, "bob")
    reloaded = load_settings("bob")
    assert reloaded.grading.similarity_tolerance == 4
    assert reloaded.grading.transliteration["a"] == ["a", "aa"]


def test_profiles_are_isolated() -> None:
    a = load_settings("a")
    a.grading.similarity_tolerance = 7
    save_settings(a, "a")
    assert load_settings("b").grading.similarity_tolerance == 0


def test_all_presets_apply() -> None:
    for name in PRESET_NAMES:
        settings = apply_preset(name)
        assert isinstance(settings, Settings)
        assert settings.preset == name
    assert apply_preset("gentle").grading.similarity_tolerance == 3
    assert apply_preset("exam_prep").grading.require_subject_pronoun is True
    assert apply_preset("polyglot_power").curriculum.passive_focus is True
