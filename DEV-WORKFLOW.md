# konjugaton — Dev Workflow

The full lifecycle of a konjugaton change across **all four surfaces** that sit
over the one pure core. Complements [`README.md`](./README.md) (what it does),
[`ARCHITECTURE.md`](./ARCHITECTURE.md) (how the layers fit), and
[`CONTRIBUTING.md`](./CONTRIBUTING.md) (taxonomy recipes). This is the *operational*
runbook: how you build, run, test, and ship each surface — and where each one's
sharp edges are.

konjugaton is a faithful clone of [`verbion`](https://github.com/berstearns/verbion)
(French) re-pointed at Hindi, so this runbook mirrors verbion's. The domain is
the difference: Hindi's verb agrees with **gender** *and* **number**, splits the
2nd person into three **honorific** registers (तू/तुम/आप), takes the
**ने-ergative** in perfectives, stacks a six-way **construction** axis (the
light-verb / passive layer — कर सकता है, कर चुका है, करना चाहता है, करने लगा,
किया जाता है), and is drilled in **both scripts**. That makes the realizable
space **660,120 coordinates** (~30× verbion's 21,600).

The mental model from [ARCHITECTURE.md](./ARCHITECTURE.md) is the whole point:

```
cli  ·  tui  ·  android        four presentations  ──┐
                                                      ├─►  ONE pure core
services ─► engine/state ─► data/analytics ─► domain ─┘   (no I/O, no UI)
```

Three of the four (CLI, TUI, Android) are *additive* front-ends — adding one
never touches the conjugator or the IRT math. The fourth, **Deploy**, is how the
core leaves the repo: as a standalone Nuitka binary, a PyPI wheel, or a pure
Kotlin/JVM Android APK.

Every workflow below is wrapped in the [`justfile`](justfile) — run `just` to
list them. The Android surface has its own Gradle wrapper.

---

## Single source of truth: the taxonomy

Before the four sections, the rule that binds them: **the combinatorial
taxonomy is authored once**, in YAML, and every surface consumes it.

```
src/konjugaton/_data/{verbs,endings,contexts}.yaml    ◀ canonical, hand-edited
        │
        ├─► CLI + TUI    Pydantic validation (data/ layer) → domain objects
        └─► Android      tools/sync_taxonomy.py  →  app/src/main/assets/*.json
```

"Adding a verb is a data edit, not a code change" only stays true if both
consumers stay in lockstep. **After editing any `_data/*.yaml`, re-run the
Android sync** (Section 4) or the APK silently drifts from the CLI/TUI.

```
src/konjugaton/_data/verbs.yaml  ── edit ──►  python minimal-konjugaton-android/tools/sync_taxonomy.py
```

One axis is *not* in the YAML: the **construction** axis (simple + ability सकना
+ completive चुकना + desiderative चाहना + inceptive लगना + passive जाना) is a
closed enum gated by TAM in the engine (`Construction` + `CONSTRUCTION_TAMS`),
because each compound reuses the *whole* conjugator on its light verb. Adding a
construction is therefore an enum + gate edit (mirrored in both engines), not a
YAML edit — see [`CONTRIBUTING.md`](./CONTRIBUTING.md) and
[`docs/COMBINATORICS.md`](./docs/COMBINATORICS.md).

---

## Layout

```
konjugaton/
├── src/konjugaton/
│   ├── domain/        # pure value objects + enums (stdlib only)
│   ├── data/          # YAML → domain (Pydantic)
│   ├── engine/        # conjugation, permutation, item generation, labels
│   ├── analytics/     # IRT (3PL), reports
│   ├── state/         # learner model, persistence, graph (v2)
│   ├── settings/      # config schema, per-user YAML store, presets
│   ├── services/      # use-cases (build session, grade, log, selfcheck)
│   ├── cli/app.py     # ◀ SECTION 1 — Typer CLI (the primary UI)
│   ├── tui/app.py     # ◀ SECTION 3 — Textual full-screen TUI
│   ├── migrate.py     # versioned event-log migration framework (schema v3)
│   └── _data/*.yaml   # the taxonomy (single source of truth)
├── entrypoint.py      # Nuitka build entry
├── justfile           # task runner — `just` lists everything
├── dist/konjugaton     # ◀ SECTION 2 — compiled standalone binary (~30 MB)
├── scripts/tui_actor.py   # headless TUI driver (Pilot harness)
├── docs/COMBINATORICS.md  # the 660,120 arithmetic, axis by axis
├── .github/workflows/ci.yml   # quality + wheel + clean-env binary gate
└── minimal-konjugaton-android/    # ◀ SECTION 4 — single-Activity Compose port
    ├── app/src/main/kotlin/com/konjugaton/hc/domain/   # pure-Kotlin core mirror
    ├── app/src/main/assets/*.json                     # synced taxonomy
    └── tools/sync_taxonomy.py                          # YAML → JSON pipeline
```

Per-learner output lives **outside** the repo, one profile per user (rooted at
`$KONJUGATON_HOME`, default `~/konjugaton/`):

```
~/konjugaton/{userid}/
├── config.yaml     # the ~80 settings flags (round-trips with CLI + TUI)
├── state.json      # learner model (scores + IRT abilities)
├── events.jsonl    # every response + IRT calculation (also .csv)
└── …               # per-session state snapshots
```

The Android app keeps the *same-shaped* `state.json` at `filesDir/state.json`
(byte-compatible with `VocabState.to_dict`) — see Section 4.

---

# 1 · UI (the Typer CLI)

The CLI is the **primary** user interface and the reference implementation of
every behaviour. The TUI and Android app are ports of what the CLI already does.

### Surface

`src/konjugaton/cli/app.py` — Typer commands, importing **only** `konjugaton.services`,
`konjugaton.state`, `konjugaton.settings` (never the conjugator or scoring math):

| Command | What it does |
|---|---|
| `version` | print version |
| `catalog` | size the combinatorial space + its axes (incl. the construction axis) |
| `verbs [--class CLASS]` | list the verb inventory |
| `practice` | the drill loop (the headline command) |
| `selfcheck` | exhaustively validate engine + data over **every** coordinate (660,120) |
| `report` | mastery + IRT-ability report |
| `assess` | time-bounded placement assessment (no per-item feedback) |
| `config {show,set,preset}` | per-user settings |
| `profile` | show the learner background + paths |
| `tui` | launch the Textual UI (Section 3) |
| `migrate` | run the versioned event-log migration (→ schema v3) |

### Dev loop

```bash
just install                       # uv venv + editable install with dev extras
just drill --tam future --gender f -n 5            # generic CLI passthrough
konjugaton practice --no-interactive -n 5 --seed 1  # deterministic, no typing
just sweep                         # tour every (TAM × script) cell
```

Hindi-specific drill shortcuts (each is a thin `practice` slice):

```bash
just tam perfect          # one TAM across the space
just feminine             # feminine-agreement drill (the big Hindi miss)
just honorific-aap        # the आप register
just ergative             # the ने-ergative (transitive perfectives)
just negatives            # नहीं / मत / न placement
just translit             # Devanagari ⇆ romanized
just script romanized     # one script across the space
konjugaton practice --construction passive --tam perfect -n 8   # the new axis
```

Profiles select state + config:

```bash
konjugaton config preset gentle --user me
konjugaton config set grading.similarity_tolerance 3 --user me
konjugaton practice --user me       # uses that profile; logs to ~/konjugaton/me/
```

### Done When (the gate before you move to any other surface)

```bash
just check        # lint + format-check + strict types + tests — exactly what CI runs
```

`just check` = `ruff check` · `ruff format --check` · `basedpyright` (strict, 0
errors) · `pytest`. Conjugations are **locked as ground truth** in the tests
(every irregular perfective, every agreement cell, the ने-ergative, the honorific
endings, and now the compound surfaces — in BOTH scripts) — if you change
morphology, the test diff is the spec change, review it.

### Adding a CLI command

One `@app.command()` function in `cli/app.py`. It may call into `services`/`state`/
`settings` only. If it needs new grammar or scoring behaviour, that goes in the
inner layers first (and gets its own unit test), then the command wires it up.

---

# 2 · Deploy

konjugaton builds artifacts that require **no Python** on the user's machine.

| Artifact | Recipe | Output | Goes to leao? |
|---|---|---|---|
| Standalone binary | `just build` | `dist/konjugaton` (~30 MB, one file, no venv) | ✅ as `<TS>-<feature>-linux` |
| Binary + bundled TUI | `just build-tui` | `dist/konjugaton` (larger) | ✅ (build this first if the TUI must work offline) |
| Android release APK | `:app:assembleRelease` (Section 4) | `app-release.apk` (R8-shrunk, pure Kotlin/JVM) | ✅ as `<TS>-<feature>-release.apk` |
| Wheel + sdist | `just build-wheel` (`uv build`) | `dist/*.whl`, `*.tar.gz` | — PyPI / `pipx` / `uv pip` channel |

### The deploy-bug gate (the hard constraint)

> **Hard constraint.** Unit tests run *inside* your dev venv with the full
> source tree on `sys.path`. They cannot catch a **packaging** regression —
> data YAML that didn't get bundled, a module Nuitka pruned, a relative import
> that only works from source. Those fail *only* in the shipped artifact, on
> the user's machine, with Python absent. So the artifact must be self-checked
> in a **clean environment with no Python on PATH**.

The single command that proves the binary is shippable:

```bash
just binary-smoke
```

which is `just build` followed by, crucially, runs under `env -i` (empty
environment — no Python, no venv):

```bash
./dist/konjugaton version
env -i ./dist/konjugaton selfcheck                 # exhaustive engine+data validation (660,120)
env -i ./dist/konjugaton catalog | tail -3         # exercises the bundled-data path
env -i ./dist/konjugaton practice --tam future --script devanagari --no-interactive -n 3 --seed 1
```

If `selfcheck` or `catalog` fails under `env -i` but passes in your venv, you
have a **bundling/pruning regression** — the failure is silent on the producer
side (builds fine) and only manifests for the end user. Do not ship. Fix the
Nuitka include flags (`--include-package-data=konjugaton` is what carries
`_data/*.yaml`).

### What CI enforces (`.github/workflows/ci.yml`)

Three jobs gate every push/PR to `main`/`master`:

1. **quality** — `ruff check`, `ruff format --check`, `basedpyright` (strict),
   `pytest` across the Python version matrix.
2. **build** — `uv build`, then asserts the wheel actually contains the data:
   `python -m zipfile -l dist/*.whl | grep -E '_data/(verbs|endings|contexts)\.yaml'`.
3. **binary** — compiles the real Nuitka binary with `just build`, then runs
   `env -i ./dist/konjugaton selfcheck` and `env -i ./dist/konjugaton catalog`.
   This is the clean-env gate above, automated.

> Mirror locally before you push: `just check && just binary-smoke`. CI's
> `binary` job is the one that catches the class of bug unit tests can't see.

### The leao remote (the deploy target)

The same rclone scheme as app7: remote `ber:` + bucket `leao-bernardo/` + a
per-app subpath + `release/`. konjugaton's subpath nests under the languages
folder, beside verbion:

```
ber:leao-bernardo/
├── manga-reading/release/        (app7  — LEAO_APP_PREFIX=app7)
├── paper-reading/release/        (app11 — LEAO_APP_PREFIX=app11)
└── linguas/
    ├── verbion/release/          (the French sibling)
    └── konjugaton/release/        ◀ konjugaton  →  ber:leao-bernardo/linguas/konjugaton/release/
        ├── <RUN_TS>-<feature>-linux         (the Nuitka standalone binary)
        └── <RUN_TS>-<feature>-release.apk   (the Android APK)
```

The target is a single justfile variable — override per invocation if needed:

```bash
just leao_remote := "ber:leao-bernardo/linguas/konjugaton/release"   # the default
```

### Ship it

```bash
just deploy-leao        my-feature   # gate (binary-smoke) + upload dist/konjugaton
just deploy-leao-apk    my-feature   # assembleRelease + upload the APK
just deploy-leao-all    my-feature   # both, in one go
just leao-list                       # what's on the remote right now
```

- **`deploy-leao` is gated** — it depends on `binary-smoke` (below), so a binary
  that fails the clean-env self-check **never reaches leao**.
- `<feature>` defaults to `latest`; pass a kebab name so the remote filename is
  self-describing (the `<RUN_TS>` prefix keeps every upload distinct).
- Needs `rclone` configured for `ber:` (`rclone listremotes` should show it).
  The APK uploads as one `rclone copyto` — no per-ABI slicing (pure Kotlin/JVM).

> **`deploy-leao` ships from your working tree** — fine for a quick personal
> push. For a *real* release (anything you'd hand to someone or push public),
> go through the safe leg instead: export a verified secret-free clone, then
> build + deploy **from scratch** out of that clone. That's app7's step-4/5
> pattern, adapted to konjugaton → see **[`RELEASE.md`](RELEASE.md)**:
>
> ```bash
> scripts/convert-to-public.sh                            # secret-scan + clean export → ../public-konjugaton-<TS>/
> scripts/release-e2e.sh ../public-konjugaton-<TS> my-feature [--with-apk]
> ```
>
> konjugaton has no secrets today, so the export is mostly a **scan gate + clean
> copy** (no `.venv`/state/caches) — but the pipeline already strips signing
> keys / backend config the moment konjugaton grows them.

### Verify a leao upload (hand-off)

```bash
REMOTE="ber:leao-bernardo/linguas/konjugaton/release"
NAME=<the-name-you-uploaded>      # e.g. 20260602_181500-my-feature-linux

# Linux binary
rclone copyto "${REMOTE}/${NAME}" /tmp/konjugaton && chmod +x /tmp/konjugaton
env -i /tmp/konjugaton selfcheck   # same clean-env gate, now against the shipped copy

# Android APK
rclone copyto "${REMOTE}/<TS>-<feature>-release.apk" /tmp/konjugaton.apk
adb install -r /tmp/konjugaton.apk # -r keeps the local state.json (no DB wipe)
```

`adb install -r` (replace) preserves `filesDir/state.json`, so the learner's
progress survives the update — konjugaton has no Room DB to wipe.

---

# 3 · TUI (Textual)

A full-screen terminal UI over the **same** services as the CLI — drilling plus
a settings screen bound bidirectionally to `config.yaml`.

### Surface

`src/konjugaton/tui/app.py` — a Textual `App` (`KonjugatonApp`) importing only
`konjugaton.services`, `konjugaton.state`, `konjugaton.settings`,
`konjugaton.analytics.irt`. The settings screen reads `Settings` on open and
writes them back on save, so editing in the TUI or editing `config.yaml` by hand
both round-trip through the **same store**. Shortcuts are **config-driven and
remappable** (text-based, vim-friendly — `prev`/`next`/`hint`/`settings`/`quit`,
default `ctrl+left`/`ctrl+right`/…).

### Run it

```bash
just tui                          # = konjugaton tui
konjugaton tui --user me           # a specific profile
```

The TUI is an **optional extra** to keep the core dependency footprint small:

```bash
uv pip install -e '.[tui]'        # or '.[dev]', which includes it
just build-tui                    # bundle Textual INTO the standalone binary
```

A plain `just build` (Section 2) does **not** include Textual — the binary's
`tui` command will fail at import. Ship `build-tui` if the binary must offer the
TUI offline.

Press the `settings` shortcut in the running TUI for the settings screen.

### Testing the TUI headlessly (the key trick)

Textual ships a `Pilot` harness (`App.run_test()`) that boots the **real** TUI
with no terminal and lets you drive it programmatically. `scripts/tui_actor.py`
is the canonical driver: it acts as an oracle — types the correct answer, goes
deliberately wrong every Nth item — and because the TUI logs through
`LearnerLogger`, the run produces a genuine `events.jsonl` *generated through the
UI* (not the CLI), under `$KONJUGATON_HOME/<user>/`.

```bash
python scripts/tui_actor.py kela-tui --errors-every 5
# → answered/correct counts + the events path it wrote
```

Use this to verify a TUI change actually records the same learner output the CLI
does — without a human at a keyboard. It presses `enter` to grade and then the
configured `next` key (default `ctrl+right`) to advance — read from the app's
own settings, so it follows your keybindings.

### Adding a TUI screen / binding

A new screen is a Textual `Screen` subclass + a binding; a new key is an entry
in the config-driven shortcut map (no hardcoded key). It must pull data through
`services`/`state` only — same decoupling rule as the CLI.

---

# 4 · Android app (`minimal-konjugaton-android`)

A **hardcore-minimalist, single-Activity Jetpack Compose** port — same
data-driven taxonomy, an equivalent pure-Kotlin domain (conjugator, generator,
grader, 3PL-IRT). Fully offline, JVM-testable in ~3s with no emulator. Its own
README is [`minimal-konjugaton-android/README.md`](./minimal-konjugaton-android/README.md);
this section is the operational summary + how it connects to the Python core.

### Surface

```
minimal-konjugaton-android/app/src/main/kotlin/com/konjugaton/hc/
├── domain/      # ◀ PURE KOTLIN, zero Android imports — the konjugaton core, mirrored
│                #   Enums, Models, Conjugator, Render, Generator, Permutations,
│                #   Labels, Grading, Irt, LearnerState, Catalog, Practice, Quality
├── data/        # Loader.kt (JSON→domain), Store.kt (VocabState ⇄ filesDir/state.json)
├── ui/          # AppState.kt (one ViewModel) + Screens.kt (router = when(screen))
└── MainActivity.kt
```

Navigation is `when (vm.screen)` over an enum — no `NavHost`, no Room, no DI.
Adding a screen = enum value + a `when` branch + a `@Composable`.

### Build · run · test

Needs `ANDROID_HOME` (the SDK) and **JDK 17** (the module is `JavaVersion.VERSION_17`
/ `jvmTarget = JVM_17`). Run from `minimal-konjugaton-android/`:

```bash
./gradlew :app:testDebugUnitTest   # fast loop — pure-JVM domain tests, no device (~3s)
./gradlew :app:installDebug        # onto a device/emulator
./gradlew :app:assembleRelease     # → app/build/outputs/apk/release/ (R8-shrunk APK)
```

The release build is `isMinifyEnabled = true` + `isShrinkResources = true`
(R8 full mode) — that's where the size shrink comes from. (The debug APK,
`:app:assembleDebug`, is ~10 MB unshrunk.)

### Keeping the taxonomy in sync (the cross-surface obligation)

```bash
cd minimal-konjugaton-android
python tools/sync_taxonomy.py      # ../src/konjugaton/_data/*.yaml → app/src/main/assets/*.json
```

`sync_taxonomy.py` mirrors `{verbs,endings,contexts}.yaml` verbatim into JSON
(`ensure_ascii=False`, so Devanagari stays readable). It only needs PyYAML
(already in the konjugaton venv). **Re-run it whenever you touch the YAML**, then
rebuild — otherwise the APK ships a stale taxonomy while the CLI/TUI moved on.
This is the single most common way the Android surface drifts. (The construction
axis lives in Kotlin code, not the assets, so a construction change is a Kotlin
edit — see below — not a re-sync.)

### Done When

```bash
./gradlew :app:testDebugUnitTest   # the ported domain matches konjugaton's behaviour
```

The Kotlin `domain/` tests (`ConjugatorTest`, `GradingTest`, `IrtTest`,
`QualityTest`) are the Android analogue of the Python `pytest` ground-truth
suite. `QualityTest` walks the **entire 660,120-coordinate** space on the plain
JVM and asserts every item is well-posed and self-grades CORRECT; `ConjugatorTest`
locks the compound surfaces and the exact per-construction counts. If a
conjugation or the taxonomy size changed, both suites should reflect it.

### Mirroring an engine change (the parity rule)

A change to grammar, scoring, or the combinatorial space must land in **both**
engines or the surfaces diverge:

```
src/konjugaton/{domain,engine}/…   ─┐
                                   ├─►  same change, same tests, both green
minimal-konjugaton-android/app/src/main/kotlin/com/konjugaton/hc/domain/…  ─┘
```

The Construction axis is the worked example: it touched `enums`, `taxonomy`/
`Models`, `conjugator`, `render`, `generator`, `permutations`, `labels` on the
Python side and the identical files under `com/konjugaton/hc/domain/` on the
Kotlin side, with the exact same `CONSTRUCTION_TAMS` gate and `660_120` count
asserted in each test suite.

### No ABI matrix here

konjugaton's Android app is **pure Kotlin/JVM — no NDK, no native libs**. There
is nothing per-ABI to get wrong: one APK runs on every device. If you ever add a
native component, that's when a per-ABI fat-APK rule becomes relevant.

### Deliberately NOT ported (minimalism)

The Textual TUI, the Typer CLI, the experimental knowledge graph, and the large
"declared but unwired" settings surface. Add them back as data/code only when
actually needed.

---

## Hard rules (all surfaces)

- **The UI never touches grammar or scoring.** `cli/app.py`, `tui/app.py`, and
  the Kotlin `ui/` package import only the application layer. A presentation
  change that reaches into `engine`/`analytics` is the bug, not the feature.
- **Edit the taxonomy in one place.** `src/konjugaton/_data/*.yaml` is canonical.
  Never hand-edit the Android `assets/*.json` — regenerate them with
  `sync_taxonomy.py`.
- **Re-sync Android after any taxonomy edit.** The two consumers drift silently
  otherwise; the APK keeps shipping the old verbs.
- **Engine changes land in both engines.** A grammar/scoring/axis change in
  Python must be mirrored in `com/konjugaton/hc/domain/` with the same tests, or
  the Android surface diverges from the CLI/TUI.
- **A passing `pytest` does not mean a shippable binary.** The clean-env
  `just binary-smoke` (Section 2) is a separate, mandatory gate — it catches the
  packaging/pruning class of bug that source-tree tests structurally cannot.
- **Only deploy through the gated recipe.** Ship with `just deploy-leao*`, never
  a raw `rclone copyto dist/konjugaton ber:…`. The recipe runs `binary-smoke`
  first, so an unverified artifact never reaches the remote. For a *public/real*
  release, go one level safer: `scripts/convert-to-public.sh` → `release-e2e.sh`
  (build from a secret-free clone, from scratch) — see [`RELEASE.md`](./RELEASE.md).
- **`build` vs `build-tui` is a real choice.** Plain `just build` omits Textual;
  shipping a binary whose `tui` command must work means `build-tui`.
- **Conjugations are ground truth.** Both the Python `pytest` suite and the
  Kotlin `domain/` tests lock conjugations — including the compound surfaces.
  Changing morphology is a reviewed spec change, visible in the test diff — not
  an incidental edit.

---

## Common failure modes

| Symptom | Surface | Cause | Fix |
|---|---|---|---|
| `selfcheck`/`catalog` works in venv, fails under `env -i ./dist/konjugaton …` | Deploy | Data/module not bundled into the Nuitka binary | Ensure `--include-package-data=konjugaton` carries `_data/*.yaml`; re-run `just binary-smoke` |
| CI **build** job: "data YAML missing from wheel" | Deploy | `_data/*.yaml` not declared as package data | Fix the packaging config so the wheel includes `_data/{verbs,endings,contexts}.yaml` |
| `konjugaton tui` errors on import in the shipped binary | TUI | Built with `just build` (no Textual) | Rebuild with `just build-tui`, or install the `[tui]` extra for source runs |
| `deploy-leao` aborts before uploading | Deploy | Its `binary-smoke` dependency failed — the gate did its job | Fix the bundling regression (clean-env rows above); the gate refuses to ship an unverified binary |
| `convert-to-public.sh` exit 5 (`secret would leak`) | Release | a real `.env`/keystore/private key is in the tree | Move it out (or `.gitignore` + delete), then re-run — the scan gate is doing its job |
| TUI change "works by hand" but logs nothing | TUI | Drill path bypasses `LearnerLogger` | Drive it with `scripts/tui_actor.py` and confirm `events.jsonl` is written |
| Android shows old verbs after a YAML edit | Android | Forgot `sync_taxonomy.py` before the build | `python tools/sync_taxonomy.py` then `:app:assembleRelease` |
| Android `count()`/`QualityTest` disagrees with `pytest` (e.g. ≠ 660,120) | Android | Kotlin port lagged a Python morphology/axis change | Port the change into `com/konjugaton/hc/domain/` + update the Kotlin test |
| `:app:*` Gradle task fails before compiling | Android | `ANDROID_HOME` unset or JDK ≠ 17 | Set the SDK path; use JDK 17 |
| `just check` green but PR red | All | Local venv missing a dev tool, or Python-version-specific | CI runs the full version matrix — reproduce with the failing version |
| `rclone copyto` returns 401/403 | Deploy | `ber:` token expired | `rclone config reconnect ber:` (interactive), then retry |
| `rclone: remote "ber" not found` | Deploy | rclone not configured on this machine | `rclone listremotes` to confirm; configure `ber:` (same remote verbion uses) |
| Artifact runs in your venv but not after `rclone copyto … && env -i /tmp/konjugaton …` | Deploy | A packaging bug `binary-smoke` would catch — you uploaded without the gate | Always run `just binary-smoke` before the `rclone copyto` |

---

## Reference

- [`README.md`](./README.md) — what konjugaton is + the combinatorial pitch
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — the inward-pointing layer diagram
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — taxonomy extension recipes
- [`RELEASE.md`](./RELEASE.md) — the public-safe convert → e2e → deploy release leg
- [`docs/COMBINATORICS.md`](./docs/COMBINATORICS.md) — the 660,120 arithmetic, axis by axis
- [`minimal-konjugaton-android/README.md`](./minimal-konjugaton-android/README.md) — the Android port in depth
- [`justfile`](justfile) — every workflow command (run `just`), incl. `build-tui` + `deploy-leao{,-apk,-all}` + `leao-list`
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — quality + wheel + clean-env binary gate
- `scripts/tui_actor.py` — headless TUI driver (Pilot harness)
- `scripts/convert-to-public.sh` · `scripts/release-e2e.sh` — the release pipeline
- leao remote: `ber:leao-bernardo/linguas/konjugaton/release/` — same rclone scheme as verbion (`linguas/verbion`)
