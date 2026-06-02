package com.konjugaton.hc.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class IrtTest {

    @Test fun `probability is one half at ability equal to difficulty (no guessing)`() {
        val p = IrtParameters(difficulty = 0.5, discrimination = 1.0, guessing = 0.0)
        assertEquals(0.5, Irt.probabilityCorrect(0.5, p), 1e-9)
    }

    @Test fun `guessing raises the lower asymptote`() {
        val p = IrtParameters(difficulty = 0.0, discrimination = 1.0, guessing = 0.25)
        assertTrue(Irt.probabilityCorrect(-4.0, p) >= 0.25)
    }

    @Test fun `a correct answer raises ability, a wrong one lowers it`() {
        val p = IrtParameters(difficulty = 0.0)
        assertTrue(Irt.updateAbility(0.0, p, correct = true) > 0.0)
        assertTrue(Irt.updateAbility(0.0, p, correct = false) < 0.0)
    }

    @Test fun `ability stays within bounds`() {
        val p = IrtParameters(difficulty = 0.0, discrimination = 2.0)
        var theta = 0.0
        repeat(100) { theta = Irt.updateAbility(theta, p, correct = true) }
        assertTrue(theta <= 4.0)
    }

    @Test fun `information is non-negative and peaks near difficulty`() {
        val p = IrtParameters(difficulty = 0.0, discrimination = 1.0)
        val atPeak = Irt.information(0.0, p)
        val offPeak = Irt.information(3.0, p)
        assertTrue(atPeak >= 0.0)
        assertTrue(atPeak > offPeak)
    }
}
