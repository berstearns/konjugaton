/*
 * The entire UI: the router + every screen, in one file.
 *
 * Navigation is a `when` over `vm.screen` — no NavHost, no routes, no back-stack
 * library. To add a screen: add a Screen enum value (AppState.kt), a branch
 * here, and a @Composable below.
 */
@file:OptIn(ExperimentalMaterial3Api::class)

package com.konjugaton.hc.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.konjugaton.hc.data.AppSettings
import com.konjugaton.hc.domain.Grade
import com.konjugaton.hc.domain.SelfCheckReport
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

@Composable
fun App(vm: AppState) {
    when (vm.screen) {
        Screen.HOME -> HomeScreen(vm)
        Screen.DRILL -> DrillScreen(vm)
        Screen.REPORT -> ReportScreen(vm)
        Screen.SETTINGS -> SettingsScreen(vm)
    }
}

// --- Home ------------------------------------------------------------------

@Composable
private fun HomeScreen(vm: AppState) {
    Scaffold(topBar = { TopAppBar(title = { Text("konjugaton · minimal") }) }) { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.height(24.dp))
            Text("Hindi verb drilling", style = MaterialTheme.typography.headlineSmall)
            Text(
                "${vm.verbCount} verbs · ${"%,d".format(vm.spaceSize)} exercises in the space",
                style = MaterialTheme.typography.bodyMedium,
                textAlign = TextAlign.Center,
            )
            if (vm.overallAttempts > 0) {
                Text(
                    "So far: ${vm.overallCorrect}/${vm.overallAttempts} correct",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            Spacer(Modifier.height(24.dp))
            Button(onClick = { vm.startPractice() }, Modifier.fillMaxWidth()) {
                Text("Practice ${vm.settings.sessionLength}")
            }
            OutlinedButton(onClick = { vm.goReport() }, Modifier.fillMaxWidth()) {
                Text("Where am I weak?")
            }
            OutlinedButton(onClick = { vm.goSettings() }, Modifier.fillMaxWidth()) {
                Text("Settings")
            }
        }
    }
}

// --- Drill -----------------------------------------------------------------

@Composable
private fun DrillScreen(vm: AppState) {
    val item = vm.current ?: return
    val fb = vm.feedback
    val s = vm.settings
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("${vm.sessionIndex + 1} / ${vm.sessionSize}   ✓ ${vm.sessionCorrect}") },
            )
        },
    ) { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(24.dp).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(item.prompt, style = MaterialTheme.typography.headlineSmall)

            // The grammatical target — ALWAYS shown; this is what makes the
            // exercise answerable in Hindi (gender/number/honorific all matter).
            Text(
                item.task,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.primary,
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    if (s.showTranslation) "${item.lemmaHint} — ${item.metadata["translation"].orEmpty()}"
                    else item.lemmaHint,
                    style = MaterialTheme.typography.bodyMedium,
                )
                if (s.showItemDifficulty) {
                    Text(
                        "   · b=${"%.2f".format(item.irt.difficulty)}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                }
            }
            Spacer(Modifier.height(4.dp))

            if (item.isMultipleChoice) {
                item.choices.forEach { choice ->
                    Button(
                        onClick = { if (fb == null) vm.submit(choice) },
                        enabled = fb == null,
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text(choice) }
                }
            } else {
                OutlinedTextField(
                    value = vm.answer,
                    onValueChange = { vm.answer = it },
                    label = { Text("your answer") },
                    enabled = fb == null,
                    modifier = Modifier.fillMaxWidth(),
                )
            }

            if (fb != null) {
                FeedbackCard(fb.grade, item.answer, item.fullSentence, s)
                Button(onClick = { vm.advance() }, Modifier.fillMaxWidth()) {
                    Text(if (s.autoAdvance) "Next now" else "Next")
                }
            } else if (!item.isMultipleChoice) {
                Button(
                    onClick = { vm.submit(vm.answer) },
                    enabled = vm.answer.isNotBlank(),
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Check") }
            }

            TextButton(onClick = { vm.goHome() }) { Text("End session") }
        }
    }
}

