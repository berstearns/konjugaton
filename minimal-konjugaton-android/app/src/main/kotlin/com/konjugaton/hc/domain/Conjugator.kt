/*
 * The conjugator: turn (verb, TAM, agreement) into a surface form.
 *
 * Direct port of konjugaton's `engine/conjugator.py`. Strategy "radicals +
 * endings" adapted to Hindi's periphrastic, agreement-rich morphology:
 *
 *   present-habitual    : imperfective + होना(present)      करता हूँ
 *   past-habitual        : imperfective + होना(past)         करता था
 *   present-progressive  : root + रहा(agr) + होना(present)   कर रहा हूँ
 *   past-progressive     : root + रहा(agr) + होना(past)      कर रहा था
 *   perfect              : perfective (+ होना present)        किया है
 *   past-perfect         : perfective + होना(past)            किया था
 *   future               : root(+oblique) + ending + gender-tail  करेगा
 *   subjunctive          : root + subjunctive ending          करे
 *   imperative           : root + honorific imperative ending  कर / करो / कीजिए
 *
 * Irregular verbs supply explicit perfective participles; everything else is
 * rule-derived. canConjugate gates unrealizable cells; realizableAgreement
 * gates ungrammatical agreement bundles.
 */
package com.konjugaton.hc.domain

class ConjugationError(message: String) : RuntimeException(message)

/** TAMs the engine can realize, in a stable display order. */
private val TAM_ORDER: List<Tam> = listOf(
    Tam.PRESENT_HABITUAL,
    Tam.PAST_HABITUAL,
    Tam.PRESENT_PROGRESSIVE,
    Tam.PAST_PROGRESSIVE,
    Tam.PERFECT,
    Tam.PAST_PERFECT,
    Tam.FUTURE,
    Tam.SUBJUNCTIVE,
    Tam.IMPERATIVE,
)

/** Devanagari vowel-sign matras + independent vowels (a root ending in one is "vowel-final"). */
private val DEVANAGARI_MATRAS = "ािीुूृेैोौॅॉ".toSet()
private val DEVANAGARI_VOWELS = "अआइईउऊऋएऐओऔ".toSet()

private val PRESENT_AUX: Set<Tam> =
    setOf(Tam.PRESENT_HABITUAL, Tam.PRESENT_PROGRESSIVE, Tam.PERFECT)

/** A synthetic, intransitive, regular light verb the engine conjugates wholesale. */
private fun lightVerb(lemma: String, lemmaRoman: String, root: String, rootRoman: String) =
    Verb(
        lemma = lemma,
        lemmaRoman = lemmaRoman,
        verbClass = VerbClass.REGULAR,
        transitivity = Transitivity.INTRANSITIVE,
        translation = "",
        frequencyRank = 0,
        conjugation = ConjugationData(root = root, rootRoman = rootRoman),
    )

/** The conjugated light verb each modal construction stacks on the main verb. */
private val LIGHT_VERBS: Map<Construction, Verb> = mapOf(
    Construction.ABILITY to lightVerb("सकना", "sakna", "सक", "sak"),
    Construction.COMPLETIVE to lightVerb("चुकना", "chukna", "चुक", "chuk"),
    Construction.DESIDERATIVE to lightVerb("चाहना", "chahna", "चाह", "chah"),
    Construction.INCEPTIVE to lightVerb("लगना", "lagna", "लग", "lag"),
)

/** PASSIVE's light verb is जाना, read from the catalog (suppletive perfective गया). */
private const val PASSIVE_LIGHT_LEMMA = "जाना"

/**
 * The closed set of TAMs each construction licenses (mirrors Python's
 * CONSTRUCTION_TAMS). SIMPLE is every TAM; the compounds drop cells that are
 * idiomatically odd or take ने. Proven equal to the Python gate by selfcheck.
 */
val CONSTRUCTION_TAMS: Map<Construction, Set<Tam>> = mapOf(
    Construction.SIMPLE to TAM_ORDER.toSet(),
    Construction.ABILITY to setOf(
        Tam.PRESENT_HABITUAL, Tam.PAST_HABITUAL, Tam.PERFECT,
        Tam.PAST_PERFECT, Tam.FUTURE, Tam.SUBJUNCTIVE,
    ),
    Construction.COMPLETIVE to setOf(Tam.PERFECT, Tam.PAST_PERFECT, Tam.FUTURE),
    Construction.DESIDERATIVE to setOf(
        Tam.PRESENT_HABITUAL, Tam.PAST_HABITUAL, Tam.FUTURE, Tam.SUBJUNCTIVE,
    ),
    Construction.INCEPTIVE to setOf(
        Tam.PRESENT_HABITUAL, Tam.PAST_HABITUAL, Tam.PAST_PERFECT, Tam.FUTURE,
    ),
    Construction.PASSIVE to setOf(
        Tam.PRESENT_HABITUAL, Tam.PAST_HABITUAL, Tam.PRESENT_PROGRESSIVE,
        Tam.PAST_PROGRESSIVE, Tam.PERFECT, Tam.PAST_PERFECT, Tam.FUTURE, Tam.SUBJUNCTIVE,
    ),
)

