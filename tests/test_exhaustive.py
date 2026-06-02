"""Layer 1 of the reliability strategy: exhaustive combinatorial validation.

Walks the ENTIRE realizable space and asserts every single coordinate produces a
valid, answerable, self-grading item. This converts a "combinatorial error" (a
verb/tense/agreement cell that raises or yields a malformed/ambiguous item) from a
runtime surprise into a failing unit test — caught on every commit, before any
build.
"""

from __future__ import annotations

from konjugaton.domain import TenseMood
from konjugaton.engine import AxisSelection
from konjugaton.services import run_selfcheck


def test_entire_space_generates_valid_items() -> None:
    report = run_selfcheck()
    assert report.coordinates_checked == 41_660
    assert report.ok, "self-check failures:\n" + "\n".join(report.failures)


def test_selfcheck_covers_all_tenses_and_verbs() -> None:
    report = run_selfcheck()
    assert report.tams == 9
    assert report.verbs >= 20


def test_selfcheck_is_deterministic() -> None:
    a = run_selfcheck(seed=1)
    b = run_selfcheck(seed=1)
    assert (a.coordinates_checked, a.ok) == (b.coordinates_checked, b.ok)


def test_perfekt_slice_is_fully_valid() -> None:
    # The haben/sein auxiliary split — a characteristic German difficulty.
    report = run_selfcheck(selection=AxisSelection(tense_moods=(TenseMood.PERFEKT,)))
    assert report.ok, "\n".join(report.failures)
    assert report.coordinates_checked > 0
