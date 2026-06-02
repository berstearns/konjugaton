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
import com.konjugaton.hc.domain.Conjugator
import com.konjugaton.hc.domain.ExerciseGenerator
import com.konjugaton.hc.domain.Grader
import com.konjugaton.hc.domain.GradedResponse
import com.konjugaton.hc.domain.Item
import com.konjugaton.hc.domain.PermutationSpace
import com.konjugaton.hc.domain.PracticeService
import com.konjugaton.hc.domain.QualityEvaluator
import com.konjugaton.hc.domain.SelfCheck
import com.konjugaton.hc.domain.SelfCheckReport
import com.konjugaton.hc.domain.VocabState
import java.io.File
import java.time.Instant
import kotlin.random.Random
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

enum class Screen { HOME, DRILL, REPORT, SETTINGS }

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
