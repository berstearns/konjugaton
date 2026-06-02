# The combinatorial space

`konjugaton catalog` prints the live size of the realizable exercise space. This
document enumerates every axis, its values, and the per-target counts that
multiply up to that number. The headline:

> **660,120 realizable coordinates** — ~30× the French `verbion`'s 21,600, and
> that gap *is the point*: Hindi makes the space explosive because the verb
> agrees with **gender** and **number** independently, the second person fans out
> into three **honorific** registers, *and* the finite verb is only the
> `simple` member of a six-way **construction** axis — the light-verb / passive
> layer (कर सकता है, कर चुका है, करना चाहता है, करने लगा, किया जाता है).

Every number here is reproduced exactly by `PermutationSpace.count()`, and
`count()` is asserted equal to a full materialised iteration in
`tests/test_permutations.py`. The whole space is walked and validated item-by-item
by `konjugaton selfcheck` (`tests/test_exhaustive.py`).

---

## The axes

A `Coordinate` is one fully-specified point:

```
(lemma, TAM, person, number, gender, honorific, construction, polarity, script, knowledge, context)
```

| Axis | Size | Values |
|------|-----:|--------|
| **lemma** (verb) | 23 | करना, होना, जाना, देना, लेना, पीना, खाना, आना, सोना, बोलना, पढ़ना, लिखना, देखना, सुनना, समझना, चलना, रहना, कहना, बनना, मिलना, उठना, बैठना, खेलना |
| **TAM** | 9 | present-habitual · past-habitual · present-progressive · past-progressive · perfect · past-perfect · future · subjunctive · imperative |
| **person** | 3 | 1 · 2 · 3 |
| **number** | 2 | sg · pl |
| **gender** | 2 | m · f *(Hindi verbs agree in gender — French does not)* |
| **honorific** | 4 | neutral · तू (intimate) · तुम (familiar) · आप (formal) |
| **construction** | 6 | simple · ability (सकना) · completive (चुकना) · desiderative (चाहना) · inceptive (लगना) · passive (जाना) |
| **polarity** | 2 | affirmative · negative (नहीं / मत / न) |
| **script** | 2 | devanagari · romanized *(a transliteration knowledge axis)* |
| **knowledge** | 3 | production · recognition · transliteration |
| **context** | 5 | rozmarra · safar · kaam · padhai · bhavnaen |

### Why person × number × gender × honorific does **not** give 3·2·2·4 = 48

Those four sub-axes are not independent: Hindi licenses only a closed set of
**agreement bundles**. There is no "1st person आप", no "2nd person neutral",
no "तू plural". The legal (person, number, honorific) triples come straight from
the pronoun table:

| pronoun | person | number | honorific |
|---------|:------:|:------:|-----------|
| मैं | 1 | sg | neutral |
| हम | 1 | pl | neutral |
| तू | 2 | sg | tu |
| तुम | 2 | pl | tum |
| आप | 2 | pl | aap |
| यह | 3 | sg | neutral |
| ये | 3 | pl | neutral |
| आप (3rd) | 3 | pl | aap |

That is **8** legal (person, number, honorific) triples. Crossed with the 2
genders gives **16 legal agreement bundles** — the realizable agreement axis.
(8 × 2 = 16, versus the naive 48; the engine never emits the 32 illegal cells.)

### Why construction does **not** multiply the space by a clean ×6

The construction axis is *gated by TAM*. Each compound is a periphrasis — the
main verb's non-finite part under a conjugated **light verb** — and each light
verb is idiomatic only in a closed set of TAMs (and, for the passive, only with
transitive verbs). So the six constructions license **wildly different** TAM
counts, and `passive` additionally drops the 10 intransitive verbs:

| construction | surface (1sg.m of करना) | licensed TAMs | TAM count | verbs |
|--------------|--------------------------|---------------|:---------:|:-----:|
| **simple** | करता हूँ | all 9 | 9 | 23 |
| **ability** (सकना) | कर सकता हूँ | pres/past-habitual · perfect · past-perfect · future · subjunctive | 6 | 23 |
| **completive** (चुकना) | कर चुका हूँ | perfect · past-perfect · future | 3 | 23 |
| **desiderative** (चाहना) | करना चाहता हूँ | pres/past-habitual · future · subjunctive | 4 | 23 |
| **inceptive** (लगना) | करने लगा था | pres/past-habitual · past-perfect · future | 4 | 23 |
| **passive** (जाना) | किया जाता है | all but imperative | 8 | 13 *(transitive)* |

