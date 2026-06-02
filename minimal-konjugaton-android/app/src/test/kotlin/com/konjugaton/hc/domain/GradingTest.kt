package com.konjugaton.hc.domain

import org.junit.Assert.assertEquals
import org.junit.Test

class GradingTest {

    private fun item(answer: String): Item {
        val coord = Coordinate(
            lemma = "करना",
            tam = Tam.PRESENT_HABITUAL,
            person = Person.P1,
            number = Number.SINGULAR,
            gender = Gender.MASCULINE,
            honorific = Honorific.NEUTRAL,
            polarity = Polarity.AFFIRMATIVE,
            script = Script.ROMANIZED,
            knowledge = KnowledgeType.PRODUCTION,
            context = "rozmarra",
        )
        return Item(coord, coord.skill(VerbClass.IRREGULAR), "prompt", answer, IrtParameters(0.0))
    }

    @Test fun `levenshtein basics`() {
        assertEquals(0, levenshtein("karta", "karta"))
        assertEquals(1, levenshtein("karta", "karti"))
        assertEquals(3, levenshtein("kitten", "sitting"))
    }

    @Test fun `exact match is correct, case-insensitively`() {
        val g = Grader()
        assertEquals(Grade.CORRECT, g.grade(item("karta hun"), "karta hun").grade)
        assertEquals(Grade.CORRECT, g.grade(item("karta hun"), "  KARTA HUN ").grade)
    }

    @Test fun `devanagari exact match`() {
        val g = Grader()
        assertEquals(Grade.CORRECT, g.grade(item("करता हूँ"), "करता हूँ").grade)
    }

    @Test fun `romanization variants are folded under ignoreAccents`() {
        val g = Grader(GradingSettings(ignoreAccents = true))
        assertEquals(Grade.CORRECT, g.grade(item("karta hun"), "kaarta hun").grade) // aa→a
        assertEquals(Grade.CORRECT, g.grade(item("kijiye"), "keejiye").grade) // ee→i
    }

    @Test fun `nonsense is incorrect`() {
        assertEquals(Grade.INCORRECT, Grader().grade(item("karta hun"), "xyzzy").grade)
    }

    @Test fun `similarity tolerance accepts a near miss`() {
        val g = Grader(GradingSettings(similarityTolerance = 5))
        assertEquals(Grade.NEAR, g.grade(item("karta hun"), "karta hn").grade)
    }
}
