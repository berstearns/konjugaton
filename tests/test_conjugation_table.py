"""Conjugation-table completion mode: table building, grading, and the paradigm.

Locks the behaviour of the single-verb table drill (``ConjugationTableService`` +
``build_conjugation_table``): the cells are the verb's real paradigm in the
canonical pronoun order, each cell is a gradable PRODUCTION item, grading routes
through the configured Grader, and the Imperativ realizes only du/ihr/Sie.
"""

from __future__ import annotations

import pytest

from konjugaton.domain import KnowledgeType, Polarity, TenseMood, Voice
from konjugaton.services import ConjugationTableService, Grade


@pytest.fixture(scope="module")
def service() -> ConjugationTableService:
    return ConjugationTableService.default()


def test_haben_praesens_matches_the_known_paradigm(service: ConjugationTableService) -> None:
    table = service.build_table("haben", TenseMood.PRAESENS)
    assert table.lemma == "haben"
    assert table.tense_label == "Präsens"
    assert [c.subject for c in table.cells] == ["ich", "du", "er", "wir", "ihr", "sie"]
    assert [c.answer for c in table.cells] == ["habe", "hast", "hat", "haben", "habt", "haben"]


def test_perfekt_uses_the_correct_auxiliary(service: ConjugationTableService) -> None:
    # gehen selects sein → "ich bin gegangen"; machen selects haben → "ich habe gemacht".
    gehen = service.build_table("gehen", TenseMood.PERFEKT)
    assert gehen.cells[0].answer == "bin gegangen"
    assert gehen.cells[3].answer == "sind gegangen"
    machen = service.build_table("machen", TenseMood.PERFEKT)
    assert machen.cells[0].answer == "habe gemacht"


def test_imperativ_is_the_three_addressees(service: ConjugationTableService) -> None:
    table = service.build_table("machen", TenseMood.IMPERATIV)
    assert [c.subject for c in table.cells] == ["(du)", "(ihr)", "(Sie)"]
    assert [c.answer for c in table.cells] == ["mach", "macht", "machen Sie"]


def test_cells_are_production_items_over_the_same_tense_mood(
    service: ConjugationTableService,
) -> None:
    table = service.build_table("machen", TenseMood.PRAESENS)
    for cell in table.cells:
        coord = cell.item.coordinate
        assert coord.lemma == "machen"
        assert coord.tense_mood is TenseMood.PRAESENS
        assert coord.knowledge is KnowledgeType.PRODUCTION
        assert coord.polarity is Polarity.AFFIRMATIVE
        assert coord.voice is Voice.AKTIV
        assert cell.item.answer == cell.answer
        assert not cell.item.is_multiple_choice


def test_grade_accepts_correct_and_rejects_wrong(service: ConjugationTableService) -> None:
    table = service.build_table("haben", TenseMood.PRAESENS)
    du_hast = table.cells[1]
    assert service.grade(du_hast.item, "hast").grade is Grade.CORRECT
    assert service.grade(du_hast.item, "habst").grade is Grade.INCORRECT


def test_every_tense_mood_builds_a_full_table(service: ConjugationTableService) -> None:
    for tm in service.available_tense_moods("sein"):
        table = service.build_table("sein", tm)
        expected = 3 if tm is TenseMood.IMPERATIV else 6
        assert len(table.cells) == expected


def test_unknown_verb_raises(service: ConjugationTableService) -> None:
    with pytest.raises(KeyError):
        service.build_table("notaverb", TenseMood.PRAESENS)