/** The oblique infinitive (करना→करने) used before लगना. */
private fun obliqueInfinitive(verb: Verb): Pair<String, String> {
    val dev = if (verb.lemma.endsWith("ना")) verb.lemma.dropLast(2) + "ने" else verb.lemma
    val rom = if (verb.lemmaRoman.endsWith("na")) verb.lemmaRoman.dropLast(2) + "ne" else verb.lemmaRoman
    return dev to rom
}

/** The canonical object a transitive ने-perfective agrees with (किया है / किया था). */
private val OBJECT_DEFAULT =
    Agreement(Person.P3, Number.SINGULAR, Gender.MASCULINE, Honorific.NEUTRAL)

/** Vowel-final future/subjunctive matra ending → its independent-vowel glide form. */
private val GLIDE_DEV: Map<String, String> = mapOf(
    "ूँ" to "ऊँ", // 1sg  खाऊँगा
    "े" to "ए", // 3sg/2tu  खाएगा
    "ें" to "एँ", // 1pl/3pl/aap  खाएँगे
    "ो" to "ओ", // 2tum  खाओगे
)

/** हो (होना) is idiosyncratic: keeps the glide for 1sg/2tum, drops it for े/ें. */
private val HO_OVERRIDE_DEV: Map<String, String> = mapOf("े" to "", "ें" to "ं")
private val HO_OVERRIDE_ROM: Map<String, String> = mapOf("e" to "", "en" to "n")

/** All TAMs the engine can realize, in a stable order. */
fun supportedTams(): List<Tam> = TAM_ORDER

private fun vowelFinal(root: String): Boolean {
    if (root.isEmpty()) return false
    val last = root.last()
    return last in DEVANAGARI_MATRAS || last in DEVANAGARI_VOWELS
}

/** Re-spell a matra future/subjunctive ending after a vowel-final stem. */
private fun glide(stem: String, endingDev: String, endingRom: String): Pair<String, String> {
    if (stem == "हो") {
        val dev = HO_OVERRIDE_DEV[endingDev] ?: GLIDE_DEV[endingDev] ?: endingDev
        val rom = HO_OVERRIDE_ROM[endingRom] ?: endingRom
        return dev to rom
    }
    return (GLIDE_DEV[endingDev] ?: endingDev) to endingRom
}

/**
 * number|gender key for the agreement tables. Hindi quirk: तुम (FAMILIAR) takes
 * plural-MASCULINE agreement (तुम करते हो) but SINGULAR-shaped FEMININE
 * (तुम करती हो, not करतीं) — so for तुम+feminine we down-key the number.
 */
private fun ngKey(agr: Agreement): String {
    var number = agr.number
    if (agr.honorific == Honorific.FAMILIAR && agr.gender == Gender.FEMININE) {
        number = Number.SINGULAR
    }
    return "${number.value}|${agr.gender.value}"
}

/** person|number|honorific key for future/subjunctive/होना(present). */
private fun pnhKey(agr: Agreement): String =
    "${agr.person.value}|${agr.number.value}|${agr.honorific.value}"

/** The ending-table paradigm name carrying a TAM's personal endings. */
fun tamParadigm(tam: Tam): String = when (tam) {
    Tam.FUTURE -> "future"
    Tam.SUBJUNCTIVE -> "subjunctive"
    else -> throw ConjugationError("no personal-ending paradigm for ${tam.value}")
}

