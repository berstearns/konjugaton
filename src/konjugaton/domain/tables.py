"""Ending tables — the data-driven regular-conjugation rules.

Loaded from ``_data/endings.yaml``. The conjugator asks for an ending by
*paradigm* and *key* (the ``person|number`` slot), then appends it to a stem.
The paradigms are:

* ``praesens`` — present endings (-e/-st/-t/-en/-t/-en).
* ``praeteritum_weak`` — endings on ``stem+te`` (''/-st/''/-n/-t/-n).
* ``praeteritum_strong`` — endings on the ablaut stem (''/-st/''/-en/-t/-en).
* ``konjunktiv`` — Konjunktiv I/II endings (-e/-est/-e/-en/-et/-en).

German is single-script, so there is exactly one table per paradigm.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class EndingTables:
    """Nested lookup: paradigm -> key -> ending."""

    tables: Mapping[str, Mapping[str, str]]

    def has(self, paradigm: str) -> bool:
        return paradigm in self.tables

    def ending(self, paradigm: str, key: str) -> str:
        return self.tables[paradigm][key]
