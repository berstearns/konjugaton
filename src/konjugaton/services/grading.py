"""Configurable grading — driven by :class:`GradingSettings`.

Pipeline: normalise (case → transliteration → punctuation → whitespace), then
match in order of strictness:

    exact → NEAR (length-scaled similarity) → ACCENT_SLIP (soft) → INCORRECT

NEAR counts as correct but is flagged and carries the edit distance, so the
learner-output logs can analyse near-misses. ``transliteration`` folds plausible
romanization variants (aa→a, ee→i, …) so a forgiving grader accepts them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from konjugaton.textutils import build_replacements, levenshtein, strip_accents, transliterate

if TYPE_CHECKING:
    from konjugaton.domain import Item
    from konjugaton.settings.models import GradingSettings

#: Sentence punctuation stripped when ignore_punctuation is on. Includes the
#: Devanagari danda (।) and double-danda (॥), the natural Hindi full stops.
_TRIM_PUNCT = set('.,;:!?…"()[]।॥')


class Grade(StrEnum):
    CORRECT = "correct"
    NEAR = "near"  # accepted within similarity tolerance
    ACCENT_SLIP = "accent-slip"  # right form, diacritics differ (soft signal)
    INCORRECT = "incorrect"


@dataclass(frozen=True, slots=True)
class GradedResponse:
    item: Item
    given: str
    grade: Grade
    distance: int
    normalized_given: str
    normalized_answer: str

    @property
    def is_correct(self) -> bool:
        return self.grade is not Grade.INCORRECT


class Grader:
    """Grades a response against an item per the user's grading settings."""

    def __init__(self, settings: GradingSettings) -> None:
        self._s = settings
        self._replacements = (
            build_replacements(settings.transliteration) if settings.ignore_accents else []
        )

    def normalize(self, text: str) -> str:
        result = text.strip()
        if self._s.ignore_case:
            result = result.lower()
        if self._s.ignore_accents:
            result = transliterate(result, self._replacements)
        if self._s.ignore_punctuation:
            result = "".join(ch for ch in result if ch not in _TRIM_PUNCT)
        return " ".join(result.split())

    def grade(self, item: Item, given: str) -> GradedResponse:
        norm_answer = self.normalize(item.answer)
        accepted = [self.normalize(a) for a in (item.answer, *item.accepted)]
        norm_given = self.normalize(given)

        if norm_given in accepted:
            return GradedResponse(item, given, Grade.CORRECT, 0, norm_given, norm_answer)

        distance = min(levenshtein(norm_given, candidate) for candidate in accepted)

        tolerance = self._s.similarity_tolerance
        if tolerance > 0:
            reference_len = len(norm_answer) or 1
            if distance <= (tolerance / 10.0) * reference_len:
                return GradedResponse(item, given, Grade.NEAR, distance, norm_given, norm_answer)

        if strip_accents(norm_given) in {strip_accents(c) for c in accepted}:
            return GradedResponse(item, given, Grade.ACCENT_SLIP, distance, norm_given, norm_answer)

        return GradedResponse(item, given, Grade.INCORRECT, distance, norm_given, norm_answer)
