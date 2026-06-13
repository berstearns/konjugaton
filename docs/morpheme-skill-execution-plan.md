# Morpheme skills — execution & implementation plan

> The build companion to [`morpheme-skill-design.md`](morpheme-skill-design.md).
> That doc argues the *why* and the domain *shape*; this one is the
> file-by-file, phase-by-phase plan to ship it — with acceptance gates, tests,
> and the reliability/answerability discipline wired in from P0.
>
> **Status:** specced, not executed. **Scope:** German prefixes only
> (separable + inseparable + dual + hin/her directionals). Stems/endings/
> circumfix are explicitly deferred (§13).

---

## 0. One-paragraph summary

Reify the morphemes the conjugator already computes-and-discards, into a
first-class `Morpheme` inventory loaded from a new `prefixes.yaml`; link each
`Verb` to its prefix and base-root; add a **parallel** generation pipeline
(`MorphemePermutationSpace` + `MorphemeGenerator`) that emits the existing
`Item`, scored under a new `morph|…`-namespaced `MorphemeSkill`. Everything
downstream of `Item` (grading, IRT, repository, report) is reused unchanged.
The verb pipeline and conjugator hot path are **not touched**.

---

## 1. Goals & non-goals

**Goals**
- A reified, identity-bearing morpheme inventory (separable, inseparable, dual, directional).
- `Verb.prefix_id` + `Verb.base_root`, making inseparable prefixes visible and the `kommen`-wheel derivable.
- Four morpheme exercise archetypes: `MEANING`, `RECOGNITION`, `CLASSIFICATION` (new), `USAGE`.
- A `MorphemeSkill` the IRT learner model can track ("weak on `ent-`").
- Tri-source self-validation + answerability gate, run locally via `selfcheck` + exhaustive test.

**Non-goals (this change)**
- No stem/ending/circumfix reification (deferred — §13).
- No change to the verb `Coordinate` space or its 41,660 count.
- No change to `ConjugatedForm`, the conjugator, `endings.yaml`, the renderer.
- No `Coordinate`/`Skill` Protocol promotion yet (earn it on the 3rd skill type).
- No cloud CI (gates are `just` + `pytest` + `selfcheck`, local).

---

## 2. Architecture deltas at a glance

```
_data/prefixes.yaml  (NEW)
        │ load + validate (Pydantic, extra=forbid)
        ▼
   Catalog{ verbs(+prefix_id,+base_root), prefixes, directionals }   ← EDIT loader/Catalog
        │
        ├── (verb pipeline) PermutationSpace → ExerciseGenerator ──┐   UNCHANGED
        │                                                          │
        └── (NEW) MorphemePermutationSpace → MorphemeGenerator ────┤
                                                                   ▼
                                                                 Item  (REUSED)
                                                                   │
                              grading / IRT / repository / report ▼  (REUSED + new skill namespace)
```

The **only** new vertical is the morpheme generation lane. It rejoins the trunk
at `Item`.

---

## 3. File-by-file change table

`port-map style`: **CREATE** = new file, **EDIT** = additive change, **REWRITE**
= structural change. No file is REWRITE — the change is strictly additive.

