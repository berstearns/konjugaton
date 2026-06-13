/*
 * The conjugator: turn (verb, tense-mood, agreement) into a German verb complex.
 *
 * Direct port of konjugaton's `engine/conjugator.py`. Strategy "stem + ending",
 * adapted to German's weak/strong/mixed morphology and its periphrastic tenses:
 *
 * - finite forms = stem (+ strong 2sg/3sg change) + personal ending, with the
 *   epenthetic-e (arbeit→arbeitest) and s-drop (iss→isst) orthography in code;
 * - periphrastic tenses conjugate an auxiliary (haben/sein/werden) — themselves
 *   ordinary catalog verbs — and append a tail (Partizip II / Infinitiv);
 * - the separable prefix is carried as the clause-final tail.
 *
 * sein/haben/werden are too suppletive to derive and ship explicit form maps.
 */
package com.konjugaton.hc.domain

class ConjugationError(message: String) : RuntimeException(message)

/** Tense-moods the engine realizes, in display order. */
private val ORDER: List<TenseMood> = listOf(
    TenseMood.PRAESENS,
    TenseMood.PRAETERITUM,
    TenseMood.PERFEKT,
    TenseMood.PLUSQUAMPERFEKT,
    TenseMood.FUTUR1,
    TenseMood.FUTUR2,
    TenseMood.KONJUNKTIV1,
    TenseMood.KONJUNKTIV2,
    TenseMood.IMPERATIV,
)

/** Tenses in which the werden-passive is realized (transitive verbs only). */
private val PASSIVE_TENSES: Set<TenseMood> = setOf(
    TenseMood.PRAESENS,
    TenseMood.PRAETERITUM,
    TenseMood.PERFEKT,
    TenseMood.PLUSQUAMPERFEKT,
    TenseMood.FUTUR1,
)

private val SIBILANT = "sßzx".toSet()
private val DENTAL = "td".toSet()
private val UMLAUT = "äöü".toSet()

/** All tense-moods the engine can realize, in a stable order. */
fun supportedTenseMoods(): List<TenseMood> = ORDER

