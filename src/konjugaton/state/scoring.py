"""Per-(vocab, knowledge) score cell and its update rule.

A cell keeps both a raw tally (attempts / correct) and a recency-weighted
mastery signal (EWMA in [0, 1]). The EWMA forgets old performance, so a learner
who has improved is not anchored to early mistakes — the right behaviour for a
practice tool.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: EWMA smoothing factor. Higher = faster to react to recent answers.
DEFAULT_ALPHA = 0.35


@dataclass(slots=True)
class ScoreCell:
    """Mastery evidence for one (vocab, knowledge-type) pair."""

    attempts: int = 0
    correct: int = 0
    ewma: float = 0.0
    last_seen: str | None = None

    def register(self, *, correct: bool, timestamp: str, alpha: float = DEFAULT_ALPHA) -> None:
        target = 1.0 if correct else 0.0
        self.ewma = target if self.attempts == 0 else alpha * target + (1 - alpha) * self.ewma
        self.attempts += 1
        if correct:
            self.correct += 1
        self.last_seen = timestamp

    @property
    def accuracy(self) -> float:
        return self.correct / self.attempts if self.attempts else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempts": self.attempts,
            "correct": self.correct,
            "ewma": round(self.ewma, 6),
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScoreCell:
        return cls(
            attempts=int(data["attempts"]),
            correct=int(data["correct"]),
            ewma=float(data["ewma"]),
            last_seen=data.get("last_seen"),
        )
