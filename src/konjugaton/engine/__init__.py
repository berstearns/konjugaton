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
from konjugaton.engine.generator import ExerciseGenerator, seed_irt
from konjugaton.engine.paradigm import build_conjugation_table
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
    "build_conjugation_table",
    "default_agreement",
    "render",
    "seed_irt",
    "supported_tense_moods",
]
