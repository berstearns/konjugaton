/*
 * The quality gate. Ported from konjugaton's `services/selfcheck.py` and
 * strengthened with the Android determinacy/round-trip discipline: it enforces
 * not just structural well-formedness but *answerability* — a German cloze is
 * genuinely ambiguous without its full task (the finite verb agrees in person +
 * number, the register selects the form, and voice/polarity change the surface).
 *
 * Invariants, per generated item:
 *   structural   — non-empty answer, prompt has a blank, finite/in-range IRT,
 *                  the lemma is presented.
 *   determinacy  — the displayed `task` encodes every answer-determining axis:
 *                  tense-mood, person+number, register (when not NEUTRAL),
 *                  voice (when PASSIV) and polarity.
 *   self-grading — the item's OWN answer grades CORRECT (generator ⇔ grader).
 *   recognition  — answer ∈ choices, ≥2 distinct non-empty choices.
 *
 * The expected determinacy tokens are re-derived from `item.coordinate` via
 * [Labels] — the same single source of truth the generator uses to build
 * `Item.task` — so the check stays in lock-step with what the learner sees.
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

        // -- determinacy -------------------------------------------------------
        // Re-derive the answer-determining axis tokens and require each to appear
        // in the displayed task. Conservative: only the axes that actually shift
        // the surface are demanded — register only when it leaves NEUTRAL, voice
        // only for the werden-Passiv (mirrors ExerciseGenerator.task()).
        for (token in expectedTaskTokens(c)) {
            if (token !in item.task) issues += "task missing axis token '$token': '${item.task}'"
        }

        // -- self-grading ------------------------------------------------------
        if (grader.grade(item, item.answer).grade != Grade.CORRECT) {
            issues += "item's own answer does not grade CORRECT"
        }

        issues += knowledgeSpecific(item)
        return issues
    }

    /**
     * The axis tokens the task must contain to make the cloze single-answer.
     * Derived from the coordinate via [Labels] — same logic the generator uses.
     */
    private fun expectedTaskTokens(c: Coordinate): List<String> {
        val tokens = mutableListOf(
            Labels.tenseOf(c.tenseMood),
            Labels.personOf(c.person),
            Labels.numberOf(c.number),
        )
        if (c.register != Register.NEUTRAL) tokens += Labels.registerOf(c.register)
        if (c.voice == Voice.PASSIV) tokens += Labels.voiceOf(c.voice)
        tokens += Labels.polarityOf(c.polarity)
        return tokens
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

/** Outcome of an exhaustive self-check run. */
data class SelfCheckReport(
    val verbs: Int,
    // Number of distinct tense-moods touched. Named `tams` for API continuity
    // with the report screen and tests that read `report.tams`.
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
            tams += coord.tenseMood.value
            val where = "${coord.lemma}/${coord.tenseMood.value}/${coord.person.value}" +
                "${coord.number.value}/${coord.register.value}/${coord.voice.value}/" +
                "${coord.polarity.value}/${coord.knowledge.value}"
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
