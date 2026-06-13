"""Application service for the conjugation-table completion drill.

Decoupled from :class:`~konjugaton.services.practice.PracticeService` (the
space-sampling session builder): this service answers a narrower question —
"give me the full paradigm of *this* verb in *this* tense-mood, and grade each
cell". It reuses the catalog, conjugator and the configured :class:`Grader`, so
table practice grades and records exactly like a normal drill.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from konjugaton.engine import build_conjugation_table, supported_tense_moods
from konjugaton.services.catalog_service import CatalogService
from konjugaton.services.grading import GradedResponse, Grader
from konjugaton.settings.models import GradingSettings

if TYPE_CHECKING:
    from konjugaton.data import Catalog
    from konjugaton.domain import ConjugationTable, Item, TenseMood, Verb
    from konjugaton.settings.models import Settings


class ConjugationTableService:
    """Build and grade single-verb conjugation tables."""

    def __init__(self, catalog_service: CatalogService, grader: Grader) -> None:
        self._catalog_service = catalog_service
        self._grader = grader

    @classmethod
    def default(cls, *, settings: Settings | None = None) -> ConjugationTableService:
        grading = settings.grading if settings is not None else GradingSettings()
        return cls(CatalogService.default(), Grader(grading))

    @property
    def grader(self) -> Grader:
        return self._grader

    @property
    def catalog(self) -> Catalog:
        return self._catalog_service.catalog

    # -- catalog queries (for menus / pickers) ------------------------------

    def verbs(self) -> list[Verb]:
        """Every verb, most frequent first — the verb picker's order."""
        return sorted(
            self._catalog_service.catalog.verbs.values(), key=lambda v: v.frequency_rank
        )

    def available_tense_moods(self, lemma: str) -> list[TenseMood]:
        """The tense-moods this verb can be conjugated in (every supported one)."""
        verb = self._catalog_service.catalog.verb(lemma)
        conjugator = self._catalog_service.conjugator
        return [tm for tm in supported_tense_moods() if conjugator.can_conjugate(verb, tm)]

    # -- table building + grading -------------------------------------------

    def build_table(self, lemma: str, tense_mood: TenseMood) -> ConjugationTable:
        """The full paradigm of ``lemma`` in ``tense_mood`` as gradable cells."""
        return build_conjugation_table(
            self._catalog_service.catalog,
            self._catalog_service.conjugator,
            lemma,
            tense_mood,
        )

    def grade(self, item: Item, given: str) -> GradedResponse:
        """Grade one cell's response (delegates to the configured Grader)."""
        return self._grader.grade(item, given)
