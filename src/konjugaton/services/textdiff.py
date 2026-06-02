"""Character-level diff that *acknowledges the grading mappings*.

Strategy: diff the **raw** learner input against the **raw** correct answer (so
real Devanagari/letters are shown), then classify each differing span by running
the grader's own normalisation over it:

* span where ``normalize(given) == normalize(answer)`` → **forgiven** (blue):
  it differed but a mapping/case/punctuation rule accepted it (e.g. ``aa`` for
  ``a`` under ignore_accents).
* span that normalises away to ``""`` → forgiven (dropped punctuation/space).
* otherwise → a real mistake: red for extra/wrong input, green for missing.

This keeps the highlight consistent with grading: blue = "accepted via your
mappings", red/green = "this is what actually cost you". Works on Devanagari and
romanized strings alike (difflib operates on Unicode code points).
"""

from __future__ import annotations

import difflib
from collections.abc import Callable

Normalizer = Callable[[str], str]


def char_diff(given: str, answer: str) -> tuple[str, str]:
    """Plain char diff (no mapping awareness): red = extra/wrong, green = missing."""
    matcher = difflib.SequenceMatcher(a=given, b=answer, autojunk=False)
    given_parts: list[str] = []
    answer_parts: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        gseg, aseg = given[i1:i2], answer[j1:j2]
        if tag == "equal":
            given_parts.append(f"[dim]{gseg}[/]")
            answer_parts.append(f"[dim]{aseg}[/]")
        elif tag == "replace":
            given_parts.append(f"[red]{gseg}[/]")
            answer_parts.append(f"[green]{aseg}[/]")
        elif tag == "delete":
            given_parts.append(f"[red]{gseg}[/]")
        elif tag == "insert":
            answer_parts.append(f"[green]{aseg}[/]")
    return "".join(given_parts), "".join(answer_parts)


def mapping_aware_diff(given: str, answer: str, normalize: Normalizer) -> tuple[str, str]:
    """Diff raw strings, marking mapping/case/punct-forgiven spans blue vs red/green."""
    matcher = difflib.SequenceMatcher(a=given, b=answer, autojunk=False)
    given_parts: list[str] = []
    answer_parts: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        gseg, aseg = given[i1:i2], answer[j1:j2]
        if tag == "equal":
            given_parts.append(f"[dim]{gseg}[/]")
            answer_parts.append(f"[dim]{aseg}[/]")
        elif tag == "replace":
            forgiven = normalize(gseg) == normalize(aseg)
            style = "blue" if forgiven else None
            given_parts.append(f"[{style or 'red'}]{gseg}[/]")
            answer_parts.append(f"[{style or 'green'}]{aseg}[/]")
        elif tag == "delete":
            given_parts.append(f"[{'blue' if normalize(gseg) == '' else 'red'}]{gseg}[/]")
        elif tag == "insert":
            answer_parts.append(f"[{'blue' if normalize(aseg) == '' else 'green'}]{aseg}[/]")
    return "".join(given_parts), "".join(answer_parts)


def mistake_markup(given: str, answer: str, normalize: Normalizer) -> str:
    """Three lines: you / want / legend, with mapping-forgiven spans in blue."""
    given_markup, answer_markup = mapping_aware_diff(given, answer, normalize)
    return (
        f"[dim]you :[/] {given_markup}\n"
        f"[dim]want:[/] {answer_markup}\n"
        "[dim](blue = accepted via your mappings · red = wrong/extra · green = missing)[/]"
    )
