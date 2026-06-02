# Contributing to konjugaton

Thanks for helping grow the taxonomy! Most contributions are **data edits, not code** — that is the whole point of the architecture.

## Setup

```bash
uv venv && uv pip install -e ".[dev]"
pre-commit install        # optional: run gates on every commit
```

## Quality gates (must pass)

```bash
ruff check . && ruff format --check .   # lint + format
basedpyright                            # strict type check (0 errors)
pytest                                  # tests
```

CI runs all three on Python 3.11–3.13, then compiles the Nuitka binary and
self-checks it in a clean (ASCII-locale) environment.

---

## Recipes

### Add a verb

Edit `src/konjugaton/_data/verbs.yaml`. For a **regular** verb, that's the whole
job — the engine derives every form from the root (lemma minus `ना`):

```yaml
- lemma: नाचना
  lemma_roman: nachna
  verb_class: regular
  transitivity: intransitive
  translation: to dance
  frequency_rank: 200
  semantic_tags: [leisure]
```

For an **irregular** (suppletive perfective) verb, supply the perfective set and,
if needed, an oblique future stem or an irregular आप-imperative — then **lock the
forms with a case** in `tests/test_conjugator.py` (both scripts):

```yaml
- lemma: देना
  lemma_roman: dena
  verb_class: irregular
  transitivity: transitive
  translation: to give
  frequency_rank: 6
  conjugation:
    future_oblique: द
    future_oblique_roman: d
    imperative_aap: दीजिए
    imperative_aap_roman: dijiye
    perfective:
      devanagari: { "sg|m": दिया, "sg|f": दी, "pl|m": दिए, "pl|f": दीं }
      romanized:  { "sg|m": diya, "sg|f": di, "pl|m": diye, "pl|f": din }
```

### Add a TAM

1. Add a value to `Tam` in `domain/enums.py`.
2. Add its ending/participle rows to `_data/endings.yaml` (Devanagari + romanized).
3. Add it to `_TAM_ORDER` in `conjugator.py` and a composition branch in `Conjugator.conjugate` (which participle + which auxiliary).
4. Add a human label in `engine/labels.py`, a hint in `services/hints.py`.
5. Add ground-truth cases to `tests/test_conjugator.py`.

### Add a semantic context

Edit `_data/contexts.yaml`. Templates must contain the contiguous token
`{subject} {verb}` (the renderer attaches the subject there). Hindi is verb-final,
so the context phrase comes before it. Provide both scripts:

```yaml
- id: khel
  label_hi: खेल
  label_en: Sports
  templates: ["मैदान में {subject} {verb}।"]
  templates_roman: ["maidan mein {subject} {verb}."]
  affinity: [खेलना, दौड़ना]
```

### Add a knowledge-type

1. Add a value to `KnowledgeType` in `domain/enums.py`.
2. If it should be generated, add it to `IMPLEMENTED_KNOWLEDGE` in `engine/permutations.py` and a branch in `ExerciseGenerator.generate`.

### Add a whole new axis

Examples of high-value axes not yet wired: **passive voice** (किया जाता है),
**compound verbs** (कर लेना / कर देना), **conjunct verbs** (कोशिश करना),
**aspect with चुकना** (कर चुका), **case-marked objects** (को).

1. Add a field to `Coordinate` (and, if it defines a new ability, to `Skill`).
2. Add the axis to `AxisSelection` and `PermutationSpace`.
3. Teach `conjugator.py` / `render.py` / the generator to realize it.
4. Surface it as a `konjugaton practice` flag.

---

## Conventions

- **Both scripts, always.** Every surface form ships Devanagari *and* a romanized twin.
- Keep `domain/` import-free of everything but the stdlib.
- New irregular forms **must** ship with a ground-truth test in both scripts. We treat conjugation correctness as non-negotiable.
- After any data/engine change, run `konjugaton selfcheck` — it walks the whole space and proves every item is well-posed.

## Known Hindi simplifications (good first issues)

- The negative present-habitual keeps the होना auxiliary (मैं नहीं करता हूँ); the prescriptive auxiliary-drop (मैं नहीं करता) is a documented variant, not yet modelled.
- The ने-ergative models the canonical masc-singular **object**; object-gender/number agreement and the को-marked-object (verb defaults to masc-sg) variants are not yet axes.
- Oblique/vocative pronoun case beyond ने is out of scope (subjects are nominative or ergative only).
