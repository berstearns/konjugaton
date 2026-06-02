/*
 * App settings — a broad, konjugaton-faithful flag surface (categories A–J of
 * `settings/models.py`), persisted to filesDir/settings.json.
 *
 * Flags are tagged [active] (wired to behaviour) or [planned] (stored, not yet
 * acted on) — mirroring konjugaton's own annotation so the settings screen is
 * honest about what actually does something today.
 */
package com.konjugaton.hc.data

import com.konjugaton.hc.domain.AxisSelection
import com.konjugaton.hc.domain.GradingSettings
import com.konjugaton.hc.domain.IMPLEMENTED_KNOWLEDGE
import com.konjugaton.hc.domain.KnowledgeType
import com.konjugaton.hc.domain.Script
import com.konjugaton.hc.domain.SessionOrder
import java.io.File
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

@Serializable
data class AppSettings(
    // --- Session & flow -------------------------------------------------------
    val autoAdvance: Boolean = true, // [active]
    val autoAdvanceDelayMs: Int = 1200, // [active]
    val sessionLength: Int = 10, // [active]
    val sessionOrder: String = "adaptive", // [active] adaptive|easy-first|hard-first|random

    // --- Question filter (which exercises you get) ---------------------------
    // answerScript: which script the verb is elicited in. "romanized" lets a
    // learner who can't type Devanagari still answer; "both" = no restriction.
    val answerScript: String = "both", // [active] both|devanagari|romanized
    // questionMode: which question type(s). "multiple-choice" = no typing at all.
    val questionMode: String = "all", // [active] all|multiple-choice|typed|transliterate

    // --- A · Answer acceptance ------------------------------------------------
    val ignoreCase: Boolean = true, // [active]
    val ignoreAccents: Boolean = false, // [active] folds romanization variants
    val ignorePunctuation: Boolean = true, // [active]
    val similarityTolerance: Int = 0, // [active] 0..10, length-scaled NEAR window
    val requireSubjectPronoun: Boolean = false, // [planned]
    val acceptEitherScript: Boolean = false, // [planned]
    val partialCreditPeriphrastic: Boolean = false, // [planned]
    val firstAttemptTypoGrace: Boolean = false, // [planned]

    // --- B · Feedback ---------------------------------------------------------
    val showCorrectOnError: Boolean = true, // [active]
    val showFullSentence: Boolean = true, // [active]
    val showTranslation: Boolean = true, // [active]
    val showItemDifficulty: Boolean = false, // [active]
    // NOTE: the grammatical task (TAM/agreement/polarity) and the lemma are
    // answerability-critical, so they are ALWAYS shown — deliberately NOT flags.
    val charDiffOnError: Boolean = false, // [planned]
    val showLiteralGloss: Boolean = false, // [planned]
    val grammarHintOnError: Boolean = false, // [planned]

    // --- D · Adaptivity -------------------------------------------------------
    val adaptiveEnabled: Boolean = true, // [active]
    val rampWithStreak: Boolean = false, // [planned]

    // --- F · Item construction ------------------------------------------------
    val mcChoices: Int = 4, // [planned]

    // --- G · Scaffolding ------------------------------------------------------
    val pollinateOnError: Boolean = false, // [planned]
    val showConjugationTableOnMiss: Boolean = false, // [planned]
    val trackGrammarTags: Boolean = false, // [planned]

    // --- H · Motivation -------------------------------------------------------
    val streaks: Boolean = false, // [planned]
    val celebrateMilestones: Boolean = false, // [planned]

    // --- I · Output & analytics ----------------------------------------------
    val logResponses: Boolean = false, // [planned]
    val snapshotState: Boolean = true, // [active] persist learner state

    // --- J · Display ----------------------------------------------------------
    val theme: String = "auto", // [planned] auto|light|dark
) {
    fun toGradingSettings() = GradingSettings(
        similarityTolerance = similarityTolerance,
        ignoreAccents = ignoreAccents,
        ignoreCase = ignoreCase,
        ignorePunctuation = ignorePunctuation,
    )

    /** The session filter from the question-filter prefs (mirrors the Python
     *  `selection_from_settings`). Empty axis = all values. */
    fun selection(): AxisSelection {
        val scripts = when (answerScript) {
            "devanagari" -> listOf(Script.DEVANAGARI)
            "romanized" -> listOf(Script.ROMANIZED)
            else -> emptyList()
        }
        val knowledge = when (questionMode) {
            "multiple-choice" -> listOf(KnowledgeType.RECOGNITION)
            "typed" -> listOf(KnowledgeType.PRODUCTION)
            "transliterate" -> listOf(KnowledgeType.TRANSLITERATION)
            else -> emptyList()
        }.filter { it in IMPLEMENTED_KNOWLEDGE }
        return AxisSelection(scripts = scripts, knowledge = knowledge)
    }

    fun order(): SessionOrder = when (sessionOrder) {
        "easy-first" -> SessionOrder.EASY_FIRST
        "hard-first" -> SessionOrder.HARD_FIRST
        "random" -> SessionOrder.RANDOM
        else -> if (adaptiveEnabled) SessionOrder.ADAPTIVE else SessionOrder.EASY_FIRST
    }
}

private val JSON = Json { ignoreUnknownKeys = true; encodeDefaults = true }

/** Reads/writes [AppSettings] as a JSON file (mirrors StateStore's pattern). */
class SettingsStore(private val file: File) {
    fun load(): AppSettings =
        if (!file.exists()) {
            AppSettings()
        } else {
            try {
                JSON.decodeFromString<AppSettings>(file.readText())
            } catch (_: Exception) {
                AppSettings()
            }
        }

    fun save(settings: AppSettings) {
        val tmp = File(file.parentFile, "${file.name}.tmp")
        tmp.writeText(JSON.encodeToString(settings))
        tmp.renameTo(file)
    }
}
