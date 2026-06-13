/*
 * The single state holder. One class drives the whole app — no DI, no nav
 * library, no repository interfaces. Screen is a field; the `when()` over it
 * lives in Screens.kt. Adding a screen = add an enum value + a branch + a composable.
 *
 * It's an AndroidViewModel so the session survives rotation for free and so
 * auto-advance can use viewModelScope. Everything else is plain Kotlin.
 */
package com.konjugaton.hc.ui

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.konjugaton.hc.BuildConfig
import com.konjugaton.hc.data.AppSettings
import com.konjugaton.hc.data.CatalogLoader
import com.konjugaton.hc.data.SettingsStore
import com.konjugaton.hc.data.StateStore
import com.konjugaton.hc.domain.ConjTable
import com.konjugaton.hc.domain.Conjugator
import com.konjugaton.hc.domain.ExerciseGenerator
import com.konjugaton.hc.domain.Grade
import com.konjugaton.hc.domain.Grader
import com.konjugaton.hc.domain.GradedResponse
import com.konjugaton.hc.domain.Item
import com.konjugaton.hc.domain.PermutationSpace
import com.konjugaton.hc.domain.PracticeService
import com.konjugaton.hc.domain.QualityEvaluator
import com.konjugaton.hc.domain.SelfCheck
import com.konjugaton.hc.domain.SelfCheckReport
import com.konjugaton.hc.domain.TenseMood
import com.konjugaton.hc.domain.Verb
import com.konjugaton.hc.domain.VocabState
import com.konjugaton.hc.domain.buildConjTable
import com.konjugaton.hc.domain.supportedTenseMoods
import java.io.File
import java.time.Instant
import kotlin.random.Random
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

enum class Screen { HOME, DRILL, REPORT, SETTINGS, CONJ_SETUP, CONJ_TABLE }

/** Per-cell outcome in the conjugation-table drill (drives the row's symbol/colour). */
enum class CellOutcome { CORRECT, NEAR, ACCENT, INCORRECT, REVEALED }

/** A weak-spot row for the report screen. */
data class SkillRow(val label: String, val theta: Double)

class AppState(app: Application) : AndroidViewModel(app) {

    // --- engine, wired transparently (no hidden factories) -----------------
    private val catalog = run {
        fun asset(name: String) = app.assets.open(name).bufferedReader().use { it.readText() }
        CatalogLoader.parse(asset("verbs.json"), asset("endings.json"), asset("contexts.json"))
    }
    private val conjugator = Conjugator(catalog.endings, catalog.verbs)
    private val space = PermutationSpace(catalog, conjugator)
    private val generator = ExerciseGenerator(catalog, conjugator)
    private val practice =
        PracticeService(catalog, conjugator, space, generator, Random.Default, Grader())
    private val evaluator = QualityEvaluator(catalog, conjugator)

    private val store = StateStore(File(app.filesDir, "state.json"))
    private val settingsStore = SettingsStore(File(app.filesDir, "settings.json"))
    private val learner: VocabState = store.load()

    // --- observable UI state ----------------------------------------------
    var screen by mutableStateOf(Screen.HOME)
        private set
    var current by mutableStateOf<Item?>(null)
        private set
    var feedback by mutableStateOf<GradedResponse?>(null)
        private set
    var answer by mutableStateOf("")
    var sessionIndex by mutableStateOf(0)
        private set
    var sessionCorrect by mutableStateOf(0)
        private set
    var settings by mutableStateOf(settingsStore.load())
        private set

    private var grader = Grader(settings.toGradingSettings())
    private var session: List<Item> = emptyList()
    val sessionSize: Int get() = session.size

    // --- conjugation-table mode state -------------------------------------
    /** Chosen verb in the setup flow; null until picked (then the tense list shows). */
    var conjLemma by mutableStateOf<String?>(null)
        private set
    var conjTable by mutableStateOf<ConjTable?>(null)
        private set
    var conjIndex by mutableStateOf(0)
        private set
    var conjCorrect by mutableStateOf(0)
        private set
    var conjAnswer by mutableStateOf("")
    /** One slot per cell: null = unanswered, else the graded/revealed outcome. */
    var conjOutcomes by mutableStateOf<List<CellOutcome?>>(emptyList())
        private set

    // --- read-only facts for the Home screen ------------------------------
    val verbCount: Int get() = catalog.lemmas.size
    val spaceSize: Int get() = space.count()

    // --- actions -----------------------------------------------------------

    fun startPractice() {
        session = practice.buildSession(settings.selection(), settings.sessionLength, learner, settings.order())
        sessionIndex = 0
        sessionCorrect = 0
        feedback = null
        answer = ""
        showItem(session.firstOrNull())
        screen = Screen.DRILL
    }

    /** Guarded item setter: in debug, refuse to show an ill-posed exercise. */
    private fun showItem(item: Item?) {
        if (BuildConfig.DEBUG && item != null) {
            val issues = evaluator.evaluate(item)
            check(issues.isEmpty()) { "ill-posed item reached UI: ${item.task}\n${issues.joinToString("\n")}" }
        }
        current = item
    }

