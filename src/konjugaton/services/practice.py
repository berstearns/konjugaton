"""Application service for running practice sessions and grading answers.

Grading itself lives in :mod:`konjugaton.services.grading` (config-driven). This
service samples the space, generates and orders items, and delegates grading to
a :class:`Grader` built from the user's settings.
"""

from __future__ import annotations

import random
from collections import defaultdict, deque
from enum import StrEnum
from typing import TYPE_CHECKING

from konjugaton.analytics import irt
from konjugaton.engine import ExerciseGenerator
from konjugaton.services.catalog_service import CatalogService
from konjugaton.services.grading import GradedResponse, Grader
from konjugaton.settings.models import GradingSettings, Settings

if TYPE_CHECKING:
    from konjugaton.domain import Coordinate, Item
    from konjugaton.engine import AxisSelection
    from konjugaton.state import VocabState

#: Safety bound on how many coordinates the sampler will scan.
_CANDIDATE_SCAN_CAP = 200_000


class SessionOrder(StrEnum):
    ADAPTIVE = "adaptive"  # most informative first (needs state)
    EASY_FIRST = "easy-first"
    HARD_FIRST = "hard-first"
    RANDOM = "random"


class PracticeService:
    """Build sessions of items and grade learner responses."""

    def __init__(
        self,
        catalog_service: CatalogService,
        generator: ExerciseGenerator,
        rng: random.Random,
        grader: Grader,
    ) -> None:
        self._catalog_service = catalog_service
        self._generator = generator
        self._rng = rng
        self._grader = grader

    @classmethod
    def default(
        cls, *, seed: int | None = None, settings: Settings | None = None
    ) -> PracticeService:
        catalog_service = CatalogService.default()
        generator = ExerciseGenerator(catalog_service.catalog, catalog_service.conjugator)
        grading = settings.grading if settings is not None else GradingSettings()
        return cls(catalog_service, generator, random.Random(seed), Grader(grading))

    @property
    def catalog_service(self) -> CatalogService:
        return self._catalog_service

    @property
    def grader(self) -> Grader:
        return self._grader

    # -- session building ---------------------------------------------------

    def build_session(
        self,
        selection: AxisSelection,
        count: int,
        *,
        state: VocabState | None = None,
        order: SessionOrder = SessionOrder.ADAPTIVE,
    ) -> list[Item]:
        """Sample coordinates, generate items, and order them for delivery."""
        candidates = self._reservoir_sample(selection, max(count * 6, count))
        items = [self._generator.generate(coord, self._rng) for coord in candidates]
        return self._order(items, state, order)[:count]

    def _reservoir_sample(self, selection: AxisSelection, k: int) -> list[Coordinate]:
        reservoir: list[Coordinate] = []
        for i, coord in enumerate(self._catalog_service.space.iter_coordinates(selection)):
            if i < k:
                reservoir.append(coord)
            else:
                j = self._rng.randint(0, i)
                if j < k:
                    reservoir[j] = coord
            if i + 1 >= _CANDIDATE_SCAN_CAP:
                break
        return reservoir

    def _order(
        self, items: list[Item], state: VocabState | None, order: SessionOrder
    ) -> list[Item]:
        if order is SessionOrder.RANDOM:
            self._rng.shuffle(items)
            return items
        if order is SessionOrder.HARD_FIRST:
            return sorted(items, key=lambda it: it.irt.difficulty, reverse=True)
        if order is SessionOrder.ADAPTIVE and state is not None:
            return sorted(
                items,
                key=lambda it: irt.information(state.ability(it.skill), it.irt),
                reverse=True,
            )
        # EASY_FIRST, or ADAPTIVE without state to inform it.
        return sorted(items, key=lambda it: it.irt.difficulty)

    def build_assessment(self, selection: AxisSelection, count: int) -> list[Item]:
        """Breadth-guided: cover as many distinct skills as possible (round-robin)."""
        catalog = self._catalog_service.catalog
        buckets: dict[str, deque[Coordinate]] = defaultdict(deque)
        for coord in self._catalog_service.space.iter_coordinates(selection):
            verb_class = catalog.verb(coord.lemma).verb_class
            buckets[coord.skill(verb_class).key].append(coord)
        keys = list(buckets)
        self._rng.shuffle(keys)
        active = [buckets[k] for k in keys]
        picked: list[Coordinate] = []
        while active and len(picked) < count:
            for q in active:
                if q:
                    picked.append(q.popleft())
                    if len(picked) >= count:
                        break
            active = [q for q in active if q]
        return [self._generator.generate(c, self._rng) for c in picked]

    # -- grading (delegated to the configured Grader) -----------------------

    def grade(self, item: Item, given: str) -> GradedResponse:
        return self._grader.grade(item, given)
