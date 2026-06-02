"""Versioned, idempotent, safe migration of the learner event logs.

Event records carry a ``schema_version``; this module knows how to bring any
record up to :data:`SCHEMA_VERSION` via an ordered registry of transforms. The
file-level migration is deliberately defensive:

* **dry-run by default** — nothing is written unless explicitly applied;
* **backup** the file before writing (``events.jsonl.bak-<utc>``);
* **atomic write** — temp file + ``os.replace`` (a crash can't corrupt the log);
* **post-write validation** — line count preserved, every record parses and is
  at the target version;
* **lossless** — unparseable lines are kept verbatim, never dropped.

Re-running is a no-op once everything is current.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from konjugaton.settings.store import base_root, profile_root

SCHEMA_VERSION = 3


def record_version(record: dict[str, Any]) -> int:
    """v1 = the original (no tag); later versions are explicitly stamped."""
    return int(record.get("schema_version", 1))


def _v1_to_v2(record: dict[str, Any]) -> dict[str, Any]:
    """Rename given/answer → user_answer/correct_answer (+ normalized pair)."""
    renames = {
        "given": "user_answer",
        "answer": "correct_answer",
        "normalized_given": "normalized_user_answer",
        "normalized_answer": "normalized_correct_answer",
    }
    for old, new in renames.items():
        if old in record and new not in record:
            record[new] = record.pop(old)
    record["schema_version"] = 2
    return record


def _v2_to_v3(record: dict[str, Any]) -> dict[str, Any]:
    """Add the ``construction`` axis (the light-verb/passive layer).

    Records written before the construction axis existed were all SIMPLE
    finite verbs, so the lossless default is ``"simple"``.
    """
    record.setdefault("construction", "simple")
    record["schema_version"] = 3
    return record


#: version N → transform that produces version N+1
_STEPS: dict[int, Any] = {1: _v1_to_v2, 2: _v2_to_v3}


def migrate_record(record: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Bring one record up to SCHEMA_VERSION. Returns (record, changed)."""
    changed = False
    current = dict(record)
    while record_version(current) < SCHEMA_VERSION:
        step = _STEPS.get(record_version(current))
        if step is None:  # no path forward — leave as-is rather than loop
            break
        current = step(dict(current))
        changed = True
    return current, changed


@dataclass(slots=True)
class FileReport:
    path: Path
    exists: bool = True
    total: int = 0
    migrated: int = 0
    unparseable: int = 0
    written: bool = False
    backup: Path | None = None
    errors: list[str] = field(default_factory=list)


def migrate_file(path: Path, *, apply: bool = False, make_backup: bool = True) -> FileReport:
    """Migrate one events.jsonl. Dry-run unless ``apply`` is True."""
    report = FileReport(path=path)
    if not path.exists():
        report.exists = False
        return report

    out_lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        report.total += 1
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            report.unparseable += 1
            out_lines.append(raw)  # preserve verbatim — never lose data
            continue
        migrated, changed = migrate_record(record)
        if changed:
            report.migrated += 1
        out_lines.append(json.dumps(migrated, ensure_ascii=False))

    if not apply or report.migrated == 0:
        return report

    if make_backup:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        report.backup = path.with_name(f"{path.name}.bak-{stamp}")
        shutil.copy2(path, report.backup)

    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    _validate(tmp, expected_lines=len(out_lines), report=report)
    tmp.replace(path)
    report.written = True
    return report


def _validate(tmp: Path, *, expected_lines: int, report: FileReport) -> None:
    """Fail loudly before the atomic replace if the rewrite looks wrong."""
    written = [ln for ln in tmp.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if len(written) != expected_lines:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"migration line-count mismatch ({len(written)} != {expected_lines})")
    bad = report.unparseable  # the only records allowed to not be at the target version
    for ln in written:
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            bad -= 1
            continue
        if record_version(rec) != SCHEMA_VERSION:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"record not at v{SCHEMA_VERSION} after migration: {ln[:60]}")
    if bad < 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("more unparseable lines after write than before")


def discover_event_logs() -> list[Path]:
    """Every ~/konjugaton/<user>/events.jsonl that exists."""
    root = base_root()
    if not root.exists():
        return []
    return [p / "events.jsonl" for p in sorted(root.iterdir()) if (p / "events.jsonl").exists()]


def migrate_user(user: str, *, apply: bool = False) -> FileReport:
    return migrate_file(profile_root(user) / "events.jsonl", apply=apply)