    /** Grade the current item (text answer for production, chosen option for MCQ). */
    fun submit(given: String) {
        val item = current ?: return
        if (feedback != null) return // already graded; the button now advances
        val result = grader.grade(item, given)
        feedback = result
        if (result.isCorrect) sessionCorrect++
        if (settings.snapshotState) {
            learner.record(item, result.isCorrect, Instant.now().toString())
            store.save(learner)
        }
        if (settings.autoAdvance) scheduleAutoAdvance(sessionIndex)
    }

    private fun scheduleAutoAdvance(forIndex: Int) {
        viewModelScope.launch {
            delay(settings.autoAdvanceDelayMs.toLong())
            if (screen == Screen.DRILL && sessionIndex == forIndex && feedback != null) advance()
        }
    }

    fun advance() {
        sessionIndex++
        if (sessionIndex < session.size) {
            showItem(session[sessionIndex])
            feedback = null
            answer = ""
        } else {
            screen = Screen.HOME // session complete
        }
    }

    fun goHome() { screen = Screen.HOME }
    fun goReport() { screen = Screen.REPORT }
    fun goSettings() { screen = Screen.SETTINGS }

    // --- conjugation-table mode (decoupled from the sampler) ---------------

    /** Open the table picker: choose a verb, then a tense-mood, then fill the table. */
    fun openConjTable() {
        conjLemma = null
        conjTable = null
        conjIndex = 0
        conjCorrect = 0
        conjAnswer = ""
        conjOutcomes = emptyList()
        screen = Screen.CONJ_SETUP
    }

    /** Verbs offered in the picker, most frequent first. */
    val conjVerbs: List<Verb> get() = catalog.verbs.values.sortedBy { it.frequencyRank }

    /** The tense-moods [lemma] can be conjugated in (every supported one). */
    fun availableTenseMoods(lemma: String): List<TenseMood> {
        val verb = catalog.verb(lemma)
        return supportedTenseMoods().filter { conjugator.canConjugate(verb, it) }
    }

    fun pickConjVerb(lemma: String) { conjLemma = lemma }
    /** Step back from the tense list to the verb list. */
    fun clearConjVerb() { conjLemma = null }

    fun startConjTable(lemma: String, tenseMood: TenseMood) {
        val table = buildConjTable(catalog, conjugator, lemma, tenseMood)
        conjTable = table
        conjIndex = 0
        conjCorrect = 0
        conjAnswer = ""
        conjOutcomes = List(table.cells.size) { null }
        screen = Screen.CONJ_TABLE
    }

    /** Grade the current cell, record it like a drill item, and advance. */
    fun submitConjCell(given: String) {
        val table = conjTable ?: return
        if (conjIndex >= table.cells.size || given.isBlank()) return
        val cell = table.cells[conjIndex]
        val result = grader.grade(cell.item, given)
        val outcome = when (result.grade) {
            Grade.CORRECT -> CellOutcome.CORRECT
            Grade.NEAR -> CellOutcome.NEAR
            Grade.ACCENT_SLIP -> CellOutcome.ACCENT
            Grade.INCORRECT -> CellOutcome.INCORRECT
        }
        conjOutcomes = conjOutcomes.toMutableList().also { it[conjIndex] = outcome }
        if (result.isCorrect) conjCorrect++
        if (settings.snapshotState) {
            learner.record(cell.item, result.isCorrect, Instant.now().toString())
            store.save(learner)
        }
        conjAnswer = ""
        conjIndex++
    }

    /** Reveal the current cell's answer without recording (the "show me" path). */
    fun revealConjCell() {
        val table = conjTable ?: return
        if (conjIndex >= table.cells.size) return
        conjOutcomes = conjOutcomes.toMutableList().also { it[conjIndex] = CellOutcome.REVEALED }
        conjAnswer = ""
        conjIndex++
    }

    val conjDone: Boolean get() = conjTable?.let { conjIndex >= it.cells.size } ?: false

    fun updateSettings(newSettings: AppSettings) {
        settings = newSettings
        grader = Grader(newSettings.toGradingSettings())
        settingsStore.save(newSettings)
    }

    /** Run the full answerability gate on-device (Settings → "Run self-check"). */
    fun runSelfCheck(): SelfCheckReport =
        SelfCheck(catalog, conjugator, generator, space).run()

    /** Weakest skills first (lowest IRT ability) — the abilities the engine tracks. */
    fun weakSkills(): List<SkillRow> =
        learner.abilities.entries
            .sortedBy { it.value }
            .map { (key, theta) -> SkillRow(label = prettySkill(key), theta = theta) }

    val overallAttempts: Int get() = learner.scores.values.sumOf { km -> km.values.sumOf { it.attempts } }
    val overallCorrect: Int get() = learner.scores.values.sumOf { km -> km.values.sumOf { it.correct } }
}

/** "irregular|perfect|production" -> "irregular perfect [production]". */
private fun prettySkill(key: String): String {
    val parts = key.split("|")
    if (parts.size != 3) return key
    val (vc, tam, knowledge) = parts
    return "$vc $tam [$knowledge]"
}
