# Morpheme skills — remodelling the domain for "token subpieces"

> Design note (ideation, no implementation). How to extend konjugaton from a
> **word-level** practice engine to one that can also drill, score, and model
> **sub-word morphemes** — starting with the German prefix system (separable,
> inseparable, dual; the hin/her directional set; Aktionsart). The focus of this
> document is the **domain remodelling**: which new objects exist, how the
> existing aggregates change, and where the new "skill" attaches.

---

## 1. Motivation — what granularity the domain commits to today

Every **addressable, persisted, scored** unit in the current model is word-wise
(really clause-wise). Morphemes *exist* — the conjugator builds them on every
call — but they are never **reified**: they live only as opaque data fragments
and as transient locals that get concatenated and discarded.

| Layer | Unit | Sub-word present? | In what form |
|-------|------|-------------------|--------------|
| `verbs.yaml` | the lemma | partially | opaque morpheme fragments as strings (`praeteritum_stem: ging`, `partizip2: gegangen`, `separable_prefix: auf`) |
| `Verb` | a word | derived-on-the-fly | `base_lemma` / `stem` *compute* sub-word strings; not stored |
| `Conjugator` internals | — | **yes, transient** | `"ge" + base + "t"`, `prefix + p2`, `base + connector + ending` — local vars, thrown away on return |
| `ConjugatedForm` | the verb complex | split in 2 | `finite` + `tail` — a **syntactic** (V2-position) split, *not* morphological |
| `Item` / grading | the clause string | no | whole-string compare vs `answer` + `accepted` |
| `Skill` / IRT | `(verb_class, tense_mood, knowledge)` | no | ability is per whole-verb-class, never per morpheme |

**The segmentation exists as an algorithm, never as a value.** `_partizip2`
knows the boundary `auf | ge | stand | en` because it is *placing* it, then
returns `"aufgestanden"` and erases it.

**The model knows exactly the morphemes it needs to *conjugate*, and not one
more.** `separable_prefix` is the only named morpheme in the system, and it
exists purely so the conjugator can detach `auf` into the `tail`. The proof:
**inseparable prefixes are invisible** — `verstehen`, `bekommen`, `entkommen`
are flat lemmas with no prefix field, because `ver-/be-/ent-` never detach, so
the engine never needed to know they are morphemes at all.

## 2. The gap, stated precisely

A "token subpiece" (morpheme) skill needs morphemes modelled where **meaning**
lives, which is a *different, larger* set than where **conjugation mechanics**
forced the issue:

- meaning needs **every** prefix — separable **and** inseparable **and** dual;
- meaning needs morpheme **identity** (this `auf` is the same morpheme as that
  `auf`), so mastery can accumulate across verbs;
- meaning needs a **skill of its own** — today's `Skill` is keyed on whole-verb
  attributes, so "weak on `ent-`" or "weak on the `ge-…-t` circumfix" is
  literally inexpressible.

> **We are not adding a sub-word layer to a word-only system. We are *reifying a
> segmentation the engine already computes and discards*, and extending its
> coverage past "what conjugation needed."**

## 3. Design principles (carried from the existing architecture)

1. **Reuse everything downstream of generation.** `Item`, `IrtParameters`,
   grading, IRT analytics, the repository, and `report` are morpheme-agnostic —
   they consume a `(prompt, answer, skill, irt)` shape. The remodelling stops at
   the *generation* boundary; nothing past `Item` changes.
2. **Do not contort `Coordinate`.** Prefix meaning is invariant across person,
   number, tense, voice, polarity, context. Forcing it through the 9-axis verb
   `Coordinate` means pinning 6 axes to dummies and mislabelling the IRT skill.
   A morpheme exercise gets its **own** coordinate type.
3. **Reify, don't recompute blindly.** The conjugator already produces the
   segmentation; the morpheme layer should consume the *same rules* (a segmenter
   that mirrors the conjugator, or a structured return) so the two can never
   disagree — see §7.
4. **Taxonomy = data.** New morpheme knowledge is a new YAML file, validated at
   load with `extra="forbid"`, exactly like `verbs.yaml`/`contexts.yaml`.
5. **Self-validating + answerable.** Every morpheme item's claimed answer is
   cross-checked against an independent source (conjugator, stress flag), and
   distractors pass a determinacy gate. Wired as a local `selfcheck` +
   exhaustive test, never cloud CI.

---

## 4. The domain remodelling (the focus)

### 4.1 New value objects

All frozen dataclasses / `StrEnum`, matching the codebase house style.

