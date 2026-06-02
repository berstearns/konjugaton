# The combinatorial space

`konjugaton catalog` prints the live size of the realizable exercise space. This
document enumerates every axis and the per-cell counts that multiply up to it.
The headline:

> **41,660 realizable coordinates.** German has no gender agreement on the verb
> and a single script, so Hindi's gender (×2), script (×2) and honorific
> multipliers are gone. The space is built instead from 9 tense-moods, the
> du/ihr/Sie register, and the werden-passive.

Every number here is reproduced exactly by `PermutationSpace.count()`, asserted
equal to a full materialised iteration in `tests/test_permutations.py`, and the
whole space is walked and validated item-by-item by `konjugaton selfcheck`
(`tests/test_exhaustive.py`).

---

## The axes

A `Coordinate` is one fully-specified point:

```
(lemma, tense_mood, person, number, register, voice, polarity, knowledge, context)
```

| Axis | Size | Values |
|------|-----:|--------|
| **lemma** (verb) | 27 | machen, sagen, spielen, lernen, kaufen, wohnen, arbeiten, gehen, kommen, sehen, geben, nehmen, fahren, finden, essen, sprechen, schlafen, stehen, denken, bringen, aufstehen, ankommen, mitkommen, einkaufen, sein, haben, werden |
| **tense-mood** | 9 | Präsens · Präteritum · Perfekt · Plusquamperfekt · Futur I · Futur II · Konjunktiv I · Konjunktiv II · Imperativ |
| **person** | 3 | 1 · 2 · 3 |
| **number** | 2 | sg · pl |
| **register** | 4 | neutral · du · ihr · Sie *(no gender — German verbs don't agree in gender)* |
| **voice** | 2 | Aktiv · Passiv *(werden-passive — transitive verbs only)* |
| **polarity** | 2 | affirmative · negative (nicht) |
| **knowledge** | 2 | production · recognition *(single script — no transliteration)* |
| **context** | 5 | Alltag · Reise · Arbeit · Studium · Gefühle |

Three further facts are **per-verb properties**, not free axes (like Hindi
transitivity drove the ने-ergative): the **verb class** (weak/strong/mixed), the
**auxiliary** (haben/sein), and the **separable prefix**.

### Why person × number × register does **not** give 3·2·4 = 24

German licenses only a closed set of **agreement bundles**, straight from the
pronoun table — and there is no gender to cross with:

| pronoun | person | number | register |
|---------|:------:|:------:|----------|
| ich | 1 | sg | neutral |
| wir | 1 | pl | neutral |
| du | 2 | sg | du |
| ihr | 2 | pl | ihr |
| Sie | 2 | pl | Sie |
| er/sie/es | 3 | sg | neutral |
| sie | 3 | pl | neutral |

That is **7 legal agreement bundles** (the verb ending is keyed by a 6-way
`person|number` slot; *Sie* uses the 3pl slot — *Sie machen* = *sie machen*). The
**Imperativ** exists in the 2nd person only and never `neutral` → **3** bundles
(du/ihr/Sie). The engine never emits an illegal bundle (no "1st-person Sie").

### Why voice does **not** simply double the space

The **Passiv** is realized only for **transitive** verbs and only in the
indicative tenses Präsens/Präteritum/Perfekt/Plusquamperfekt/Futur I (no
Imperativ, no Konjunktiv/Futur II in v1). Of the 27 verbs, **14 are transitive**.

---

## Per-cell multiplier

For a fixed (lemma, tense, agreement, voice) the remaining axes multiply freely:

```
polarity (2) × knowledge (2) × context (5) = 20
```

---

## The arithmetic

### Aktiv

| tenses | agreements | count |
|--------|:----------:|------:|
| 8 non-imperative (Präsens … Konjunktiv II) | 7 | 8 × 27 × 7 × 20 = **30,240** |
| Imperativ | 3 (du/ihr/Sie) | 1 × 27 × 3 × 20 = **1,620** |
| **Aktiv total** | | **31,860** |

### Passiv (14 transitive verbs, 5 indicative tenses, 7 agreements)

```
5 × 14 × 7 × 20 = 9,800
```

### Total

```
31,860 (Aktiv) + 9,800 (Passiv) = 41,660
```

---

## How the gating works (why "realizable", not "raw product")

The raw Cartesian product would be
`27 × 9 × 3 × 2 × 4 × 2 × 2 × 2 × 5 = 1,399,680`. The realizable space is
**41,660** — about 3 % of that — because three gates fire:

1. **`realizable_agreement(tense, agr)`** keeps only the 7 legal bundles and
   collapses the imperative to its 3 second-person cells.
2. **`realizable_voice(verb, tense, voice)`** drops the passive of intransitive
   verbs and the passive of the imperative / Konjunktiv / Futur II.
3. **`can_conjugate(verb, tense)`** — here always true; every verb realizes every
   tense (strong/mixed ship their ablaut stems, the irregulars their forms).

`selfcheck` proves it by generating and validating all 41,660: each item
re-conjugates to its own answer and self-grades CORRECT.

---

## Comparison to the family

| | verbion (FR) | namastion (HI) | konjugaton (DE) |
|---|---:|---:|---:|
| verbs | 30 | 23 | 27 |
| tense-mood | 6 | 9 | 9 |
| gender agreement | — | ×2 | — |
| register / honorific | — | 4 (folded into 16 bundles) | 4 (7 bundles) |
| voice / construction | — | 6 (light-verb layer) | 2 (werden-passive) |
| script | — | 2 | — |
| knowledge | 2 | 3 | 2 |
| **realizable total** | **21,600** | **660,120** | **41,660** |

German sits between French and Hindi: richer than French (the register, the
auxiliary split, strong ablaut, the passive) but without Hindi's gender×script×
honorific explosion.

---

## Growing the space (it's a data edit)

| Add… | Edit | New coordinates |
|------|------|----------------:|
| a weak verb | `_data/verbs.yaml` (lemma + aux) | + ~**1,180** (more if transitive — gains the passive) |
| a context | `_data/contexts.yaml` | + ~**8,300** (the space ÷ 5) |
| a knowledge type | enum + generator branch | + ~half the current total |

The family promise holds: **extending the taxonomy is a data edit, not a code
change.**
