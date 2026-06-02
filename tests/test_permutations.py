"""The combinatorial space: sizing, filtering, and agreement/voice legality."""

from __future__ import annotations

from konjugaton.data import load_catalog
from konjugaton.domain import Person, Register, TenseMood, Voice
from konjugaton.engine import AxisSelection, Conjugator, PermutationSpace
from konjugaton.engine.permutations import all_agreements


def _space() -> PermutationSpace:
    catalog = load_catalog()
    return PermutationSpace(catalog, Conjugator(catalog.endings, dict(catalog.verbs)))


def test_space_is_counted_exactly() -> None:
    space = _space()
    n = space.count()
    assert n == 41_660, f"space size changed: {n}"
    assert space.count() == sum(1 for _ in space.iter_coordinates())


def test_tense_filter_restricts_axis() -> None:
    space = _space()
    sel = AxisSelection(tense_moods=(TenseMood.FUTUR1,))
    assert {c.tense_mood for c in space.iter_coordinates(sel)} == {TenseMood.FUTUR1}


def test_no_illegal_agreement_bundles() -> None:
    # German has no gender; the legal triples never pair 1st person with Sie, etc.
    for agr in all_agreements():
        if agr.person is Person.P1:
            assert agr.register is Register.NEUTRAL
        if agr.register in (Register.DU, Register.IHR):
            assert agr.person is Person.P2
    assert len(all_agreements()) == 7


def test_imperative_is_second_person_only() -> None:
    space = _space()
    sel = AxisSelection(tense_moods=(TenseMood.IMPERATIV,))
    assert {c.person for c in space.iter_coordinates(sel)} == {Person.P2}


def test_passive_is_transitive_only() -> None:
    catalog = load_catalog()
    space = PermutationSpace(catalog, Conjugator(catalog.endings, dict(catalog.verbs)))
    lemmas = {c.lemma for c in space.iter_coordinates(AxisSelection(voices=(Voice.PASSIV,)))}
    for lemma in lemmas:
        assert catalog.verb(lemma).transitive, lemma


def test_aktiv_plus_passiv_is_whole_and_aktiv_dominates() -> None:
    space = _space()
    aktiv = space.count(AxisSelection(voices=(Voice.AKTIV,)))
    passiv = space.count(AxisSelection(voices=(Voice.PASSIV,)))
    assert aktiv + passiv == 41_660
    assert aktiv > passiv  # passive is transitive-only and indicative-only
