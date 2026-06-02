"""Learner-output logging writes the configured files to the profile folder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from konjugaton.services.output import LearnerLogger
from konjugaton.settings import Settings, resolve_output_dir
from konjugaton.state import VocabState


@pytest.fixture(autouse=True)
def _isolated_home(  # pyright: ignore[reportUnusedFunction]
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KONJUGATON_HOME", str(tmp_path))


def test_response_logged_to_jsonl_and_csv() -> None:
    settings = Settings()
    logger = LearnerLogger(settings, "alice")
    record = {
        "lemma": "करना",
        "tam": "perfect",
        "grade": "correct",
        "is_correct": True,
        "theta_before": 0.0,
        "theta_after": 0.5,
        "p_correct": 0.5,
    }
    logger.log_response(record)

    out = resolve_output_dir(settings, "alice")
    jsonl = out / "events.jsonl"
    csv = out / "events.csv"
    assert jsonl.exists() and csv.exists()
    row = json.loads(jsonl.read_text(encoding="utf-8").strip())
    assert row["lemma"] == "करना"  # Devanagari preserved (ensure_ascii=False)
    assert "theta_after" in csv.read_text(encoding="utf-8")


def test_disabled_output_writes_nothing() -> None:
    settings = Settings()
    settings.output.enabled = False
    logger = LearnerLogger(settings, "bob")
    logger.log_response({"lemma": "x"})
    out = resolve_output_dir(settings, "bob")
    assert not (out / "events.jsonl").exists()


def test_state_snapshot() -> None:
    settings = Settings()
    logger = LearnerLogger(settings, "carol")
    snap = logger.snapshot_state(VocabState())
    assert snap is not None
    assert snap.exists()
