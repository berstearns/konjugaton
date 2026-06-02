/*
 * Text utilities + configurable grading.
 *
 * Ports konjugaton's `textutils.py` (Levenshtein, accent stripping) and
 * `services/grading.py`. Pipeline: normalise (case -> transliteration ->
 * punctuation -> whitespace), then match in order of strictness:
 *
 *     exact -> NEAR (length-scaled similarity) -> ACCENT_SLIP (soft) -> INCORRECT
 *
 * The transliteration fold collapses romanization variants (aa→a, ee→i, …).
 */
package com.konjugaton.hc.domain

import java.text.Normalizer

// -- text utilities ---------------------------------------------------------

/** Edit distance (insert/delete/substitute) between two strings. */
fun levenshtein(a: String, b: String): Int {
    if (a == b) return 0
    if (a.isEmpty()) return b.length
    if (b.isEmpty()) return a.length
    var previous = IntArray(b.length + 1) { it }
    for (i in 1..a.length) {
        val current = IntArray(b.length + 1)
        current[0] = i
        for (j in 1..b.length) {
            val cost = if (a[i - 1] == b[j - 1]) 0 else 1
            current[j] = minOf(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
        }
        previous = current
    }
    return previous[b.length]
}

/** Drop combining marks. Normalises optional Devanagari marks and roman diacritics. */
fun stripAccents(text: String): String =
    Normalizer.normalize(text, Normalizer.Form.NFKD).filter { !it.isCombiningMark() }

private fun Char.isCombiningMark(): Boolean = when (Character.getType(this)) {
    Character.NON_SPACING_MARK.toInt(),
    Character.COMBINING_SPACING_MARK.toInt(),
    Character.ENCLOSING_MARK.toInt() -> true
    else -> false
}

/** Compile a transliteration map into longest-first (sequence → canonical) pairs. */
fun buildReplacements(mapping: Map<String, List<String>>): List<Pair<String, String>> {
    val replacements = LinkedHashMap<String, String>()
    for ((char, accepted) in mapping) {
        val canonical = accepted.firstOrNull() ?: char
        replacements.putIfAbsent(char, canonical)
        for (seq in accepted) replacements.putIfAbsent(seq, canonical)
    }
    return replacements.entries
        .map { it.key to it.value }
        .sortedByDescending { it.first.length } // longest match first (aa before a)
}

/** Apply compiled replacements left-to-right, longest match first. */
fun transliterate(text: String, replacements: List<Pair<String, String>>): String {
    if (replacements.isEmpty()) return text
    val out = StringBuilder()
    var i = 0
    while (i < text.length) {
        var matched = false
        for ((seq, canonical) in replacements) {
            if (seq.isNotEmpty() && text.startsWith(seq, i)) {
                out.append(canonical)
                i += seq.length
                matched = true
                break
            }
        }
        if (!matched) {
            out.append(text[i])
            i++
        }
    }
    return out.toString()
}

// -- grading settings -------------------------------------------------------

/** Default Hindi romanization-tolerance map (aa→a, ee→i, oo→u, v→w, …). */
val DEFAULT_TRANSLITERATION: Map<String, List<String>> = mapOf(
    "a" to listOf("a", "aa"),
    "i" to listOf("i", "ee", "ii"),
    "u" to listOf("u", "oo", "uu"),
    "n" to listOf("n", "ñ", "ṅ", "ṇ"),
    "t" to listOf("t", "ṭ"),
    "d" to listOf("d", "ḍ"),
    "r" to listOf("r", "ṛ"),
    "sh" to listOf("sh", "ś", "ṣ"),
    "w" to listOf("w", "v"),
)

/** Mirrors the *active* defaults of konjugaton's `GradingSettings`. */
data class GradingSettings(
    val similarityTolerance: Int = 0, // 0..10, length-scaled NEAR window; 0 = off
    val ignoreAccents: Boolean = false,
    val ignoreCase: Boolean = true,
    val ignorePunctuation: Boolean = true,
    val transliteration: Map<String, List<String>> = DEFAULT_TRANSLITERATION,
)

// -- grades ------------------------------------------------------------------

enum class Grade { CORRECT, NEAR, ACCENT_SLIP, INCORRECT }

data class GradedResponse(
    val item: Item,
    val given: String,
    val grade: Grade,
    val distance: Int,
    val normalizedGiven: String,
    val normalizedAnswer: String,
) {
    val isCorrect: Boolean get() = grade != Grade.INCORRECT
}

// Sentence punctuation stripped when ignorePunctuation is on (incl. Devanagari danda).
private val TRIM_PUNCT: Set<Char> = ".,;:!?…\"()[]।॥".toSet()

/** Grades a response against an item per the user's grading settings. */
class Grader(private val s: GradingSettings = GradingSettings()) {

    private val replacements: List<Pair<String, String>> =
        if (s.ignoreAccents) buildReplacements(s.transliteration) else emptyList()

    fun normalize(text: String): String {
        var result = text.trim()
        if (s.ignoreCase) result = result.lowercase()
        if (s.ignoreAccents) result = transliterate(result, replacements)
        if (s.ignorePunctuation) result = result.filter { it !in TRIM_PUNCT }
        return result.split(Regex("\\s+")).filter { it.isNotEmpty() }.joinToString(" ")
    }

    fun grade(item: Item, given: String): GradedResponse {
        val normAnswer = normalize(item.answer)
        val accepted = (listOf(item.answer) + item.accepted).map { normalize(it) }
        val normGiven = normalize(given)

        if (normGiven in accepted) {
            return GradedResponse(item, given, Grade.CORRECT, 0, normGiven, normAnswer)
        }

        val distance = accepted.minOf { levenshtein(normGiven, it) }

        if (s.similarityTolerance > 0) {
            val referenceLen = normAnswer.length.coerceAtLeast(1)
            if (distance <= (s.similarityTolerance / 10.0) * referenceLen) {
                return GradedResponse(item, given, Grade.NEAR, distance, normGiven, normAnswer)
            }
        }

        if (stripAccents(normGiven) in accepted.map { stripAccents(it) }.toSet()) {
            return GradedResponse(item, given, Grade.ACCENT_SLIP, distance, normGiven, normAnswer)
        }

        return GradedResponse(item, given, Grade.INCORRECT, distance, normGiven, normAnswer)
    }
}