| File | Action | What |
|------|--------|------|
| `_data/prefixes.yaml` | **CREATE** | the prefix + directional taxonomy (data) |
| `_data/README.md` | EDIT | document the new file's schema |
| `domain/morphology.py` | **CREATE** | `MorphemeKind`, `Stress`, `Morpheme`, `Segment`, `Segmentation` |
| `domain/morph_taxonomy.py` | **CREATE** | `MorphemeCoordinate`, `MorphemeSkill` |
| `domain/enums.py` | EDIT | add `KnowledgeType.CLASSIFICATION`; keep `MEANING`/`USAGE` |
| `domain/verb.py` | EDIT | add `prefix_id: str\|None`, `base_root: str\|None` (additive fields); derive `separable_prefix` compatibility |
| `domain/__init__.py` | EDIT | export the new symbols |
| `data/models.py` | EDIT | `PrefixModel`, `DirectionalModel`, `PrefixesFile`; add `prefix_id`/`base_root` to `VerbModel` |
| `data/loader.py` | EDIT | parse `prefixes.yaml`; build `Morpheme`s; extend `Catalog`; `_to_verb` passes new fields |
| `engine/morph_permutations.py` | **CREATE** | `MorphemePermutationSpace` (+ `MorphAxisSelection`, `count()`) |
| `engine/morph_generator.py` | **CREATE** | `MorphemeGenerator` — coordinate→`Item`, one branch per knowledge type |
| `engine/segmenter.py` | **CREATE** | mirror the conjugator's boundary rules → `Segmentation` (the round-trip oracle for `CLASSIFICATION`) |
| `engine/__init__.py` | EDIT | export the new engine classes |
| `services/selfcheck.py` | EDIT | walk the morpheme space too; morpheme-specific invariants; tri-source check |
| `services/grading.py` | EDIT (maybe) | accept set-answers for `USAGE` "pick the prefix" (else reuse as-is) |
| `analytics/reports.py` | EDIT | a `morph|…` section: weak prefixes, prefix-class rollups, the wheel heatmap |
| `state/*` (scoring/repository) | EDIT (minimal) | none if keyed by `skill.key` string; verify `morph|…` keys round-trip |
| `cli/app.py` | EDIT | `practice --domain morpheme` (or a `drill` command); `catalog` shows morpheme-space size |
| `justfile` | EDIT | `selfcheck` already covers it; add `drill` convenience recipe |
| `tests/test_morphemes.py` | **CREATE** | unit: taxonomy load, segmenter, generator per knowledge type |
| `tests/test_morphemes_exhaustive.py` | **CREATE** | walk full morpheme space, assert all invariants |
| `tests/test_permutations.py` | EDIT | assert verb-space count **unchanged** (regression guard) |
| `docs/COMBINATORICS.md` | EDIT | add the morpheme-space count section |
| `docs/ideas.md` | EDIT | pointer line under "axes worth adding" |

---

## 4. Data contracts

### 4.1 `_data/prefixes.yaml`

```yaml
prefixes:
  - id: an                       # stable morpheme identity (the FK target)
    kind: prefix_separable       # prefix_separable | prefix_inseparable | prefix_dual
    stress: prefix               # prefix | root | meaning_dependent
    core_meaning_en: "toward / onto / switch-on"
    semantic_fields: [approach, attach, begin]
    aspect_roles: [ingressive]
  - id: ent
    kind: prefix_inseparable
    stress: root
    core_meaning_en: "away / out of / reversal / escape"
    semantic_fields: [separation, escape, undoing]
    aspect_roles: [reversal, privative]
  - id: durch
    kind: prefix_dual
    stress: meaning_dependent
    core_meaning_en: "through"
    literal_gloss: "through (physical)"
    figurative_gloss: "thoroughly / see-through"

directionals:
  - axis: in
    toward_speaker: herein
    away_speaker: hinein
    spoken: rein
```

### 4.2 `verbs.yaml` additions (additive, optional)

```yaml
  - lemma: entkommen
    translation: to escape
    verb_class: strong
    auxiliary: sein
    transitive: false
    frequency_rank: 120
    prefix_id: ent          # NEW — now inseparable prefixes are visible
    base_root: kommen       # NEW — joins the kommen-wheel
    conjugation: { praeteritum_stem: kam, partizip2: entkommen, konjunktiv2_stem: käm }
```

`separable_prefix` stays valid for existing entries; new entries may use
`prefix_id` instead. The loader reconciles the two (§5.2).

### 4.3 Pydantic (`data/models.py`)

