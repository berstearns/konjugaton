"""Semantic context — the situational framing axis for generated sentences."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SemanticContext:
    """A themed bundle of sentence templates (travel, work, daily life, ...).

    Templates carry the contiguous token ``{subject} {verb}`` (the renderer
    attaches the subject pronoun there) plus a context tail. German is
    single-script, so one template set per context.
    """

    id: str
    label_de: str
    label_en: str
    templates: tuple[str, ...]
    affinity: tuple[str, ...] = ()
