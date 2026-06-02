"""Human-facing labels for the grammatical axes.

Single source of truth so the generator (building ``Item.task``) and the UIs
render identical strings — and so the determinacy check (the task must encode every
answer-determining axis) stays in lock-step with what is displayed. The task a
learner sees for a cloze must pin down every axis the answer depends on:
tense-mood, person, number, register, voice, polarity.
"""

from __future__ import annotations

from konjugaton.domain import (
    KnowledgeType,
    Number,
    Person,
    Polarity,
    Register,
    TenseMood,
    Voice,
)

TENSE_LABEL: dict[TenseMood, str] = {
    TenseMood.PRAESENS: "Präsens",
    TenseMood.PRAETERITUM: "Präteritum",
    TenseMood.PERFEKT: "Perfekt",
    TenseMood.PLUSQUAMPERFEKT: "Plusquamperfekt",
    TenseMood.FUTUR1: "Futur I",
    TenseMood.FUTUR2: "Futur II",
    TenseMood.KONJUNKTIV1: "Konjunktiv I",
    TenseMood.KONJUNKTIV2: "Konjunktiv II",
    TenseMood.IMPERATIV: "Imperativ",
}
PERSON_LABEL: dict[Person, str] = {Person.P1: "1st", Person.P2: "2nd", Person.P3: "3rd"}
NUMBER_LABEL: dict[Number, str] = {Number.SINGULAR: "sg", Number.PLURAL: "pl"}
REGISTER_LABEL: dict[Register, str] = {
    Register.NEUTRAL: "neutral",
    Register.DU: "du",
    Register.IHR: "ihr",
    Register.SIE: "Sie",
}
VOICE_LABEL: dict[Voice, str] = {Voice.AKTIV: "Aktiv", Voice.PASSIV: "Passiv"}
POLARITY_LABEL: dict[Polarity, str] = {
    Polarity.AFFIRMATIVE: "affirmative",
    Polarity.NEGATIVE: "negative",
}
KNOWLEDGE_LABEL: dict[KnowledgeType, str] = {
    KnowledgeType.PRODUCTION: "production",
    KnowledgeType.RECOGNITION: "recognition",
    KnowledgeType.MEANING: "meaning",
    KnowledgeType.USAGE: "usage",
}


def tense_of(tm: TenseMood) -> str:
    return TENSE_LABEL[tm]


def person_of(person: Person) -> str:
    return PERSON_LABEL[person]


def number_of(number: Number) -> str:
    return NUMBER_LABEL[number]


def register_of(register: Register) -> str:
    return REGISTER_LABEL[register]


def voice_of(voice: Voice) -> str:
    return VOICE_LABEL[voice]


def polarity_of(polarity: Polarity) -> str:
    return POLARITY_LABEL[polarity]
