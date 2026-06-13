package com.konjugaton.hc.domain

import com.konjugaton.hc.data.CatalogLoader
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The conjugation-table completion drill. Mirrors konjugaton's
 * `tests/test_conjugation_table.py`: the cells are the verb's real paradigm in the
 * canonical pronoun order, each cell is a gradable PRODUCTION item, grading routes
 * through the Grader, and the Imperativ realizes only du/ihr/Sie.
 */
class ConjTableTest {

    private val catalog = run {
        fun asset(n: String) = File("src/main/assets/$n").readText()
        CatalogLoader.parse(asset("verbs.json"), asset("endings.json"), asset("contexts.json"))
    }
    private val conjugator = Conjugator(catalog.endings, catalog.verbs)
    private val grader = Grader()

    private fun table(lemma: String, tm: TenseMood) =
        buildConjTable(catalog, conjugator, lemma, tm)

    @Test fun `haben praesens matches the known paradigm`() {
        val t = table("haben", TenseMood.PRAESENS)
        assertEquals("haben", t.lemma)
        assertEquals("Präsens", t.tenseLabel)
        assertEquals(
            listOf("ich", "du", "er", "wir", "ihr", "sie"),
            t.cells.map { it.subject },
        )
        assertEquals(
            listOf("habe", "hast", "hat", "haben", "habt", "haben"),
            t.cells.map { it.answer },
        )
    }

    @Test fun `perfekt uses the verb's selected auxiliary`() {
        // gehen selects sein → "ich bin gegangen"; machen selects haben → "ich habe gemacht".
        val gehen = table("gehen", TenseMood.PERFEKT)
        assertEquals("bin gegangen", gehen.cells.first().answer)
        assertEquals("sind gegangen", gehen.cells[3].answer)
        val machen = table("machen", TenseMood.PERFEKT)
        assertEquals("habe gemacht", machen.cells.first().answer)
    }

    @Test fun `imperativ is the three addressees`() {
        val t = table("machen", TenseMood.IMPERATIV)
        assertEquals(listOf("(du)", "(ihr)", "(Sie)"), t.cells.map { it.subject })
        assertEquals(listOf("mach", "macht", "machen Sie"), t.cells.map { it.answer })
    }

    @Test fun `cells are production items over the same tense-mood`() {
        val t = table("machen", TenseMood.PRAESENS)
        for (cell in t.cells) {
            val coord = cell.item.coordinate
            assertEquals("machen", coord.lemma)
            assertEquals(TenseMood.PRAESENS, coord.tenseMood)
            assertEquals(KnowledgeType.PRODUCTION, coord.knowledge)
            assertEquals(Polarity.AFFIRMATIVE, coord.polarity)
            assertEquals(Voice.AKTIV, coord.voice)
            assertEquals(cell.answer, cell.item.answer)
            assertFalse(cell.item.isMultipleChoice)
        }
    }

    @Test fun `grade accepts the correct form and rejects a wrong one`() {
        val t = table("haben", TenseMood.PRAESENS)
        val duHast = t.cells[1]
        assertEquals(Grade.CORRECT, grader.grade(duHast.item, "hast").grade)
        assertEquals(Grade.INCORRECT, grader.grade(duHast.item, "habst").grade)
    }

    @Test fun `every tense-mood builds a full table`() {
        for (tm in supportedTenseMoods()) {
            val t = table("sein", tm)
            val expected = if (tm == TenseMood.IMPERATIV) 3 else 6
            assertEquals("size for ${tm.value}", expected, t.cells.size)
        }
    }

    @Test fun `unknown verb raises`() {
        var raised = false
        try {
            table("notaverb", TenseMood.PRAESENS)
        } catch (e: Exception) {
            raised = true
        }
        assertTrue("building a table for an unknown verb should raise", raised)
    }
}
