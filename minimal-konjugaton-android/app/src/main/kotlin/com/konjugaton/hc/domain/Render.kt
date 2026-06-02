/*
 * Surface rendering: preverbal negation, subject attachment, the ने-ergative.
 *
 * Port of konjugaton's `engine/render.py`. The conjugator produces morphology;
 * this applies the syntactic surface rules: Hindi negation is a PREVERBAL
 * particle whose form depends on the TAM (नहीं / मत / न), and a transitive verb
 * in a perfective TAM attaches ने to its subject (मैंने किया है).
 */
package com.konjugaton.hc.domain

/** Preverbal negator per TAM, (Devanagari, romanized). */
private val NEGATOR: Map<Tam, Pair<String, String>> = mapOf(
    Tam.IMPERATIVE to ("मत" to "mat"),
    Tam.SUBJUNCTIVE to ("न" to "na"),
)
private val DEFAULT_NEGATOR = "नहीं" to "nahin"

/** Pronoun → ergative form (suppletive: मैं→मैंने, यह→इसने). */
private val ERGATIVE_PRONOUN: Map<String, String> = mapOf(
    "मैं" to "मैंने",
    "हम" to "हमने",
    "तू" to "तूने",
    "तुम" to "तुमने",
    "आप" to "आपने",
    "यह" to "इसने",
    "ये" to "इन्होंने",
)
private val ERGATIVE_PRONOUN_ROMAN: Map<String, String> = mapOf(
    "main" to "maine",
    "ham" to "hamne",
    "tu" to "tune",
    "tum" to "tumne",
    "aap" to "aapne",
    "yah" to "isne",
    "ye" to "inhonne",
)

/** Perfective TAMs that trigger the ने-ergative for transitive verbs. */
private val ERGATIVE_TAMS: Set<Tam> = setOf(Tam.PERFECT, Tam.PAST_PERFECT)

object Render {
    /** The preverbal negation particle for a TAM. */
    fun negator(tam: Tam, roman: Boolean = false): String {
        val (dev, rom) = NEGATOR[tam] ?: DEFAULT_NEGATOR
        return if (roman) rom else dev
    }

    /** The verb complex with negation applied (preverbal particle). */
    fun predicate(verbSurface: String, tam: Tam, polarity: Polarity, roman: Boolean = false): String {
        if (polarity == Polarity.AFFIRMATIVE) return verbSurface
        return "${negator(tam, roman)} $verbSurface"
    }

    /** The subject pronoun for an agreement bundle, in the elicited script. */
    fun subjectPronoun(agr: Agreement, script: Script): String {
        val table = if (script == Script.ROMANIZED) SUBJECT_PRONOUN_ROMAN else SUBJECT_PRONOUN
        return table.getValue(Triple(agr.person, agr.number, agr.honorific))
    }

    /**
     * Join subject + predicate (SOV), inserting ने for transitive perfectives.
     * The ने-ergative is a property of the SIMPLE perfective only — the compound
     * constructions keep a nominative subject (मैं कर सका; काम किया जाता है).
     */
    fun attachSubject(
        agr: Agreement,
        predicateText: String,
        tam: Tam,
        transitivity: Transitivity,
        script: Script,
        construction: Construction = Construction.SIMPLE,
    ): String {
        var pronoun = subjectPronoun(agr, script)
        val isErgative = construction == Construction.SIMPLE &&
            transitivity == Transitivity.TRANSITIVE && tam in ERGATIVE_TAMS
        if (isErgative) {
            val map = if (script == Script.ROMANIZED) ERGATIVE_PRONOUN_ROMAN else ERGATIVE_PRONOUN
            pronoun = map[pronoun] ?: pronoun
        }
        return "$pronoun $predicateText"
    }
}
