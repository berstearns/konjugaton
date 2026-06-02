"""Engine: conjugation, combinatorial enumeration and item generation.

Depends only on :mod:`konjugaton.domain` and :mod:`konjugaton.data`. Knows nothing
about the learner, persistence or any UI.
"""

from __future__ import annotations

from konjugaton.engine import render
from konjugaton.engine.conjugator import (
    ConjugationError,
    Conjugator,
    default_agreement,
    supported_tense_moods,
)
from konjugaton.engine.generator import ExerciseGenerator
from konjugaton.engine.permutations import (
    IMPLEMENTED_KNOWLEDGE,
    AxisSelection,
    PermutationSpace,
)

__all__ = [
    "IMPLEMENTED_KNOWLEDGE",
    "AxisSelection",
    "ConjugationError",
    "Conjugator",
    "ExerciseGenerator",
    "PermutationSpace",
    "default_agreement",
    "render",
    "supported_tense_moods",
]
