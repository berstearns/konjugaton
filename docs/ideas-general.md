# Cross-App Ideas — verbion · konjugaton · namastion

Ideas that apply equally to all three language-drilling apps. When implemented in
one app, port to the others (or promote to a shared library).

Per-language ideas live in the sibling folders: `../konjugaton/`, `../verbion/`,
`../namastion/`.

---

## 1. Feedback field below the answer + LLM-designed hint

**Status:** triaged in verbion · open in konjugaton · open in namastion  
**Effort:** M  
**Tags:** ux, feedback, hint, llm

After the user answers, show a toggle-able free-text field where they can write
"I don't know what _Plusquamperfekt_ is" or "I always confuse _haben_ vs _sein_."

- Captured feedback goes into the event log.
- Phase 2: feed that text to an LLM to generate a tailored hint/mini-explanation
  and surface it inline.

**Open questions**
- Should the hint be generated on-demand (API call) or pre-baked into data files?
- CLI vs TUI vs Android — which surfaces get it first?

---

## 2. Collect learner background profile

**Status:** triaged in all three  
**Effort:** M  
**Tags:** profile, data, irt

Collect at first run (or in settings):

- L1 / native language + nationality
- Age
- Sex
- Prior assessment / test results (DELF, CEFR self-rating, etc.)

Use to seed IRT ability priors instead of starting everyone at θ = 0. Also
enables analytics segmentation (does L1 predict which errors are most common?).

**Open questions**
- First-run wizard vs settings command vs profile file?
- Which fields feed the IRT prior vs. are analytics-only?

---

## 3. Practice mode vs Assessment mode

**Status:** triaged in verbion · open in konjugaton · open in namastion  
**Effort:** L  
**Tags:** engine, cli, practice, assessment

Split the single drill flow into two named modes:

| Mode | Question selection | Goal |
|------|--------------------|------|
| **practice** | depth-guided — drill weak skills harder | build mastery |
| **assessment** | breadth-guided, time-bounded — sample the full taxonomy fast | estimate current ability |

Assessment seeds / refreshes the IRT θ estimate that practice then consumes.
Assessment results also link to idea #2 (background profile).

**Open questions**
- How does the axis/selector differ for breadth vs depth?
- Does assessment output a summary report / CEFR-band estimate?

---

## 4. Turso cloud DB sync (CLI ↔ Android, cross-device)

**Status:** triaged in verbion · open in konjugaton · open in namastion  
**Effort:** XL  
**Tags:** data, infra, sync

Learner state is currently trapped per-device. The Python CLI writes to
`~/{app}/{userid}/` and the Android app keeps its own JSON — nothing reconciles
them.

Add a **Turso (libSQL/SQLite) cloud DB** as the shared backbone, mirroring the
pattern proven in app7
(`/home/b/p/minimal-android-apps/app7-haskell-cross-device-alignment_20260520_154912`).

Architecture (copy from app7):

```
shared remote Turso schema
├── Python outbox → PayloadUploader (CLI sync client)
└── Kotlin outbox → PayloadUploader (Android sync client)
        ↕  last-writer-wins per (device_id, local_id)
    AlignmentService (merge skill-ability snapshots)
```

Reference: app7 `schemas/turso-schema.sql` + `shared/.../data/sync/`.  
Secrets: `TURSO_URL` + `TURSO_AUTH_TOKEN` via env / OS keyring (never baked into binary).

Decomposed child tasks (do in order):
1. Remote Turso schema + device identity model
2. Python sync client with outbox + HTTP adapters
3. Android sync client mirroring app7 adapters

**Open questions**
- Python-first (canonical log) then Android, or both from day one?
- Conflict policy for snapshots: LWW acceptable, or per-skill CRDT merge?

---

## 5. Single-topic drill from the weak-spots view

**Status:** in-progress in verbion · open in konjugaton · open in namastion  
**Effort:** L  
**Tags:** android, engine, practice, ux, logging

The "Where am I weak?" report currently dead-ends — it shows weak skills but
gives no path to drill them. Make each weak-spot row **tappable**:

1. Tap row → confirm dialog "Start a session on _<topic>_?"
2. Confirm → drill scoped to **only that topic** (hard-pin one axis value in the
   selection engine, distinct from the existing soft weak-axis weighting).
3. Tag the session in the event log as `origin: user_topic_drill` so analytics
   can distinguish targeted remediation from regular adaptive practice.

Grain decision (from verbion): pin the *broadest* valid filter for now (e.g. a
whole tense family), not a narrow full coordinate. Narrow later.

**Open questions**
- Which axis to pin when a row could map to more than one (verb vs tense vs mood)?
- Event-log schema: new field or reuse an existing session-metadata slot?

---

## 6. Paradigm / conjugation-table completion mode

**Status:** shipped in konjugaton · in-progress in verbion · open in namastion  
**Effort:** L  
**Tags:** engine, practice, ux, android, tui

Pick a lexeme + tense-mood (or TAM for Hindi), fill the **entire paradigm** in
one focused session. Each cell is graded and recorded like a normal drill item.

The focused, single-lexeme counterpart to the random-sampling adaptive drill.

Surfaces:
- **CLI** — `table` command (`konjugaton table --verb haben --tense-mood praesens`)
- **TUI** — `HomeScreen → VerbPickScreen → TenseMoodPickScreen → table drill`
- **Android** — `ConjSetupScreen → ConjTableScreen`

Port order for the remaining apps: verbion next (French/Spanish morphology maps
cleanly), namastion last (Hindi needs the gender × number × TAM cell grid).

---

## 7. Canonical shared domain (Haskell or Rust core)

**Status:** triaged in verbion · future / research in konjugaton + namastion  
**Effort:** XL  
**Tags:** engine, build, refactor, research

All three apps ship the domain **twice**: a Python core and a hand-mirrored
Kotlin port. Drift is structural — guarded only by independent test suites, and
`DEV-WORKFLOW.md` already names the failure mode.

Long-term fix: one algebraic source of truth compiled to a shared C ABI `.so`
and consumed by every surface (CLI via ctypes, Android via JNI, future iOS).

Two candidate source languages:

| | Haskell | Rust |
|-|---------|------|
| proven in | app7 | — |
| ships to Android | hand-translated C (no GHC runtime) | via `cargo ndk` / JNI directly |
| ships to Python | ctypes of the same .so | PyO3/maturin |
| drift eliminated? | yes (Haskell = spec, C = artifact, parity test pins them) | yes (one binary everywhere) |
| complexity | XL — two copies still, parity test is the guard | XL — build toolchain, but one copy |

**Trigger to reconsider:** repeated parity-test failures, a third platform (iOS),
or domain complexity that makes maintaining two implementations dominate feature
work.

Incremental first step (already in flight in verbion): a py→fixture←kotlin
**parity test harness** that pins both implementations to the same golden outputs.

---

## Implementation priority (suggested order)

| # | Idea | Effort | Blocking? |
|---|------|--------|-----------|
| 5 | Single-topic drill from weak-spots | L | no |
| 3 | Practice vs Assessment modes | L | feeds #2 |
| 2 | Learner background profile | M | feeds #3 |
| 1 | Feedback field + LLM hint | M | no |
| 6 | Paradigm table mode | L | done in konjugaton |
| 4 | Turso cross-device sync | XL | no, but high value |
| 7 | Shared canonical domain | XL | wait for pain threshold |