```python
# domain/morphology.py  — ILLUSTRATIVE shapes, not implementation

class MorphemeKind(StrEnum):
    PREFIX_SEPARABLE   = "prefix_separable"     # an-, auf-, mit-
    PREFIX_INSEPARABLE = "prefix_inseparable"   # be-, ver-, ent-
    PREFIX_DUAL        = "prefix_dual"          # durch-, über-, um-
    DIRECTIONAL        = "directional"          # herein/hinein/rein (hin/her)
    # future: STEM, ENDING, GE_CIRCUMFIX, CONNECTOR — the rest of the segmentation

class Stress(StrEnum):
    PREFIX = "prefix"            # ⇒ separable
    ROOT   = "root"              # ⇒ inseparable
    MEANING_DEPENDENT = "meaning_dependent"   # ⇒ dual

@dataclass(frozen=True, slots=True)
class Morpheme:
    """A reified, identity-bearing sub-word piece. The thing the model lacked."""
    id: str                     # "an", "ent", "durch"  — stable identity
    kind: MorphemeKind
    stress: Stress
    core_meaning_en: str
    semantic_fields: tuple[str, ...] = ()
    aspect_roles: tuple[str, ...] = ()          # ingressive, resultative, privative…
    # dual prefixes carry both readings:
    literal_gloss: str | None = None
    figurative_gloss: str | None = None

@dataclass(frozen=True, slots=True)
class Segment:
    """One span of a surface form, tagged with the morpheme it realizes."""
    text: str                   # "auf", "ge", "stand", "en"
    kind: MorphemeKind | None   # None for the bare stem until stems are modelled
    morpheme_id: str | None     # links back to a Morpheme when known

@dataclass(frozen=True, slots=True)
class Segmentation:
    """The reified boundary the conjugator currently discards."""
    surface: str                # "aufgestanden"
    segments: tuple[Segment, ...]
```

`Morpheme` is the heart of the remodelling: **the first sub-word object with an
identity**, so ability can accumulate across every verb that carries it.

### 4.2 Remodelling `Verb` — decompose, link, group

Today: `separable_prefix: str | None` (mechanics only). Proposed: a real link
into the morpheme inventory plus a **base root** for the minimal-pair wheel.

```python
@dataclass(frozen=True, slots=True)
class Verb:
    ...
    prefix_id: str | None = None     # FK into the Morpheme inventory (an / ent / durch)
    base_root: str | None = None     # "kommen" for {ankommen, bekommen, entkommen, …}
    # separable_prefix stays, but becomes a *derived* convenience:
    #   = prefix_id if the linked Morpheme.kind is PREFIX_SEPARABLE else None
```

Two payoffs fall straight out of this:

- **`base_root` makes the `kommen`-wheel derivable, not authored** — group the
  catalog by `base_root` and the minimal-pair set materializes from data.
- **`prefix_id` finally sees inseparable prefixes** — `entkommen` gets
  `prefix_id: ent`, which today's `separable_prefix` could never hold.

Backward-compat: the conjugator only ever reads `separable_prefix`; keep that as
a derived property so the hot conjugation path is untouched (principle 3).

### 4.3 The new coordinate + skill — the crux

A morpheme exercise is **not** a point in the verb `Coordinate` product. It gets
a sibling atom and, critically, a **sibling skill** so the learner model can
finally track sub-word mastery.

```python
@dataclass(frozen=True, slots=True)
class MorphemeCoordinate:
    """One fully-specified morpheme exercise point."""
    morpheme_id: str
    knowledge: KnowledgeType        # MEANING | RECOGNITION | classification | USAGE
    base_root: str | None = None    # set for minimal-pair / wheel items (entkommen)
    context: str | None = None      # set for USAGE-in-context items

    def skill(self, kind: MorphemeKind) -> MorphemeSkill:
        return MorphemeSkill(morpheme_id=self.morpheme_id,
                             kind=kind, knowledge=self.knowledge)

@dataclass(frozen=True, slots=True)
class MorphemeSkill:
    """The latent ability the verb-level Skill could never express."""
    morpheme_id: str        # "ent"  → "do you know what ent- means / does"
    kind: MorphemeKind      # rolls up to "dual-prefix classification" aggregates
    knowledge: KnowledgeType

    @property
    def key(self) -> str:
        return f"morph|{self.morpheme_id}|{self.kind.value}|{self.knowledge.value}"
```

Note the `key` is namespaced `morph|…` so it coexists with verb `Skill` keys in
the same repository / IRT store without collision. `report` then has two skill
families to aggregate: `verb|…` and `morph|…`.

### 4.4 Two ways to wire it in — and the recommendation

**Option B — parallel atom (ship this).** `MorphemeCoordinate` and
`MorphemeSkill` live beside the verb ones; a second small
`MorphemePermutationSpace` + `MorphemeGenerator` produce `Item`s that flow into
the *same* grading / IRT / repository / report. The verb pipeline is **not
touched**. Lowest risk, fastest to a working drill.

**Option C — `Coordinate` / `Skill` as Protocols (grow into this).** Promote
both to `typing.Protocol` (`skill()`, `cache_key`), so `VerbCoordinate` and
`MorphemeCoordinate` both satisfy them and `ExerciseGenerator.generate`
dispatches on coordinate *type*. This is the Open/Closed realization of the
project's stated "language-agnostic core" — but only earn it once a **third**
skill type (noun cases? adjective endings?) proves the abstraction.

> **Recommendation: build B, name the seams so C is a refactor not a rewrite.**
> Concretely: put the shared shape (`skill()`, a stable `cache_key`) on both
> coordinate types from day one, even while they are separate classes.

