/*
 * Item Response Theory: the 3-parameter logistic (3PL) model.
 *
 * Port of konjugaton's `analytics/irt.py`.
 *
 *     P(correct | theta) = c + (1 - c) * sigmoid(a * (theta - b))
 *
 * theta = learner ability, b = difficulty, a = discrimination, c = guessing.
 */
package com.konjugaton.hc.domain

import kotlin.math.exp

object Irt {
    val ABILITY_BOUNDS = -4.0 to 4.0

    private fun sigmoid(z: Double): Double =
        if (z >= 0) {
            1.0 / (1.0 + exp(-z))
        } else {
            val ez = exp(z)
            ez / (1.0 + ez)
        }

    /** 3PL probability of a correct response. */
    fun probabilityCorrect(theta: Double, p: IrtParameters): Double {
        val z = p.discrimination * (theta - p.difficulty)
        return p.guessing + (1.0 - p.guessing) * sigmoid(z)
    }

    /** d/dtheta of the log-likelihood of one response under 3PL. */
    fun abilityGradient(theta: Double, params: IrtParameters, correct: Boolean): Double {
        val p = probabilityCorrect(theta, params)
        val u = if (correct) 1.0 else 0.0
        val c = params.guessing
        if (c <= 0.0 || p <= 1e-9 || p >= 1.0 - 1e-9) {
            return params.discrimination * (u - p)
        }
        return params.discrimination * (u - p) * (p - c) / (p * (1.0 - c))
    }

    /** One online gradient-ascent step on ability, clamped to [bounds]. */
    fun updateAbility(
        theta: Double,
        params: IrtParameters,
        correct: Boolean,
        learningRate: Double = 0.5,
        bounds: Pair<Double, Double> = ABILITY_BOUNDS,
    ): Double {
        val updated = theta + learningRate * abilityGradient(theta, params, correct)
        val (low, high) = bounds
        return updated.coerceIn(low, high)
    }

    /** Fisher information of an item at [theta] (item-selection signal). */
    fun information(theta: Double, params: IrtParameters): Double {
        val p = probabilityCorrect(theta, params)
        if (p <= 1e-9 || p >= 1.0 - 1e-9) return 0.0
        val a = params.discrimination
        val c = params.guessing
        val q = 1.0 - p
        val k = (p - c) / (1.0 - c)
        return (a * a) * (q / p) * (k * k)
    }
}
