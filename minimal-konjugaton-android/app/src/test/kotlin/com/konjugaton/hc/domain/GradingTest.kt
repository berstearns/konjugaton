package com.konjugaton.hc.domain

import org.junit.Assert.assertEquals
import org.junit.Test

class GradingTest {

    private fun item(answer: String): Item {
        val coord = Coordinate(
            lemma = "machen",
            tenseMood = TenseMood.PRAESENS,
            person = Person.P1,
            number = Number.SINGULAR,
            register = Register.NEUTRAL,
            polarity = Polarity.AFFIRMATIVE,
            knowledge = KnowledgeType.PRODUCTION,
            context = "alltag",
            voice = Voice.AKTIV,
        )
        return Item(coord, coord.skill(VerbClass.WEAK), "prompt", answer, IrtParameters(0.0))
    }

    @Test fun `levenshtein basics`() {
        assertEquals(0, levenshtein("mache", "mache"))
        assertEquals(1, levenshtein("mache", "macht")) // e→t, one substitution
        assertEquals(3, levenshtein("kitten", "sitting"))
    }

    @Test fun `exact match is correct, case-insensitively`() {
        val g = Grader()
        assertEquals(Grade.CORRECT, g.grade(item("habe gemacht"), "habe gemacht").grade)
        assertEquals(Grade.CORRECT, g.grade(item("habe gemacht"), "  HABE GEMACHT ").grade)
    }

    @Test fun `umlaut answers match exactly`() {
        val g = Grader()
        assertEquals(Grade.CORRECT, g.grade(item("fährst"), "fährst").grade)
    }

    @Test fun `umlaut variants are folded under ignoreAccents`() {
        val g = Grader(GradingSettings(ignoreAccents = true))
        assertEquals(Grade.CORRECT, g.grade(item("fährst"), "fahrst").grade) // ä→a
        assertEquals(Grade.CORRECT, g.grade(item("würde machen"), "wurde machen").grade) // ü→u
    }

    @Test fun `nonsense is incorrect`() {
        assertEquals(Grade.INCORRECT, Grader().grade(item("habe gemacht"), "xyzzy").grade)
    }

    @Test fun `similarity tolerance accepts a near miss`() {
        val g = Grader(GradingSettings(similarityTolerance = 5))
        assertEquals(Grade.NEAR, g.grade(item("habe gemacht"), "habe gemcht").grade)
    }
}