/** Stateless (w.r.t. learner) conjugation engine over a fixed catalog. */
class Conjugator(
    private val endings: EndingTables,
    private val verbs: Map<String, Verb> = emptyMap(),
) {
    // -- capability queries -------------------------------------------------

    fun supports(tam: Tam): Boolean = tam in TAM_ORDER

    fun canConjugate(verb: Verb, tam: Tam): Boolean {
        if (!supports(tam)) return false
        if ((tam == Tam.PERFECT || tam == Tam.PAST_PERFECT) &&
            verb.verbClass == VerbClass.IRREGULAR
        ) {
            return verb.conjugation.perfective != null
        }
        return true
    }

    /** Not every (TAM, agreement) cell is grammatical. */
    fun realizableAgreement(tam: Tam, agr: Agreement): Boolean = when {
        tam == Tam.IMPERATIVE ->
            agr.person == Person.P2 && agr.honorific != Honorific.NEUTRAL
        tam == Tam.FUTURE || tam == Tam.SUBJUNCTIVE ->
            pnhKey(agr) in endings.tables.getValue(tamParadigm(tam))
        tam in PRESENT_AUX ->
            pnhKey(agr) in endings.tables.getValue("hona_present")
        else -> true // past-aux TAMs key on number|gender, always present
    }

    /** True if (verb, TAM) can be realized in this construction. */
    fun realizableConstruction(verb: Verb, tam: Tam, construction: Construction): Boolean {
        if (construction == Construction.SIMPLE) return canConjugate(verb, tam)
        if (tam !in CONSTRUCTION_TAMS.getValue(construction)) return false
        if (construction == Construction.PASSIVE) {
            val light = verbs[PASSIVE_LIGHT_LEMMA] ?: return false
            if (verb.transitivity != Transitivity.TRANSITIVE) return false
            return canConjugate(verb, Tam.PERFECT) && canConjugate(light, tam)
        }
        return canConjugate(LIGHT_VERBS.getValue(construction), tam)
    }

    // -- main entry point ---------------------------------------------------

    fun conjugate(verb: Verb, tam: Tam, agr: Agreement): ConjugatedForm {
        if (!canConjugate(verb, tam)) {
            throw ConjugationError("${verb.lemma}: cannot realize ${tam.value}")
        }
        return when (tam) {
            Tam.PRESENT_HABITUAL, Tam.PAST_HABITUAL -> habitual(verb, tam, agr)
            Tam.PRESENT_PROGRESSIVE, Tam.PAST_PROGRESSIVE -> progressive(verb, tam, agr)
            Tam.PERFECT, Tam.PAST_PERFECT -> perfect(verb, tam, agr)
            Tam.FUTURE -> future(verb, agr)
            Tam.SUBJUNCTIVE -> subjunctive(verb, agr)
            Tam.IMPERATIVE -> imperative(verb, agr)
        }
    }

    // -- compound constructions (light-verb / passive layer) ----------------

    /** Conjugate a verb in a given construction (SIMPLE = the plain verb). */
    fun conjugateConstruction(
        verb: Verb,
        tam: Tam,
        agr: Agreement,
        construction: Construction,
    ): ConjugatedForm {
        if (!realizableConstruction(verb, tam, construction)) {
            throw ConjugationError("${verb.lemma}: cannot realize ${construction.value} ${tam.value}")
        }
        return when (construction) {
            Construction.SIMPLE -> conjugate(verb, tam, agr)
            Construction.PASSIVE -> passive(verb, tam, agr)
            else -> modal(verb, tam, agr, construction)
        }
    }

    /** काम किया जाता है — perfective participle (agreeing with the patient) + जाना. */
    private fun passive(verb: Verb, tam: Tam, agr: Agreement): ConjugatedForm {
        val (main, mainRom) = perfective(verb, agr)
        val light = verbs.getValue(PASSIVE_LIGHT_LEMMA)
        val aux = conjugate(light, tam, agr)
        return ConjugatedForm.periphrastic(main, mainRom, aux.surface, aux.surfaceRoman)
    }

    /** कर सकता है / कर चुका है / करना चाहता है / करने लगा — non-finite main + modal light verb. */
    private fun modal(verb: Verb, tam: Tam, agr: Agreement, construction: Construction): ConjugatedForm {
        val (main, mainRom) = nonfinite(verb, construction)
        val light = LIGHT_VERBS.getValue(construction)
        val aux = conjugate(light, tam, agr)
        return ConjugatedForm.periphrastic(main, mainRom, aux.surface, aux.surfaceRoman)
    }

    /** The non-finite part of the main verb a modal construction stacks on. */
    private fun nonfinite(verb: Verb, construction: Construction): Pair<String, String> = when (construction) {
        Construction.ABILITY, Construction.COMPLETIVE -> verb.root to verb.rootRoman
        Construction.DESIDERATIVE -> verb.lemma to verb.lemmaRoman
        Construction.INCEPTIVE -> obliqueInfinitive(verb)
        else -> throw ConjugationError("no non-finite form for ${construction.value}")
    }

    // -- participles --------------------------------------------------------

    private fun imperfective(verb: Verb, agr: Agreement): Pair<String, String> {
        val key = ngKey(agr)
        return (verb.root + endings.ending("imperfective", key)) to
            (verb.rootRoman + endings.endingRoman("imperfective", key))
    }

    private fun perfective(verb: Verb, agr: Agreement): Pair<String, String> {
        val key = ngKey(agr)
        val perf = verb.conjugation.perfective
        if (perf != null) return perf.forms.getValue(key) to perf.formsRoman.getValue(key)
        val paradigm = if (vowelFinal(verb.root)) "perfective_glide" else "perfective"
        return (verb.root + endings.ending(paradigm, key)) to
            (verb.rootRoman + endings.endingRoman(paradigm, key))
    }

    // -- present/past habitual ----------------------------------------------

    private fun habitual(verb: Verb, tam: Tam, agr: Agreement): ConjugatedForm {
        val (main, mainRom) = imperfective(verb, agr)
        val (aux, auxRom) = auxiliary(tam, agr)
        return ConjugatedForm.periphrastic(main, mainRom, aux, auxRom)
    }

    // -- progressive --------------------------------------------------------

    private fun progressive(verb: Verb, tam: Tam, agr: Agreement): ConjugatedForm {
        val key = ngKey(agr)
        val main = "${verb.root} ${endings.ending("progressive", key)}"
        val mainRom = "${verb.rootRoman} ${endings.endingRoman("progressive", key)}"
        val (aux, auxRom) = auxiliary(tam, agr)
        return ConjugatedForm.periphrastic(main, mainRom, aux, auxRom)
    }

    // -- perfect / past-perfect ---------------------------------------------

    private fun perfect(verb: Verb, tam: Tam, agr: Agreement): ConjugatedForm {
        // ने-ERGATIVE: a TRANSITIVE verb in a perfective TAM agrees with the
        // (default masc-sg) OBJECT, not the subject — so किया है is invariant
        // across subjects. Intransitive verbs keep ordinary subject agreement.
        val effective = if (verb.transitivity == Transitivity.TRANSITIVE) OBJECT_DEFAULT else agr
        val (main, mainRom) = perfective(verb, effective)
        return if (tam == Tam.PERFECT) {
            val aux = endings.ending("hona_present", pnhKey(effective))
            val auxRom = endings.endingRoman("hona_present", pnhKey(effective))
            ConjugatedForm.periphrastic(main, mainRom, aux, auxRom)
        } else {
            val aux = endings.ending("hona_past", ngKey(effective))
            val auxRom = endings.endingRoman("hona_past", ngKey(effective))
            ConjugatedForm.periphrastic(main, mainRom, aux, auxRom)
        }
    }

    // -- future -------------------------------------------------------------

    private fun future(verb: Verb, agr: Agreement): ConjugatedForm {
        val (stem, stemRom) = futureOblique(verb)
        var ending = endings.ending("future", pnhKey(agr))
        var endingRom = endings.endingRoman("future", pnhKey(agr))
        if (vowelFinal(stem)) {
            val (e, r) = glide(stem, ending, endingRom)
            ending = e; endingRom = r
        }
        val tail = endings.ending("future_tail", ngKey(agr))
        val tailRom = endings.endingRoman("future_tail", ngKey(agr))
        return ConjugatedForm.simple(stem + ending + tail, stemRom + endingRom + tailRom)
    }

    private fun futureOblique(verb: Verb): Pair<String, String> {
        val ob = verb.conjugation.futureOblique
        return if (ob != null) {
            ob to (verb.conjugation.futureObliqueRoman ?: verb.rootRoman)
        } else {
            verb.root to verb.rootRoman
        }
    }

    // -- subjunctive --------------------------------------------------------

    private fun subjunctive(verb: Verb, agr: Agreement): ConjugatedForm {
        val (stem, stemRom) = futureOblique(verb)
        var ending = endings.ending("subjunctive", pnhKey(agr))
        var endingRom = endings.endingRoman("subjunctive", pnhKey(agr))
        if (vowelFinal(stem)) {
            val (e, r) = glide(stem, ending, endingRom)
            ending = e; endingRom = r
        }
        return ConjugatedForm.simple(stem + ending, stemRom + endingRom)
    }

    // -- imperative ---------------------------------------------------------

    private fun imperative(verb: Verb, agr: Agreement): ConjugatedForm {
        // आप (formal) imperative is lexically irregular for a small set
        // (कीजिए/दीजिए/लीजिए/पीजिए); those ship an explicit form. Else root + इए.
        if (agr.honorific == Honorific.FORMAL && verb.conjugation.imperativeAap != null) {
            return ConjugatedForm.simple(
                verb.conjugation.imperativeAap,
                verb.conjugation.imperativeAapRoman ?: verb.rootRoman,
            )
        }
        var ending = endings.ending("imperative", agr.honorific.value)
        val endingRom = endings.endingRoman("imperative", agr.honorific.value)
        // Vowel-final root + इए uses the independent vowel (खा → खाइए).
        if (agr.honorific == Honorific.FORMAL && vowelFinal(verb.root)) ending = "इए"
        return ConjugatedForm.simple(verb.root + ending, verb.rootRoman + endingRom)
    }

    // -- auxiliary ----------------------------------------------------------

    private fun auxiliary(tam: Tam, agr: Agreement): Pair<String, String> =
        if (tam in PRESENT_AUX) {
            val key = pnhKey(agr)
            endings.ending("hona_present", key) to endings.endingRoman("hona_present", key)
        } else {
            val key = ngKey(agr)
            endings.ending("hona_past", key) to endings.endingRoman("hona_past", key)
        }
}
