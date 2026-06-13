"""A :class:`ConjugationTable` — one verb, one tense-mood, the standard paradigm.

This is the value object behind the *conjugation-table completion* drill: instead
of one cloze sampled from across the space, the learner fills the whole paradigm
of a single verb in a single tense-mood (ich habe / du hast / er hat / …).

Each cell wraps a real PRODUCTION :class:`~konjugaton.domain.item.Item` whose
answer is the contiguous verb complex, so grading, IRT and state-recording are
reused verbatim — a table is just six (or, for the Imperativ, three) focused
items over the same tense-mood.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from konjugaton.domain.agreement import Agreement
    from konjugaton.domain.enums import TenseMood
    from konjugaton.domain.item import Item


@dataclass(frozen=True, slots=True)
class ConjugationCell:
    """One row of the table: an agreement bundle, its display subject, and the item."""

    agreement: Agreement
    subject: str  # display label: ich/du/er/wir/ihr/sie, or (du)/(ihr)/(Sie) for the Imperativ
    item: Item

    @property
    def answer(self) -> str:
        """The expected verb complex for this cell (e.g. ``hast``, ``hast gehabt``)."""
        return self.item.answer


@dataclass(frozen=True, slots=True)
class ConjugationTable:
    """The full paradigm of one verb in one tense-mood, in canonical pronoun order."""

    lemma: str
    translation: str
    tense_mood: TenseMood
    tense_label: str  # display label, e.g. "Präsens" (computed by the engine layer)
    cells: tuple[ConjugationCell, ...]
