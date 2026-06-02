"""Ground-truth German conjugation tests.

These lock the hand-verified forms in verbs.yaml + endings.yaml. If a refactor of
the engine or an edit to the data breaks a form, it surfaces here, not in a
learner's face. Weak, strong, mixed, the separable prefix, sein/haben/werden, the
periphrastic tenses, the imperative and the werden-passive are all pinned.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from konjugaton.data import load_catalog
from konjugaton.domain import (
    Agreement,
    Number,
    Person,
    Polarity,
    Register,
    TenseMood,
    Verb,
    Voice,
)
from konjugaton.engine import Conjugator, render

T, P, N, R = TenseMood, Person, Number, Register


@pytest.fixture(scope="module")
def conjugator() -> Conjugator:
    catalog = load_catalog()
    return Conjugator(catalog.endings, dict(catalog.verbs))


@pytest.fixture(scope="module")
def verbs() -> Mapping[str, Verb]:
    return load_catalog().verbs


def _a(p: Person, n: Number, r: Register) -> Agreement:
    return Agreement(p, n, r)


ICH = _a(P.P1, N.SINGULAR, R.NEUTRAL)
DU = _a(P.P2, N.SINGULAR, R.DU)
ER = _a(P.P3, N.SINGULAR, R.NEUTRAL)
WIR = _a(P.P1, N.PLURAL, R.NEUTRAL)
IHR = _a(P.P2, N.PLURAL, R.IHR)
SIE = _a(P.P2, N.PLURAL, R.SIE)

# (lemma, tense, agreement, expected surface)
CASES: list[tuple[str, TenseMood, Agreement, str]] = [
    # weak präsens across the 6 slots
    ("machen", T.PRAESENS, ICH, "mache"),
    ("machen", T.PRAESENS, DU, "machst"),
    ("machen", T.PRAESENS, ER, "macht"),
    ("machen", T.PRAESENS, WIR, "machen"),
    ("machen", T.PRAESENS, IHR, "macht"),
    ("machen", T.PRAESENS, SIE, "machen"),
    # weak präteritum + perfekt
    ("machen", T.PRAETERITUM, DU, "machtest"),
    ("machen", T.PERFEKT, ER, "hat gemacht"),
    # epenthetic-e weak (arbeiten)
    ("arbeiten", T.PRAESENS, DU, "arbeitest"),
    ("arbeiten", T.PRAESENS, ER, "arbeitet"),
    ("arbeiten", T.PRAETERITUM, ICH, "arbeitete"),
    # strong: ablaut + sein-perfekt + präsens stem change
    ("gehen", T.PRAETERITUM, WIR, "gingen"),
    ("gehen", T.PERFEKT, ICH, "bin gegangen"),
    ("sehen", T.PRAESENS, DU, "siehst"),
    ("sehen", T.PRAESENS, ER, "sieht"),
    ("geben", T.PRAESENS, ER, "gibt"),
    ("fahren", T.PRAESENS, DU, "fährst"),
    ("fahren", T.PERFEKT, ICH, "bin gefahren"),
    ("essen", T.PRAESENS, DU, "isst"),
    # mixed
    ("denken", T.PRAETERITUM, ICH, "dachte"),
    ("denken", T.PERFEKT, ICH, "habe gedacht"),
    ("bringen", T.PERFEKT, ER, "hat gebracht"),
    # separable prefix: detaches in simple tenses, bound in PII
    ("aufstehen", T.PRAESENS, ICH, "stehe auf"),
    ("aufstehen", T.PERFEKT, ICH, "bin aufgestanden"),
    ("einkaufen", T.PRAESENS, ICH, "kaufe ein"),
    ("einkaufen", T.PERFEKT, ICH, "habe eingekauft"),
    # irregular auxiliaries
    ("sein", T.PRAESENS, DU, "bist"),
    ("sein", T.PRAETERITUM, ICH, "war"),
    ("sein", T.PERFEKT, ICH, "bin gewesen"),
    ("haben", T.PRAETERITUM, ICH, "hatte"),
    ("werden", T.PRAESENS, ER, "wird"),
    ("werden", T.PERFEKT, ICH, "bin geworden"),
    # futur + konjunktiv
    ("machen", T.FUTUR1, ICH, "werde machen"),
    ("machen", T.FUTUR2, ICH, "werde gemacht haben"),
    ("gehen", T.KONJUNKTIV2, ICH, "ginge"),
    ("machen", T.KONJUNKTIV2, ICH, "würde machen"),
    ("sein", T.KONJUNKTIV2, ER, "wäre"),
    ("haben", T.KONJUNKTIV2, ER, "hätte"),
    ("machen", T.KONJUNKTIV1, ER, "mache"),
    ("haben", T.KONJUNKTIV1, ER, "habe"),
]


@pytest.mark.parametrize(("lemma", "tense", "agr", "want"), CASES)
def test_forms(
    conjugator: Conjugator,
    verbs: Mapping[str, Verb],
    lemma: str,
    tense: TenseMood,
    agr: Agreement,
    want: str,
) -> None:
    got = conjugator.conjugate(verbs[lemma], tense, agr).surface
    assert got == want, f"{lemma}/{tense.value}/{agr.key}: {got!r} != {want!r}"


# (lemma, register, expected imperative predicate)
IMPERATIVES: list[tuple[str, Agreement, str]] = [
    ("machen", DU, "mach"),
    ("machen", IHR, "macht"),
    ("machen", SIE, "machen Sie"),
    ("geben", DU, "gib"),  # e→i stem change kept
    ("sehen", DU, "sieh"),
    ("fahren", DU, "fahr"),  # a→ä NOT applied in the imperative
    ("arbeiten", DU, "arbeite"),  # epenthetic e
    ("aufstehen", DU, "steh auf"),  # separable prefix detaches
    ("sein", DU, "sei"),
    ("sein", SIE, "seien Sie"),
]


@pytest.mark.parametrize(("lemma", "agr", "want"), IMPERATIVES)
def test_imperatives(
    conjugator: Conjugator, verbs: Mapping[str, Verb], lemma: str, agr: Agreement, want: str
) -> None:
    form = conjugator.conjugate(verbs[lemma], TenseMood.IMPERATIV, agr)
    got = render.predicate(form, TenseMood.IMPERATIV, Polarity.AFFIRMATIVE, agr.register)
    assert got == want, f"imp {lemma}/{agr.register.value}: {got!r} != {want!r}"


# (lemma, tense, expected passive surface, agr)
PASSIVES: list[tuple[str, TenseMood, str]] = [
    ("machen", T.PRAESENS, "wird gemacht"),
    ("machen", T.PRAETERITUM, "wurde gemacht"),
    ("machen", T.PERFEKT, "ist gemacht worden"),
    ("machen", T.FUTUR1, "wird gemacht werden"),
]


@pytest.mark.parametrize(("lemma", "tense", "want"), PASSIVES)
def test_passive(
    conjugator: Conjugator, verbs: Mapping[str, Verb], lemma: str, tense: TenseMood, want: str
) -> None:
    got = conjugator.conjugate_voice(verbs[lemma], tense, ER, Voice.PASSIV).surface
    assert got == want, f"passiv {lemma}/{tense.value}: {got!r} != {want!r}"


def test_negation_after_finite(conjugator: Conjugator, verbs: Mapping[str, Verb]) -> None:
    form = conjugator.conjugate(verbs["machen"], TenseMood.PERFEKT, ICH)
    assert render.predicate(form, TenseMood.PERFEKT, Polarity.NEGATIVE, R.NEUTRAL) == (
        "habe nicht gemacht"
    )
    sep = conjugator.conjugate(verbs["aufstehen"], TenseMood.PRAESENS, ICH)
    assert render.predicate(sep, TenseMood.PRAESENS, Polarity.NEGATIVE, R.NEUTRAL) == (
        "stehe nicht auf"
    )


def test_passive_gated_to_transitive(conjugator: Conjugator, verbs: Mapping[str, Verb]) -> None:
    assert not conjugator.realizable_voice(verbs["gehen"], TenseMood.PRAESENS, Voice.PASSIV)
    assert conjugator.realizable_voice(verbs["machen"], TenseMood.PRAESENS, Voice.PASSIV)


def test_imperative_is_second_person_only(conjugator: Conjugator) -> None:
    assert not conjugator.realizable_agreement(TenseMood.IMPERATIV, ICH)
    assert conjugator.realizable_agreement(TenseMood.IMPERATIV, DU)
