"""JSON-file implementation of :class:`StateRepository`."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from konjugaton.state.vocab_state import VocabState

if TYPE_CHECKING:
    from pathlib import Path


class JsonStateRepository:
    """Persist learner state as a single pretty-printed JSON document."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> VocabState:
        if not self._path.exists():
            return VocabState()
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return VocabState.from_dict(data)

    def save(self, state: VocabState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state.to_dict(), ensure_ascii=False, indent=2)
        self._path.write_text(payload, encoding="utf-8")
