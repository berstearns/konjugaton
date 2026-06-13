package com.konjugaton.hc.domain

import com.konjugaton.hc.data.CatalogLoader
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Locks the German conjugation engine to ground truth, loading the *same* JSON
 * assets the app ships. Mirrors konjugaton's `tests/test_conjugator.py` intent:
 * if the taxonomy or a stem rule regresses, this fails on the plain JVM in ms.
 *
 * The engine is the source of truth (a faithful port of the selfcheck-passing
 * Python); every asserted surface here is a hand-verified German form.
 */
class ConjugatorTest {

    private val catalog = run {
        fun asset(n: String) = File("src/main/assets/$n").readText()
        CatalogLoader.parse(asset("verbs.json"), asset("endings.json"), asset("contexts.json"))
    }
    private val conj = Conjugator(catalog.endings, catalog.verbs)

    // The six standard agreement bundles in textbook order.
    private val ich = Agreement(Person.P1, Number.SINGULAR, Register.NEUTRAL)
    private val du = Agreement(Person.P2, Number.SINGULAR, Register.DU)
    private val er = Agreement(Person.P3, Number.SINGULAR, Register.NEUTRAL)
    private val wir = Agreement(Person.P1, Number.PLURAL, Register.NEUTRAL)
    private val ihr = Agreement(Person.P2, Number.PLURAL, Register.IHR)
    private val sie = Agreement(Person.P3, Number.PLURAL, Register.NEUTRAL)
    private val sieFormal = Agreement(Person.P2, Number.PLURAL, Register.SIE)

    private fun surface(lemma: String, tm: TenseMood, a: Agreement) =
        conj.conjugate(catalog.verb(lemma), tm, a).surface

    @Test fun `weak praesens across the six slots`() {
        assertEquals("mache", surface("machen", TenseMood.PRAESENS, ich))
        assertEquals("machst", surface("machen", TenseMood.PRAESENS, du))
        assertEquals("macht", surface("machen", TenseMood.PRAESENS, er))
        assertEquals("machen", surface("machen", TenseMood.PRAESENS, wir))
        assertEquals("macht", surface("machen", TenseMood.PRAESENS, ihr))
        assertEquals("machen", surface("machen", TenseMood.PRAESENS, sie))
    }

    @Test fun `sein praesens is suppletive across the six slots`() {
        assertEquals("bin", surface("sein", TenseMood.PRAESENS, ich))
        assertEquals("bist", surface("sein", TenseMood.PRAESENS, du))
        assertEquals("ist", surface("sein", TenseMood.PRAESENS, er))
        assertEquals("sind", surface("sein", TenseMood.PRAESENS, wir))
        assertEquals("seid", surface("sein", TenseMood.PRAESENS, ihr))
        assertEquals("sind", surface("sein", TenseMood.PRAESENS, sie))
    }

    @Test fun `epenthetic-e weak verbs insert e before t-st endings`() {
        assertEquals("arbeitest", surface("arbeiten", TenseMood.PRAESENS, du))
        assertEquals("arbeitet", surface("arbeiten", TenseMood.PRAESENS, er))
        assertEquals("arbeitete", surface("arbeiten", TenseMood.PRAETERITUM, ich))
    }

    @Test fun `weak praeteritum and perfekt`() {
        assertEquals("machtest", surface("machen", TenseMood.PRAETERITUM, du))
        assertEquals("hat gemacht", surface("machen", TenseMood.PERFEKT, er))
        assertEquals("habe gemacht", surface("machen", TenseMood.PERFEKT, ich))
    }

    @Test fun `strong verbs ablaut and take their selected auxiliary`() {
        assertEquals("gingen", surface("gehen", TenseMood.PRAETERITUM, wir))
        assertEquals("bin gegangen", surface("gehen", TenseMood.PERFEKT, ich))
        assertEquals("siehst", surface("sehen", TenseMood.PRAESENS, du))
        assertEquals("sieht", surface("sehen", TenseMood.PRAESENS, er))
        assertEquals("gibt", surface("geben", TenseMood.PRAESENS, er))
        assertEquals("fährst", surface("fahren", TenseMood.PRAESENS, du))
        assertEquals("isst", surface("essen", TenseMood.PRAESENS, du))
    }

    @Test fun `mixed verbs use the ablaut past stem plus the weak suffix`() {
        assertEquals("dachte", surface("denken", TenseMood.PRAETERITUM, ich))
        assertEquals("habe gedacht", surface("denken", TenseMood.PERFEKT, ich))
        assertEquals("hat gebracht", surface("bringen", TenseMood.PERFEKT, er))
    }

    @Test fun `separable prefix detaches in simple tenses, binds in the PII`() {
        assertEquals("stehe auf", surface("aufstehen", TenseMood.PRAESENS, ich))
        assertEquals("bin aufgestanden", surface("aufstehen", TenseMood.PERFEKT, ich))
        assertEquals("kaufe ein", surface("einkaufen", TenseMood.PRAESENS, ich))
        assertEquals("habe eingekauft", surface("einkaufen", TenseMood.PERFEKT, ich))
    }

