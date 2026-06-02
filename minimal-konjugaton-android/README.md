# konjugaton · minimal-konjugaton-android

A **hardcore-minimalist, single-Activity Jetpack Compose** port of
[konjugaton](../). Same data-driven taxonomy, equivalent domain (conjugator,
generator, grader, 3PL-IRT learner model), Android only. No DI, no navigation
library, no Room — the whole "framework" is a `when` over an enum.

```
26 JVM unit tests, ~3s   ·   fully offline   ·   660,120-coordinate self-check on device
```

## Philosophy: simplicity wins

| Decision | Why |
|----------|-----|
| **Single `Activity`** | One `MainActivity`, one `setContent`. |
| **Navigation = `when(vm.screen)`** | No `NavHost`, no routes, no back-stack lib. Add a screen = add an enum value + a branch + a `@Composable`. |
| **One state holder** (`AppState`) | Plain `AndroidViewModel` with `mutableStateOf` fields. No Hilt, no repository interfaces, no use-cases. |
| **Domain = pure Kotlin** (`domain/`) | Zero Android imports → unit-tested on the JVM in milliseconds, no emulator. This is the part that mirrors konjugaton. |
| **Taxonomy = JSON assets** | The *same* verbs/endings/contexts as the Python project, synced by one script. Adding a verb is a data edit. |
| **State = one JSON file** | `filesDir/state.json`, byte-compatible with konjugaton's `VocabState.to_dict`. No database. |

## Layout

```
minimal-konjugaton-android/
├── app/src/main/
│   ├── assets/                 # the taxonomy (generated from ../src/konjugaton/_data/*.yaml)
│   │   ├── verbs.json  endings.json  contexts.json
│   ├── kotlin/com/konjugaton/hc/
│   │   ├── domain/             # ◀ PURE KOTLIN — ported konjugaton engine, JVM-testable
│   │   │   ├── Enums.kt        # the combinatorial axes (Tam/Person/Number/Gender/Honorific/…) + Agreement
│   │   │   ├── Models.kt       # Verb, Coordinate, Skill, Item, ConjugatedForm, EndingTables, …
│   │   │   ├── Conjugator.kt   # radicals + endings → surface form (gender/number/honorific agreement)
│   │   │   ├── Render.kt       # preverbal negation (नहीं/मत/न), ने-ergative, subject attach (SOV)
│   │   │   ├── Generator.kt    # Coordinate → gradable Item (+ MCQ distractors, transliteration, IRT seed)
│   │   │   ├── Permutations.kt # enumerate / count the realizable space (legal agreement bundles)
│   │   │   ├── Grading.kt      # Levenshtein, romanization fold, configurable Grader
│   │   │   ├── Irt.kt          # 3PL: P(correct), ability update, Fisher info
│   │   │   ├── LearnerState.kt # ScoreCell (EWMA) + VocabState
│   │   │   ├── Catalog.kt      # the indexed reference data
│   │   │   ├── Labels.kt       # human-facing axis labels (single source for task + determinacy)
│   │   │   ├── Quality.kt      # QualityEvaluator + SelfCheck (answerability gate)
│   │   │   └── Practice.kt     # session building (reservoir sample + adaptive order)
│   │   ├── data/               # I/O boundary
│   │   │   ├── Loader.kt       # JSON → domain (Serializable DTOs, like pydantic→domain)
│   │   │   ├── Store.kt        # VocabState ⇄ filesDir/state.json
│   │   │   └── Settings.kt     # AppSettings ⇄ filesDir/settings.json
│   │   ├── ui/
│   │   │   ├── AppState.kt     # the single state holder + actions
│   │   │   └── Screens.kt      # App router + Home/Drill/Report/Settings, all in one file
│   │   └── MainActivity.kt
│   └── res/values{,-night}/themes.xml   # dependency-free DayNight window theme
├── app/src/test/kotlin/…/domain/        # ConjugatorTest, GradingTest, IrtTest, QualityTest
└── tools/sync_taxonomy.py               # YAML → JSON asset pipeline
```

## Build · run · test

```bash
# fast loop — pure-JVM domain tests, no device needed (~3s)
./gradlew :app:testDebugUnitTest

# install on a device/emulator
./gradlew :app:installDebug

# minified release APK
./gradlew :app:assembleRelease   # → app/build/outputs/apk/release/

# re-sync the taxonomy after editing the YAML in the Python project
python tools/sync_taxonomy.py
```

Needs `ANDROID_HOME` set (the SDK) and a JDK 17. Open the folder in Android
Studio and it just works.

## "Effortless to change" cheatsheet

| I want to… | Edit | Then |
|------------|------|------|
| **Add a verb** | `../src/konjugaton/_data/verbs.yaml` | `python tools/sync_taxonomy.py` + rebuild |
| **Add a TAM** | `endings.yaml` + `Tam` enum + `TAM_ORDER` + a branch in `Conjugator.conjugate` + `Labels` | run `:app:testDebugUnitTest` |
| **Add a semantic context** | `contexts.yaml` | sync + rebuild |
| **Tune grading** (romanization fold, tolerance) | `GradingSettings` defaults in `Grading.kt` | — |
| **Add a screen** | `Screen` enum (`AppState.kt`) + a `when` branch + a `@Composable` (`Screens.kt`) | — |
| **Change session length / order** | `AppState.startPractice` / Settings | — |

## Relationship to the Python project

The `domain/` package is a faithful port — same algorithms, same data, same
state-file shape — so behaviour matches the CLI. Skill keys
(`verb_class|tam|knowledge`), enum `value` strings, and the `state.json` layout
are byte-compatible with konjugaton. The pieces deliberately **not** ported
(minimalism): the Textual TUI, Typer CLI, the experimental knowledge graph, and
the large "declared but unwired" settings surface. Add them back as data/code
when you actually need them.

## Notes

- **Offline by design** — no `INTERNET` permission. Taxonomy is bundled; state is local.
- **Devanagari is free** — Compose/Android use the OS text stack (HarfBuzz/ICU), so देवनागरी renders and the IME works without bundling anything.
- The committed Gradle wrapper pins **Gradle 8.11.1** (AGP 8.7.3). Bump both together.
- **Not built here:** per project process, the APK/Gradle build runs on a separate device-build pipeline. This tree ships faithful source + synced assets; `./gradlew :app:testDebugUnitTest` is the local gate.
