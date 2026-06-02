package com.konjugaton.hc.domain

import com.konjugaton.hc.data.CatalogLoader
import java.io.File
import kotlin.random.Random
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The reliability gate. Walks the ENTIRE realizable space (660,120 coordinates)
 * and asserts every generated exercise is *well-posed* (answerable), not merely
 * structurally valid — the task must pin TAM + agreement + construction +
 * polarity, and the item must self-grade CORRECT.
 */
class QualityTest {

    private val catalog = run {
        fun asset(n: String) = File("src/main/assets/$n").readText()
        CatalogLoader.parse(asset("verbs.json"), asset("endings.json"), asset("contexts.json"))
    }
    private val conjugator = Conjugator(catalog.endings, catalog.verbs)
    private val generator = ExerciseGenerator(catalog, conjugator)
    private val space = PermutationSpace(catalog, conjugator)
    private val selfCheck = SelfCheck(catalog, conjugator, generator, space)

    @Test fun `entire space generates well-posed items`() {
        val report = selfCheck.run()
        assertTrue("space looks suspiciously small", report.coordinatesChecked > 100_000)
        assertEquals(660_120, report.coordinatesChecked)
        assertTrue("quality failures:\n" + report.failures.joinToString("\n"), report.ok)
    }

    @Test fun `self-check covers all TAMs and verbs`() {
        val report = selfCheck.run()
        assertEquals(9, report.tams)
        assertTrue(report.verbs >= 20)
    }

    @Test fun `self-check is deterministic`() {
        val a = selfCheck.run(seed = 1)
        val b = selfCheck.run(seed = 1)
        assertTrue(a.coordinatesChecked == b.coordinatesChecked && a.ok == b.ok)
    }

    // --- determinacy regressions ----------------------------------------------

    @Test fun `negative perfect cloze presents the negative target and the ne-form`() {
        val coord = Coordinate(
            "करना", Tam.PERFECT, Person.P1, Number.SINGULAR, Gender.MASCULINE,
            Honorific.NEUTRAL, Polarity.NEGATIVE, Script.DEVANAGARI,
            KnowledgeType.PRODUCTION, catalog.contextIds.first(),
        )
        val item = generator.generate(coord, Random(0))
        assertTrue("task must say negative: '${item.task}'", "negative" in item.task)
        assertTrue("task must say perfect: '${item.task}'", "perfect" in item.task)
        assertEquals("नहीं किया है", item.answer) // object-default invariant + नहीं
        assertTrue("मैंने" in item.fullSentence) // ने-ergative on the subject
        assertTrue(QualityEvaluator(catalog, conjugator).isWellPosed(item))
    }

    @Test fun `feminine future cloze pins gender (which changes the tail)`() {
        val coord = Coordinate(
            "बोलना", Tam.FUTURE, Person.P3, Number.SINGULAR, Gender.FEMININE,
            Honorific.NEUTRAL, Polarity.AFFIRMATIVE, Script.DEVANAGARI,
            KnowledgeType.PRODUCTION, catalog.contextIds.first(),
        )
        val item = generator.generate(coord, Random(0))
        assertTrue("task must pin gender (fem): '${item.task}'", "fem" in item.task)
        assertEquals("बोलेगी", item.answer)
        assertTrue(QualityEvaluator(catalog, conjugator).isWellPosed(item))
    }

    @Test fun `an item stripped of its task is detected as ill-posed`() {
        val coord = Coordinate(
            "करना", Tam.PAST_HABITUAL, Person.P1, Number.SINGULAR, Gender.MASCULINE,
            Honorific.NEUTRAL, Polarity.AFFIRMATIVE, Script.DEVANAGARI,
            KnowledgeType.PRODUCTION, catalog.contextIds.first(),
        )
        val good = generator.generate(coord, Random(0))
        val stripped = good.copy(task = "")
        val issues = QualityEvaluator(catalog, conjugator).evaluate(stripped)
        assertTrue("stripped item should fail determinacy", issues.any { "axis token" in it })
    }
}
