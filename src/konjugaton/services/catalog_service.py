"""Application service exposing the catalog and combinatorial space to the UI.

Wires together the data catalog, the conjugator and the permutation space, and
answers the "how big / what axes" questions the CLI's ``catalog`` command needs.
"""

from __future__ import annotations

from dataclasses import dataclass

from konjugaton.data import Catalog, load_catalog
from konjugaton.domain import Number, Person, Polarity, Register, Voice
from konjugaton.engine import (
    IMPLEMENTED_KNOWLEDGE,
    AxisSelection,
    Conjugator,
    PermutationSpace,
    supported_tense_moods,
)
from konjugaton.engine.labels import TENSE_LABEL
from konjugaton.engine.permutations import all_agreements


@dataclass(frozen=True, slots=True)
class AxisInfo:
    name: str
    size: int
    values: tuple[str, ...]


class CatalogService:
    """Read-only facade over reference data and the permutation space."""

    def __init__(self, catalog: Catalog, conjugator: Conjugator, space: PermutationSpace) -> None:
        self._catalog = catalog
        self._conjugator = conjugator
        self._space = space

    @classmethod
    def default(cls) -> CatalogService:
        catalog = load_catalog()
        conjugator = Conjugator(catalog.endings, dict(catalog.verbs))
        space = PermutationSpace(catalog, conjugator)
        return cls(catalog, conjugator, space)

    @property
    def catalog(self) -> Catalog:
        return self._catalog

    @property
    def space(self) -> PermutationSpace:
        return self._space

    @property
    def conjugator(self) -> Conjugator:
        return self._conjugator

    def total_space_size(self, selection: AxisSelection | None = None) -> int:
        return self._space.count(selection)

    def axes(self) -> list[AxisInfo]:
        tenses = supported_tense_moods()
        legal_agr = all_agreements()
        return [
            AxisInfo("verb", len(self._catalog.lemmas), tuple(self._catalog.lemmas)),
            AxisInfo("tense-mood", len(tenses), tuple(TENSE_LABEL[t] for t in tenses)),
            AxisInfo("person", len(tuple(Person)), tuple(p.value for p in Person)),
            AxisInfo("number", len(tuple(Number)), tuple(n.value for n in Number)),
            AxisInfo("register", len(tuple(Register)), tuple(r.value for r in Register)),
            # The legal agreement bundles are the realizable (person, number,
            # register) triples (no "1st-person Sie", etc.) — German has no gender.
            AxisInfo(
                "agreement (legal bundles)",
                len(legal_agr),
                tuple(a.key for a in legal_agr),
            ),
            AxisInfo("voice", len(tuple(Voice)), tuple(v.value for v in Voice)),
            AxisInfo("polarity", len(tuple(Polarity)), tuple(p.value for p in Polarity)),
            AxisInfo(
                "knowledge",
                len(IMPLEMENTED_KNOWLEDGE),
                tuple(k.value for k in IMPLEMENTED_KNOWLEDGE),
            ),
            AxisInfo(
                "context",
                len(self._catalog.context_ids),
                tuple(self._catalog.context_ids),
            ),
        ]