### 4.5 KnowledgeType — extend, carefully

The enum already declares dormant `MEANING` and `USAGE`. Morpheme drilling needs
those plus one genuinely new kind:

| KnowledgeType | Morpheme item it powers | Answer source |
|---------------|-------------------------|---------------|
| `MEANING` | "`an-` adds…?" | `prefixes.yaml` |
| `RECOGNITION` | MCQ over glosses / classes | data + distractor gate |
| `CLASSIFICATION` *(new)* | "sep/insep? where does `ge-` go?" | **the conjugator** (round-trip) |
| `USAGE` | "kommen + *escape* → ?", hin/her in context | data + context |

`CLASSIFICATION` is the one that turns the existing engine into an oracle (§7).
Add it to a morpheme-scoped `IMPLEMENTED_KNOWLEDGE` list — the verb space keeps
its own, so the two never accidentally cross-emit.

---

## 5. Data layer

A new taxonomy sibling, validated strictly at load like the others.

```yaml
# _data/prefixes.yaml  — ILLUSTRATIVE
prefixes:
  - id: an
    kind: prefix_separable
    stress: prefix
    core_meaning_en: toward / onto / switch-on
    semantic_fields: [approach, attach, begin, address]
    aspect_roles: [ingressive]
  - id: ent
    kind: prefix_inseparable
    stress: root
    core_meaning_en: away / out of / reversal / escape
    semantic_fields: [separation, escape, undoing]
    aspect_roles: [reversal, privative]
  - id: durch
    kind: prefix_dual
    stress: meaning_dependent
    literal_gloss: "through (physical)"
    figurative_gloss: "thoroughly / see-through"

directionals:                 # the hin/her closed set
  - axis: in
    toward_speaker: herein
    away_speaker: hinein
    spoken: rein
```

Verb entries gain `prefix_id:` and `base_root:`; `separable_prefix:` can be
dropped from data (derived) or kept transitionally.

---

## 6. What does *not* change (scope guard)

- `ConjugatedForm`, the conjugator's hot path, the `Agreement` model,
  `endings.yaml`, the renderer's word-order logic — **untouched**.
- `Item`, `IrtParameters`, grading, `analytics/irt.py`, the repository,
  `report`'s rendering primitives — **reused as-is**; they only gain a second
  skill-key namespace to bucket on.
- The verb `Coordinate` space and its 41,660 count — **unchanged**; morpheme
  items are counted in a separate space with its own `count()`.

The blast radius is: `domain/morphology.py` (new), small edits to `Verb`, a new
`prefixes.yaml` + its Pydantic schema, a `MorphemePermutationSpace` +
`MorphemeGenerator`, and report/CLI surfacing.

---

## 7. Self-validation & answerability (the invariants)

Three independent sources must agree per prefix; disagreement is a **startup /
test error**, not a wrong flashcard (the "validate-what-you-display" rule):

1. `Morpheme.stress == PREFIX`  ⟺  `kind == PREFIX_SEPARABLE`
2. … ⟺  the **conjugator** places `ge-` *inside* the Partizip II for verbs
   carrying that prefix (`aufgestanden`, not `geaufstanden`).
3. For dual prefixes, both readings exist (`literal_gloss` *and*
   `figurative_gloss` non-null) and map to the two stress patterns.

Answerability gate for generated items:

- **Determinacy:** a meaning-MCQ's distractor set contains no synonym of the key
  (`weg-/fort-/ab-` all gloss "away" → forbidden together).
- **Round-trip (CLASSIFICATION):** the claimed Partizip-II / class is read back
  from the conjugator, never authored.
- **Uniqueness (USAGE production):** "base + target-meaning → prefix" prompts are
  constrained until exactly one prefix survives (else accept the set explicitly).

Wire as a `selfcheck` extension walking the full morpheme space, asserted in a
`tests/test_morphemes_exhaustive.py` mirroring `tests/test_exhaustive.py`.

---

## 8. Phasing

1. **Reify + taxonomy:** `domain/morphology.py`, `prefixes.yaml`, `Verb.prefix_id`
   / `base_root`, the tri-source self-check. No new exercises yet — just the data
   and the invariants green.
2. **First drill:** `MEANING` + `CLASSIFICATION` via Option-B parallel generator;
   `report` grows a `morph|…` section. Highest value, lowest risk.
3. **Usage + wheel:** `base_root` minimal-pair items, hin/her directional
   contexts, aspect targets — these need discriminating contexts.
4. **(If a 3rd skill type appears):** promote `Coordinate`/`Skill` to Protocols
   (Option C).

## 9. Open questions

- Do stems/endings/the `ge-…-t` circumfix get reified now, or only prefixes
  first? (Prefixes carry the most *meaning*; endings carry the most *form*.)
- Is `CLASSIFICATION` a `KnowledgeType` value, or a separate orthogonal
  dimension? (It probes form-class, not meaning — arguably its own axis.)
- Should `MorphemeCoordinate` and `Coordinate` share a base now (earn-it-later
  says no; symmetry says yes).
- Where do dual-prefix *stress* items get their audio/IPA cue in a text CLI?