    @Test fun `irregular auxiliaries are pinned`() {
        assertEquals("war", surface("sein", TenseMood.PRAETERITUM, ich))
        assertEquals("bin gewesen", surface("sein", TenseMood.PERFEKT, ich))
        assertEquals("hatte", surface("haben", TenseMood.PRAETERITUM, ich))
        assertEquals("wird", surface("werden", TenseMood.PRAESENS, er))
    }

    @Test fun `futur and konjunktiv periphrases`() {
        assertEquals("werde machen", surface("machen", TenseMood.FUTUR1, ich))
        assertEquals("werde gemacht haben", surface("machen", TenseMood.FUTUR2, ich))
        assertEquals("ginge", surface("gehen", TenseMood.KONJUNKTIV2, ich))
        assertEquals("würde machen", surface("machen", TenseMood.KONJUNKTIV2, ich))
        assertEquals("wäre", surface("sein", TenseMood.KONJUNKTIV2, er))
        assertEquals("hätte", surface("haben", TenseMood.KONJUNKTIV2, er))
        assertEquals("mache", surface("machen", TenseMood.KONJUNKTIV1, er))
    }

    @Test fun `imperative agrees with the addressee register`() {
        fun imp(lemma: String, a: Agreement) =
            Render.predicate(
                conj.conjugate(catalog.verb(lemma), TenseMood.IMPERATIV, a),
                TenseMood.IMPERATIV,
                Polarity.AFFIRMATIVE,
                a.register,
            )
        assertEquals("mach", imp("machen", du))
        assertEquals("macht", imp("machen", ihr))
        assertEquals("machen Sie", imp("machen", sieFormal))
        assertEquals("gib", imp("geben", du)) // e→i stem change kept
        assertEquals("sieh", imp("sehen", du))
        assertEquals("fahr", imp("fahren", du)) // a→ä NOT applied in the imperative
        assertEquals("arbeite", imp("arbeiten", du)) // epenthetic e
        assertEquals("steh auf", imp("aufstehen", du)) // separable prefix detaches
    }

    @Test fun `render applies negation after the finite verb`() {
        val perf = conj.conjugate(catalog.verb("machen"), TenseMood.PERFEKT, ich)
        assertEquals(
            "habe nicht gemacht",
            Render.predicate(perf, TenseMood.PERFEKT, Polarity.NEGATIVE, Register.NEUTRAL),
        )
        val sep = conj.conjugate(catalog.verb("aufstehen"), TenseMood.PRAESENS, ich)
        assertEquals(
            "stehe nicht auf",
            Render.predicate(sep, TenseMood.PRAESENS, Polarity.NEGATIVE, Register.NEUTRAL),
        )
    }

    @Test fun `render attaches the subject pronoun verb-second`() {
        val pres = conj.conjugate(catalog.verb("machen"), TenseMood.PRAESENS, ich)
        val pred = Render.predicate(pres, TenseMood.PRAESENS, Polarity.AFFIRMATIVE, Register.NEUTRAL)
        assertEquals("ich mache", Render.attachSubject(ich, pred, TenseMood.PRAESENS))
        // Imperatives drop the subject.
        val imp = conj.conjugate(catalog.verb("machen"), TenseMood.IMPERATIV, du)
        val impPred = Render.predicate(imp, TenseMood.IMPERATIV, Polarity.AFFIRMATIVE, Register.DU)
        assertEquals("mach", Render.attachSubject(du, impPred, TenseMood.IMPERATIV))
    }

    @Test fun `the werden-passive is realized for transitive verbs`() {
        fun pass(lemma: String, tm: TenseMood) =
            conj.conjugateVoice(catalog.verb(lemma), tm, er, Voice.PASSIV).surface
        assertEquals("wird gemacht", pass("machen", TenseMood.PRAESENS))
        assertEquals("wurde gemacht", pass("machen", TenseMood.PRAETERITUM))
        assertEquals("ist gemacht worden", pass("machen", TenseMood.PERFEKT))
        assertEquals("wird gemacht werden", pass("machen", TenseMood.FUTUR1))
    }

    @Test fun `passive is gated to transitive verbs`() {
        assertFalse(conj.realizableVoice(catalog.verb("gehen"), TenseMood.PRAESENS, Voice.PASSIV))
        assertTrue(conj.realizableVoice(catalog.verb("machen"), TenseMood.PRAESENS, Voice.PASSIV))
    }

    @Test fun `the imperative is second-person only`() {
        assertFalse(conj.realizableAgreement(TenseMood.IMPERATIV, ich))
        assertTrue(conj.realizableAgreement(TenseMood.IMPERATIV, du))
    }

    @Test fun `the catalog ships the expected German verbs`() {
        assertTrue("expected at least 20 verbs", catalog.lemmas.size >= 20)
        assertTrue("sein/haben/werden are present", catalog.verbs.keys.containsAll(
            listOf("sein", "haben", "werden", "machen", "gehen"),
        ))
        // Nine tense-moods are realized.
        assertEquals(9, supportedTenseMoods().size)
    }
}