The compounds never take the imperative, so for them the agreement axis is always
the full **16** bundles (the imperative's 16→6 collapse only touches `simple`).
And a compound is always **nominative** — the ने-ergative is a property of the
`simple` perfective alone (मैं कर सका, not *मैंने; काम किया जाता है, not *ने).

---

## Per-cell multiplier

For a fixed (lemma, TAM, agreement, construction) the remaining axes multiply
freely:

```
polarity (2) × script (2) × knowledge (3) × context (5) = 60
```

---

## Per-construction coordinate counts

```
coordinates(construction) = Σ over licensed TAMs of
                            realizable_verbs(construction) × legal_agreements(TAM) × 60
```

For every compound the agreement axis is the full 16 (no imperative), so the sum
collapses to `verbs × TAMs × 16 × 60`. `simple` keeps its per-TAM detail (the
imperative drops to 6 bundles), giving the familiar 184,920.

| construction | worked product | coordinates |
|--------------|----------------|------------:|
| simple | 8 TAMs × 16 × 60 × 23 + 1 imperative × 6 × 60 × 23 | **184,920** |
| ability | 6 × 23 × 16 × 60 | **132,480** |
| completive | 3 × 23 × 16 × 60 | **66,240** |
| desiderative | 4 × 23 × 16 × 60 | **88,320** |
| inceptive | 4 × 23 × 16 × 60 | **88,320** |
| passive | 8 × 13 × 16 × 60 | **99,840** |
| **TOTAL** | | **660,120** |

Sum: `184,920 + 132,480 + 66,240 + 88,320 + 88,320 + 99,840 = 660,120`. ✓

(`simple` worked example for a 16-bundle TAM: `23 × 16 × 60 = 22,080`; the
imperative: `23 × 6 × 60 = 8,280`; `8 × 22,080 + 8,280 = 184,920`.)

---

## How the gating works (why "realizable", not "raw product")

The raw Cartesian product would be
`23 × 9 × 3 × 2 × 2 × 4 × 6 × 2 × 2 × 3 × 5 = 42,923,520`. The realizable space is
**660,120** — about 1.5 % of that — because three gates fire:

1. **`Conjugator.realizable_agreement(tam, agr)`** drops every illegal agreement
   bundle (the 48→16 collapse above) and, for the imperative, the non-2nd-person
   and neutral cells (16→6).
2. **`Conjugator.realizable_construction(verb, tam, construction)`** drops every
   (construction, TAM) pair the construction does not license, and every passive
   of an intransitive verb. `simple` here reduces to `can_conjugate`.
3. **`Conjugator.can_conjugate(verb, tam)`** drops cells a verb cannot realize
   (here: none — all 23 verbs cover all 9 TAMs, and the 6 irregulars ship their
   suppletive perfectives, so the passive participle is always available).

Neither gate ever lets an ungrammatical or unanswerable cell reach the learner;
`selfcheck` proves it by generating and validating all 660,120 — each item must
round-trip (re-conjugating the stated target reproduces the answer) and
self-grade CORRECT.

---

## The construction axis is a thin layer (and that's the point)

A compound is built by reusing the **whole** finite conjugator on the light verb:

```
compound = [main verb's non-finite part] + [light verb conjugated in (TAM, agreement)]
```

* **ability / completive** stack on the bare **root**:  कर + सकता हूँ / चुका हूँ.
* **desiderative** stacks on the **infinitive**:  करना + चाहता हूँ.
* **inceptive** stacks on the **oblique infinitive**:  करने + लगा था.
* **passive** stacks जाना on the **perfective participle**, which agrees with the
  patient:  की (fem) + जाती है → की जाती है;  किया + गया है → किया गया है.

Because सकना/चुकना/चाहना/लगना decline exactly like any regular intransitive verb
and जाना is already in the catalog (suppletive गया), the engine gets every
TAM/agreement of every compound *for free* — the construction module only picks
the non-finite stem and concatenates. The same holds in the Kotlin port.

---

## Comparison to verbion (French)

| | verbion (FR) | konjugaton (HI) |
|---|---:|---:|
| primary verb axis | 30 verbs | 23 verbs |
| mood/tense (TAM) | 6 | 9 |
| person (incl. number) | 6 | — |
| agreement (person × number × gender × honorific, legal bundles) | — | 16 |
| construction (light-verb / passive layer) | — | 6 |
| polarity | 2 | 2 |
| script | — | 2 |
| knowledge | 2 | 3 |
| context | 5 | 5 |
| **realizable total** | **21,600** | **660,120** |

konjugaton is **~30× larger** with *fewer verbs and fewer contexts* — the
multiplier is entirely structural: gender agreement (×2), the honorific register
(folded into the 16 agreement bundles), the second script (×2), the extra
transliteration knowledge type (×1.5), and now the construction axis (×~3.6 on
top of all that). That is the Hindi verb system being genuinely more
combinatorial than the French one.

---

## Growing the space (it's a data edit)

| Add… | Edit | New coordinates (per addition) |
|------|------|-----------------------------------------------:|
| a verb | `_data/verbs.yaml` | + ~**28,800** (more if transitive — gains the passive) |
| a context | `_data/contexts.yaml` | + ~**132,000** (the whole space ÷ 5) |
| a knowledge type | enum + generator branch | + ~ one-third of the current total |
| a construction | `Construction` enum + `CONSTRUCTION_TAMS` + light verb | + (licensed TAMs) × verbs × 16 × 60 |

The point inherited from verbion holds: **extending the taxonomy is a data edit,
not a code change** — and even the newest, richest axis (construction) adds a
value by naming a light verb and its licensed TAMs, then reuses the existing
conjugator wholesale.
