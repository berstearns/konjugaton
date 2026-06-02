/*
 * Enumerate the combinatorial exercise space.
 *
 * Port of konjugaton's `engine/permutations.py`. The space is the Cartesian
 * product of the axes:
 *
 *   lemma × TAM × person × number × gender × honorific × polarity × script
 *         × knowledge × context
 *
 * filtered to the cells the conjugator can realize (canConjugate) AND the
 * agreement bundles Hindi licenses (realizableAgreement). The legal (person,
 * number, honorific) triples are read once from the pronoun table, then crossed
 * with gender — so we never emit an ungrammatical bundle like "1st person आप".
 */
package com.konjugaton.hc.domain

/** Knowledge types with a generator implementation today. */
val IMPLEMENTED_KNOWLEDGE: List<KnowledgeType> =
    listOf(KnowledgeType.PRODUCTION, KnowledgeType.RECOGNITION, KnowledgeType.TRANSLITERATION)

val ALL_POLARITIES: List<Polarity> = Polarity.entries.toList()
val ALL_SCRIPTS: List<Script> = Script.entries.toList()
val ALL_GENDERS: List<Gender> = Gender.entries.toList()

/** All verbal constructions, SIMPLE first so the unmarked space enumerates first. */
val ALL_CONSTRUCTIONS: List<Construction> = Construction.entries.toList()

/** The legal (person, number, honorific) triples, read from the pronoun table. */
private val LEGAL_PNH: List<Triple<Person, Number, Honorific>> = SUBJECT_PRONOUN.keys.toList()

/** Every legal agreement bundle, optionally narrowed by each sub-axis. */
fun allAgreements(
    persons: List<Person> = emptyList(),
    numbers: List<Number> = emptyList(),
    genders: List<Gender> = emptyList(),
    honorifics: List<Honorific> = emptyList(),
): List<Agreement> {
    val out = mutableListOf<Agreement>()
    for ((person, number, honorific) in LEGAL_PNH) {
        if (persons.isNotEmpty() && person !in persons) continue
        if (numbers.isNotEmpty() && number !in numbers) continue
        if (honorifics.isNotEmpty() && honorific !in honorifics) continue
        for (gender in genders.ifEmpty { ALL_GENDERS }) {
            out.add(Agreement(person, number, gender, honorific))
        }
    }
    return out
}

/** A narrowing filter over each axis. Empty list means 'all'. */
data class AxisSelection(
    val lemmas: List<String> = emptyList(),
    val tams: List<Tam> = emptyList(),
    val persons: List<Person> = emptyList(),
    val numbers: List<Number> = emptyList(),
    val genders: List<Gender> = emptyList(),
    val honorifics: List<Honorific> = emptyList(),
    val polarities: List<Polarity> = emptyList(),
    val scripts: List<Script> = emptyList(),
    val knowledge: List<KnowledgeType> = emptyList(),
    val contexts: List<String> = emptyList(),
    val constructions: List<Construction> = emptyList(),
)

/** Queryable view over the realizable exercise coordinates. */
class PermutationSpace(
    private val catalog: Catalog,
    private val conjugator: Conjugator,
) {
    private fun tams(sel: AxisSelection): List<Tam> {
        var ts = supportedTams()
        if (sel.tams.isNotEmpty()) ts = ts.filter { it in sel.tams }
        return ts
    }

    private fun lemmas(sel: AxisSelection): List<String> = sel.lemmas.ifEmpty { catalog.lemmas }
    private fun contexts(sel: AxisSelection): List<String> = sel.contexts.ifEmpty { catalog.contextIds }
    private fun agreements(sel: AxisSelection): List<Agreement> =
        allAgreements(sel.persons, sel.numbers, sel.genders, sel.honorifics)

    private fun constructions(sel: AxisSelection): List<Construction> =
        if (sel.constructions.isEmpty()) ALL_CONSTRUCTIONS
        else ALL_CONSTRUCTIONS.filter { it in sel.constructions }

    /** Yield every realizable coordinate in the (possibly narrowed) space. */
    fun iterCoordinates(sel: AxisSelection = AxisSelection()): Sequence<Coordinate> = sequence {
        val polarities = sel.polarities.ifEmpty { ALL_POLARITIES }
        val scripts = sel.scripts.ifEmpty { ALL_SCRIPTS }
        val knowledge = sel.knowledge.ifEmpty { IMPLEMENTED_KNOWLEDGE }
        val contexts = contexts(sel)
        val agreements = agreements(sel)
        val constructions = constructions(sel)

        for (tam in tams(sel)) {
            for (construction in constructions) {
                for (lemma in lemmas(sel)) {
                    val verb = catalog.verb(lemma)
                    if (!conjugator.realizableConstruction(verb, tam, construction)) continue
                    for (agr in agreements) {
                        if (!conjugator.realizableAgreement(tam, agr)) continue
                        for (polarity in polarities) {
                            for (script in scripts) {
                                for (know in knowledge) {
                                    for (context in contexts) {
                                        yield(
                                            Coordinate(
                                                lemma = lemma,
                                                tam = tam,
                                                person = agr.person,
                                                number = agr.number,
                                                gender = agr.gender,
                                                honorific = agr.honorific,
                                                polarity = polarity,
                                                script = script,
                                                knowledge = know,
                                                context = context,
                                                construction = construction,
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
    }

    /** Size of the (narrowed) realizable space, without materializing it. */
    fun count(sel: AxisSelection = AxisSelection()): Int {
        val nPolarities = sel.polarities.ifEmpty { ALL_POLARITIES }.size
        val nScripts = sel.scripts.ifEmpty { ALL_SCRIPTS }.size
        val nKnowledge = sel.knowledge.ifEmpty { IMPLEMENTED_KNOWLEDGE }.size
        val nContexts = contexts(sel).size
        val perCell = nPolarities * nScripts * nKnowledge * nContexts
        val agreements = agreements(sel)
        val lemmas = lemmas(sel)

        var total = 0
        for (tam in tams(sel)) {
            val realizableAgr = agreements.count { conjugator.realizableAgreement(tam, it) }
            if (realizableAgr == 0) continue
            for (construction in constructions(sel)) {
                val verbsOk = lemmas.count {
                    conjugator.realizableConstruction(catalog.verb(it), tam, construction)
                }
                total += verbsOk * realizableAgr * perCell
            }
        }
        return total
    }
}
