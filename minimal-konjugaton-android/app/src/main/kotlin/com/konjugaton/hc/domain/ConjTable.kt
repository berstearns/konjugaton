/*
 * The conjugation-table completion drill: one verb, one tense-mood, the standard
 * paradigm filled in by the learner.
 *
 * Mirrors konjugaton's `domain/conjugation_table.py` + `engine/paradigm.py`. A
 * table is just bare-form PRODUCTION [Item]s over the same (verb, tense-mood), so
 * grading, IRT and learner-state recording are reused unchanged. The paradigm is
 * tense-mood dependent: finite tenses take the six standard pronouns
 * (ich/du/er/wir/ihr/sie); the Imperativ takes the three addressees (du/ihr/Sie).
 */
package com.konjugaton.hc.domain

/** One row of a fill-in table: an agreement bundle, its display subject, and the item. */
data class ConjCell(val agreement: Agreement, val subject: String, val item: Item) {
    val answer: String get() = item.answer
}

/** The full paradigm of one verb in one tense-mood, in canonical pronoun order. */
data class ConjTable(
    val lemma: String,
    val translation: String,
    val tenseMood: TenseMood,
    val tenseLabel: String,
    val cells: List<ConjCell>,
)

/** The six standard pronouns, in textbook order, for every finite tense-mood. */
private val STANDARD_PARADIGM: List<Agreement> = listOf(
    Agreement(Person.P1, Number.SINGULAR, Register.NEUTRAL), // ich
    Agreement(Person.P2, Number.SINGULAR, Register.DU), // du
    Agreement(Person.P3, Number.SINGULAR, Register.NEUTRAL), // er/sie/es
    Agreement(Person.P1, Number.PLURAL, Register.NEUTRAL), // wir
    Agreement(Person.P2, Number.PLURAL, Register.IHR), // ihr
    Agreement(Person.P3, Number.PLURAL, Register.NEUTRAL), // sie
)

/** The Imperativ addresses only du / ihr / Sie. */
private val IMPERATIVE_PARADIGM: List<Agreement> = listOf(
    Agreement(Person.P2, Number.SINGULAR, Register.DU),
    Agreement(Person.P2, Number.PLURAL, Register.IHR),
    Agreement(Person.P2, Number.PLURAL, Register.SIE),
)

private val IMPERATIVE_LABEL: Map<Register, String> =
    mapOf(Register.DU to "(du)", Register.IHR to "(ihr)", Register.SIE to "(Sie)")

private fun paradigmFor(tenseMood: TenseMood): List<Agreement> =
    if (tenseMood == TenseMood.IMPERATIV) IMPERATIVE_PARADIGM else STANDARD_PARADIGM

private fun subjectLabel(agreement: Agreement, tenseMood: TenseMood): String =
    if (tenseMood == TenseMood.IMPERATIV) {
        IMPERATIVE_LABEL.getValue(agreement.register)
    } else {
        Render.subjectPronoun(agreement)
    }

/**
 * Realize the canonical paradigm of [lemma] in [tenseMood] as gradable cells.
 * Every supported tense-mood is realizable for every verb, so no pre-gating needed.
 */
fun buildConjTable(
    catalog: Catalog,
    conjugator: Conjugator,
    lemma: String,
    tenseMood: TenseMood,
): ConjTable {
    val verb = catalog.verb(lemma)
    val tenseLabel = Labels.tenseOf(tenseMood)
    val cells = paradigmFor(tenseMood).map { agr ->
        val form = conjugator.conjugate(verb, tenseMood, agr)
        val answer = Render.predicate(form, tenseMood, Polarity.AFFIRMATIVE, agr.register)
        val coord = Coordinate(
            lemma = lemma,
            tenseMood = tenseMood,
            person = agr.person,
            number = agr.number,
            register = agr.register,
            polarity = Polarity.AFFIRMATIVE,
            knowledge = KnowledgeType.PRODUCTION,
            context = "",
            voice = Voice.AKTIV,
        )
        val subject = subjectLabel(agr, tenseMood)
        val full = if (tenseMood == TenseMood.IMPERATIV) answer else "${Render.subjectPronoun(agr)} $answer"
        val item = Item(
            coordinate = coord,
            skill = coord.skill(verb.verbClass),
            prompt = subject,
            answer = answer,
            irt = seedIrt(verb.verbClass, coord, 0),
            accepted = listOf(answer),
            lemmaHint = lemma,
            task = "$tenseLabel · $subject",
            fullSentence = full,
            metadata = mapOf("translation" to verb.translation),
        )
        ConjCell(agr, subject, item)
    }
    return ConjTable(lemma, verb.translation, tenseMood, tenseLabel, cells)
}