@Composable
private fun FeedbackCard(grade: Grade, answer: String, fullSentence: String, s: AppSettings) {
    val (verdict, color) = when (grade) {
        Grade.CORRECT -> "सही (correct)" to MaterialTheme.colorScheme.primary
        Grade.NEAR -> "Almost (accepted)" to MaterialTheme.colorScheme.primary
        Grade.ACCENT_SLIP -> "Right word, check the diacritics" to MaterialTheme.colorScheme.tertiary
        Grade.INCORRECT -> "Not quite" to MaterialTheme.colorScheme.error
    }
    val wrong = grade == Grade.INCORRECT
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(verdict, style = MaterialTheme.typography.titleMedium, color = color)
            if (!wrong || s.showCorrectOnError) {
                Text("Answer: $answer", style = MaterialTheme.typography.bodyLarge)
            }
            if (s.showFullSentence && fullSentence.isNotBlank()) {
                Text(fullSentence, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

// --- Report ----------------------------------------------------------------

@Composable
private fun ReportScreen(vm: AppState) {
    val rows = vm.weakSkills()
    Scaffold(topBar = { TopAppBar(title = { Text("Weak spots") }) }) { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(24.dp).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (rows.isEmpty()) {
                Text("No data yet — practice a session first.")
            } else {
                Text(
                    "Ability per skill (lowest first). θ ranges −4…+4.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                rows.forEach { row ->
                    Card(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(12.dp)) {
                            Text(row.label, style = MaterialTheme.typography.titleSmall)
                            Text("θ = ${"%.2f".format(row.theta)}", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
            Button(onClick = { vm.goHome() }, Modifier.fillMaxWidth()) { Text("Back") }
        }
    }
}

// --- Settings --------------------------------------------------------------

@Composable
private fun SettingsScreen(vm: AppState) {
    val s = vm.settings
    fun set(block: AppSettings.() -> AppSettings) = vm.updateSettings(s.block())

    Scaffold(topBar = { TopAppBar(title = { Text("Settings") }) }) { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(horizontal = 20.dp).verticalScroll(rememberScrollState()),
        ) {
            Section("Session & flow")
            SwitchRow("Auto-advance", "go to the next exercise automatically", s.autoAdvance) {
                set { copy(autoAdvance = it) }
            }
            if (s.autoAdvance) {
                StepperRow("Auto-advance delay", s.autoAdvanceDelayMs, 200, 4000, 200, "ms") {
                    set { copy(autoAdvanceDelayMs = it) }
                }
            }
            StepperRow("Session length", s.sessionLength, 3, 50, 1, "items") {
                set { copy(sessionLength = it) }
            }
            ChoiceRow("Order", s.sessionOrder, listOf("adaptive", "easy-first", "hard-first", "random")) {
                set { copy(sessionOrder = it) }
            }
            SwitchRow("Adaptive selection", "order by Item-Response-Theory information", s.adaptiveEnabled) {
                set { copy(adaptiveEnabled = it) }
            }

            Section("Question filter")
            ChoiceRow(
                "Answer script",
                s.answerScript,
                listOf("both", "devanagari", "romanized"),
            ) { set { copy(answerScript = it) } }
            ChoiceRow(
                "Question types",
                s.questionMode,
                listOf("all", "multiple-choice", "typed", "transliterate"),
            ) { set { copy(questionMode = it) } }

            Section("Answer acceptance")
            SwitchRow("Ignore case", null, s.ignoreCase) { set { copy(ignoreCase = it) } }
            SwitchRow("Ignore accents", "fold romanization variants (aa=a, ee=i…)", s.ignoreAccents) { set { copy(ignoreAccents = it) } }
            SwitchRow("Ignore punctuation", null, s.ignorePunctuation) { set { copy(ignorePunctuation = it) } }
            StepperRow("Similarity tolerance", s.similarityTolerance, 0, 10, 1, "/10") {
                set { copy(similarityTolerance = it) }
            }
            SwitchRow("Require subject pronoun", null, s.requireSubjectPronoun, planned = true) { set { copy(requireSubjectPronoun = it) } }
            SwitchRow("Accept either script", "Devanagari ⇆ romanized", s.acceptEitherScript, planned = true) { set { copy(acceptEitherScript = it) } }
            SwitchRow("Partial credit (periphrastic)", null, s.partialCreditPeriphrastic, planned = true) { set { copy(partialCreditPeriphrastic = it) } }
            SwitchRow("First-attempt typo grace", null, s.firstAttemptTypoGrace, planned = true) { set { copy(firstAttemptTypoGrace = it) } }

            Section("Feedback")
            SwitchRow("Show correct answer on error", null, s.showCorrectOnError) { set { copy(showCorrectOnError = it) } }
            SwitchRow("Show full sentence", null, s.showFullSentence) { set { copy(showFullSentence = it) } }
            SwitchRow("Show translation", null, s.showTranslation) { set { copy(showTranslation = it) } }
            SwitchRow("Show item difficulty", "surfaces the IRT b parameter", s.showItemDifficulty) { set { copy(showItemDifficulty = it) } }
            SwitchRow("Char-diff on error", null, s.charDiffOnError, planned = true) { set { copy(charDiffOnError = it) } }
            SwitchRow("Literal English gloss", null, s.showLiteralGloss, planned = true) { set { copy(showLiteralGloss = it) } }
            SwitchRow("Grammar hint on error", null, s.grammarHintOnError, planned = true) { set { copy(grammarHintOnError = it) } }

            Section("Item construction")
            StepperRow("Multiple-choice options", s.mcChoices, 2, 6, 1, "", planned = true) { set { copy(mcChoices = it) } }
            SwitchRow("Ramp difficulty with streak", null, s.rampWithStreak, planned = true) { set { copy(rampWithStreak = it) } }

            Section("Scaffolding (planned)")
            SwitchRow("Pollinate on error", "i+1 micro-step chain to the answer", s.pollinateOnError, planned = true) { set { copy(pollinateOnError = it) } }
            SwitchRow("Conjugation table on miss", null, s.showConjugationTableOnMiss, planned = true) { set { copy(showConjugationTableOnMiss = it) } }
            SwitchRow("Track grammar tags", null, s.trackGrammarTags, planned = true) { set { copy(trackGrammarTags = it) } }

            Section("Motivation (planned)")
            SwitchRow("Streaks", null, s.streaks, planned = true) { set { copy(streaks = it) } }
            SwitchRow("Celebrate milestones", null, s.celebrateMilestones, planned = true) { set { copy(celebrateMilestones = it) } }

            Section("Output")
            SwitchRow("Persist learner state", "save scores & abilities between sessions", s.snapshotState) { set { copy(snapshotState = it) } }
            SwitchRow("Log responses", "write an event log per answer", s.logResponses, planned = true) { set { copy(logResponses = it) } }

            Section("Display")
            ChoiceRow("Theme", s.theme, listOf("auto", "light", "dark"), planned = true) { set { copy(theme = it) } }

            Section("Quality")
            SelfCheckRow(vm)

            Spacer(Modifier.height(16.dp))
            Button(onClick = { vm.goHome() }, Modifier.fillMaxWidth()) { Text("Back") }
            Spacer(Modifier.height(24.dp))
        }
    }
}

@Composable
private fun Section(title: String) {
    Spacer(Modifier.height(16.dp))
    Text(title, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
    HorizontalDivider(Modifier.padding(top = 4.dp, bottom = 4.dp))
}

@Composable
private fun SwitchRow(
    label: String,
    subtitle: String?,
    checked: Boolean,
    planned: Boolean = false,
    onChange: (Boolean) -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(label, style = MaterialTheme.typography.bodyLarge)
            val sub = listOfNotNull(subtitle, if (planned) "planned" else null).joinToString(" · ")
            if (sub.isNotEmpty()) {
                Text(sub, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline)
            }
        }
        Switch(checked = checked, onCheckedChange = onChange)
    }
}

@Composable
private fun StepperRow(
    label: String,
    value: Int,
    min: Int,
    max: Int,
    step: Int,
    unit: String,
    planned: Boolean = false,
    onChange: (Int) -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(label, style = MaterialTheme.typography.bodyLarge)
            if (planned) {
                Text("planned", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline)
            }
        }
        TextButton(onClick = { onChange((value - step).coerceAtLeast(min)) }) { Text("−") }
        Text("$value$unit", style = MaterialTheme.typography.bodyLarge, modifier = Modifier.width(64.dp), textAlign = TextAlign.Center)
        TextButton(onClick = { onChange((value + step).coerceAtMost(max)) }) { Text("+") }
    }
}

@Composable
private fun ChoiceRow(
    label: String,
    value: String,
    options: List<String>,
    planned: Boolean = false,
    onChange: (String) -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 6.dp).clickable {
            val next = options[(options.indexOf(value) + 1) % options.size]
            onChange(next)
        },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(label, style = MaterialTheme.typography.bodyLarge)
            if (planned) {
                Text("planned · tap to cycle", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline)
            } else {
                Text("tap to cycle", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline)
            }
        }
        Text(value, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.primary)
    }
}

@Composable
private fun SelfCheckRow(vm: AppState) {
    var report by remember { mutableStateOf<SelfCheckReport?>(null) }
    var running by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    Column(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
        OutlinedButton(
            onClick = {
                running = true
                scope.launch(Dispatchers.Default) {
                    val r = vm.runSelfCheck()
                    report = r
                    running = false
                }
            },
            enabled = !running,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(if (running) "Running…" else "Run answerability self-check") }

        report?.let { r ->
            val color = if (r.ok) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
            Text(
                if (r.ok) "✓ ${r.coordinatesChecked} exercises checked, all well-posed (${r.verbs} verbs, ${r.tams} TAMs)"
                else "✗ ${r.failures.size} failures / ${r.coordinatesChecked} checked",
                style = MaterialTheme.typography.bodyMedium,
                color = color,
                fontWeight = FontWeight.Medium,
                modifier = Modifier.padding(top = 8.dp),
            )
            r.failures.take(5).forEach {
                Text("• $it", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
            }
        }
    }
}
