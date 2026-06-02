/*
 * The domain value objects: verbs, conjugated forms, coordinates/skills, items.
 *
 * Ports of konjugaton's `domain/verb.py`, `conjugation.py`, `taxonomy.py`,
 * `item.py`, `tables.py`. All immutable `data class`es (cheap to hash, safe as
 * map keys), exactly as the Python frozen dataclasses were. Every surface form
 * carries a Devanagari and a romanized twin.
 */
package com.konjugaton.hc.domain

/** Explicit, hand-verified perfective participles for an irregular verb. */
data class PerfectiveForms(
    val forms: Map<String, String>, // "sg|m" -> "किया"
    val formsRoman: Map<String, String>, // "sg|m" -> "kiya"
)

/** Stems/overrides that drive the [Conjugator]. Regular verbs need none. */
data class ConjugationData(
    val root: String? = null,
    val rootRoman: String? = null,
    val perfective: PerfectiveForms? = null,
    val futureOblique: String? = null,
    val futureObliqueRoman: String? = null,
    val imperativeAap: String? = null,
    val imperativeAapRoman: String? = null,
)

/** A verb lemma plus the metadata the engine and taxonomy need. */
data class Verb(
    val lemma: String, // Devanagari infinitive, e.g. करना
    val lemmaRoman: String, // romanized infinitive, e.g. karna
    val verbClass: VerbClass,
    val transitivity: Transitivity,
    val translation: String,
    val frequencyRank: Int,
    val conjugation: ConjugationData = ConjugationData(),
    val family: String? = null,
    val semanticTags: List<String> = emptyList(),
) {
    /** Devanagari verb root (lemma minus the ना infinitive marker). */
    val root: String
        get() = conjugation.root ?: if (lemma.endsWith("ना")) lemma.dropLast(2) else lemma

    /** Romanized verb root (lemma_roman minus the -na infinitive marker). */
    val rootRoman: String
        get() = conjugation.rootRoman
            ?: if (lemmaRoman.endsWith("na")) lemmaRoman.dropLast(2) else lemmaRoman
}

/**
 * A single conjugated Hindi verb form, in both scripts. Periphrastic TAMs keep
 * the main participle and the होना auxiliary separate, because Hindi negation is
 * preverbal and may drop the present auxiliary — impossible on a pre-joined string.
 */
data class ConjugatedForm(
    val main: String,
    val mainRoman: String,
    val auxiliary: String? = null,
    val auxiliaryRoman: String? = null,
) {
    val surface: String get() = if (auxiliary != null) "$main $auxiliary" else main
    val surfaceRoman: String
        get() = if (auxiliaryRoman != null) "$mainRoman $auxiliaryRoman" else mainRoman
    val hasAuxiliary: Boolean get() = auxiliary != null

    companion object {
        fun simple(main: String, mainRoman: String) = ConjugatedForm(main, mainRoman)
        fun periphrastic(main: String, mainRoman: String, aux: String, auxRoman: String) =
            ConjugatedForm(main, mainRoman, aux, auxRoman)
    }
}

/** A semantic context — the "where does this verb live" axis (verb-final SOV). */
data class SemanticContext(
    val id: String,
    val labelHi: String,
    val labelEn: String,
    val templates: List<String>,
    val templatesRoman: List<String>,
    val affinity: List<String> = emptyList(),
)

/**
 * Conjugation ending tables: paradigm -> key -> suffix, with a romanized twin.
 * A conjugated regular form = stem + ending(paradigm, key).
 */
class EndingTables(
    val tables: Map<String, Map<String, String>>,
    private val tablesRoman: Map<String, Map<String, String>>,
) {
    fun has(paradigm: String): Boolean = paradigm in tables

    fun ending(paradigm: String, key: String): String =
        tables[paradigm]?.get(key)
            ?: throw ConjugationError("no ending for $paradigm/$key")

    fun endingRoman(paradigm: String, key: String): String =
        tablesRoman[paradigm]?.get(key)
            ?: throw ConjugationError("no roman ending for $paradigm/$key")
}

/** 3PL item parameters: difficulty (b), discrimination (a), guessing (c). */
data class IrtParameters(
    val difficulty: Double,
    val discrimination: Double = 1.0,
    val guessing: Double = 0.0,
)

/** One fully-specified point in the combinatorial exercise space. */
data class Coordinate(
    val lemma: String,
    val tam: Tam,
    val person: Person,
    val number: Number,
    val gender: Gender,
    val honorific: Honorific,
    val polarity: Polarity,
    val script: Script,
    val knowledge: KnowledgeType,
    val context: String,
    // The light-verb / passive layer. Defaults to SIMPLE so pre-construction
    // coordinates stay valid; like polarity/script it modulates difficulty, not skill.
    val construction: Construction = Construction.SIMPLE,
) {
    /**
     * Project onto the coarse IRT skill. Agreement features, polarity, script,
     * context and the specific lemma are abstracted away — they modulate item
     * difficulty (a `b` shift) rather than defining a new latent ability.
     */
    fun skill(verbClass: VerbClass) = Skill(verbClass, tam, knowledge)

    /** The (person, number, gender, honorific) bundle this coordinate fixes. */
    fun agreement() = Agreement(person, number, gender, honorific)
}

/** A latent ability dimension: (verb_class, tam, knowledge). */
data class Skill(
    val verbClass: VerbClass,
    val tam: Tam,
    val knowledge: KnowledgeType,
) {
    /** Stable string key for persistence and graph node ids. */
    val key: String get() = "${verbClass.value}|${tam.value}|${knowledge.value}"

    override fun toString(): String = "${verbClass.value} ${tam.value} [${knowledge.value}]"
}

/**
 * A renderable, gradable exercise instance. [prompt] is shown to the learner;
 * [answer] is the canonical correct response (in the coordinate's script);
 * [task] is the grammatical target that makes the cloze answerable.
 */
data class Item(
    val coordinate: Coordinate,
    val skill: Skill,
    val prompt: String,
    val answer: String,
    val irt: IrtParameters,
    val accepted: List<String> = emptyList(),
    val choices: List<String> = emptyList(),
    val lemmaHint: String = "",
    val task: String = "",
    val fullSentence: String = "",
    val metadata: Map<String, String> = emptyMap(),
) {
    val isMultipleChoice: Boolean get() = choices.isNotEmpty()
}
