"""Coordinates in the practice space, and the skills they load onto.

* :class:`Coordinate` — the finest point the generator targets. One exercise is
  built from exactly one coordinate. The full Cartesian product is the
  combinatorial space: lemma × tense-mood × person × number × register × voice ×
  polarity × knowledge × context.

* :class:`Skill` — a coarser grouping for state aggregation and the IRT latent
  dimension: ``(verb_class, tense_mood, knowledge)``. Register, voice, polarity
  and the specific lemma modulate item *difficulty* (an IRT ``b`` shift), not
  *which* ability is exercised — keeping the learner model compact.
"""

from __future__ import annotations

from dataclasses import dataclass

from konjugaton.domain.enums import (
    KnowledgeType,
    Number,
    Person,
    Polarity,
    Register,
    TenseMood,
    VerbClass,
    Voice,
)


@dataclass(frozen=True, slots=True)
class Coordinate:
    """One fully-specified point in the combinatorial exercise space."""

    lemma: str
    tense_mood: TenseMood
    person: Person
    number: Number
    register: Register
    polarity: Polarity
    knowledge: KnowledgeType
    context: str
    voice: Voice = Voice.AKTIV

    def skill(self, verb_class: VerbClass) -> Skill:
        """Project onto the coarse IRT skill (register/voice/polarity/lemma abstracted)."""
        return Skill(verb_class=verb_class, tense_mood=self.tense_mood, knowledge=self.knowledge)


@dataclass(frozen=True, slots=True)
class Skill:
    """A latent ability dimension: (verb_class, tense_mood, knowledge)."""

    verb_class: VerbClass
    tense_mood: TenseMood
    knowledge: KnowledgeType

    @property
    def key(self) -> str:
        return f"{self.verb_class.value}|{self.tense_mood.value}|{self.knowledge.value}"

    def __str__(self) -> str:
        return f"{self.verb_class.value} {self.tense_mood.value} [{self.knowledge.value}]"
