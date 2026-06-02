package com.konjugaton.hc.domain

import com.konjugaton.hc.data.CatalogLoader
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Locks the conjugation engine to ground truth, loading the *same* JSON assets
 * the app ships. Mirrors konjugaton's `tests/test_conjugator.py` intent: if the
 * taxonomy or a stem rule regresses, this fails on the plain JVM in ms — in both
 * scripts.
 */
class ConjugatorTest {

    private val catalog = run {
        fun asset(n: String) = File("src/main/assets/$n").readText()
        CatalogLoader.parse(asset("verbs.json"), asset("endings.json"), asset("contexts.json"))
    }
    private val conj = Conjugator(catalog.endings, catalog.verbs)

    private fun agr(p: Person, n: Number, g: Gender, h: Honorific) = Agreement(p, n, g, h)
    private fun dev(lemma: String, tam: Tam, a: Agreement) =
        conj.conjugate(catalog.verb(lemma), tam, a).surface
    private fun rom(lemma: String, tam: Tam, a: Agreement) =
        conj.conjugate(catalog.verb(lemma), tam, a).surfaceRoman

    @Test fun `present habitual = imperfective participle + hona`() {
        val a = agr(Person.P1, Number.SINGULAR, Gender.MASCULINE, Honorific.NEUTRAL)
        assertEquals("करता हूँ", dev("करना", Tam.PRESENT_HABITUAL, a))
        assertEquals("karta hun", rom("करना", Tam.PRESENT_HABITUAL, a))
        val f = agr(Person.P1, Number.SINGULAR, Gender.FEMININE, Honorific.NEUTRAL)
        assertEquals("करती हूँ", dev("करना", Tam.PRESENT_HABITUAL, f))
    }

    @Test fun `tum feminine uses singular-shaped participle, not nasal plural`() {
        val a = agr(Person.P2, Number.PLURAL, Gender.FEMININE, Honorific.FAMILIAR)
        assertEquals("पढ़ती हो", dev("पढ़ना", Tam.PRESENT_HABITUAL, a)) // not पढ़तीं
        val m = agr(Person.P2, Number.PLURAL, Gender.MASCULINE, Honorific.FAMILIAR)
        assertEquals("पढ़ते हो", dev("पढ़ना", Tam.PRESENT_HABITUAL, m))
    }

    @Test fun `irregular perfectives are suppletive`() {
        val a = agr(Person.P3, Number.SINGULAR, Gender.MASCULINE, Honorific.NEUTRAL)
        assertEquals("किया है", dev("करना", Tam.PERFECT, a))
        assertEquals("गया है", dev("जाना", Tam.PERFECT, a))
        assertEquals("दिया है", dev("देना", Tam.PERFECT, a))
        assertEquals("लिया है", dev("लेना", Tam.PERFECT, a))
        assertEquals("पिया है", dev("पीना", Tam.PERFECT, a))
        // regular vowel-final glide perfective
        assertEquals("खाया है", dev("खाना", Tam.PERFECT, a))
    }

    @Test fun `ne-ergative perfect is invariant for transitive verbs`() {
        // transitive करना: किया है regardless of subject person/gender/number.
        val fem1sg = agr(Person.P1, Number.SINGULAR, Gender.FEMININE, Honorific.NEUTRAL)
        assertEquals("किया है", dev("करना", Tam.PERFECT, fem1sg))
        // intransitive जाना keeps subject agreement.
        val fem3sg = agr(Person.P3, Number.SINGULAR, Gender.FEMININE, Honorific.NEUTRAL)
        assertEquals("गई है", dev("जाना", Tam.PERFECT, fem3sg))
    }

    @Test fun `future has personal ending + gender tail, with vowel glide`() {
        val m = agr(Person.P1, Number.SINGULAR, Gender.MASCULINE, Honorific.NEUTRAL)
        assertEquals("करूँगा", dev("करना", Tam.FUTURE, m))
        val f = agr(Person.P1, Number.SINGULAR, Gender.FEMININE, Honorific.NEUTRAL)
        assertEquals("करूँगी", dev("करना", Tam.FUTURE, f))
        val third = agr(Person.P3, Number.SINGULAR, Gender.MASCULINE, Honorific.NEUTRAL)
        assertEquals("करेगा", dev("करना", Tam.FUTURE, third))
        // vowel-final stem glides; हो is special-cased.
        assertEquals("खाएगा", dev("खाना", Tam.FUTURE, third))
        assertEquals("होगा", dev("होना", Tam.FUTURE, third))
    }

    @Test fun `imperative agrees with the honorific, with irregular aap forms`() {
        assertEquals("कर", dev("करना", Tam.IMPERATIVE, agr(Person.P2, Number.SINGULAR, Gender.MASCULINE, Honorific.INTIMATE)))
        assertEquals("करो", dev("करना", Tam.IMPERATIVE, agr(Person.P2, Number.PLURAL, Gender.MASCULINE, Honorific.FAMILIAR)))
        assertEquals("कीजिए", dev("करना", Tam.IMPERATIVE, agr(Person.P2, Number.PLURAL, Gender.MASCULINE, Honorific.FORMAL)))
        assertEquals("बोलिए", dev("बोलना", Tam.IMPERATIVE, agr(Person.P2, Number.PLURAL, Gender.MASCULINE, Honorific.FORMAL)))
    }

