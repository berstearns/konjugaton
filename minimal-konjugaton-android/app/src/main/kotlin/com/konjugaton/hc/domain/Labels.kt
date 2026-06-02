/*
 * Human-facing labels for the grammatical axes.
 *
 * Single source of truth so the generator (building Item.task) and the UI
 * render identical strings — and so the QualityEvaluator's determinacy check
 * (task must CONTAIN these tokens) stays in lock-step with what's displayed.
 *
 * The task a learner sees must pin every answer-determining axis: a Hindi cloze
 * is ambiguous without TAM + person + number + gender + honorific + polarity,
 * because the verb agrees with gender & number and the honorific changes the
 * ending. Port of konjugaton's `engine/labels.py`.
 */
package com.konjugaton.hc.domain

object Labels {
    val tam: Map<Tam, String> = mapOf(
        Tam.PRESENT_HABITUAL to "present-habitual",
        Tam.PAST_HABITUAL to "past-habitual",
        Tam.PRESENT_PROGRESSIVE to "present-progressive",
        Tam.PAST_PROGRESSIVE to "past-progressive",
        Tam.PERFECT to "perfect",
        Tam.PAST_PERFECT to "past-perfect",
        Tam.FUTURE to "future",
        Tam.SUBJUNCTIVE to "subjunctive",
        Tam.IMPERATIVE to "imperative",
    )
    val person: Map<Person, String> = mapOf(Person.P1 to "1st", Person.P2 to "2nd", Person.P3 to "3rd")
    val number: Map<Number, String> = mapOf(Number.SINGULAR to "sg", Number.PLURAL to "pl")
    val gender: Map<Gender, String> = mapOf(Gender.MASCULINE to "masc", Gender.FEMININE to "fem")
    val honorific: Map<Honorific, String> = mapOf(
        Honorific.NEUTRAL to "neutral",
        Honorific.INTIMATE to "तू",
        Honorific.FAMILIAR to "तुम",
        Honorific.FORMAL to "आप",
    )
    val polarity: Map<Polarity, String> =
        mapOf(Polarity.AFFIRMATIVE to "affirmative", Polarity.NEGATIVE to "negative")
    val construction: Map<Construction, String> = mapOf(
        Construction.SIMPLE to "simple",
        Construction.ABILITY to "ability (सकना)",
        Construction.COMPLETIVE to "completive (चुकना)",
        Construction.DESIDERATIVE to "desiderative (चाहना)",
        Construction.INCEPTIVE to "inceptive (लगना)",
        Construction.PASSIVE to "passive (जाना)",
    )

    fun tamOf(t: Tam): String = tam.getValue(t)
    fun personOf(p: Person): String = person.getValue(p)
    fun numberOf(n: Number): String = number.getValue(n)
    fun genderOf(g: Gender): String = gender.getValue(g)
    fun honorificOf(h: Honorific): String = honorific.getValue(h)
    fun polarityOf(p: Polarity): String = polarity.getValue(p)
    fun constructionOf(c: Construction): String = construction.getValue(c)
}
