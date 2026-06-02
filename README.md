# konjugaton

**Hyper-combinatorial grammar practice — exhaustive, IRT-scored verb drilling over a data-driven taxonomy. Hindi (देवनागरी + romanization) first; language-agnostic core.**

`konjugaton` generates exercises from every point in a combinatorial space —

```
verb × TAM × person × number × gender × honorific × construction × polarity × script × knowledge-type × semantic-context
```

— grades your answers, and builds a learner model (`vocab → knowledge-type → score`, plus a per-skill Item-Response-Theory ability estimate). Adding a tense, a verb, or a whole new exercise type is a **data edit**, not a code change.

```bash
konjugaton catalog          # how big is the space, and along which axes?
konjugaton practice -n 10   # drill 10 adaptive exercises
konjugaton report           # where am I weak?
konjugaton tui              # full-screen terminal UI (needs the [tui] extra)
```

It is a faithful clone of [`verbion`](https://github.com/berstearns/verbion) (French), re-pointed at Hindi — same layered architecture, same IRT learner model, same config-flag system, same exhaustive self-check discipline. The difference is the domain: Hindi's verb agrees with **gender** *and* **number**, splits the 2nd person into three **honorific** registers (तू/तुम/आप), takes the **ने-ergative** in perfectives, stacks a six-way **construction** axis — the light-verb / passive layer (कर सकता है, कर चुका है, करना चाहता है, करने लगा, किया जाता है) — and is drilled in **both scripts**. That makes the realizable space **660,120 coordinates** — ~30× larger than verbion's 21,600. See [docs/COMBINATORICS.md](docs/COMBINATORICS.md).

Every workflow is wrapped in a [`justfile`](justfile) — run `just` to list them.
The headline is **`just build`**, which compiles a fully standalone native binary
with [Nuitka](https://nuitka.net) (Python → C): one file, no Python, no venv.

```bash
just build          # → ./dist/konjugaton   (one file, no runtime needed)
./dist/konjugaton practice -n 10
```

---

## Quick start

```bash
uv venv && uv pip install -e ".[dev]"   # or: pipx install konjugaton
konjugaton practice --tam present-habitual --script devanagari -n 8
```

A non-interactive sample (great for seeing the engine without typing):

```bash
konjugaton practice --tam perfect --script devanagari --no-interactive -n 5
```

## What makes it "hyper-combinatorial"

Every axis is an independent dimension; the realizable space is their product,
minus the cells the engine cannot conjugate **and** the ungrammatical agreement
bundles. `konjugaton catalog` prints the live count. The axes shipped today:

| Axis | Values (today) |
|------|----------------|
| verb | 23 verbs (regular + the 6 suppletive irregulars) |
| TAM | present-habitual, past-habitual, present-progressive, past-progressive, perfect, past-perfect, future, subjunctive, imperative |
| person | 1, 2, 3 |
| number | singular, plural |
| gender | masculine, feminine (**the verb agrees** — this is the big multiplier) |
| honorific | neutral, तू (intimate), तुम (familiar), आप (formal) |
| construction | simple, ability (सकना), completive (चुकना), desiderative (चाहना), inceptive (लगना), passive (जाना) |
| polarity | affirmative, negative (नहीं / मत / न) |
| script | Devanagari, romanized |
| knowledge-type | production (cloze), recognition (MC), transliteration (देवनागरी ⇆ roman) |
| semantic-context | daily life, travel, work, studies, emotions |

person × number × gender × honorific do not combine freely — Hindi licenses only
**16 legal agreement bundles** (no "1st person आप", etc.), so the engine never
emits an ungrammatical cell.

## The Hindi engine, in brief

Conjugation is **"radicals + endings"** (the verbion strategy) adapted to Hindi's
periphrastic, agreement-rich morphology:

- The **root** is the lemma minus its `ना` (कर, बोल, खा).
- A **participle** = root + an agreeing suffix (imperfective कर+ता, perfective बोल+ा,
  vowel-glide खा+या).
- Most **TAMs are periphrastic**: a participle (or root+रहा) carrying
  gender/number agreement, plus a होना auxiliary carrying person/tense
  (करता हूँ, कर रहा था, किया है).
- **Future/subjunctive/imperative** take personal endings keyed by person ×
  number × honorific (करूँगा, करे, कीजिए).
- **Irregular** verbs supply only their suppletive perfectives (किया, गया, हुआ,
  दिया, लिया, पिया).
- The **renderer** places negation *preverbally* (नहीं/मत/न, by TAM) and inserts
  the **ने-ergative** on a transitive subject in a perfective TAM (मैंने किया है),
  where the verb agrees with the object, not the subject.
- The **construction axis** stacks a non-finite form of the main verb under a
  conjugated **light verb** — ability सकना, completive चुकना, desiderative चाहना,
  inceptive लगना, and the passive जाना (कर सकता है, कर चुका है, करना चाहता है,
  करने लगा, किया जाता है). Each compound reuses the *whole* conjugator on its
  light verb, so every TAM/agreement comes for free; compounds stay nominative
  (no ने). Which TAMs each licenses is a closed set (`CONSTRUCTION_TAMS`).

All irregular/agreement forms are **locked as ground-truth pytest cases in both
scripts** — correctness is non-negotiable.

## The learner model

1. **`vocab → knowledge-type → score`** — a recency-weighted mastery cell per (verb, knowledge-type).
2. **IRT abilities** — a latent ability `θ` per *skill* `(verb-class, TAM, knowledge)`, updated online with a 3-parameter-logistic model. This drives **adaptive item selection** (Fisher information) and difficulty-ordered sessions.
3. **Knowledge graph** *(experimental, v2)* — `konjugaton/state/graph.py` relates vocab nodes (same family, same class) and diffuses scores, so mastering `देना` informs your prior on `लेना`.

## Settings, profiles & learner output

Each learner is a **profile** at `~/konjugaton/{userid}/` holding `config.yaml`,
`state.json`, and all output. Pick a profile with `--user`.

```bash
konjugaton config preset gentle --user me   # apply a bundle of ~80 flags
konjugaton config set grading.similarity_tolerance 3 --user me
konjugaton config show --user me            # the full YAML
konjugaton practice --user me               # uses your settings; logs everything
```

**~80 config flags across 15 categories** plus **7 presets** (`default`,
`gentle`, `exam_prep`, `kids`, `polyglot_power`, `listening`, `zen`). Edit
`config.yaml` by hand or in the **TUI settings screen** (press `ctrl+o` in
`konjugaton tui`) — both round-trip through the same store.

Highlights you can flip today:
- **`ignore_accents` + `transliteration`** — a `char → [accepted sequences]` map folding romanization variants (`aa`→`a`, `ee`→`i`, `oo`→`u`, `v`→`w`), so a forgiving grader accepts them.
- **`similarity_tolerance: 0–10`** — length-scaled edit-distance acceptance; near-misses count as correct, flagged `NEAR`.
- **Learner output** — every response, item, and **IRT calculation** (P(correct), θ before/after, EWMA deltas) to `events.jsonl`/`events.csv`, plus per-session state snapshots, under the profile folder.

## Architecture in one diagram

```
cli / tui  ─►  services  ─►  engine  ─►  data  ─►  domain
                   └──────►  state   ─►  analytics ─► domain
```

Dependencies point inward. `domain/` imports nothing but the stdlib. The UI never
touches grammar rules; the grammar rules never touch a terminal. See
[ARCHITECTURE.md](ARCHITECTURE.md).

## Android

A hardcore-minimalist single-Activity Jetpack Compose port lives in
[`minimal-konjugaton-android/`](minimal-konjugaton-android/) — a pure-Kotlin port
of this engine (package `com.konjugaton.hc`), with the Hindi taxonomy synced from
the YAML by `tools/sync_taxonomy.py`, JVM unit tests, and a byte-compatible
`state.json`.

## Extending the taxonomy

- **Add a verb** → one entry in `src/konjugaton/_data/verbs.yaml`.
- **Add a TAM** → a `Tam` value, an ending row in `endings.yaml`, a small composition rule in the conjugator.
- **Add a context** → an entry in `contexts.yaml`.
- **Add a knowledge-type** → a `KnowledgeType` value + a branch in the generator.
- **Add a construction** → a `Construction` value, its licensed TAMs in `CONSTRUCTION_TAMS`, and a light verb (the conjugator does the rest).

Full recipes in [CONTRIBUTING.md](CONTRIBUTING.md).

## Development

```bash
just install     # uv venv + editable install with dev extras
just check       # lint + format-check + strict types + tests (what CI runs)
just sweep       # tour every (TAM × script) cell — see the combinatorics
just build       # compile the standalone Nuitka binary → dist/konjugaton
```

Or call the tools directly:

```bash
ruff check . && ruff format --check .   # lint + format
basedpyright                            # strict type check (0 errors)
pytest                                  # tests (conjugations are locked as ground truth)
```

## License

MIT © 2026 — see [LICENSE](LICENSE).
