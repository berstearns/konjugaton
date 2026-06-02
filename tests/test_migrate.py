"""Versioned, idempotent, safe event-log migration."""

from __future__ import annotations

import json
from pathlib import Path

from konjugaton.migrate import SCHEMA_VERSION, migrate_file, migrate_record, record_version


def test_v1_record_renames_and_versions() -> None:
    v1 = {"given": "x", "answer": "y", "normalized_given": "x", "normalized_answer": "y"}
    out, changed = migrate_record(v1)
    assert changed
    assert out["user_answer"] == "x"
    assert out["correct_answer"] == "y"
    assert out["normalized_user_answer"] == "x"
    assert "given" not in out and "answer" not in out
    assert out["schema_version"] == SCHEMA_VERSION


def test_idempotent() -> None:
    once, _ = migrate_record({"given": "x", "answer": "y"})
    twice, changed = migrate_record(once)
    assert not changed
    assert twice == once


def test_transitional_record_gets_tagged() -> None:
    out, changed = migrate_record({"user_answer": "x", "correct_answer": "y"})
    assert changed
    assert out["schema_version"] == SCHEMA_VERSION


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    f = tmp_path / "events.jsonl"
    f.write_text(json.dumps({"given": "x", "answer": "y"}) + "\n", encoding="utf-8")
    before = f.read_text(encoding="utf-8")
    report = migrate_file(f, apply=False)
    assert report.migrated == 1
    assert not report.written
    assert f.read_text(encoding="utf-8") == before


def test_apply_backs_up_and_rewrites(tmp_path: Path) -> None:
    f = tmp_path / "events.jsonl"
    f.write_text(
        json.dumps({"given": "करता हूँ", "answer": "किया है"})
        + "\n"
        + json.dumps({"schema_version": 2, "user_answer": "c", "correct_answer": "d"})
        + "\n",
        encoding="utf-8",
    )
    report = migrate_file(f, apply=True)
    assert report.written
    assert report.backup is not None and report.backup.exists()
    rows = [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 2  # line count preserved
    assert all(r["schema_version"] == SCHEMA_VERSION for r in rows)
    assert rows[0]["user_answer"] == "करता हूँ"  # Devanagari preserved


def test_unparseable_line_preserved(tmp_path: Path) -> None:
    f = tmp_path / "events.jsonl"
    f.write_text(json.dumps({"given": "x", "answer": "y"}) + "\nNOT JSON\n", encoding="utf-8")
    report = migrate_file(f, apply=True)
    assert report.unparseable == 1
    lines = [ln for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert "NOT JSON" in lines
    assert record_version(json.loads(lines[0])) == SCHEMA_VERSION
