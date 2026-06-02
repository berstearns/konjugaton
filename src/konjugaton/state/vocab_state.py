"""The learner model.

Two layers, exactly as scoped:

1. **Now** — ``scores``: the ``vocab -> knowledge-type -> score`` map.
2. **IRT** — ``abilities``: a latent ability theta per :class:`Skill`, updated
   online from each response via the 3PL model.

A future third layer (knowledge graph) consumes both — see
:mod:`konjugaton.state.graph`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from konjugaton.analytics import irt
from konjugaton.domain import KnowledgeType
from konjugaton.state.scoring import ScoreCell

if TYPE_CHECKING:
    from konjugaton.domain import Item, Skill


@dataclass(slots=True)
class VocabState:
    """Mutable learner state, serialisable to JSON."""

    #: lemma -> knowledge-type -> score cell
    scores: dict[str, dict[KnowledgeType, ScoreCell]] = field(default_factory=dict)
    #: Skill.key -> IRT ability estimate (theta)
    abilities: dict[str, float] = field(default_factory=dict)

    def cell(self, lemma: str, knowledge: KnowledgeType) -> ScoreCell:
        """Get (creating if absent) the score cell for a (lemma, knowledge)."""
        knowledge_map = self.scores.setdefault(lemma, {})
        return knowledge_map.setdefault(knowledge, ScoreCell())

    def ability(self, skill: Skill) -> float:
        """Current ability estimate for a skill (0.0 if never practised)."""
        return self.abilities.get(skill.key, 0.0)

    def record(self, item: Item, *, correct: bool, timestamp: str) -> None:
        """Fold one graded response into both the score map and the ability."""
        self.cell(item.coordinate.lemma, item.coordinate.knowledge).register(
            correct=correct, timestamp=timestamp
        )
        theta = self.ability(item.skill)
        self.abilities[item.skill.key] = irt.update_ability(theta, item.irt, correct)

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "scores": {
                lemma: {k.value: cell.to_dict() for k, cell in kmap.items()}
                for lemma, kmap in self.scores.items()
            },
            "abilities": dict(self.abilities),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VocabState:
        scores: dict[str, dict[KnowledgeType, ScoreCell]] = {}
        for lemma, kmap in data.get("scores", {}).items():
            scores[lemma] = {
                KnowledgeType(k): ScoreCell.from_dict(cell) for k, cell in kmap.items()
            }
        abilities = {k: float(v) for k, v in data.get("abilities", {}).items()}
        return cls(scores=scores, abilities=abilities)
