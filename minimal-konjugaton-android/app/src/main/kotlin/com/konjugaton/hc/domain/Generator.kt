/*
 * Turn a Coordinate into a concrete, gradable Item.
 *
 * Port of konjugaton's `engine/generator.py`. Difficulty is seeded heuristically
 * from the cell's features (TAM, verb class, gender, polarity, knowledge); once
 * response data exists, IRT can calibrate real parameters and replace it.
 *
 * Three knowledge types: production (cloze in the elicited script), recognition
 * (MC over plausible wrong forms), transliteration (show the OTHER script, ask
 * for the coordinate's).
 */
package com.konjugaton.hc.domain

import kotlin.random.Random

private const val BLANK = "_____"

// --- IRT difficulty seed tables -------------------------------------------
private val TAM_BASE: Map<Tam, Double> = mapOf(
    Tam.PRESENT_HABITUAL to 0.0,
    Tam.PAST_HABITUAL to 0.3,
    Tam.PRESENT_PROGRESSIVE to 0.4,
    Tam.PAST_PROGRESSIVE to 0.6,
    Tam.PERFECT to 0.8,
    Tam.PAST_PERFECT to 0.9,
    Tam.FUTURE to 0.5,
    Tam.SUBJUNCTIVE to 1.2,
    Tam.IMPERATIVE to 0.2,
)
private val CLASS_DELTA: Map<String, Double> = mapOf("regular" to 0.0, "irregular" to 0.6)
private val KNOWLEDGE_DELTA: Map<KnowledgeType, Double> = mapOf(
    KnowledgeType.PRODUCTION to 0.3,
    KnowledgeType.RECOGNITION to -0.3,
    KnowledgeType.TRANSLITERATION to 0.1,
)
private val CONSTRUCTION_DELTA: Map<Construction, Double> = mapOf(
    Construction.SIMPLE to 0.0,
    Construction.ABILITY to 0.5,
    Construction.COMPLETIVE to 0.6,
    Construction.DESIDERATIVE to 0.5,
    Construction.INCEPTIVE to 0.6,
    Construction.PASSIVE to 0.8,
)

