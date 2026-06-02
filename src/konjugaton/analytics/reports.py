"""Tabular analytics over the learner state — pure Python, no pandas.

Returns lightweight, ordered row objects so any front-end (a rich table, a CSV
writer, a notebook) can consume them. Kept dependency-free on purpose: it keeps
the compiled binary small and the analytics layer trivially portable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from konjugaton.data import Catalog
    from konjugaton.state.vocab_state import VocabState

MASTERY_COLUMNS: tuple[str, ...] = (
    "lemma",
    "class",
    "translation",
    "knowledge",
    "attempts",
    "correct",
    "accuracy",
    "ewma",
    "last_seen",
)
ABILITY_COLUMNS: tuple[str, ...] = ("class", "tam", "knowledge", "theta")


@dataclass(frozen=True, slots=True)
class MasteryRow:
    """One (vocab, knowledge-type) the learner has attempted."""

    lemma: str
    verb_class: str
    translation: str
    knowledge: str
    attempts: int
    correct: int
    accuracy: float
    ewma: float
    last_seen: str | None

    def as_cells(self) -> tuple[str, ...]:
        return (
            self.lemma,
            self.verb_class,
            self.translation,
            self.knowledge,
            str(self.attempts),
            str(self.correct),
            f"{self.accuracy:.3f}",
            f"{self.ewma:.3f}",
            self.last_seen or "",
        )


@dataclass(frozen=True, slots=True)
class AbilityRow:
    """One practised skill and its IRT ability estimate."""

    verb_class: str
    tam: str
    knowledge: str
    theta: float

    def as_cells(self) -> tuple[str, ...]:
        return (self.verb_class, self.tam, self.knowledge, f"{self.theta:.3f}")


def mastery_rows(state: VocabState, catalog: Catalog) -> list[MasteryRow]:
    """Mastery rows, weakest (lowest EWMA) first."""
    rows: list[MasteryRow] = []
    for lemma, knowledge_map in state.scores.items():
        verb = catalog.verbs.get(lemma)
        for knowledge, cell in knowledge_map.items():
            rows.append(
                MasteryRow(
                    lemma=lemma,
                    verb_class=verb.verb_class.value if verb else "?",
                    translation=verb.translation if verb else "",
                    knowledge=knowledge.value,
                    attempts=cell.attempts,
                    correct=cell.correct,
                    accuracy=round(cell.accuracy, 3),
                    ewma=round(cell.ewma, 3),
                    last_seen=cell.last_seen,
                )
            )
    rows.sort(key=lambda r: (r.ewma, -r.attempts))
    return rows


def ability_rows(state: VocabState) -> list[AbilityRow]:
    """Skill ability rows, lowest theta first."""
    rows: list[AbilityRow] = []
    for key, theta in state.abilities.items():
        verb_class, tam, knowledge = key.split("|")
        rows.append(
            AbilityRow(verb_class=verb_class, tam=tam, knowledge=knowledge, theta=round(theta, 3))
        )
    rows.sort(key=lambda r: r.theta)
    return rows


def summary(state: VocabState) -> dict[str, float | int]:
    """Headline numbers for the dashboard / CLI footer."""
    attempts = 0
    correct = 0
    vocab_seen = 0
    for knowledge_map in state.scores.values():
        if knowledge_map:
            vocab_seen += 1
        for cell in knowledge_map.values():
            attempts += cell.attempts
            correct += cell.correct
    return {
        "vocab_seen": vocab_seen,
        "skills_seen": len(state.abilities),
        "attempts": attempts,
        "correct": correct,
        "accuracy": round(correct / attempts, 3) if attempts else 0.0,
    }
