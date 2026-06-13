"""Build a full :class:`ConjugationTable` for a single (verb, tense-mood).

The engine behind the conjugation-table completion drill. A decoupled sibling of
:class:`~konjugaton.engine.generator.ExerciseGenerator`: where the generator
samples one cloze from the whole space, this enumerates the canonical German
pronoun paradigm of one verb in one tense-mood and packages each row as a
contiguous-verb-complex PRODUCTION :class:`~konjugaton.domain.item.Item`. Grading,
IRT and state-recording are reused verbatim.

The paradigm is tense-mood dependent: finite tenses take the six standard pronouns
(ich/du/er/wir/ihr/sie); the **Imperativ** inflects in the 2nd person only, so its
table is the three addressees (du/ihr/Sie).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from konjugaton.domain import (
    Agreement,
    ConjugationCell,
    ConjugationTable,
    Coordinate,
    Item,
    KnowledgeType,
    Number,
    Person,
    Polarity,
    Register,
    TenseMood,
    Voice,
)
from konjugaton.engine import render
from konjugaton.engine.generator import seed_irt
from konjugaton.engine.labels import tense_of

if TYPE_CHECKING:
    from konjugaton.data import Catalog
    from konjugaton.engine.conjugator import Conjugator

#: The six standard pronouns, in textbook order, for every finite tense-mood.
_STANDARD_PARADIGM: tuple[Agreement, ...] = (
    Agreement(Person.P1, Number.SINGULAR, Register.NEUTRAL),  # ich
    Agreement(Person.P2, Number.SINGULAR, Register.DU),  # du
    Agreement(Person.P3, Number.SINGULAR, Register.NEUTRAL),  # er/sie/es
    Agreement(Person.P1, Number.PLURAL, Register.NEUTRAL),  # wir
    Agreement(Person.P2, Number.PLURAL, Register.IHR),  # ihr
    Agreement(Person.P3, Number.PLURAL, Register.NEUTRAL),  # sie
)

#: The Imperativ addresses only du / ihr / Sie.
_IMPERATIVE_PARADIGM: tuple[Agreement, ...] = (
    Agreement(Person.P2, Number.SINGULAR, Register.DU),  # du
    Agreement(Person.P2, Number.PLURAL, Register.IHR),  # ihr
    Agreement(Person.P2, Number.PLURAL, Register.SIE),  # Sie
)

_IMPERATIVE_LABEL: dict[Register, str] = {
    Register.DU: "(du)",
    Register.IHR: "(ihr)",
    Register.SIE: "(Sie)",
}

#: The drill is always an unconditioned, affirmative, active production.
_TABLE_POLARITY = Polarity.AFFIRMATIVE
_TABLE_KNOWLEDGE = KnowledgeType.PRODUCTION
_TABLE_VOICE = Voice.AKTIV
_TABLE_CONTEXT = ""


def _paradigm_for(tense_mood: TenseMood) -> tuple[Agreement, ...]:
    return _IMPERATIVE_PARADIGM if tense_mood is TenseMood.IMPERATIV else _STANDARD_PARADIGM


def _subject_label(agreement: Agreement, tense_mood: TenseMood) -> str:
    """Left-column label: the pronoun, or the addressee in parens for the Imperativ."""
    if tense_mood is TenseMood.IMPERATIV:
        return _IMPERATIVE_LABEL[agreement.register]
    return render.subject_pronoun(agreement)


def build_conjugation_table(
    catalog: Catalog, conjugator: Conjugator, lemma: str, tense_mood: TenseMood
) -> ConjugationTable:
    """Realize the canonical paradigm of ``lemma`` in ``tense_mood`` as gradable cells.

    Raises :class:`KeyError` for an unknown lemma. Every supported tense-mood is
    realizable for every verb (``conjugator.can_conjugate`` is total), so callers
    need not pre-gate.
    """
    verb = catalog.verb(lemma)
    cells: list[ConjugationCell] = []
    for agreement in _paradigm_for(tense_mood):
        form = conjugator.conjugate(verb, tense_mood, agreement)
        answer = render.predicate(form, tense_mood, _TABLE_POLARITY, agreement.register)
        coordinate = Coordinate(
            lemma=lemma,
            tense_mood=tense_mood,
            person=agreement.person,
            number=agreement.number,
            register=agreement.register,
            polarity=_TABLE_POLARITY,
            knowledge=_TABLE_KNOWLEDGE,
            context=_TABLE_CONTEXT,
            voice=_TABLE_VOICE,
        )
        subject = _subject_label(agreement, tense_mood)
        full_sentence = (
            answer
            if tense_mood is TenseMood.IMPERATIV
            else f"{render.subject_pronoun(agreement)} {answer}"
        )
        item = Item(
            coordinate=coordinate,
            skill=coordinate.skill(verb.verb_class),
            prompt=subject,
            answer=answer,
            irt=seed_irt(verb.verb_class, coordinate, n_choices=0),
            accepted=(answer,),
            lemma_hint=lemma,
            task=f"{tense_of(tense_mood)} · {subject}",
            full_sentence=full_sentence,
            metadata={"translation": verb.translation},
        )
        cells.append(ConjugationCell(agreement=agreement, subject=subject, item=item))

    return ConjugationTable(
        lemma=lemma,
        translation=verb.translation,
        tense_mood=tense_mood,
        tense_label=tense_of(tense_mood),
        cells=tuple(cells),
    )