```python
class PrefixModel(BaseModel):
    model_config = _STRICT
    id: str
    kind: MorphemeKind
    stress: Stress
    core_meaning_en: str
    semantic_fields: list[str] = Field(default_factory=list)
    aspect_roles: list[str] = Field(default_factory=list)
    literal_gloss: str | None = None
    figurative_gloss: str | None = None

class DirectionalModel(BaseModel):
    model_config = _STRICT
    axis: str
    toward_speaker: str
    away_speaker: str
    spoken: str | None = None

class PrefixesFile(BaseModel):
    model_config = _STRICT
    prefixes: list[PrefixModel]
    directionals: list[DirectionalModel] = Field(default_factory=list)

# VerbModel gains:  prefix_id: str | None = None ; base_root: str | None = None
```

---

## 5. Domain objects (final shapes)

### 5.1 `domain/morphology.py`
`MorphemeKind`/`Stress` StrEnums + frozen `Morpheme`, `Segment`, `Segmentation`
as in the design doc §4.1.

### 5.2 `domain/verb.py` — additive fields + reconciliation

```python
@dataclass(frozen=True, slots=True)
class Verb:
    ...
    prefix_id: str | None = None
    base_root: str | None = None

    @property
    def effective_separable_prefix(self) -> str | None:
        """What the conjugator reads. Prefer the explicit field; fall back to
        prefix_id only when the linked morpheme is separable (resolved at load)."""
        return self.separable_prefix
```

> **Invariant enforced at load:** if both `separable_prefix` and `prefix_id` are
> set they must agree; if only `prefix_id` is set and its morpheme is separable,
> the loader fills `separable_prefix` so the **conjugator path stays byte-for-byte
> identical**. This is what makes §1's "hot path untouched" promise true.

### 5.3 `domain/morph_taxonomy.py`
`MorphemeCoordinate` + `MorphemeSkill` (design §4.3), `key` namespaced `morph|…`.

---

## 6. Engine

### 6.1 `engine/segmenter.py` — the round-trip oracle

A `Segmenter` that, given a `Verb`, returns the `Segmentation` for a target form
by mirroring the conjugator's boundary rules (prefix | ge | stem | ending). It
does **not** call the conjugator (avoids coupling) but is asserted equal to the
conjugator's surface in the exhaustive test — if they ever diverge, the build
fails. This is the engine that powers `CLASSIFICATION` answers without
hand-authoring.

### 6.2 `engine/morph_permutations.py`

```python
class MorphemePermutationSpace:
    def __init__(self, catalog): self._catalog = catalog
    def iter_coordinates(self, sel=None) -> Iterator[MorphemeCoordinate]: ...
    def count(self, sel=None) -> int: ...
```

The space is `morpheme × knowledge (× base_root for wheel × context for usage)`
— far smaller than the verb space, and **independent** of it (`count()` is
reported separately; `test_permutations.py` asserts the verb count is unchanged).

A morpheme-scoped implemented-knowledge tuple (mirrors `IMPLEMENTED_KNOWLEDGE`):

```python
MORPH_IMPLEMENTED_KNOWLEDGE = (MEANING, RECOGNITION, CLASSIFICATION, USAGE)
```

### 6.3 `engine/morph_generator.py`

`MorphemeGenerator.generate(coord, rng) -> Item`, dispatching on `coord.knowledge`:

| knowledge | prompt | answer source | distractors |
|-----------|--------|---------------|-------------|
| `MEANING` | "What does `an-` add?" | `Morpheme.core_meaning_en` | other glosses, **determinacy-gated** |
| `RECOGNITION` | MCQ over class/gloss | data | gated |
| `CLASSIFICATION` | "Where does `ge-` go in `entkommen`?" | **segmenter** (round-trip) | sep/insep/dual cells |
| `USAGE` | "kommen + *escape* → ?" / hin-her in context | data + `base_root` / context | constrained to unique answer |

Each fills the same `Item` fields (`prompt/answer/choices/irt/task/metadata`) so
selfcheck's structural checks apply verbatim. `task` must pin the answer-
determining axis (the morpheme id and the asked dimension) — answerability.

