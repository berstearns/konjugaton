"""EXPERIMENTAL — the knowledge-state graph (planned v2 of the learner model).

The flat ``vocab -> knowledge -> score`` map cannot express that mastering
*देना* should raise your prior on *लेना* (same द/ल-stem family), or that the
imperfective-participle rule transfers across every regular verb. A graph can:
nodes are vocab and skills, edges are typed relations (same-family, same-class,
semantic), and scores diffuse along edges.

This module builds such a graph from a :class:`VocabState` and supports a single
diffusion step. The propagation rule is intentionally simple and is the natural
place to plug a more principled model (e.g. a Bayesian knowledge graph) later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from konjugaton.domain import KnowledgeType

if TYPE_CHECKING:
    from konjugaton.data import Catalog
    from konjugaton.state.vocab_state import VocabState


class Relation(StrEnum):
    SAME_FAMILY = "same-family"
    SAME_CLASS = "same-class"
    SEMANTIC = "semantic"


@dataclass(slots=True)
class GraphNode:
    id: str
    kind: str  # "vocab" | "skill"
    score: float


@dataclass(frozen=True, slots=True)
class GraphEdge:
    src: str
    dst: str
    relation: Relation
    weight: float = 1.0


@dataclass(slots=True)
class KnowledgeGraph:
    """A score-bearing graph over vocab (and, later, skill) nodes."""

    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    @classmethod
    def from_state(cls, state: VocabState, catalog: Catalog) -> KnowledgeGraph:
        graph = cls()
        # Vocab nodes scored by mean EWMA across knowledge types.
        for lemma in catalog.lemmas:
            cells = state.scores.get(lemma, {})
            score = sum(c.ewma for c in cells.values()) / len(cells) if cells else 0.0
            graph.nodes[lemma] = GraphNode(id=lemma, kind="vocab", score=score)

        # Family + class edges (undirected, stored once per ordered pair).
        verbs = [catalog.verb(lemma) for lemma in catalog.lemmas]
        for i, a in enumerate(verbs):
            for b in verbs[i + 1 :]:
                if a.family and a.family == b.family:
                    graph.edges.append(
                        GraphEdge(a.lemma, b.lemma, Relation.SAME_FAMILY, weight=0.8)
                    )
                elif a.verb_class is b.verb_class:
                    graph.edges.append(GraphEdge(a.lemma, b.lemma, Relation.SAME_CLASS, weight=0.2))
        return graph

    def propagate(self, *, retention: float = 0.7) -> None:
        """One diffusion step: blend each node toward its neighbours' scores.

        ``retention`` is how much of a node's own score it keeps; the rest is a
        weighted average of neighbours. Idempotent enough for a single pass; not
        a fixed-point solver (that is the v2 modelling work).
        """
        incoming: dict[str, list[tuple[float, float]]] = {n: [] for n in self.nodes}
        for edge in self.edges:
            incoming.setdefault(edge.dst, []).append((self.nodes[edge.src].score, edge.weight))
            incoming.setdefault(edge.src, []).append((self.nodes[edge.dst].score, edge.weight))

        for node_id, contributions in incoming.items():
            if not contributions:
                continue
            total_weight = sum(w for _, w in contributions)
            if total_weight == 0:
                continue
            neighbour_mean = sum(s * w for s, w in contributions) / total_weight
            node = self.nodes[node_id]
            node.score = retention * node.score + (1 - retention) * neighbour_mean

    def neighbours(self, node_id: str) -> list[str]:
        out = [e.dst for e in self.edges if e.src == node_id]
        out += [e.src for e in self.edges if e.dst == node_id]
        return out


# Marker so callers/tests can branch on availability without guessing.
KNOWLEDGE_TYPES_TRACKED: tuple[KnowledgeType, ...] = tuple(KnowledgeType)
