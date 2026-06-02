/*
 * The learner model — ports of konjugaton's `state/scoring.py` + `vocab_state.py`.
 *
 *   1. NOW  — `scores`: the vocab -> knowledge-type -> ScoreCell map.
 *   2. IRT  — `abilities`: a latent ability theta per Skill, updated online.
 *
 * Plain mutable Kotlin (no serialization annotations). The data-layer Store
 * converts to/from a JSON snapshot that is byte-compatible with konjugaton.
 */
package com.konjugaton.hc.domain

/** EWMA smoothing factor. Higher = faster to react to recent answers. */
const val DEFAULT_ALPHA = 0.35

/** Mastery evidence for one (vocab, knowledge-type) pair. */
data class ScoreCell(
    var attempts: Int = 0,
    var correct: Int = 0,
    var ewma: Double = 0.0,
    var lastSeen: String? = null,
) {
    fun register(correct: Boolean, timestamp: String, alpha: Double = DEFAULT_ALPHA) {
        val target = if (correct) 1.0 else 0.0
        ewma = if (attempts == 0) target else alpha * target + (1 - alpha) * ewma
        attempts += 1
        if (correct) this.correct += 1
        lastSeen = timestamp
    }

    val accuracy: Double get() = if (attempts > 0) correct.toDouble() / attempts else 0.0
}

/** Mutable learner state. */
class VocabState(
    /** lemma -> knowledge-type -> score cell */
    val scores: MutableMap<String, MutableMap<KnowledgeType, ScoreCell>> = mutableMapOf(),
    /** Skill.key -> IRT ability estimate (theta) */
    val abilities: MutableMap<String, Double> = mutableMapOf(),
) {
    fun cell(lemma: String, knowledge: KnowledgeType): ScoreCell =
        scores.getOrPut(lemma) { mutableMapOf() }.getOrPut(knowledge) { ScoreCell() }

    fun ability(skill: Skill): Double = abilities[skill.key] ?: 0.0

    fun record(item: Item, correct: Boolean, timestamp: String) {
        cell(item.coordinate.lemma, item.coordinate.knowledge).register(correct, timestamp)
        val theta = ability(item.skill)
        abilities[item.skill.key] = Irt.updateAbility(theta, item.irt, correct)
    }
}
