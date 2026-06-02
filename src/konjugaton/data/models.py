"""Pydantic schemas for the on-disk data files.

These exist *only* at the I/O boundary: they validate the YAML (strictly —
``extra="forbid"`` turns a typo'd key into a startup error rather than a silent
mystery) and are then converted to pure domain dataclasses by the loader. The
domain never sees a Pydantic model.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from konjugaton.domain.enums import Auxiliary, VerbClass

_STRICT = ConfigDict(extra="forbid")


class ConjugationModel(BaseModel):
    """The optional `conjugation:` block on a verb (strong/mixed/irregular data)."""

    model_config = _STRICT

    praesens_stem_23: str | None = None
    praeteritum_stem: str | None = None
    partizip2: str | None = None
    konjunktiv2_stem: str | None = None
    #: paradigm -> slot -> form, for the suppletive sein/haben/werden.
    irregular: dict[str, dict[str, str]] = Field(default_factory=dict)


class VerbModel(BaseModel):
    model_config = _STRICT

    lemma: str
    translation: str
    verb_class: VerbClass
    auxiliary: Auxiliary
    transitive: bool
    frequency_rank: int
    separable_prefix: str | None = None
    family: str | None = None
    semantic_tags: list[str] = Field(default_factory=list)
    conjugation: ConjugationModel | None = None


class VerbsFile(BaseModel):
    model_config = _STRICT
    verbs: list[VerbModel]


class EndingsModel(BaseModel):
    """endings.yaml — paradigm -> slot -> suffix (single script)."""

    model_config = _STRICT

    praesens: dict[str, str]
    praeteritum_weak: dict[str, str]
    praeteritum_strong: dict[str, str]
    konjunktiv: dict[str, str]


class ContextModel(BaseModel):
    model_config = _STRICT

    id: str
    label_de: str
    label_en: str
    templates: list[str]
    affinity: list[str] = Field(default_factory=list)


class ContextsFile(BaseModel):
    model_config = _STRICT
    contexts: list[ContextModel]
