"""Mapping-aware character diff for 'where did I go wrong'."""

from __future__ import annotations

from konjugaton.services.grading import Grader
from konjugaton.services.textdiff import char_diff, mapping_aware_diff, mistake_markup
from konjugaton.settings.models import GradingSettings


def _normalizer():
    return Grader(GradingSettings(ignore_accents=True)).normalize


def test_plain_char_diff() -> None:
    given, answer = char_diff("karta", "karti")
    assert "[red]" in given  # extra/wrong in input
    assert "[green]" in answer  # missing in answer


def test_mapping_aware_marks_forgiven_blue() -> None:
    # "ee" for "i" is forgiven by ignore_accents → the differing span is blue,
    # not red/green. (keejiye vs kijiye normalize equal under the ee→i fold.)
    given, answer = mapping_aware_diff("keejiye", "kijiye", _normalizer())
    assert "[blue]" in given or "[blue]" in answer
    # sanity: a genuine error is NOT blue
    g2, a2 = mapping_aware_diff("karti", "karta", _normalizer())
    assert "[blue]" not in g2 and "[blue]" not in a2


def test_mistake_markup_has_legend() -> None:
    markup = mistake_markup("karta", "karti", _normalizer())
    assert "you :" in markup
    assert "want:" in markup
    assert "accepted via your mappings" in markup


def test_diff_works_on_devanagari() -> None:
    given, answer = char_diff("करता", "करती")
    assert "[red]" in given and "[green]" in answer
