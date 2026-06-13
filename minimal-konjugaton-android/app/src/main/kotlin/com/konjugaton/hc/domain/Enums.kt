/*
 * The combinatorial axes of the practice space, as closed enumerations.
 *
 * Direct port of konjugaton's `domain/enums.py` (German). Each enum carries the
 * same string `value` the Python StrEnum used, so skill keys and serialized state
 * are byte-compatible with the reference implementation. Plain Kotlin enums — the
 * data layer maps raw JSON strings onto them, just like pydantic -> domain.
 *
 * German splits weak/strong/mixed conjugations (ablaut), the haben/sein auxiliary
 * in the perfect tenses, separable prefixes, the du/ihr/Sie register, the
 * Konjunktiv I/II moods and the werden-passive. The verb agrees in person and
 * number only (no gender).
 */
package com.konjugaton.hc.domain

/** Tense-Mood — the German verb's primary axis (Indikativ + Konjunktiv + Imperativ). */
enum class TenseMood(val value: String) {
    PRAESENS("praesens"),
    PRAETERITUM("praeteritum"),
    PERFEKT("perfekt"),
    PLUSQUAMPERFEKT("plusquamperfekt"),
    FUTUR1("futur1"),
    FUTUR2("futur2"),
    KONJUNKTIV1("konjunktiv1"),
    KONJUNKTIV2("konjunktiv2"),
    IMPERATIV("imperativ");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Grammatical person (1/2/3). Number and register are separate axes. */
enum class Person(val value: String) {
    P1("1"), // ich / wir
    P2("2"), // du / ihr / Sie
    P3("3"); // er,sie,es / sie

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Grammatical number. The German verb agrees in number (not gender). */
enum class Number(val value: String) {
    SINGULAR("sg"),
    PLURAL("pl");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Politeness register — selects the 2nd/3rd-person pronoun and, for Sie, the form. */
enum class Register(val value: String) {
    NEUTRAL("neutral"), // 1st person, and plain 3rd person
    DU("du"), // informal singular addressee
    IHR("ihr"), // informal plural addressee
    SIE("sie_formal"); // formal addressee; takes the 3rd-plural verb form

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Aktiv vs the werden-Passiv (es wird gemacht). Passive ⇒ transitive verbs only. */
enum class Voice(val value: String) {
    AKTIV("aktiv"),
    PASSIV("passiv");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Conjugation class: weak (regular), strong (ablaut), mixed, irregular (sein/haben/werden). */
enum class VerbClass(val value: String) {
    WEAK("weak"),
    STRONG("strong"),
    MIXED("mixed"),
    IRREGULAR("irregular");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** The perfect-tense auxiliary a verb selects (a per-verb property). */
enum class Auxiliary(val value: String) {
    HABEN("haben"),
    SEIN("sein");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Affirmative vs negated clause (German negates with the particle `nicht`). */
enum class Polarity(val value: String) {
    AFFIRMATIVE("affirmative"),
    NEGATIVE("negative");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** What *kind* of knowing an item probes. German is single-script (no transliteration). */
enum class KnowledgeType(val value: String) {
    PRODUCTION("production"),
    RECOGNITION("recognition"),
    MEANING("meaning"),
    USAGE("usage");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/**
 * The (person, number, register) bundle a German verb agrees with. The register
 * selects the pronoun and, for the formal Sie, the verb form: `Sie machen` uses
 * the 3rd-plural slot.
 */
data class Agreement(
    val person: Person,
    val number: Number,
    val register: Register,
) {
    val key: String get() = "${person.value}|${number.value}|${register.value}"

    /** The `person|number` ending slot; the formal Sie uses the 3|pl form. */
    val slot: String
        get() = if (register == Register.SIE) {
            "${Person.P3.value}|${Number.PLURAL.value}"
        } else {
            "${person.value}|${number.value}"
        }
}

/**
 * Subject pronoun per (person, number, register). The register selects the
 * 2nd/3rd-person pronoun; illegal cells (e.g. "1st-person Sie") have no entry,
 * so this closed map IS the legal-bundle gate.
 */
val SUBJECT_PRONOUN: Map<Triple<Person, Number, Register>, String> = mapOf(
    Triple(Person.P1, Number.SINGULAR, Register.NEUTRAL) to "ich",
    Triple(Person.P1, Number.PLURAL, Register.NEUTRAL) to "wir",
    Triple(Person.P2, Number.SINGULAR, Register.DU) to "du",
    Triple(Person.P2, Number.PLURAL, Register.IHR) to "ihr",
    Triple(Person.P2, Number.PLURAL, Register.SIE) to "Sie",
    Triple(Person.P3, Number.SINGULAR, Register.NEUTRAL) to "er",
    Triple(Person.P3, Number.PLURAL, Register.NEUTRAL) to "sie",
)
