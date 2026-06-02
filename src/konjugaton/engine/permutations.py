"""Enumerate the combinatorial exercise space.

The space is the Cartesian product of the axes:

    lemma × tense-mood × person × number × register × voice × polarity
          × knowledge × context

filtered to the cells the conjugator can realize: the legal agreement bundles
(the imperative is 2nd-person only) and the legal voices (the werden-passive is
transitive-only and indicative-tense-only). The legal `(person, number, register)`
triples are read once from the pronoun table, so no ungrammatical bundle (e.g.
"1st-person Sie") is ever emitted.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING

from konjugaton.domain import (
    SUBJECT_PRONOUN,
    Agreement,
    Coordinate,
    KnowledgeType,
    Number,
    Person,
    Polarity,
    Register,
    TenseMood,
    Voice,
)
from konjugaton.engine.conjugator import supported_tense_moods

if TYPE_CHECKING:
    from konjugaton.data import Catalog
    from konjugaton.engine.conjugator import Conjugator

#: Knowledge types with a generator implementation today.
IMPLEMENTED_KNOWLEDGE: tuple[KnowledgeType, ...] = (
    KnowledgeType.PRODUCTION,
    KnowledgeType.RECOGNITION,
)

ALL_POLARITIES: tuple[Polarity, ...] = tuple(Polarity)
ALL_VOICES: tuple[Voice, ...] = tuple(Voice)

#: The legal (person, number, register) triples — the closed set German licenses.
_LEGAL_PNR: tuple[tuple[Person, Number, Register], ...] = tuple(SUBJECT_PRONOUN)


def all_agreements(
    *,
    persons: tuple[Person, ...] = (),
    numbers: tuple[Number, ...] = (),
    registers: tuple[Register, ...] = (),
) -> list[Agreement]:
    """Every legal agreement bundle, optionally narrowed by each sub-axis."""
    out: list[Agreement] = []
    for person, number, register in _LEGAL_PNR:
        if persons and person not in persons:
            continue
        if numbers and number not in numbers:
            continue
        if registers and register not in registers:
            continue
        out.append(Agreement(person, number, register))
    return out


@dataclass(frozen=True, slots=True)
class AxisSelection:
    """A narrowing filter over each axis. Empty tuple means 'all'."""

    lemmas: tuple[str, ...] = ()
    tense_moods: tuple[TenseMood, ...] = ()
    persons: tuple[Person, ...] = ()
    numbers: tuple[Number, ...] = ()
    registers: tuple[Register, ...] = ()
    voices: tuple[Voice, ...] = ()
    polarities: tuple[Polarity, ...] = ()
    knowledge: tuple[KnowledgeType, ...] = ()
    contexts: tuple[str, ...] = ()


class PermutationSpace:
    """Queryable view over the realizable exercise coordinates."""

    def __init__(self, catalog: Catalog, conjugator: Conjugator) -> None:
        self._catalog = catalog
        self._conjugator = conjugator

    def _tenses(self, sel: AxisSelection) -> list[TenseMood]:
        tenses = supported_tense_moods()
        if sel.tense_moods:
            tenses = [t for t in tenses if t in sel.tense_moods]
        return tenses

    def _lemmas(self, sel: AxisSelection) -> list[str]:
        return list(sel.lemmas) if sel.lemmas else self._catalog.lemmas

    def _contexts(self, sel: AxisSelection) -> list[str]:
        return list(sel.contexts) if sel.contexts else self._catalog.context_ids

    def _voices(self, sel: AxisSelection) -> tuple[Voice, ...]:
        return sel.voices or ALL_VOICES

    def _agreements(self, sel: AxisSelection) -> list[Agreement]:
        return all_agreements(persons=sel.persons, numbers=sel.numbers, registers=sel.registers)

    def iter_coordinates(self, sel: AxisSelection | None = None) -> Iterator[Coordinate]:
        sel = sel or AxisSelection()
        polarities = sel.polarities or ALL_POLARITIES
        knowledge = sel.knowledge or IMPLEMENTED_KNOWLEDGE
        contexts = self._contexts(sel)
        agreements = self._agreements(sel)

        for tm in self._tenses(sel):
            for voice in self._voices(sel):
                for lemma in self._lemmas(sel):
                    verb = self._catalog.verb(lemma)
                    if not self._conjugator.realizable_voice(verb, tm, voice):
                        continue
                    for agr in agreements:
                        if not self._conjugator.realizable_agreement(tm, agr):
                            continue
                        for polarity, know, context in product(polarities, knowledge, contexts):
                            yield Coordinate(
                                lemma=lemma,
                                tense_mood=tm,
                                person=agr.person,
                                number=agr.number,
                                register=agr.register,
                                polarity=polarity,
                                knowledge=know,
                                context=context,
                                voice=voice,
                            )

    def count(self, sel: AxisSelection | None = None) -> int:
        sel = sel or AxisSelection()
        n_polarities = len(sel.polarities or ALL_POLARITIES)
        n_knowledge = len(sel.knowledge or IMPLEMENTED_KNOWLEDGE)
        n_contexts = len(self._contexts(sel))
        per_cell = n_polarities * n_knowledge * n_contexts
        agreements = self._agreements(sel)
        lemmas = self._lemmas(sel)

        total = 0
        for tm in self._tenses(sel):
            realizable_agr = sum(
                1 for agr in agreements if self._conjugator.realizable_agreement(tm, agr)
            )
            if not realizable_agr:
                continue
            for voice in self._voices(sel):
                verbs_ok = sum(
                    1
                    for lemma in lemmas
                    if self._conjugator.realizable_voice(self._catalog.verb(lemma), tm, voice)
                )
                total += verbs_ok * realizable_agr * per_cell
        return total
