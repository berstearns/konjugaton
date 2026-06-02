"""Item Response Theory: the 3-parameter logistic (3PL) model.

P(correct | theta) = c + (1 - c) * sigmoid(a * (theta - b))

where theta is learner ability, b difficulty, a discrimination, c guessing.

We expose the response probability, the per-response ability gradient (for
online updating during a session), and Fisher information (for adaptively
*selecting* the most informative next item — used by the scheduler later).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from konjugaton.domain import IrtParameters

ABILITY_BOUNDS: tuple[float, float] = (-4.0, 4.0)


def _sigmoid(z: float) -> float:
    # Numerically stable logistic.
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def probability_correct(theta: float, params: IrtParameters) -> float:
    """3PL probability of a correct response."""
    z = params.discrimination * (theta - params.difficulty)
    return params.guessing + (1.0 - params.guessing) * _sigmoid(z)


def ability_gradient(theta: float, params: IrtParameters, correct: bool) -> float:
    """d/dtheta of the log-likelihood of one response under 3PL.

    Reduces to a*(u - P) when c = 0 (the 2PL case).
    """
    p = probability_correct(theta, params)
    u = 1.0 if correct else 0.0
    c = params.guessing
    if c <= 0.0 or p <= 1e-9 or p >= 1.0 - 1e-9:
        return params.discrimination * (u - p)
    return params.discrimination * (u - p) * (p - c) / (p * (1.0 - c))


def update_ability(
    theta: float,
    params: IrtParameters,
    correct: bool,
    *,
    learning_rate: float = 0.5,
    bounds: tuple[float, float] = ABILITY_BOUNDS,
) -> float:
    """One online gradient-ascent step on ability, clamped to ``bounds``."""
    updated = theta + learning_rate * ability_gradient(theta, params, correct)
    low, high = bounds
    return max(low, min(high, updated))


def information(theta: float, params: IrtParameters) -> float:
    """Fisher information of an item at ``theta`` (item-selection signal)."""
    p = probability_correct(theta, params)
    if p <= 1e-9 or p >= 1.0 - 1e-9:
        return 0.0
    a, c = params.discrimination, params.guessing
    q = 1.0 - p
    return (a * a) * (q / p) * ((p - c) / (1.0 - c)) ** 2
