"""Pure domain: entities, value objects and the combinatorial vocabulary.

This package imports nothing outside the standard library. It is the stable
core every other layer depends on, and depends on no other layer in return.
"""

from __future__ import annotations

from konjugaton.domain.agreement import Agreement
from konjugaton.domain.conjugation import ConjugatedForm
from konjugaton.domain.conjugation_table import ConjugationCell, ConjugationTable
from konjugaton.domain.context import SemanticContext
from konjugaton.domain.enums import (
    SUBJECT_PRONOUN,
    Auxiliary,
    KnowledgeType,
    Number,
    Person,
    Polarity,
    Register,
    TenseMood,
    VerbClass,
    Voice,
)
from konjugaton.domain.item import IrtParameters, Item
from konjugaton.domain.tables import EndingTables
from konjugaton.domain.taxonomy import Coordinate, Skill
from konjugaton.domain.verb import ConjugationData, Verb

__all__ = [
    "SUBJECT_PRONOUN",
    "Agreement",
    "Auxiliary",
    "ConjugatedForm",
    "ConjugationCell",
    "ConjugationData",
    "ConjugationTable",
    "Coordinate",
    "EndingTables",
    "IrtParameters",
    "Item",
    "KnowledgeType",
    "Number",
    "Person",
    "Polarity",
    "Register",
    "SemanticContext",
    "Skill",
    "TenseMood",
    "Verb",
    "VerbClass",
    "Voice",
]
