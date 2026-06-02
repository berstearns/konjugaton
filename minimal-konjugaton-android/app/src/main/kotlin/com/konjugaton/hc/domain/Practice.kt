/*
 * Build practice sessions and grade responses.
 *
 * Port of konjugaton's `services/practice.py`. Samples the space (reservoir
 * sampling so we never materialize the full 184,920-coordinate product),
 * generates and orders items, and delegates grading to a [Grader].
 */
package com.konjugaton.hc.domain

import kotlin.random.Random

/** Safety bound on how many coordinates the sampler will scan. */
private const val CANDIDATE_SCAN_CAP = 200_000

enum class SessionOrder {
    ADAPTIVE, // most informative first (needs state)
    EASY_FIRST,
    HARD_FIRST,
    RANDOM,
}

class PracticeService(
    private val catalog: Catalog,
    private val conjugator: Conjugator,
    private val space: PermutationSpace,
    private val generator: ExerciseGenerator,
    private val rng: Random,
    private val grader: Grader,
) {
    companion object {
        /** Wire up the whole engine from a loaded catalog. */
        fun create(
            catalog: Catalog,
            seed: Long? = null,
            grading: GradingSettings = GradingSettings(),
        ): PracticeService {
            val conjugator = Conjugator(catalog.endings, catalog.verbs)
            val space = PermutationSpace(catalog, conjugator)
            val generator = ExerciseGenerator(catalog, conjugator)
            val rng = if (seed != null) Random(seed) else Random.Default
            return PracticeService(catalog, conjugator, space, generator, rng, Grader(grading))
        }
    }

    // -- session building ---------------------------------------------------

    fun buildSession(
        selection: AxisSelection,
        count: Int,
        state: VocabState? = null,
        order: SessionOrder = SessionOrder.ADAPTIVE,
    ): List<Item> {
        val candidates = reservoirSample(selection, maxOf(count * 6, count))
        val items = candidates.map { generator.generate(it, rng) }
        return order(items, state, order).take(count)
    }

    private fun reservoirSample(selection: AxisSelection, k: Int): List<Coordinate> {
        val reservoir = ArrayList<Coordinate>(k)
        var i = 0
        for (coord in space.iterCoordinates(selection)) {
            if (i < k) {
                reservoir.add(coord)
            } else {
                val j = rng.nextInt(i + 1) // randint(0, i) inclusive
                if (j < k) reservoir[j] = coord
            }
            i++
            if (i >= CANDIDATE_SCAN_CAP) break
        }
        return reservoir
    }

    private fun order(items: List<Item>, state: VocabState?, order: SessionOrder): List<Item> =
        when (order) {
            SessionOrder.RANDOM -> items.shuffled(rng)
            SessionOrder.HARD_FIRST -> items.sortedByDescending { it.irt.difficulty }
            SessionOrder.ADAPTIVE ->
                if (state != null) {
                    items.sortedByDescending { Irt.information(state.ability(it.skill), it.irt) }
                } else {
                    items.sortedBy { it.irt.difficulty }
                }
            SessionOrder.EASY_FIRST -> items.sortedBy { it.irt.difficulty }
        }

    // -- grading ------------------------------------------------------------

    fun grade(item: Item, given: String): GradedResponse = grader.grade(item, given)
}
