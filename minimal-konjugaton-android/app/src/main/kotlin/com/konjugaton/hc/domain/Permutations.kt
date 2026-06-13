/*
 * Enumerate the combinatorial exercise space.
 *
 * Port of konjugaton's `engine/permutations.py` (German). The space is the
 * Cartesian product of the axes:
 *
 *   lemma × tense-mood × person × number × register × voice × polarity
 *         × knowledge × context
 *
 * filtered to the cells the conjugator can realize: the legal agreement bundles
 * (the imperative is 2nd-person only, realizableAgreement) and the legal voices
 * (the werden-passive is transitive-only and indicative-tense-only,
 * realizableVoice). The legal (person, number, register) triples are read once
 * from the pronoun table, so no ungrammatical bundle (e.g. "1st-person Sie") is
 * ever emitted.
 */
package com.konjugaton.hc.domain

/** Knowledge types with a generator implementation today. */
val IMPLEMENTED_KNOWLEDGE: List<KnowledgeType> =
    listOf(KnowledgeType.PRODUCTION, KnowledgeType.RECOGNITION)

val ALL_POLARITIES: List<Polarity> = Polarity.entries.toList()
val ALL_VOICES: List<Voice> = Voice.entries.toList()

/** The legal (person, number, register) triples, read from the pronoun table. */
private val LEGAL_PNR: List<Triple<Person, Number, Register>> = SUBJECT_PRONOUN.keys.toList()

/** Every legal agreement bundle, optionally narrowed by each sub-axis. */
fun allAgreements(
    persons: List<Person> = emptyList(),
    numbers: List<Number> = emptyList(),
    registers: List<Register> = emptyList(),
): List<Agreement> {
    val out = mutableListOf<Agreement>()
    for ((person, number, register) in LEGAL_PNR) {
        if (persons.isNotEmpty() && person !in persons) continue
        if (numbers.isNotEmpty() && number !in numbers) continue
        if (registers.isNotEmpty() && register !in registers) continue
        out.add(Agreement(person, number, register))
    }
    return out
}

/** A narrowing filter over each axis. Empty list means 'all'. */
data class AxisSelection(
    val lemmas: List<String> = emptyList(),
    val tenseMoods: List<TenseMood> = emptyList(),
    val persons: List<Person> = emptyList(),
    val numbers: List<Number> = emptyList(),
    val registers: List<Register> = emptyList(),
    val voices: List<Voice> = emptyList(),
    val polarities: List<Polarity> = emptyList(),
    val knowledge: List<KnowledgeType> = emptyList(),
    val contexts: List<String> = emptyList(),
)

/** Queryable view over the realizable exercise coordinates. */
class PermutationSpace(
    private val catalog: Catalog,
    private val conjugator: Conjugator,
) {
    private fun tenses(sel: AxisSelection): List<TenseMood> {
        var ts = supportedTenseMoods()
        if (sel.tenseMoods.isNotEmpty()) ts = ts.filter { it in sel.tenseMoods }
        return ts
    }

    private fun lemmas(sel: AxisSelection): List<String> = sel.lemmas.ifEmpty { catalog.lemmas }
    private fun contexts(sel: AxisSelection): List<String> = sel.contexts.ifEmpty { catalog.contextIds }
    private fun voices(sel: AxisSelection): List<Voice> = sel.voices.ifEmpty { ALL_VOICES }
    private fun agreements(sel: AxisSelection): List<Agreement> =
        allAgreements(sel.persons, sel.numbers, sel.registers)

    /** Yield every realizable coordinate in the (possibly narrowed) space. */
    fun iterCoordinates(sel: AxisSelection = AxisSelection()): Sequence<Coordinate> = sequence {
        val polarities = sel.polarities.ifEmpty { ALL_POLARITIES }
        val knowledge = sel.knowledge.ifEmpty { IMPLEMENTED_KNOWLEDGE }
        val contexts = contexts(sel)
        val agreements = agreements(sel)

        for (tm in tenses(sel)) {
            for (voice in voices(sel)) {
                for (lemma in lemmas(sel)) {
                    val verb = catalog.verb(lemma)
                    if (!conjugator.realizableVoice(verb, tm, voice)) continue
                    for (agr in agreements) {
                        if (!conjugator.realizableAgreement(tm, agr)) continue
                        for (polarity in polarities) {
                            for (know in knowledge) {
                                for (context in contexts) {
                                    yield(
                                        Coordinate(
                                            lemma = lemma,
                                            tenseMood = tm,
                                            person = agr.person,
                                            number = agr.number,
                                            register = agr.register,
                                            polarity = polarity,
                                            knowledge = know,
                                            context = context,
                                            voice = voice,
                                        ),
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    /** Size of the (narrowed) realizable space, without materializing it. */
    fun count(sel: AxisSelection = AxisSelection()): Int {
        val nPolarities = sel.polarities.ifEmpty { ALL_POLARITIES }.size
        val nKnowledge = sel.knowledge.ifEmpty { IMPLEMENTED_KNOWLEDGE }.size
        val nContexts = contexts(sel).size
        val perCell = nPolarities * nKnowledge * nContexts
        val agreements = agreements(sel)
        val lemmas = lemmas(sel)

        var total = 0
        for (tm in tenses(sel)) {
            val realizableAgr = agreements.count { conjugator.realizableAgreement(tm, it) }
            if (realizableAgr == 0) continue
            for (voice in voices(sel)) {
                val verbsOk = lemmas.count {
                    conjugator.realizableVoice(catalog.verb(it), tm, voice)
                }
                total += verbsOk * realizableAgr * perCell
            }
        }
        return total
    }
}
