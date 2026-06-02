/*
 * The combinatorial axes of the practice space, as closed enumerations.
 *
 * Direct port of konjugaton's `domain/enums.py`. Each enum carries the same
 * string `value` the Python StrEnum used, so skill keys and serialized state are
 * byte-compatible with the reference implementation. These are plain Kotlin
 * enums — no serialization annotations — keeping the domain framework-free (the
 * data layer maps raw JSON strings onto them, just like pydantic -> domain).
 *
 * Hindi is far more combinatorial than French: the verb agrees with gender AND
 * number, the 2nd person fans into three honorific registers (तू/तुम/आप), and
 * there are nine TAMs built from participles + the होना auxiliary.
 */
package com.konjugaton.hc.domain

/** Tense-Aspect-Mood — the Hindi verb's primary axis. */
enum class Tam(val value: String) {
    PRESENT_HABITUAL("present-habitual"),
    PAST_HABITUAL("past-habitual"),
    PRESENT_PROGRESSIVE("present-progressive"),
    PAST_PROGRESSIVE("past-progressive"),
    PERFECT("perfect"),
    PAST_PERFECT("past-perfect"),
    FUTURE("future"),
    SUBJUNCTIVE("subjunctive"),
    IMPERATIVE("imperative");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Grammatical person (1/2/3). Number and honorific are separate axes. */
enum class Person(val value: String) {
    P1("1"), // मैं / हम
    P2("2"), // तू / तुम / आप
    P3("3"); // यह/वह / ये/वे

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Grammatical number. Hindi verbs agree in number. */
enum class Number(val value: String) {
    SINGULAR("sg"),
    PLURAL("pl");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Grammatical gender of the agreeing argument. Hindi verbs agree in gender. */
enum class Gender(val value: String) {
    MASCULINE("m"),
    FEMININE("f");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Second-person register (and the 3rd-person formal). Drives the pronoun and,
 *  for future/subjunctive/imperative, the verb ending. */
enum class Honorific(val value: String) {
    NEUTRAL("neutral"), // 1st person, and plain 3rd person
    INTIMATE("tu"), // तू
    FAMILIAR("tum"), // तुम
    FORMAL("aap"); // आप

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Conjugation class. REGULAR derives everything; IRREGULAR ships suppletive perfectives. */
enum class VerbClass(val value: String) {
    REGULAR("regular"),
    IRREGULAR("irregular");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Transitivity governs the ने-ergative in perfective TAMs. */
enum class Transitivity(val value: String) {
    TRANSITIVE("transitive"),
    INTRANSITIVE("intransitive");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/**
 * The verbal construction — Hindi's light-verb / voice layer. Port of the Python
 * `Construction` enum. SIMPLE is the bare finite verb; each compound stacks a
 * non-finite form of the main verb under a conjugated light verb (सकना/चुकना/
 * चाहना/लगना) or, for the passive, जाना. Compounds never take the ने-ergative.
 */
enum class Construction(val value: String) {
    SIMPLE("simple"),
    ABILITY("ability"), // सकना: कर सकता है
    COMPLETIVE("completive"), // चुकना: कर चुका है
    DESIDERATIVE("desiderative"), // चाहना: करना चाहता है
    INCEPTIVE("inceptive"), // लगना: करने लगा
    PASSIVE("passive"); // जाना: किया जाता है

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Affirmative vs negated clause (नहीं / मत / न, by TAM). */
enum class Polarity(val value: String) {
    AFFIRMATIVE("affirmative"),
    NEGATIVE("negative");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** Which script the answer is elicited in — a transliteration knowledge axis. */
enum class Script(val value: String) {
    DEVANAGARI("devanagari"),
    ROMANIZED("romanized");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/** What *kind* of knowing an item probes. The learner model maps onto this. */
enum class KnowledgeType(val value: String) {
    PRODUCTION("production"),
    RECOGNITION("recognition"),
    TRANSLITERATION("transliteration"),
    MEANING("meaning"),
    USAGE("usage"),
    AGREEMENT("agreement");

    companion object {
        fun fromValue(v: String) = entries.first { it.value == v }
    }
}

/**
 * The (person, number, gender, honorific) bundle a Hindi verb agrees with.
 * French collapses person+number into a single 6-way Person; Hindi cannot, so
 * we bundle the four sub-axes into one hashable value object (a `data class`
 * is auto-hashable, safe as a map key — like the Python frozen dataclass).
 */
data class Agreement(
    val person: Person,
    val number: Number,
    val gender: Gender,
    val honorific: Honorific,
) {
    val key: String get() = "${person.value}|${number.value}|${gender.value}|${honorific.value}"
}

/**
 * Subject pronoun (Devanagari) per (person, number, honorific). For the 2nd
 * person the honorific selects the pronoun; for 1st/3rd it is NEUTRAL and the
 * number selects between singular/plural. This closed map IS the legal-bundle
 * gate — illegal cells (e.g. "1st person आप") simply have no entry.
 */
val SUBJECT_PRONOUN: Map<Triple<Person, Number, Honorific>, String> = mapOf(
    Triple(Person.P1, Number.SINGULAR, Honorific.NEUTRAL) to "मैं",
    Triple(Person.P1, Number.PLURAL, Honorific.NEUTRAL) to "हम",
    Triple(Person.P2, Number.SINGULAR, Honorific.INTIMATE) to "तू",
    Triple(Person.P2, Number.PLURAL, Honorific.FAMILIAR) to "तुम",
    Triple(Person.P2, Number.PLURAL, Honorific.FORMAL) to "आप",
    Triple(Person.P3, Number.SINGULAR, Honorific.NEUTRAL) to "यह",
    Triple(Person.P3, Number.PLURAL, Honorific.NEUTRAL) to "ये",
    Triple(Person.P3, Number.PLURAL, Honorific.FORMAL) to "आप",
)

/** Romanized subject pronoun, same keys. */
val SUBJECT_PRONOUN_ROMAN: Map<Triple<Person, Number, Honorific>, String> = mapOf(
    Triple(Person.P1, Number.SINGULAR, Honorific.NEUTRAL) to "main",
    Triple(Person.P1, Number.PLURAL, Honorific.NEUTRAL) to "ham",
    Triple(Person.P2, Number.SINGULAR, Honorific.INTIMATE) to "tu",
    Triple(Person.P2, Number.PLURAL, Honorific.FAMILIAR) to "tum",
    Triple(Person.P2, Number.PLURAL, Honorific.FORMAL) to "aap",
    Triple(Person.P3, Number.SINGULAR, Honorific.NEUTRAL) to "yah",
    Triple(Person.P3, Number.PLURAL, Honorific.NEUTRAL) to "ye",
    Triple(Person.P3, Number.PLURAL, Honorific.FORMAL) to "aap",
)
