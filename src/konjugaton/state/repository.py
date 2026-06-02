"""Persistence abstraction for the learner state.

The application layer depends on the :class:`StateRepository` *protocol*, never
on a concrete store. Swapping JSON for SQLite or a remote API is a new class,
not a change to services.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from konjugaton.state.vocab_state import VocabState


class StateRepository(Protocol):
    """Load/save the learner state."""

    def load(self) -> VocabState: ...

    def save(self, state: VocabState) -> None: ...


def default_state_path() -> Path:
    """XDG-respecting default location for the state file."""
    xdg = os.environ.get("XDG_STATE_HOME")
    root = Path(xdg) if xdg else Path.home() / ".local" / "state"
    return root / "konjugaton" / "state.json"
