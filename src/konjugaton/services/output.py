"""Learner-output logging to the per-user profile folder.

Writes "every log and calculation about the learner" the config asks for:
responses (with full IRT calculations), generated items, and state snapshots —
as JSONL and/or CSV under ``~/konjugaton/{userid}/``. All gated by OutputSettings.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from konjugaton.settings.store import resolve_output_dir

if TYPE_CHECKING:
    from pathlib import Path

    from konjugaton.domain import Item
    from konjugaton.services.grading import GradedResponse
    from konjugaton.settings.models import Settings
    from konjugaton.state import VocabState

#: Stable CSV column order for the response event log. Carries the full German
#: coordinate (tense-mood + agreement + register + voice) and the IRT calculations.
EVENT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "timestamp",
    "user",
    "lemma",
    "verb_class",
    "tense_mood",
    "person",
    "number",
    "register",
    "voice",
    "polarity",
    "knowledge",
    "context",
    "prompt",
    "correct_answer",
    "user_answer",
    "grade",
    "is_correct",
    "distance",
    "normalized_user_answer",
    "normalized_correct_answer",
    "irt_a",
    "irt_b",
    "irt_c",
    "p_correct",
    "information",
    "theta_before",
    "theta_after",
    "ewma_before",
    "ewma_after",
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class LearnerLogger:
    """Append learner events to the profile folder, per OutputSettings."""

    def __init__(self, settings: Settings, user: str) -> None:
        self._out = settings.output
        self._user = user
        self._dir = resolve_output_dir(settings, user)
        if self._out.enabled:
            self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._dir

    @property
    def enabled(self) -> bool:
        return self._out.enabled

    def _append_jsonl(self, filename: str, record: dict[str, Any]) -> None:
        with (self._dir / filename).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _append_csv(self, filename: str, fields: tuple[str, ...], record: dict[str, Any]) -> None:
        path = self._dir / filename
        write_header = not path.exists()
        with path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            if write_header:
                writer.writeheader()
            writer.writerow({k: record.get(k, "") for k in fields})

    def log_response(self, record: dict[str, Any]) -> None:
        if not self._out.enabled or not self._out.log_responses:
            return
        if "jsonl" in self._out.formats:
            self._append_jsonl("events.jsonl", record)
        if "csv" in self._out.formats:
            self._append_csv("events.csv", EVENT_FIELDS, record)

    def log_item(self, item: Item) -> None:
        if not self._out.enabled or not self._out.log_items:
            return
        coord = item.coordinate
        self._append_jsonl(
            "items.jsonl",
            {
                "timestamp": utc_now(),
                "lemma": coord.lemma,
                "tense_mood": coord.tense_mood.value,
                "person": coord.person.value,
                "number": coord.number.value,
                "register": coord.register.value,
                "voice": coord.voice.value,
                "polarity": coord.polarity.value,
                "knowledge": coord.knowledge.value,
                "context": coord.context,
                "prompt": item.prompt,
                "answer": item.answer,
                "choices": list(item.choices),
                "difficulty": item.irt.difficulty,
            },
        )

    def snapshot_state(self, state: VocabState) -> Path | None:
        if not self._out.enabled or not self._out.snapshot_state:
            return None
        path = self._dir / f"state-{datetime.now(UTC):%Y%m%dT%H%M%S}.json"
        path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def log_session(self, summary: dict[str, Any]) -> None:
        if not self._out.enabled:
            return
        self._append_jsonl("sessions.jsonl", {"timestamp": utc_now(), **summary})

    def log_feedback(self, *, user: str, item: Item, text: str) -> None:
        """Append the learner's free-text feedback on an item."""
        if not self._out.enabled:
            return
        coord = item.coordinate
        self._append_jsonl(
            "feedback.jsonl",
            {
                "timestamp": utc_now(),
                "user": user,
                "lemma": coord.lemma,
                "tense_mood": coord.tense_mood.value,
                "person": coord.person.value,
                "number": coord.number.value,
                "register": coord.register.value,
                "voice": coord.voice.value,
                "polarity": coord.polarity.value,
                "knowledge": coord.knowledge.value,
                "prompt": item.prompt,
                "feedback": text,
            },
        )


def build_response_record(
    *,
    user: str,
    item: Item,
    graded: GradedResponse,
    p_correct: float,
    information: float,
    theta_before: float,
    theta_after: float,
    ewma_before: float,
    ewma_after: float,
    verb_class: str,
) -> dict[str, object]:
    """Assemble the flat response event (shared by the CLI and TUI loops)."""
    coord = item.coordinate
    return {
        "schema_version": 3,  # see konjugaton.migrate.SCHEMA_VERSION
        "timestamp": utc_now(),
        "user": user,
        "lemma": coord.lemma,
        "verb_class": verb_class,
        "tense_mood": coord.tense_mood.value,
        "person": coord.person.value,
        "number": coord.number.value,
        "register": coord.register.value,
        "voice": coord.voice.value,
        "polarity": coord.polarity.value,
        "knowledge": coord.knowledge.value,
        "context": coord.context,
        "prompt": item.prompt,
        "correct_answer": item.answer,
        "user_answer": graded.given,
        "grade": graded.grade.value,
        "is_correct": graded.is_correct,
        "distance": graded.distance,
        "normalized_user_answer": graded.normalized_given,
        "normalized_correct_answer": graded.normalized_answer,
        "irt_a": item.irt.discrimination,
        "irt_b": item.irt.difficulty,
        "irt_c": item.irt.guessing,
        "p_correct": round(p_correct, 4),
        "information": round(information, 4),
        "theta_before": round(theta_before, 4),
        "theta_after": round(theta_after, 4),
        "ewma_before": round(ewma_before, 4),
        "ewma_after": round(ewma_after, 4),
    }
