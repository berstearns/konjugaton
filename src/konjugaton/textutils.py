"""Pure text utilities for grading — Levenshtein distance and transliteration.

Stdlib-only and side-effect-free, so they're trivially testable and cheap to
bundle in the binary. Used by the configurable grader.

For Hindi the transliteration map plays a different role than in French: it
absorbs the many-to-one romanization variants a learner will plausibly type
(``aa`` for ``a``, ``ee`` for ``i``, ``oo`` for ``u``, ``v`` for ``w``, the
silent terminal ``a``), collapsing them to one canonical romanized form so a
forgiving grader can accept them.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence


def levenshtein(a: str, b: str) -> int:
    """Edit distance (insert/delete/substitute) between two strings."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost))
        previous = current
    return previous[-1]


def strip_accents(text: str) -> str:
    """Drop combining marks. For Devanagari this normalises optional nukta/etc.,
    and for romanized text it strips any diacritics a learner might add."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def build_replacements(mapping: Mapping[str, Sequence[str]]) -> list[tuple[str, str]]:
    """Compile a transliteration map into longest-first (sequence → canonical) pairs.

    For each entry ``char: [seq0, seq1, ...]`` the *canonical* form is ``seq0``
    (the first listed). The special char itself and every listed sequence all
    canonicalise to ``seq0``, so any accepted spelling collapses to one form.

    First definition wins on collision (deterministic), so a sequence shared by
    two chars resolves stably.
    """
    replacements: dict[str, str] = {}
    for char, accepted in mapping.items():
        canonical = accepted[0] if accepted else char
        replacements.setdefault(char, canonical)
        for sequence in accepted:
            replacements.setdefault(sequence, canonical)
    # Longest sequences first so e.g. "aa" matches before "a".
    return sorted(replacements.items(), key=lambda kv: len(kv[0]), reverse=True)


def transliterate(text: str, replacements: Sequence[tuple[str, str]]) -> str:
    """Apply compiled replacements left-to-right, longest match first."""
    if not replacements:
        return text
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        for sequence, canonical in replacements:
            if sequence and text.startswith(sequence, i):
                out.append(canonical)
                i += len(sequence)
                break
        else:
            out.append(text[i])
            i += 1
    return "".join(out)