---

## 7. Self-validation & answerability (P0 deliverable)

Extend `services/selfcheck.py`:

1. **Static taxonomy invariants** (run once on `prefixes.yaml`):
   - `stress == prefix ⟺ kind == prefix_separable`; `root ⟺ inseparable`;
     `meaning_dependent ⟺ dual`.
   - dual ⇒ both `literal_gloss` and `figurative_gloss` non-null.
   - every `Verb.prefix_id` / `base_root` resolves to a known morpheme / a real root group.
2. **Round-trip** (per separable verb): `segmenter(verb).surface ==
   conjugator.conjugate(...).tail-bound PII` (the `ge-` lands inside).
3. **Per-item invariants** (walk the morpheme space): reuse `_check_item`'s
   structural + self-grading checks; add a `_check_morph_specific`:
   - `MEANING`/`RECOGNITION`: distractor set contains **no synonym** of the key
     (determinacy gate — the `weg-/fort-/ab-` trap).
   - `CLASSIFICATION`: the stated class matches the segmenter.
   - `USAGE` production: exactly one prefix satisfies the prompt, **or** the
     accepted-set is explicit.

Wire into `run_selfcheck` (a second loop over `MorphemePermutationSpace`) and a
new `tests/test_morphemes_exhaustive.py` mirroring `test_exhaustive.py`.

---

## 8. Scoring / IRT / report integration

- **Scoring/repository:** `ScoreCell` is keyed by a string (`skill.key`). Because
  `MorphemeSkill.key` is `morph|<id>|<kind>|<knowledge>`, it coexists with verb
  `verb|…` keys with **zero schema change**. Verify the JSON repository
  round-trips the new keys (add a test).
- **IRT (`analytics/irt.py`):** ability is estimated per skill key; morpheme
  skills get their own latent dimensions for free.
- **`report`:** add a "Morphemes" section — sort `morph|…` cells by ascending
  EWMA (weakest first), plus a **prefix-wheel heatmap** (rows = `base_root`,
  cols = `prefix_id`, cell = mastery) once `base_root` data exists.

---

## 9. CLI & justfile surface

- `practice`: add `--domain {verb|morpheme}` (default `verb` — additive, no
  behavior change) **or** a sibling `drill` command. Recommendation: a `drill`
  command, so the verb `practice` surface and its many axis flags stay clean.
- `catalog`: print the morpheme-space size alongside the 41,660 verb count
  (clearly separated, two spaces not one product).
- `selfcheck`: already the universal gate — it now covers both spaces.
- `justfile`: add `drill *ARGS` convenience; `check` is unchanged (it runs `test`
  which gains the two new test modules).

---

## 10. Phased execution (each phase independently green)

| Phase | Deliverable | Acceptance gate (all local) |
|-------|-------------|------------------------------|
| **P0 — Reify + invariants** | `prefixes.yaml`, `domain/morphology.py`, `morph_taxonomy.py`, `Verb.prefix_id/base_root`, loader, Pydantic, `segmenter.py`, static + round-trip self-checks | `just check` green; `selfcheck` passes taxonomy + round-trip; **verb-space count unchanged** (`test_permutations.py`); no new exercises yet |
| **P1 — First drill** | `MorphemeGenerator` for `MEANING` + `CLASSIFICATION`; `MorphemePermutationSpace`; `drill` command; `test_morphemes_exhaustive.py` | every generated morpheme item passes structural + self-grading + determinacy; `drill -n 10 --no-interactive` runs |
| **P2 — Learner model** | `MorphemeSkill` scored through repository/IRT; `report` "Morphemes" section | a drill session updates `morph|…` cells; `report` shows weakest prefixes; repository round-trips keys |
| **P3 — Usage + wheel** | `base_root` data for ≥2 wheels (kommen, ziehen); `USAGE` items; hin/her directional items; wheel heatmap | usage items pass uniqueness gate; heatmap renders |
| **P4 — (optional) Protocol** | promote `Coordinate`/`Skill` to Protocols *iff* a 3rd skill type lands | verb + morpheme generators dispatch through one `generate()` |

