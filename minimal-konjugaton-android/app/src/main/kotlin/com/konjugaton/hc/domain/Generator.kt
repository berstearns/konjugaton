/*
 * Turn a Coordinate into a concrete, gradable Item.
 *
 * Port of konjugaton's `engine/generator.py` (German). Difficulty is seeded
 * heuristically from the cell's features (tense-mood, verb class, register, voice,
 * polarity, knowledge); once response data exists, IRT can calibrate real
 * parameters and replace it.
 *
 * Two knowledge types are realized here: production (a cloze; the learner types
 * the verb complex) and recognition (multiple choice over plausible wrong forms).
 */
package com.konjugaton.hc.domain

import kotlin.random.Random

private const val BLANK = "_____"

// --- IRT difficulty seed tables -------------------------------------------
private val TENSE_BASE: Map<TenseMood, Double> = mapOf(
    TenseMood.PRAESENS to 0.0,
    TenseMood.PRAETERITUM to 0.4,
    TenseMood.PERFEKT to 0.5,
    TenseMood.PLUSQUAMPERFEKT to 0.8,
    TenseMood.FUTUR1 to 0.5,
    TenseMood.FUTUR2 to 1.0,
    TenseMood.KONJUNKTIV1 to 1.1,
    TenseMood.KONJUNKTIV2 to 1.2,
    TenseMood.IMPERATIV to 0.3,
)
private val CLASS_DELTA: Map<String, Double> = mapOf(
    "weak" to 0.0,
    "strong" to 0.4,
    "mixed" to 0.5,
    "irregular" to 0.6,
)
private val KNOWLEDGE_DELTA: Map<KnowledgeType, Double> = mapOf(
    KnowledgeType.PRODUCTION to 0.3,
    KnowledgeType.RECOGNITION to -0.3,
)

/** Build items from coordinates, using the conjugator and catalog data. */
class ExerciseGenerator(
    private val catalog: Catalog,
    private val conjugator: Conjugator,
) {
    fun generate(coordinate: Coordinate, rng: Random): Item {
        val verb = catalog.verb(coordinate.lemma)
        val agr = coordinate.agreement()
        val form = conjugator.conjugateVoice(verb, coordinate.tenseMood, agr, coordinate.voice)
        val answer = Render.predicate(form, coordinate.tenseMood, coordinate.polarity, coordinate.register)
        val clause = Render.attachSubject(agr, answer, coordinate.tenseMood)

        val ctx = catalog.contexts.getValue(coordinate.context)
        val template = ctx.templates[rng.nextInt(ctx.templates.size)]
        val subject =
            if (coordinate.tenseMood == TenseMood.IMPERATIV) "" else Render.subjectPronoun(agr)
        val fullSentence = template.replace("{subject} {verb}", clause).trim()
        val cloze = template.replace("{subject}", subject).replace("{verb}", BLANK).trim()

        val choices: List<String> =
            if (coordinate.knowledge == KnowledgeType.RECOGNITION) {
                buildChoices(verb, coordinate, agr, answer, rng)
            } else {
                emptyList()
            }

        return Item(
            coordinate = coordinate,
            skill = coordinate.skill(verb.verbClass),
            prompt = cloze,
            answer = answer,
            irt = seedIrt(verb.verbClass, coordinate, choices.size),
            accepted = listOf(answer),
            choices = choices,
            lemmaHint = verb.lemma,
            task = task(coordinate),
            fullSentence = fullSentence,
            metadata = mapOf(
                "polarity" to coordinate.polarity.value,
                "voice" to coordinate.voice.value,
                "translation" to verb.translation,
            ),
        )
    }

    // -- multiple-choice distractors ----------------------------------------

    private fun buildChoices(
        verb: Verb,
        coordinate: Coordinate,
        agr: Agreement,
        answer: String,
        rng: Random,
    ): List<String> {
        val distractors = distractors(verb, coordinate, agr, answer, rng)
        val options = (listOf(answer) + distractors).toMutableList()
        options.shuffle(rng)
        return options
    }

    /** Wrong-but-tempting forms: same verb+voice, wrong agreement or wrong tense. */
    private fun distractors(
        verb: Verb,
        coordinate: Coordinate,
        agr: Agreement,
        answer: String,
        rng: Random,
        k: Int = 3,
    ): List<String> {
        val tm = coordinate.tenseMood
        val voice = coordinate.voice
        val pol = coordinate.polarity
        val reg = coordinate.register
        val candidates = mutableListOf<String>()

        // Wrong agreement (other legal bundles for this tense).
        for (alt in allAgreements()) {
            if (alt == agr || !conjugator.realizableAgreement(tm, alt)) continue
            val form = conjugator.conjugateVoice(verb, tm, alt, voice)
            candidates.add(Render.predicate(form, tm, pol, alt.register))
        }
        // Wrong tense (same agreement).
        for (altTm in supportedTenseMoods()) {
            if (altTm == tm || !conjugator.realizableVoice(verb, altTm, voice)) continue
            if (!conjugator.realizableAgreement(altTm, agr)) continue
            val form = conjugator.conjugateVoice(verb, altTm, agr, voice)
            candidates.add(Render.predicate(form, altTm, pol, reg))
        }

        val unique = candidates.distinct().filter { it != answer }.toMutableList()
        unique.shuffle(rng)
        return unique.take(k)
    }

    // -- task string + IRT seed ---------------------------------------------

    /** The grammatical target. MUST encode every answer-determining axis. */
    private fun task(c: Coordinate): String {
        val bits = mutableListOf(
            Labels.tenseOf(c.tenseMood),
            "${Labels.personOf(c.person)}·${Labels.numberOf(c.number)}",
        )
        if (c.register != Register.NEUTRAL) bits.add(Labels.registerOf(c.register))
        if (c.voice == Voice.PASSIV) bits.add(Labels.voiceOf(c.voice))
        bits.add(Labels.polarityOf(c.polarity))
        return bits.joinToString(" · ")
    }

    private fun irt(verbClass: VerbClass, coordinate: Coordinate, nChoices: Int): IrtParameters =
        seedIrt(verbClass, coordinate, nChoices)
}

/**
 * Heuristic IRT seed from a cell's features. Shared by every item builder
 * (ExerciseGenerator and the conjugation-table builder) so both paths seed
 * difficulty identically. Transparent and overrideable once data exists.
 */
fun seedIrt(verbClass: VerbClass, coordinate: Coordinate, nChoices: Int): IrtParameters {
    var b = TENSE_BASE[coordinate.tenseMood] ?: 0.5
    b += CLASS_DELTA.getValue(verbClass.value)
    if (coordinate.polarity == Polarity.NEGATIVE) b += 0.15
    if (coordinate.voice == Voice.PASSIV) b += 0.4
    b += KNOWLEDGE_DELTA[coordinate.knowledge] ?: 0.0
    b = b.coerceIn(-3.0, 3.0)

    val guessing = if (nChoices > 0) 1.0 / nChoices else 0.0
    return IrtParameters(round3(b), 1.0, round3(guessing))
}

private fun round3(x: Double): Double = Math.round(x * 1000.0) / 1000.0
