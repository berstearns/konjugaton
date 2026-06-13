package com.konjugaton.hc.data

import com.konjugaton.hc.domain.KnowledgeType
import com.konjugaton.hc.domain.SessionOrder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Locks the question-filter prefs → AxisSelection mapping (mirrors the Python
 *  `selection_from_settings`): the lever that makes the app usable when the learner
 *  wants no typing at all ("mcq") or only typed production ("written"). German is
 *  single-script, so the only filtered axis is knowledge. */
class SettingsTest {

    @Test fun `defaults impose no knowledge filter`() {
        val sel = AppSettings().selection()
        assertTrue(sel.knowledge.isEmpty())
    }

    @Test fun `mcq restricts to recognition (no typing)`() {
        val sel = AppSettings(questionType = "mcq").selection()
        assertEquals(listOf(KnowledgeType.RECOGNITION), sel.knowledge)
    }

    @Test fun `written restricts to production (typed)`() {
        val sel = AppSettings(questionType = "written").selection()
        assertEquals(listOf(KnowledgeType.PRODUCTION), sel.knowledge)
    }

    @Test fun `both leaves the knowledge axis open`() {
        val sel = AppSettings(questionType = "both").selection()
        assertTrue(sel.knowledge.isEmpty())
    }

    @Test fun `grading settings flow through from acceptance flags`() {
        val g = AppSettings(
            ignoreCase = false,
            ignoreAccents = true,
            ignorePunctuation = false,
            similarityTolerance = 4,
        ).toGradingSettings()
        assertEquals(false, g.ignoreCase)
        assertEquals(true, g.ignoreAccents)
        assertEquals(false, g.ignorePunctuation)
        assertEquals(4, g.similarityTolerance)
    }

    @Test fun `session order maps from the order pref`() {
        assertEquals(SessionOrder.EASY_FIRST, AppSettings(sessionOrder = "easy-first").order())
        assertEquals(SessionOrder.HARD_FIRST, AppSettings(sessionOrder = "hard-first").order())
        assertEquals(SessionOrder.RANDOM, AppSettings(sessionOrder = "random").order())
        assertEquals(SessionOrder.ADAPTIVE, AppSettings(sessionOrder = "adaptive").order())
    }
}
