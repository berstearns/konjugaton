"""The :class:`Item` — a single generated exercise, carrying IRT parameters.

We follow Item Response Theory: every item exposes a difficulty ``b``, a
discrimination ``a`` and a pseudo-guessing ``c`` (the 3-parameter logistic
model). These let us (a) order a session by ascending difficulty, (b) estimate
the learner's ability from their responses, and (c) later *calibrate* the
parameters empirically from response data instead of the heuristic seed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from konjugaton.domain.taxonomy import Coordinate, Skill


@dataclass(frozen=True, slots=True)
class IrtParameters:
    """3PL item parameters.

    * ``difficulty`` (b): ability at which P(correct) is halfway up the curve.
    * ``discrimination`` (a): how sharply the item separates ability levels.
    * ``guessing`` (c): lower asymptote — P(correct) for very low ability
      (≈ 1/n_choices for multiple choice, 0 for free production).
    """

    difficulty: float
    discrimination: float = 1.0
    guessing: float = 0.0


@dataclass(frozen=True, slots=True)
class Item:
    """A renderable, gradable exercise instance.

    ``prompt`` is shown to the learner; ``answer`` is the canonical correct
    response (in the coordinate's elicited script); ``accepted`` holds extra
    surface variants graded as correct; ``choices`` is populated only for
    recognition (multiple-choice) items. ``task`` is the human-readable
    grammatical target ("present-habitual · तुम · feminine · negative") that
    makes the cloze answerable.
    """

    coordinate: Coordinate
    skill: Skill
    prompt: str
    answer: str
    irt: IrtParameters
    accepted: tuple[str, ...] = ()
    choices: tuple[str, ...] = ()
    lemma_hint: str = ""
    task: str = ""
    full_sentence: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)

    @property
    def is_multiple_choice(self) -> bool:
        return bool(self.choices)
