/*
 * Human-facing labels for the grammatical axes.
 *
 * Single source of truth so the generator (building Item.task) and the UI render
 * identical strings — and so the determinacy check stays in lock-step with what's
 * displayed. The task a learner sees must pin every answer-determining axis:
 * tense-mood, person, number, register, voice, polarity. Port of `engine/labels.py`.
 */
package com.konjugaton.hc.domain

object Labels {
    val tenseMood: Map<TenseMood, String> = mapOf(
        TenseMood.PRAESENS to "Präsens",
        TenseMood.PRAETERITUM to "Präteritum",
        TenseMood.PERFEKT to "Perfekt",
        TenseMood.PLUSQUAMPERFEKT to "Plusquamperfekt",
        TenseMood.FUTUR1 to "Futur I",
        TenseMood.FUTUR2 to "Futur II",
        TenseMood.KONJUNKTIV1 to "Konjunktiv I",
        TenseMood.KONJUNKTIV2 to "Konjunktiv II",
        TenseMood.IMPERATIV to "Imperativ",
    )
    val person: Map<Person, String> = mapOf(Person.P1 to "1st", Person.P2 to "2nd", Person.P3 to "3rd")
    val number: Map<Number, String> = mapOf(Number.SINGULAR to "sg", Number.PLURAL to "pl")
    val register: Map<Register, String> = mapOf(
        Register.NEUTRAL to "neutral",
        Register.DU to "du",
        Register.IHR to "ihr",
        Register.SIE to "Sie",
    )
    val voice: Map<Voice, String> = mapOf(Voice.AKTIV to "Aktiv", Voice.PASSIV to "Passiv")
    val polarity: Map<Polarity, String> =
        mapOf(Polarity.AFFIRMATIVE to "affirmative", Polarity.NEGATIVE to "negative")

    fun tenseOf(t: TenseMood): String = tenseMood.getValue(t)
    fun personOf(p: Person): String = person.getValue(p)
    fun numberOf(n: Number): String = number.getValue(n)
    fun registerOf(r: Register): String = register.getValue(r)
    fun voiceOf(v: Voice): String = voice.getValue(v)
    fun polarityOf(p: Polarity): String = polarity.getValue(p)
}
