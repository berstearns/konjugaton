# Architecture

konjugaton is a layered, data-driven system. The guiding rule: **dependencies point inward, toward a pure domain that knows nothing of I/O, frameworks, or UIs.** It is a direct clone of verbion's architecture, re-pointed at Hindi.

```
        ┌─────────────┐   ┌─────────────┐
        │     cli     │   │     tui     │      presentation (Typer / Textual)
        └──────┬──────┘   └──────┬──────┘
               └────────┬────────┘
                 ┌───────▼───────┐
                 │   services    │              application / use-cases
                 └───┬───────┬───┘
            ┌────────▼──┐  ┌─▼──────────┐
            │   engine  │  │   state    │        engine = grammar; state = learner
            └────┬──────┘  └─────┬──────┘
                 │               │
            ┌────▼──────┐   ┌────▼───────┐
            │   data    │   │ analytics  │        data = catalog; analytics = IRT/reports
            └────┬──────┘   └────┬───────┘
                 └───────┬───────┘
                  ┌───────▼───────┐
                  │    domain     │              pure value objects + enums (stdlib only)
                  └───────────────┘
```

## Layers

| Layer | Responsibility | May import |
|-------|----------------|------------|
| `domain` | Entities, value objects, the combinatorial vocabulary (enums). Pure. | stdlib only |
| `data` | Validate bundled YAML (Pydantic), hand back domain objects. | `domain` |
| `engine` | Conjugation, permutation enumeration, item generation, surface rendering. | `domain`, `data` |
| `analytics` | IRT math (3PL), pure-Python tabular reports. | `domain` |
| `state` | Learner model: scores, abilities, persistence, graph (v2). | `domain`, `analytics` |
| `settings` | Pydantic config schema, per-user YAML store, preset bundles. | `domain` |
| `services` | Use-cases: build sessions, grade (config-driven), log learner output, query the space. | all inner |
| `cli` / `tui` | Presentation + I/O wiring only. | `services`, `state`, `settings` |

The import direction is enforced by convention and is easy to audit: `grep -r "import" src/konjugaton/domain` returns only stdlib.

## Why the UI is decoupled

`cli/app.py` and `tui/app.py` both import **only** `konjugaton.services` and `konjugaton.state`. Neither touches the conjugator or the scoring math. That is why there are two front-ends over one core, and why a third (web API, GUI) would be additive, not invasive.

## The combinatorial space

A `Coordinate` is one fully-specified point:

```
(lemma, TAM, person, number, gender, honorific, construction, polarity, script, knowledge, context)
```

`PermutationSpace.iter_coordinates(selection)` yields the Cartesian product filtered by `AxisSelection`, by `Conjugator.realizable_construction` (which gates the light-verb/passive layer per TAM and folds in `can_conjugate`, so unrealizable cells never appear), and by `Conjugator.realizable_agreement` (so ungrammatical agreement bundles never appear — there is no "1st person आप"). `count()` sizes the space without materializing it. See [docs/COMBINATORICS.md](docs/COMBINATORICS.md) for the exact arithmetic (660,120).

A `Coordinate` projects onto a coarser `Skill = (verb_class, TAM, knowledge)` — the latent dimension of the learner model. Agreement features (person/number/gender/honorific), construction, polarity, script and the specific lemma modulate *item difficulty*, not *which ability* is exercised. This keeps the IRT model from exploding to one parameter per sentence.

## Conjugation: radicals + endings, the Hindi way

French is concatenative (stem + ending → one word). Hindi is overwhelmingly **periphrastic and agreement-rich**, so `engine/conjugator.py` composes a structured `ConjugatedForm` (main word + optional auxiliary) from:

- a **root** (lemma minus `ना`),
- a **participle suffix** that agrees in number + gender (imperfective `ता/ती/ते/तीं`, perfective `ा/ी/े/ीं` or the vowel-glide `या/यी/ये/यीं`), and
- a **होना auxiliary** carrying person/tense for the periphrastic TAMs.

Special rules baked in (each is a small, documented branch):

- **Future/subjunctive** personal endings keyed by person × number × honorific, with a gender tail on the future (`करूँगा`/`करेगी`); a **vowel-final glide** re-spells the matra ending after a vowel stem (`खाएगा`), with the idiosyncratic `हो`-stem special-cased (`होगा`/`होंगे`).
- The **तुम-feminine quirk**: तुम takes plural-masculine but singular-feminine participle agreement (`तुम करते हो` / `तुम करती हो`, not `करतीं`).
- The **ने-ergative**: a transitive verb in a perfective TAM agrees with the (default masc-sg) **object**, not the subject — so `मैंने/तुमने/उसने किया है` is invariant; the subject's `ने` is attached by the renderer.
- **Irregular** verbs supply only their suppletive perfectives and, where needed, an oblique future stem or an irregular आप-imperative.

`render.py` applies the surface/syntactic rules kept out of the morphology: **preverbal negation** (नहीं for indicative, मत for imperative, न for subjunctive) and the **ने** postposition on ergative subjects (with the suppletive pronoun forms मैं→मैंने, यह→इसने).

## Item Response Theory

`analytics/irt.py` implements the 3-parameter logistic model:

```
P(correct | θ) = c + (1 − c)·σ(a·(θ − b))
```

- Each generated `Item` carries seed parameters (`b` from cell features — TAM, verb class, gender, polarity, knowledge; `c = 1/n_choices` for MC, 0 otherwise).
- After each answer, `update_ability` takes one gradient step on the learner's `θ` for that skill.
- `information(θ, params)` (Fisher information) lets `PracticeService` order a session **adaptively** — most informative item first.

The seed parameters are heuristic and transparent; the design anticipates replacing them with parameters *calibrated* from response data.

## The learner model (two layers, + a third planned)

1. `VocabState.scores`: `lemma → knowledge-type → ScoreCell` (attempts, correct, recency-weighted EWMA).
2. `VocabState.abilities`: `Skill → θ`, updated by IRT.
3. `state/graph.py` (**experimental**): a `KnowledgeGraph` over vocab/skill nodes with typed edges (same-family, same-class, semantic) and score diffusion — the path to "mastering *देना* informs *लेना*".

## Persistence

`StateRepository` is a `Protocol`; `JsonStateRepository` is the shipped implementation. The on-disk shape (`version`, `scores`, `abilities`, `ensure_ascii=False`) is **byte-compatible with the Android port's `state.json`**. Swapping in SQLite or a remote store is a new class, not a service change.

## Reliability strategy

Three layers, the verbion discipline:

1. **Ground-truth conjugation tests** (`tests/test_conjugator.py`) — 58 hand-verified forms in both scripts pin every irregular, every agreement cell, the ने-ergative, the honorific endings.
2. **Exhaustive selfcheck** (`tests/test_exhaustive.py`, `konjugaton selfcheck`) — walks all 660,120 coordinates and asserts each item is structurally valid, **answerable** (its task pins TAM + agreement + construction + polarity), and **self-grades CORRECT**.
3. **Binary smoke in a clean env** (CI) — compiles the Nuitka binary and runs `selfcheck` / `catalog` under `env -i` (ASCII locale), which is also the UTF-8 path that matters most for Devanagari output.