P0 ships **no user-visible feature** on purpose — it's the data + invariants
foundation, fully gated, so P1+ build on something proven correct.

---

## 11. Test plan

- `test_morphemes.py` (unit): taxonomy loads; every `Verb.prefix_id` resolves;
  segmenter boundaries for a hand-picked set (`aufstehen→auf|ge|stand|en`,
  `entkommen→ent|kommen` no `ge-`); generator produces a valid `Item` per
  knowledge type.
- `test_morphemes_exhaustive.py`: walk the whole morpheme space; assert §7
  invariants; cap failures like the existing report.
- `test_permutations.py` (regression): verb-space `count()` byte-identical to
  pre-change; the morpheme space is counted **separately**.
- Property tests (optional): for any verb with a separable `prefix_id`, the
  conjugator's PII contains `ge` *after* the prefix.

---

## 12. Migration & backward-compat

- `verbs.yaml` existing entries are untouched; `prefix_id`/`base_root` are
  optional. A migration pass can backfill them (separable verbs already imply a
  prefix; inseparable ones need a one-time tag).
- No state-file migration: new skill keys are additive; old `verb|…` cells are
  inert and preserved. (If a `migrate` step is wanted, follow the existing
  `cli/app.py:migrate` pattern.)
- `_STRICT` (`extra="forbid"`) means a typo in `prefixes.yaml` is a **startup
  error**, consistent with the rest of the data layer.

---

## 13. Deferred / out of scope

- **Stem / ending / `ge-…-t` circumfix reification.** Prefixes carry the most
  *meaning per token*; endings carry the most *form*. Ship prefixes first; the
  `MorphemeKind` enum leaves room (`STEM`, `ENDING`, `GE_CIRCUMFIX`, `CONNECTOR`).
- **Protocol unification** (P4) — earn it on the 3rd skill type.
- **Audio/IPA for dual-prefix stress** (`UMfahren` vs `umFAHRen`) — text CLI has
  no clean cue; frame as "which stress?" MCQ until audio exists.

---

## 14. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Segmenter drifts from conjugator | exhaustive test asserts `segmenter.surface == conjugator surface` for every verb — divergence fails the build |
| Gloss-collision makes MCQs unanswerable (`weg/fort/ab` = "away") | determinacy gate in `_check_morph_specific`; synonym sets declared in data |
| `prefix_id`/`separable_prefix` disagree | load-time reconciliation invariant; conjugator keeps reading `separable_prefix` |
| Verb-space count silently changes | dedicated regression assertion in `test_permutations.py` |
| Scope creep into stems/endings | `MorphemeKind` ships prefix-only values in P0–P3; others are deferred enum slots |
| New skill keys pollute old state | namespaced `morph|…` keys; old cells inert; repository round-trip test |

---

## 15. Definition of done

- [ ] `prefixes.yaml` loads under `_STRICT`; covers separable + inseparable + dual + directionals.
- [ ] Every `Verb.prefix_id`/`base_root` resolves; inseparable prefixes now visible.
- [ ] `segmenter` reproduces the conjugator's surface for **every** verb (exhaustive).
- [ ] `drill` runs `MEANING` + `CLASSIFICATION` + `USAGE` items; all pass self-grading + determinacy.
- [ ] `MorphemeSkill` cells persist + drive IRT; `report` shows weakest prefixes + wheel heatmap.
- [ ] Verb-space count and conjugator output **unchanged** (regression green).
- [ ] `just check` + `selfcheck` green; two new test modules in `test`.
- [ ] `COMBINATORICS.md` documents the morpheme space; `ideas.md` points to the design doc.
