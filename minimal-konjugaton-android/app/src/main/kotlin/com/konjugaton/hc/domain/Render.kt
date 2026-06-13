/*
 * Surface rendering: negation, separable-prefix placement, subject attachment.
 *
 * Port of konjugaton's `engine/render.py` (German). The conjugator produces
 * morphology (a finite head + a clause-final tail); this applies German syntax:
 *
 * - negation: `nicht` is placed after the finite verb and before the tail
 *   (ich mache nicht, ich habe nicht gemacht, ich stehe nicht auf).
 * - separable prefix: carried as the tail by the conjugator, so it lands
 *   clause-finally in simple tenses and stays bound in periphrastic ones.
 * - Imperativ: no leading subject for du/ihr; formal Sie is appended after the
 *   finite verb (machen Sie!).
 * - subject: subject-first so the verb complex is contiguous (the cloze target).
 */
package com.konjugaton.hc.domain

object Render {
    /** The subject pronoun for an agreement bundle (ich/du/er/wir/ihr/Sie/sie). */
    fun subjectPronoun(agr: Agreement): String =
        SUBJECT_PRONOUN.getValue(Triple(agr.person, agr.number, agr.register))

    /** The contiguous verb complex the learner types — finite (+Sie) (+nicht) (+tail). */
    fun predicate(
        form: ConjugatedForm,
        tenseMood: TenseMood,
        polarity: Polarity,
        register: Register,
    ): String {
        val parts = mutableListOf(form.finite)
        if (tenseMood == TenseMood.IMPERATIV && register == Register.SIE) parts.add("Sie")
        if (polarity == Polarity.NEGATIVE) parts.add("nicht")
        if (form.tail.isNotEmpty()) parts.add(form.tail)
        return parts.joinToString(" ")
    }

    /** Join subject + predicate (verb-second, subject-first). Imperatives drop it. */
    fun attachSubject(agr: Agreement, predicateText: String, tenseMood: TenseMood): String =
        if (tenseMood == TenseMood.IMPERATIV) predicateText
        else "${subjectPronoun(agr)} $predicateText"
}
