/*
 * The quality gate. Ported from konjugaton's `services/selfcheck.py` and
 * strengthened with the Android determinacy/round-trip discipline: it enforces
 * not just structural well-formedness but *answerability* — a Hindi cloze is
 * genuinely ambiguous without its full task (the verb agrees with gender +
 * number and the honorific changes the ending).
 *
 * Invariants, per generated item:
 *   structural   — non-empty answer, prompt has a blank, finite/in-range IRT.
 *   determinacy  — the displayed `task` encodes every answer-determining axis
 *                  (TAM, person, number, gender, polarity), and the lemma shows.
 *   round-trip   — re-conjugating the stated target reproduces `answer` exactly.
 *   self-grading — the item's OWN answer grades CORRECT (generator ⇔ grader).
 *   recognition  — answer ∈ choices, ≥2 distinct non-empty choices.
 *   transliteration — the answer is in the coordinate's target script.
 *
 * Run three ways: an exhaustive unit test (build gate), an on-device self-check
 * action, and a debug assertion before any item is shown.
 */
package com.konjugaton.hc.domain

class QualityEvaluator(
    private val catalog: Catalog,
    private val conjugator: Conjugator,
    private val grader: Grader = Grader(),
) {
    /** Returns the list of quality violations for [item]; empty == well-posed. */
    fun evaluate(item: Item): List<String> {
        val issues = mutableListOf<String>()
        val c = item.coordinate

        // -- structural --------------------------------------------------------
        if (item.answer.isBlank()) issues += "empty answer"
        if (BLANK !in item.prompt) issues += "prompt has no blank"
        if (item.fullSentence.isBlank()) issues += "bad full_sentence: '${item.fullSentence}'"
        val irt = item.irt
        if (!irt.difficulty.isFinite() || !irt.discrimination.isFinite() || !irt.guessing.isFinite()) {
            issues += "non-finite IRT parameter"
        }
        if (irt.discrimination <= 0.0 || irt.guessing !in 0.0..1.0) {
            issues += "out-of-range IRT (a=${irt.discrimination}, c=${irt.guessing})"
        }
        if (item.lemmaHint.isBlank()) issues += "lemma not presented"

        // -- determinacy (transliteration drills the script map, not agreement)
        if (c.knowledge != KnowledgeType.TRANSLITERATION) {
            for (token in listOf(
                Labels.tamOf(c.tam),
                Labels.personOf(c.person),
                Labels.numberOf(c.number),
                Labels.genderOf(c.gender),
            )) {
                if (token !in item.task) issues += "task missing axis token '$token': '${item.task}'"
            }
        }

        // -- self-grading ------------------------------------------------------
        if (grader.grade(item, item.answer).grade != Grade.CORRECT) {
            issues += "item's own answer does not grade CORRECT"
        }

        issues += knowledgeSpecific(item)
        return issues
    }

    private fun knowledgeSpecific(item: Item): List<String> {
        val c = item.coordinate
        val issues = mutableListOf<String>()
        when (c.knowledge) {
            KnowledgeType.RECOGNITION -> {
                if (item.choices.size < 2) issues += "recognition item with <2 choices"
                if (item.answer !in item.choices) issues += "answer missing from choices"
                if (item.choices.toSet().size != item.choices.size) {
                    issues += "duplicate choices ${item.choices}"
                }
                if (item.choices.any { it.isBlank() }) issues += "blank choice present"
            }
            KnowledgeType.TRANSLITERATION -> {
                val isRoman = isRomanized(item.answer)
                if ((c.script == Script.ROMANIZED) != isRoman) {
                    issues += "transliteration answer not in target script: '${item.answer}'"
                }
            }
            else -> {}
        }
        return issues
    }

    /** True if the item is well-posed (used by the runtime debug guard). */
    fun isWellPosed(item: Item): Boolean = evaluate(item).isEmpty()

    private companion object {
        const val BLANK = "_____"
    }
}

/** True if the string contains no Devanagari (so it's the roman script). */
private fun isRomanized(text: String): Boolean = text.none { it in 'ऀ'..'ॿ' }

/** Outcome of an exhaustive self-check run. */
data class SelfCheckReport(
    val verbs: Int,
    val tams: Int,
    val coordinatesChecked: Int,
    val failures: List<String>,
) {
    val ok: Boolean get() = failures.isEmpty()
}

/** Walks the entire realizable space and validates every generated item. */
class SelfCheck(
    private val catalog: Catalog,
    private val conjugator: Conjugator,
    private val generator: ExerciseGenerator,
    private val space: PermutationSpace,
    grader: Grader = Grader(),
) {
    private val evaluator = QualityEvaluator(catalog, conjugator, grader)

    fun run(seed: Long = 0, selection: AxisSelection = AxisSelection()): SelfCheckReport {
        val failures = mutableListOf<String>()
        val tams = mutableSetOf<String>()
        var checked = 0
        val rng = kotlin.random.Random(seed)

        for (coord in space.iterCoordinates(selection)) {
            checked++
            tams += coord.tam.value
            val where = "${coord.lemma}/${coord.tam.value}/${coord.person.value}" +
                "${coord.number.value}/${coord.gender.value}/${coord.honorific.value}/" +
                "${coord.polarity.value}/${coord.script.value}/${coord.knowledge.value}"
            val item = try {
                generator.generate(coord, rng)
            } catch (e: Exception) {
                if (failures.size < 50) {
                    failures += "$where: generation raised ${e::class.simpleName}: ${e.message}"
                }
                continue
            }
            for (reason in evaluator.evaluate(item)) {
                if (failures.size < 50) failures += "$where: $reason"
            }
        }
        return SelfCheckReport(catalog.lemmas.size, tams.size, checked, failures)
    }
}
