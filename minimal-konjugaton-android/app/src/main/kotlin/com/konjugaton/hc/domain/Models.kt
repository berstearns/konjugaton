/*
 * The domain value objects: verbs, conjugated forms, coordinates/skills, items.
 *
 * Ports of konjugaton's `domain/verb.py`, `conjugation.py`, `taxonomy.py`,
 * `item.py`, `tables.py` (German). All immutable `data class`es (cheap to hash,
 * safe as map keys), exactly as the Python frozen dataclasses were.
 */
package com.konjugaton.hc.domain

/**
 * Stems/overrides that drive the [Conjugator]. Weak verbs need none of it.
 *
 * - [praesensStem23] — strong Präsens 2sg/3sg stem change (geben→gib, sehen→sieh).
 * - [praeteritumStem] — strong (ging, sah) or mixed (dach, brach) past stem.
 * - [partizip2] — Partizip II (strong/mixed/irregular); weak is derived (ge+stem+t).
 *   For separable verbs this is the *base* PII (gestanden); the prefix is prepended.
 * - [konjunktiv2Stem] — strong/irregular K2 stem (ging→ginge, käm→käme, wär→wäre).
 * - [irregular] — paradigm → slot → form maps for sein/haben/werden.
 */
data class ConjugationData(
    val praesensStem23: String? = null,
    val praeteritumStem: String? = null,
    val partizip2: String? = null,
    val konjunktiv2Stem: String? = null,
    val irregular: Map<String, Map<String, String>> = emptyMap(),
)

/** A verb lemma plus the metadata the engine and taxonomy need. */
data class Verb(
    val lemma: String, // infinitive, e.g. machen / aufstehen
    val translation: String,
    val verbClass: VerbClass,
    val auxiliary: Auxiliary,
    val transitive: Boolean,
    val frequencyRank: Int,
    val conjugation: ConjugationData = ConjugationData(),
    val separablePrefix: String? = null,
    val family: String? = null,
    val semanticTags: List<String> = emptyList(),
) {
    /** The lemma with any separable prefix removed (aufstehen → stehen). */
    val baseLemma: String
        get() {
            val p = separablePrefix
            return if (p != null && lemma.startsWith(p)) lemma.substring(p.length) else lemma
        }

    /** The conjugation stem: base lemma minus the -en / -n infinitive marker. */
    val stem: String
        get() {
            val b = baseLemma
            return when {
                b.endsWith("en") -> b.dropLast(2)
                b.endsWith("n") -> b.dropLast(1)
                else -> b
            }
        }
}

/**
 * A conjugated German verb complex: a finite head + a clause-final tail of
 * non-finite material (Partizip II, Infinitiv, a detached separable prefix, or a
 * stack). Keeping the two parts separate lets the renderer place `nicht` between
 * them and assemble the right word order.
 */
data class ConjugatedForm(
    val finite: String,
    val tail: String = "",
) {
    /** The contiguous verb complex (finite + tail), e.g. "habe gemacht", "stehe auf". */
    val surface: String get() = if (tail.isNotEmpty()) "$finite $tail" else finite
    val hasTail: Boolean get() = tail.isNotEmpty()

    companion object {
        fun simple(finite: String) = ConjugatedForm(finite)
        fun periphrastic(finite: String, tail: String) = ConjugatedForm(finite, tail)
    }
}

/** A semantic context — the "where does this verb live" axis. */
data class SemanticContext(
    val id: String,
    val labelDe: String,
    val labelEn: String,
    val templates: List<String>,
    val affinity: List<String> = emptyList(),
)

/**
 * Conjugation ending tables: paradigm -> slot -> suffix. A conjugated regular
 * form = stem + ending(paradigm, slot). German is single-script (no roman twin).
 */
class EndingTables(val tables: Map<String, Map<String, String>>) {
    fun has(paradigm: String): Boolean = paradigm in tables

    fun ending(paradigm: String, slot: String): String =
        tables[paradigm]?.get(slot)
            ?: throw ConjugationError("no ending for $paradigm/$slot")
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
    val tenseMood: TenseMood,
    val person: Person,
    val number: Number,
    val register: Register,
    val polarity: Polarity,
    val knowledge: KnowledgeType,
    val context: String,
    // The voice layer. Defaults to AKTIV so pre-voice coordinates stay valid;
    // like polarity it modulates difficulty, not skill.
    val voice: Voice = Voice.AKTIV,
) {
    /**
     * Project onto the coarse IRT skill. Register, voice, polarity, context and
     * the specific lemma are abstracted away — they modulate item difficulty (a
     * `b` shift) rather than defining a new latent ability.
     */
    fun skill(verbClass: VerbClass) = Skill(verbClass, tenseMood, knowledge)

    /** The (person, number, register) bundle this coordinate fixes. */
    fun agreement() = Agreement(person, number, register)
}

/** A latent ability dimension: (verb_class, tense_mood, knowledge). */
data class Skill(
    val verbClass: VerbClass,
    val tenseMood: TenseMood,
    val knowledge: KnowledgeType,
) {
    /** Stable string key for persistence and graph node ids. */
    val key: String get() = "${verbClass.value}|${tenseMood.value}|${knowledge.value}"

    override fun toString(): String = "${verbClass.value} ${tenseMood.value} [${knowledge.value}]"
}

/**
 * A renderable, gradable exercise instance. [prompt] is shown to the learner;
 * [answer] is the canonical correct response; [task] is the grammatical target
 * that makes the cloze answerable.
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