/** Stateless (w.r.t. learner) conjugation engine over a fixed catalog. */
class Conjugator(
    private val endings: EndingTables,
    private val verbs: Map<String, Verb> = emptyMap(),
) {
    // -- capability queries -------------------------------------------------

    fun supports(tm: TenseMood): Boolean = tm in ORDER

    @Suppress("UNUSED_PARAMETER") // all verbs realize all tense-moods
    fun canConjugate(verb: Verb, tm: TenseMood): Boolean = supports(tm)

    /** The imperative inflects in the 2nd person only (du/ihr/Sie). */
    fun realizableAgreement(tm: TenseMood, agr: Agreement): Boolean =
        if (tm == TenseMood.IMPERATIV) {
            agr.register == Register.DU || agr.register == Register.IHR || agr.register == Register.SIE
        } else {
            true
        }

    fun realizableVoice(verb: Verb, tm: TenseMood, voice: Voice): Boolean =
        if (voice == Voice.AKTIV) true else verb.transitive && tm in PASSIVE_TENSES

    // -- finite paradigms ---------------------------------------------------

    private fun praesens(verb: Verb, agr: Agreement): String {
        val slot = agr.slot
        verb.conjugation.irregular["praesens"]?.let { return it.getValue(slot) }
        val base = verb.stem
        val stem23 = verb.conjugation.praesensStem23 ?: base
        return when (slot) {
            "1|sg" -> base + "e"
            "2|sg" -> {
                val s = stem23
                when (s.last()) {
                    in SIBILANT -> s + "t"
                    in DENTAL -> s + "est"
                    else -> s + "st"
                }
            }
            "3|sg" -> {
                val s = stem23
                s + (if (s.last() in DENTAL) "et" else "t")
            }
            "2|pl" -> base + (if (base.last() in DENTAL) "et" else "t")
            else -> base + "en" // 1|pl, 3|pl
        }
    }

    private fun praeteritum(verb: Verb, agr: Agreement): String {
        val slot = agr.slot
        verb.conjugation.irregular["praeteritum"]?.let { return it.getValue(slot) }
        if (verb.verbClass == VerbClass.STRONG) {
            val stem = verb.conjugation.praeteritumStem
                ?: throw ConjugationError("${verb.lemma}: strong verb missing praeteritumStem")
            return stem + endings.ending("praeteritum_strong", slot)
        }
        // weak or mixed: (mixed) ablaut stem or (weak) base stem, + (e)te + endings
        val base = (if (verb.verbClass == VerbClass.MIXED) verb.conjugation.praeteritumStem else verb.stem)
            ?: throw ConjugationError("${verb.lemma}: mixed verb missing praeteritumStem")
        val connector = if (base.last() in DENTAL) "ete" else "te"
        return base + connector + endings.ending("praeteritum_weak", slot)
    }

    private fun konjunktiv1(verb: Verb, agr: Agreement): String {
        verb.conjugation.irregular["konjunktiv1"]?.let { return it.getValue(agr.slot) }
        return verb.stem + endings.ending("konjunktiv", agr.slot)
    }

    /** K2 finite, or null for weak/mixed (caller falls back to würde+Infinitiv). */
    private fun konjunktiv2(verb: Verb, agr: Agreement): String? {
        verb.conjugation.irregular["konjunktiv2"]?.let { return it.getValue(agr.slot) }
        val k2 = verb.conjugation.konjunktiv2Stem ?: return null
        return k2 + endings.ending("konjunktiv", agr.slot)
    }

    private fun partizip2(verb: Verb): String {
        val prefix = verb.separablePrefix ?: ""
        val p2 = verb.conjugation.partizip2 ?: run {
            val base = verb.stem
            "ge" + base + (if (base.last() in DENTAL) "et" else "t")
        }
        return prefix + p2
    }

    private fun aux(verb: Verb): Verb {
        val lemma = if (verb.auxiliary == Auxiliary.HABEN) "haben" else "sein"
        return verbs.getValue(lemma)
    }

    // -- main entry points --------------------------------------------------

    fun conjugate(verb: Verb, tm: TenseMood, agr: Agreement): ConjugatedForm {
        if (!realizableAgreement(tm, agr)) {
            throw ConjugationError("${verb.lemma}: cannot realize ${tm.value} for ${agr.key}")
        }
        val sep = verb.separablePrefix ?: ""
        return when (tm) {
            TenseMood.PRAESENS -> ConjugatedForm(praesens(verb, agr), sep)
            TenseMood.PRAETERITUM -> ConjugatedForm(praeteritum(verb, agr), sep)
            TenseMood.KONJUNKTIV1 -> ConjugatedForm(konjunktiv1(verb, agr), sep)
            TenseMood.KONJUNKTIV2 -> {
                val k2 = konjunktiv2(verb, agr)
                if (k2 != null) {
                    ConjugatedForm(k2, sep)
                } else {
                    val wuerde = konjunktiv2(verbs.getValue("werden"), agr)!!
                    ConjugatedForm(wuerde, verb.lemma) // würde + Infinitiv
                }
            }
            TenseMood.PERFEKT -> ConjugatedForm(praesens(aux(verb), agr), partizip2(verb))
            TenseMood.PLUSQUAMPERFEKT -> ConjugatedForm(praeteritum(aux(verb), agr), partizip2(verb))
            TenseMood.FUTUR1 -> ConjugatedForm(praesens(verbs.getValue("werden"), agr), verb.lemma)
            TenseMood.FUTUR2 -> {
                val tail = "${partizip2(verb)} ${verb.auxiliary.value}"
                ConjugatedForm(praesens(verbs.getValue("werden"), agr), tail)
            }
            TenseMood.IMPERATIV -> imperativ(verb, agr)
        }
    }

    private fun imperativ(verb: Verb, agr: Agreement): ConjugatedForm {
        val sep = verb.separablePrefix ?: ""
        val irr = verb.conjugation.irregular["imperativ"]
        if (agr.register == Register.DU) {
            val form = if (irr != null && "2|sg" in irr) {
                irr.getValue("2|sg")
            } else {
                val s23 = verb.conjugation.praesensStem23
                val useS23 = s23 != null && s23.none { it in UMLAUT }
                if (useS23) s23!! else verb.stem + (if (verb.stem.last() in DENTAL) "e" else "")
            }
            return ConjugatedForm(form, sep)
        }
        if (agr.register == Register.IHR) {
            val form = if (irr != null && "2|pl" in irr) irr.getValue("2|pl") else praesens(verb, agr)
            return ConjugatedForm(form, sep)
        }
        // Sie (formal): 3pl form; the renderer appends "Sie".
        val form = if (irr != null && "3|pl" in irr) irr.getValue("3|pl") else praesens(verb, agr)
        return ConjugatedForm(form, sep)
    }

    fun conjugateVoice(verb: Verb, tm: TenseMood, agr: Agreement, voice: Voice): ConjugatedForm {
        if (!realizableVoice(verb, tm, voice)) {
            throw ConjugationError("${verb.lemma}: cannot realize ${voice.value} ${tm.value}")
        }
        if (voice == Voice.AKTIV) return conjugate(verb, tm, agr)
        val werden = verbs.getValue("werden")
        val sein = verbs.getValue("sein")
        val pii = partizip2(verb)
        return when (tm) {
            TenseMood.PRAESENS -> ConjugatedForm(praesens(werden, agr), pii)
            TenseMood.PRAETERITUM -> ConjugatedForm(praeteritum(werden, agr), pii)
            TenseMood.PERFEKT -> ConjugatedForm(praesens(sein, agr), "$pii worden")
            TenseMood.PLUSQUAMPERFEKT -> ConjugatedForm(praeteritum(sein, agr), "$pii worden")
            TenseMood.FUTUR1 -> ConjugatedForm(praesens(werden, agr), "$pii werden")
            else -> throw ConjugationError("unsupported passive tense: ${tm.value}")
        }
    }
}

/** Convenience constructor mirroring the Python `default_agreement`. */
fun defaultAgreement(person: Person, number: Number, register: Register) =
    Agreement(person, number, register)
