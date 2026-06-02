"""The :class:`Verb` aggregate and its conjugation data.

A verb carries just enough for the engine to *derive* every form. Weak verbs need
almost nothing — their stem follows from the lemma and every form is rule-derived.
Strong/mixed verbs supply the ablaut stems Hindi-style (Präteritum stem, Partizip
II, an optional Präsens 2sg/3sg stem change, a Konjunktiv II stem). The three
auxiliaries (sein/haben/werden) are too suppletive to derive and ship explicit
``irregular`` form maps.

Frozen dataclasses: pure data, cheaply hashable for the combinatorial engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from konjugaton.domain.enums import Auxiliary, VerbClass


@dataclass(frozen=True, slots=True)
class ConjugationData:
    """Stems/overrides that drive the conjugator. Weak verbs need none of it.

    * ``praesens_stem_23`` — strong Präsens 2sg/3sg stem change (geben→gib, sehen→sieh).
    * ``praeteritum_stem`` — strong (ging, sah) or mixed (dach, brach) past stem.
    * ``partizip2`` — Partizip II (strong/mixed/irregular); weak is derived (ge+stem+t).
      For separable verbs this is the *base* PII (gestanden); the prefix is prepended.
    * ``konjunktiv2_stem`` — strong/irregular K2 stem (ging→ginge, käm→käme, wär→wäre).
    * ``irregular`` — paradigm → slot → form maps for sein/haben/werden.
    """

    praesens_stem_23: str | None = None
    praeteritum_stem: str | None = None
    partizip2: str | None = None
    konjunktiv2_stem: str | None = None
    irregular: Mapping[str, Mapping[str, str]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Verb:
    """A verb lemma plus the metadata the engine and taxonomy need."""

    lemma: str  # infinitive, e.g. machen / aufstehen
    translation: str
    verb_class: VerbClass
    auxiliary: Auxiliary
    transitive: bool
    frequency_rank: int
    conjugation: ConjugationData
    separable_prefix: str | None = None
    family: str | None = None
    semantic_tags: tuple[str, ...] = ()

    @property
    def base_lemma(self) -> str:
        """The lemma with any separable prefix removed (aufstehen → stehen)."""
        p = self.separable_prefix
        if p and self.lemma.startswith(p):
            return self.lemma[len(p) :]
        return self.lemma

    @property
    def stem(self) -> str:
        """The conjugation stem: base lemma minus the -en / -n infinitive marker."""
        b = self.base_lemma
        if b.endswith("en"):
            return b[:-2]
        if b.endswith("n"):
            return b[:-1]
        return b

    def __str__(self) -> str:
        return self.lemma


__all__ = ["ConjugationData", "Verb"]
