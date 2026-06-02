"""Pure text utilities: edit distance and transliteration folding."""

from __future__ import annotations

from konjugaton.textutils import build_replacements, levenshtein, strip_accents, transliterate


def test_levenshtein() -> None:
    assert levenshtein("karta", "karta") == 0
    assert levenshtein("karta", "kaarta") == 1
    assert levenshtein("", "abc") == 3
    assert levenshtein("करता", "करती") == 1  # works on Devanagari code points


def test_strip_accents() -> None:
    assert strip_accents("ā") == "a"
    assert strip_accents("ṭ") == "t"


def test_transliterate_folds_romanization_variants() -> None:
    # "aa" and "a" both collapse to canonical "a".
    repl = build_replacements({"a": ["a", "aa"]})
    assert transliterate("kaarta", repl) == "karta"
    assert transliterate("karta", repl) == "karta"


def test_transliterate_longest_match_first() -> None:
    repl = build_replacements({"i": ["i", "ee"]})  # ee → i
    assert transliterate("keejiye", repl) == "kijiye"
    assert transliterate("kijiye", repl) == "kijiye"
