"""The combinatorial axes of the practice space, as closed enumerations.

German is combinatorially rich in a different way than Hindi: the verb does **not**
agree in gender and there is only **one script**, but it splits weak/strong/mixed
conjugations (ablaut: singen→sang→gesungen), the **haben/sein** auxiliary in the
perfect tenses, **separable prefixes** (aufstehen → ich stehe auf), the
**du/ihr/Sie** register, the Konjunktiv I/II moods and the werden-passive.

Each enum is a :class:`~enum.StrEnum`, so values serialize transparently to
JSON/YAML and read naturally in logs and the CLI.
"""

from __future__ import annotations

from enum import StrEnum


class TenseMood(StrEnum):
    """Tense-Mood — the German verb's primary axis (Indikativ + Konjunktiv + Imperativ)."""

    PRAESENS = "praesens"  # ich mache / ich gehe
    PRAETERITUM = "praeteritum"  # ich machte / ich ging
    PERFEKT = "perfekt"  # ich habe gemacht / ich bin gegangen
    PLUSQUAMPERFEKT = "plusquamperfekt"  # ich hatte gemacht / ich war gegangen
    FUTUR1 = "futur1"  # ich werde machen
    FUTUR2 = "futur2"  # ich werde gemacht haben
    KONJUNKTIV1 = "konjunktiv1"  # er mache (reported speech)
    KONJUNKTIV2 = "konjunktiv2"  # er ginge / er würde machen
    IMPERATIV = "imperativ"  # mach! / macht! / machen Sie!


class Person(StrEnum):
    """Grammatical person (1/2/3). Number and register are separate axes."""

    P1 = "1"  # ich / wir
    P2 = "2"  # du / ihr / Sie
    P3 = "3"  # er,sie,es / sie


class Number(StrEnum):
    """Grammatical number. The German verb agrees in number (not gender)."""

    SINGULAR = "sg"
    PLURAL = "pl"


class Register(StrEnum):
    """Politeness register — the German analogue of Hindi's honorific.

    * NEUTRAL — 1st person (ich/wir) and plain 3rd person (er/sie/es, sie).
    * DU — informal singular addressee (2sg verb form).
    * IHR — informal plural addressee (2pl verb form).
    * SIE — formal addressee; takes the **3rd-plural** verb form (Sie machen).
    """

    NEUTRAL = "neutral"
    DU = "du"
    IHR = "ihr"
    SIE = "sie_formal"


class Voice(StrEnum):
    """Aktiv vs the werden-Passiv (es wird gemacht). Passive ⇒ transitive verbs only."""

    AKTIV = "aktiv"
    PASSIV = "passiv"


class VerbClass(StrEnum):
    """Conjugation class.

    * WEAK — regular: stem+te (Prät), ge+stem+t (PII).
    * STRONG — ablaut: stored Präteritum/Partizip stems (ging/gegangen), often a
      Präsens 2sg/3sg stem change (du gibst, er sieht).
    * MIXED — weak endings on an ablaut stem (denken→dachte→gedacht).
    * IRREGULAR — sein/haben/werden: fully stored forms (too suppletive to derive).
    """

    WEAK = "weak"
    STRONG = "strong"
    MIXED = "mixed"
    IRREGULAR = "irregular"


class Auxiliary(StrEnum):
    """The perfect-tense auxiliary a verb selects (a per-verb property)."""

    HABEN = "haben"
    SEIN = "sein"


class Polarity(StrEnum):
    """Affirmative vs negated clause. German negates with the particle ``nicht``
    (placed after the finite verb); ``kein`` negates nouns (not drilled in v1)."""

    AFFIRMATIVE = "affirmative"
    NEGATIVE = "negative"


class KnowledgeType(StrEnum):
    """What *kind* of knowing an item probes. German is single-script, so there is
    no transliteration type (unlike Hindi)."""

    PRODUCTION = "production"  # write the correct conjugated form (cloze)
    RECOGNITION = "recognition"  # choose the correct form (multiple choice)
    MEANING = "meaning"  # map form <-> meaning (planned)
    USAGE = "usage"  # choose the right form in context (planned)


# --- Display helpers -------------------------------------------------------

#: Subject pronoun per (person, number, register). The register selects the
#: 2nd/3rd-person pronoun; illegal cells (e.g. "1st-person Sie") have no entry,
#: so this map IS the legal-bundle gate.
SUBJECT_PRONOUN: dict[tuple[Person, Number, Register], str] = {
    (Person.P1, Number.SINGULAR, Register.NEUTRAL): "ich",
    (Person.P1, Number.PLURAL, Register.NEUTRAL): "wir",
    (Person.P2, Number.SINGULAR, Register.DU): "du",
    (Person.P2, Number.PLURAL, Register.IHR): "ihr",
    (Person.P2, Number.PLURAL, Register.SIE): "Sie",
    (Person.P3, Number.SINGULAR, Register.NEUTRAL): "er",
    (Person.P3, Number.PLURAL, Register.NEUTRAL): "sie",
}
