package com.konjugaton.hc.domain

import com.konjugaton.hc.data.CatalogLoader
import java.io.File
import kotlin.random.Random
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The reliability gate. Walks the ENTIRE realizable German space and asserts every
 * generated exercise is *well-posed* (answerable), not merely structurally valid —
 * the task must pin tense-mood + person + number + register + voice + polarity, and
 * the item must self-grade CORRECT.
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
        assertTrue("space looks suspiciously small", report.coordinatesChecked > 10_000)
        assertEquals(space.count(), report.coordinatesChecked)
        assertTrue("quality failures:\n" + report.failures.joinToString("\n"), report.ok)
    }

    @Test fun `self-check covers all tense-moods and verbs`() {
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

    @Test fun `negative perfekt cloze presents the negative target`() {
        val coord = Coordinate(
            lemma = "machen",
            tenseMood = TenseMood.PERFEKT,
            person = Person.P1,
            number = Number.SINGULAR,
            register = Register.NEUTRAL,
            polarity = Polarity.NEGATIVE,
            knowledge = KnowledgeType.PRODUCTION,
            context = catalog.contextIds.first(),
            voice = Voice.AKTIV,
        )
        val item = generator.generate(coord, Random(0))
        assertTrue("task must say negative: '${item.task}'", "negative" in item.task)
        assertTrue("task must say Perfekt: '${item.task}'", "Perfekt" in item.task)
        assertEquals("habe nicht gemacht", item.answer)
        assertTrue("ich" in item.fullSentence) // subject attached verb-second
        assertTrue(QualityEvaluator(catalog, conjugator).isWellPosed(item))
    }

    @Test fun `formal Sie cloze pins the register`() {
        val coord = Coordinate(
            lemma = "machen",
            tenseMood = TenseMood.IMPERATIV,
            person = Person.P2,
            number = Number.PLURAL,
            register = Register.SIE,
            polarity = Polarity.AFFIRMATIVE,
            knowledge = KnowledgeType.PRODUCTION,
            context = catalog.contextIds.first(),
            voice = Voice.AKTIV,
        )
        val item = generator.generate(coord, Random(0))
        assertTrue("task must pin register (Sie): '${item.task}'", "Sie" in item.task)
        assertEquals("machen Sie", item.answer)
        assertTrue(QualityEvaluator(catalog, conjugator).isWellPosed(item))
    }

    @Test fun `an item stripped of its task is detected as ill-posed`() {
        val coord = Coordinate(
            lemma = "machen",
            tenseMood = TenseMood.PRAETERITUM,
            person = Person.P1,
            number = Number.SINGULAR,
            register = Register.NEUTRAL,
            polarity = Polarity.AFFIRMATIVE,
            knowledge = KnowledgeType.PRODUCTION,
            context = catalog.contextIds.first(),
            voice = Voice.AKTIV,
        )
        val good = generator.generate(coord, Random(0))
        val stripped = good.copy(task = "")
        val issues = QualityEvaluator(catalog, conjugator).evaluate(stripped)
        assertTrue("stripped item should fail determinacy", issues.any { "axis token" in it })
    }
}
