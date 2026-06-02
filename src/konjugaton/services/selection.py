"""Turn user settings (the ``curriculum`` block) into an :class:`AxisSelection`.

The ``curriculum.*`` lists are the *persistent* session filter — "only drill me on
these tense-moods / registers / voices / question types". Every surface (CLI, TUI,
Android-parity) funnels through here so a setting set in one place takes effect
everywhere. Explicit per-invocation ``base`` axes win; otherwise the curriculum
value is used; empty means "all". Knowledge is clamped to the implemented types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from konjugaton.domain import (
    KnowledgeType,
    Number,
    Person,
    Polarity,
    Register,
    TenseMood,
    Voice,
)
from konjugaton.engine import IMPLEMENTED_KNOWLEDGE, AxisSelection

if TYPE_CHECKING:
    from collections.abc import Sequence
    from enum import StrEnum

    from konjugaton.settings.models import Settings

_E = TypeVar("_E", bound="StrEnum")


def _coerce(strings: Sequence[str], enum: type[_E]) -> tuple[_E, ...]:
    out: list[_E] = []
    for s in strings:
        try:
            out.append(enum(s))
        except ValueError:
            continue
    return tuple(out)


def _pick(base: tuple[_E, ...], strings: Sequence[str], enum: type[_E]) -> tuple[_E, ...]:
    return base if base else _coerce(strings, enum)


def selection_from_settings(settings: Settings, base: AxisSelection | None = None) -> AxisSelection:
    """Build the session filter from ``settings.curriculum`` (+ optional overrides)."""
    base = base or AxisSelection()
    cur = settings.curriculum

    knowledge = _pick(base.knowledge, cur.knowledge, KnowledgeType)
    knowledge = tuple(k for k in knowledge if k in IMPLEMENTED_KNOWLEDGE)

    return AxisSelection(
        lemmas=base.lemmas,
        tense_moods=_pick(base.tense_moods, cur.tense_moods, TenseMood),
        persons=_pick(base.persons, cur.persons, Person),
        numbers=_pick(base.numbers, cur.numbers, Number),
        registers=_pick(base.registers, cur.registers, Register),
        voices=_pick(base.voices, cur.voices, Voice),
        polarities=_pick(base.polarities, cur.polarities, Polarity),
        knowledge=knowledge,
        contexts=base.contexts or tuple(cur.contexts),
    )
