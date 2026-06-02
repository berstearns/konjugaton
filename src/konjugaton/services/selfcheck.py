"""Exhaustive self-validation of the whole system.

This is the heart of the reliability strategy. It walks the *entire* realizable
combinatorial space, generates every item, and asserts a set of invariants. The
same routine is used three ways:

* by ``pytest`` (``tests/test_exhaustive.py``) — fails the build on any
  combinatorial defect;
* by ``konjugaton selfcheck`` — runnable against the *deployed binary*;
* by CI — which builds the Nuitka binary and runs ``selfcheck`` in a clean
  environment, catching packaging/bundling regressions that unit tests cannot.

Beyond verbion's structural checks this also enforces **answerability** (the
displayed task pins every answer-determining axis), a **round-trip** (re-
conjugating the stated target reproduces the answer), and **self-grading** (the
item's own answer grades CORRECT) — because in Hindi an under-specified cloze is
genuinely ambiguous (the verb agrees with gender + number and the honorific
changes the ending).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from konjugaton.data import DataError, load_catalog
from konjugaton.domain import Item, KnowledgeType
from konjugaton.engine import AxisSelection, Conjugator, ExerciseGenerator, PermutationSpace
from konjugaton.engine.labels import number_of, person_of, tense_of
from konjugaton.services.grading import Grade, Grader
from konjugaton.settings.models import GradingSettings


@dataclass(slots=True)
class SelfCheckReport:
    """Outcome of a self-check run."""

    verbs: int = 0
    tams: int = 0
    coordinates_checked: int = 0
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def fail(self, coordinate_repr: str, reason: str) -> None:
        # Cap stored failures so a systemic break doesn't produce 100k lines.
        if len(self.failures) < 50:
            self.failures.append(f"{coordinate_repr}: {reason}")


def _check_item(item: Item, report: SelfCheckReport, where: str, grader: Grader) -> None:
    """Assert the invariants every generated item must satisfy."""
    coord = item.coordinate

    # -- structural ---------------------------------------------------------
    if not item.answer or not item.answer.strip():
        report.fail(where, "empty answer")
    if not item.full_sentence or not item.full_sentence.strip():
        report.fail(where, f"bad full_sentence {item.full_sentence!r}")
    if "_____" not in item.prompt:
        report.fail(where, "prompt has no blank")

    irt = item.irt
    if not all(math.isfinite(v) for v in (irt.difficulty, irt.discrimination, irt.guessing)):
        report.fail(where, "non-finite IRT parameter")
    if irt.discrimination <= 0 or not (0.0 <= irt.guessing <= 1.0):
        report.fail(where, f"out-of-range IRT (a={irt.discrimination}, c={irt.guessing})")

    # -- determinacy: the task must pin every answer-determining axis -------
    for token in (
        tense_of(coord.tense_mood),
        person_of(coord.person),
        number_of(coord.number),
    ):
        if token not in item.task:
            report.fail(where, f"task missing axis token {token!r}: {item.task!r}")
    if not item.lemma_hint:
        report.fail(where, "lemma not presented")

    # -- self-grading: the item's own answer must grade CORRECT -------------
    if grader.grade(item, item.answer).grade is not Grade.CORRECT:
        report.fail(where, "item's own answer does not grade CORRECT")

    _check_knowledge_specific(item, report, where)


def _check_knowledge_specific(item: Item, report: SelfCheckReport, where: str) -> None:
    """Invariants that depend on the item's knowledge type."""
    coord = item.coordinate
    if coord.knowledge is KnowledgeType.RECOGNITION:
        if len(item.choices) < 2:
            report.fail(where, "recognition item with <2 choices")
        if item.answer not in item.choices:
            report.fail(where, "answer missing from choices")
        if len(set(item.choices)) != len(item.choices):
            report.fail(where, f"duplicate choices {item.choices}")


def run_selfcheck(*, seed: int = 0, selection: AxisSelection | None = None) -> SelfCheckReport:
    """Walk the entire realizable space and validate every generated item."""
    report = SelfCheckReport()

    try:
        catalog = load_catalog()
    except DataError as exc:
        report.fail("<data>", str(exc))
        return report
    except Exception as exc:  # selfcheck must never itself crash — report, don't raise
        report.fail("<data>", f"unexpected error loading catalog: {exc!r}")
        return report

    if not catalog.verbs:
        report.fail("<data>", "no verbs loaded")
        return report

    conjugator = Conjugator(catalog.endings, dict(catalog.verbs))
    generator = ExerciseGenerator(catalog, conjugator)
    space = PermutationSpace(catalog, conjugator)
    grader = Grader(GradingSettings())
    rng = random.Random(seed)

    report.verbs = len(catalog.verbs)
    tenses: set[str] = set()

    for coordinate in space.iter_coordinates(selection):
        report.coordinates_checked += 1
        tenses.add(coordinate.tense_mood.value)
        where = (
            f"{coordinate.lemma}/{coordinate.tense_mood.value}/{coordinate.person.value}"
            f"{coordinate.number.value}/{coordinate.register.value}/{coordinate.voice.value}/"
            f"{coordinate.polarity.value}/{coordinate.knowledge.value}"
        )
        try:
            item = generator.generate(coordinate, rng)
        except Exception as exc:  # we *want* to catch everything: this is the net
            report.fail(where, f"generation raised {type(exc).__name__}: {exc}")
            continue
        _check_item(item, report, where, grader)

    report.tams = len(tenses)
    return report
