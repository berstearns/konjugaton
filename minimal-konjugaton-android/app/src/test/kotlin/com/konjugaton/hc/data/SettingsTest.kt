package com.konjugaton.hc.data

import com.konjugaton.hc.domain.KnowledgeType
import com.konjugaton.hc.domain.Script
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Locks the question-filter prefs → AxisSelection mapping (mirrors the Python
 *  `selection_from_settings`): the levers that make the app usable when the
 *  learner can't type Devanagari ("romanized") or wants no typing at all ("mcq"). */
class SettingsTest {

    @Test fun `defaults impose no filter`() {
        val sel = AppSettings().selection()
        assertTrue(sel.scripts.isEmpty())
        assertTrue(sel.knowledge.isEmpty())
    }

    @Test fun `romanized restricts the elicitation script`() {
        val sel = AppSettings(answerScript = "romanized").selection()
        assertEquals(listOf(Script.ROMANIZED), sel.scripts)
    }

    @Test fun `multiple-choice restricts to recognition (no typing)`() {
        val sel = AppSettings(questionMode = "multiple-choice").selection()
        assertEquals(listOf(KnowledgeType.RECOGNITION), sel.knowledge)
    }

    @Test fun `typed and transliterate map to their knowledge types`() {
        assertEquals(listOf(KnowledgeType.PRODUCTION), AppSettings(questionMode = "typed").selection().knowledge)
        assertEquals(
            listOf(KnowledgeType.TRANSLITERATION),
            AppSettings(questionMode = "transliterate").selection().knowledge,
        )
    }

    @Test fun `romanized multiple-choice combines both axes`() {
        val sel = AppSettings(answerScript = "romanized", questionMode = "multiple-choice").selection()
        assertEquals(listOf(Script.ROMANIZED), sel.scripts)
        assertEquals(listOf(KnowledgeType.RECOGNITION), sel.knowledge)
    }
}