    @Test fun `render applies preverbal negation and ne-ergative`() {
        assertEquals("नहीं करता हूँ", Render.predicate("करता हूँ", Tam.PRESENT_HABITUAL, Polarity.NEGATIVE))
        assertEquals("मत करो", Render.predicate("करो", Tam.IMPERATIVE, Polarity.NEGATIVE))
        val a = agr(Person.P1, Number.SINGULAR, Gender.MASCULINE, Honorific.NEUTRAL)
        assertEquals(
            "मैंने किया",
            Render.attachSubject(a, "किया", Tam.PERFECT, Transitivity.TRANSITIVE, Script.DEVANAGARI),
        )
        assertEquals(
            "मैं गया",
            Render.attachSubject(a, "गया", Tam.PERFECT, Transitivity.INTRANSITIVE, Script.DEVANAGARI),
        )
    }

    @Test fun `catalog and space have the expected explosive shape`() {
        assertEquals(23, catalog.lemmas.size)
        val space = PermutationSpace(catalog, conj)
        assertTrue("space should be explosive", space.count() > 100_000)
        assertEquals(660_120, space.count())
        // SIMPLE slice must equal the pre-construction baseline exactly.
        assertEquals(
            184_920,
            space.count(AxisSelection(constructions = listOf(Construction.SIMPLE))),
        )
    }

    @Test fun `per-construction counts match the Python engine`() {
        val space = PermutationSpace(catalog, conj)
        val expected = mapOf(
            Construction.SIMPLE to 184_920,
            Construction.ABILITY to 132_480,
            Construction.COMPLETIVE to 66_240,
            Construction.DESIDERATIVE to 88_320,
            Construction.INCEPTIVE to 88_320,
            Construction.PASSIVE to 99_840,
        )
        for ((c, want) in expected) {
            assertEquals(c.value, want, space.count(AxisSelection(constructions = listOf(c))))
        }
        assertEquals(660_120, expected.values.sum())
    }

    @Test fun `compound constructions produce the canonical surface forms`() {
        fun cc(lemma: String, tam: Tam, a: Agreement, c: Construction) =
            conj.conjugateConstruction(catalog.verb(lemma), tam, a, c).surface
        val m1 = agr(Person.P1, Number.SINGULAR, Gender.MASCULINE, Honorific.NEUTRAL)
        val f3 = agr(Person.P3, Number.SINGULAR, Gender.FEMININE, Honorific.NEUTRAL)
        assertEquals("कर सकता हूँ", cc("करना", Tam.PRESENT_HABITUAL, m1, Construction.ABILITY))
        assertEquals("कर चुका हूँ", cc("करना", Tam.PERFECT, m1, Construction.COMPLETIVE))
        assertEquals("करना चाहता हूँ", cc("करना", Tam.PRESENT_HABITUAL, m1, Construction.DESIDERATIVE))
        assertEquals("करने लगा था", cc("करना", Tam.PAST_PERFECT, m1, Construction.INCEPTIVE))
        assertEquals("की जाती है", cc("करना", Tam.PRESENT_HABITUAL, f3, Construction.PASSIVE))
        assertEquals("किया गया है", cc("करना", Tam.PERFECT, agr(Person.P3, Number.SINGULAR, Gender.MASCULINE, Honorific.NEUTRAL), Construction.PASSIVE))
    }

    @Test fun `compounds never take the ne-ergative`() {
        val a = agr(Person.P1, Number.SINGULAR, Gender.MASCULINE, Honorific.NEUTRAL)
        val comp = conj.conjugateConstruction(catalog.verb("करना"), Tam.PERFECT, a, Construction.COMPLETIVE)
        val clause = Render.attachSubject(
            a, comp.surface, Tam.PERFECT, Transitivity.TRANSITIVE, Script.DEVANAGARI,
            Construction.COMPLETIVE,
        )
        assertTrue("compound must stay nominative: $clause", clause.startsWith("मैं "))
    }

    @Test fun `construction realizability is gated`() {
        // passive needs a transitive verb
        assertFalse(conj.realizableConstruction(catalog.verb("आना"), Tam.PERFECT, Construction.PASSIVE))
        assertTrue(conj.realizableConstruction(catalog.verb("करना"), Tam.PERFECT, Construction.PASSIVE))
        // no compound licenses the imperative
        for (c in Construction.entries) {
            if (c == Construction.SIMPLE) continue
            assertFalse(conj.realizableConstruction(catalog.verb("करना"), Tam.IMPERATIVE, c))
        }
    }

    @Test fun `illegal agreement bundles are blocked`() {
        assertFalse(
            conj.realizableAgreement(
                Tam.IMPERATIVE, agr(Person.P1, Number.SINGULAR, Gender.MASCULINE, Honorific.NEUTRAL),
            ),
        )
        assertTrue(
            conj.realizableAgreement(
                Tam.IMPERATIVE, agr(Person.P2, Number.PLURAL, Gender.MASCULINE, Honorific.FAMILIAR),
            ),
        )
    }
}