/** Build items from coordinates, using the conjugator and catalog data. */
class ExerciseGenerator(
    private val catalog: Catalog,
    private val conjugator: Conjugator,
) {
    fun generate(coordinate: Coordinate, rng: Random): Item {
        val verb = catalog.verb(coordinate.lemma)
        val agr = coordinate.agreement()
        val form = conjugator.conjugateConstruction(verb, coordinate.tam, agr, coordinate.construction)

        val roman = coordinate.script == Script.ROMANIZED
        val verbSurface = if (roman) form.surfaceRoman else form.surface
        val predicate = Render.predicate(verbSurface, coordinate.tam, coordinate.polarity, roman)
        val clause = Render.attachSubject(
            agr, predicate, coordinate.tam, verb.transitivity, coordinate.script,
            coordinate.construction,
        )

        val ctx = catalog.contexts.getValue(coordinate.context)
        val templates = if (roman) ctx.templatesRoman else ctx.templates
        val template = templates[rng.nextInt(templates.size)]
        val subject = Render.subjectPronoun(agr, coordinate.script)
        val fullSentence = template.replace("{subject} {verb}", clause)
        val cloze = template.replace("{subject}", subject).replace("{verb}", BLANK)

        if (coordinate.knowledge == KnowledgeType.TRANSLITERATION) {
            return transliterationItem(coordinate, verb, form, fullSentence)
        }

        val answer = predicate
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
            irt = irt(verb.verbClass, coordinate, choices.size),
            accepted = listOf(answer),
            choices = choices,
            lemmaHint = if (roman) verb.lemmaRoman else verb.lemma,
            task = task(coordinate),
            fullSentence = fullSentence,
            metadata = mapOf(
                "polarity" to coordinate.polarity.value,
                "translation" to verb.translation,
                "script" to coordinate.script.value,
            ),
        )
    }

    // -- transliteration knowledge type -------------------------------------

    private fun transliterationItem(
        coordinate: Coordinate,
        verb: Verb,
        form: ConjugatedForm,
        fullSentence: String,
    ): Item {
        val toRoman = coordinate.script == Script.ROMANIZED
        val source = if (toRoman) form.surface else form.surfaceRoman
        val answer = if (toRoman) form.surfaceRoman else form.surface
        val direction = if (toRoman) "romanize" else "write in Devanagari"
        return Item(
            coordinate = coordinate,
            skill = coordinate.skill(verb.verbClass),
            prompt = "$direction:  $source   $BLANK",
            answer = answer,
            irt = irt(verb.verbClass, coordinate, 0),
            accepted = listOf(answer),
            lemmaHint = if (toRoman) verb.lemmaRoman else verb.lemma,
            task = task(coordinate),
            fullSentence = fullSentence,
            metadata = mapOf(
                "translation" to verb.translation,
                "script" to coordinate.script.value,
                "transliteration" to "true",
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

    /** Wrong-but-tempting forms: same verb, wrong gender/number or wrong TAM. */
    private fun distractors(
        verb: Verb,
        coordinate: Coordinate,
        agr: Agreement,
        answer: String,
        rng: Random,
        k: Int = 3,
    ): List<String> {
        val roman = coordinate.script == Script.ROMANIZED
        val cons = coordinate.construction
        val candidates = mutableListOf<String>()

        for (g in Gender.entries) {
            for (n in Number.entries) {
                val alt = Agreement(agr.person, n, g, agr.honorific)
                if (alt == agr || !conjugator.realizableAgreement(coordinate.tam, alt)) continue
                val form = conjugator.conjugateConstruction(verb, coordinate.tam, alt, cons)
                val surface = if (roman) form.surfaceRoman else form.surface
                candidates.add(Render.predicate(surface, coordinate.tam, coordinate.polarity, roman))
            }
        }

        for (tam in supportedTams()) {
            if (tam == coordinate.tam || !conjugator.realizableConstruction(verb, tam, cons)) continue
            if (!conjugator.realizableAgreement(tam, agr)) continue
            val form = conjugator.conjugateConstruction(verb, tam, agr, cons)
            val surface = if (roman) form.surfaceRoman else form.surface
            candidates.add(Render.predicate(surface, tam, coordinate.polarity, roman))
        }

        val unique = candidates.distinct().filter { it != answer }.toMutableList()
        unique.shuffle(rng)
        return unique.take(k)
    }

    // -- task string + IRT seed ---------------------------------------------

    /** The grammatical target. MUST encode every answer-determining axis. */
    private fun task(c: Coordinate): String {
        val bits = mutableListOf(
            Labels.tamOf(c.tam),
            "${Labels.personOf(c.person)}·${Labels.numberOf(c.number)}",
            Labels.genderOf(c.gender),
        )
        if (c.honorific.value != "neutral") bits.add(Labels.honorificOf(c.honorific))
        bits.add(Labels.polarityOf(c.polarity))
        // The construction is answer-determining; only surfaced when marked.
        if (c.construction != Construction.SIMPLE) bits.add(Labels.constructionOf(c.construction))
        return bits.joinToString(" · ")
    }

    private fun irt(verbClass: VerbClass, coordinate: Coordinate, nChoices: Int): IrtParameters {
        var b = TAM_BASE[coordinate.tam] ?: 0.5
        b += CLASS_DELTA.getValue(verbClass.value)
        if (coordinate.polarity == Polarity.NEGATIVE) b += 0.2
        if (coordinate.gender.value == "f") b += 0.1
        b += KNOWLEDGE_DELTA[coordinate.knowledge] ?: 0.0
        b += CONSTRUCTION_DELTA[coordinate.construction] ?: 0.0
        b = b.coerceIn(-3.0, 3.0)

        val guessing = if (nChoices > 0) 1.0 / nChoices else 0.0
        return IrtParameters(round3(b), 1.0, round3(guessing))
    }
}

private fun round3(x: Double): Double = Math.round(x * 1000.0) / 1000.0
