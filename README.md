# konjugaton

**Hyper-combinatorial grammar practice — exhaustive, IRT-scored verb drilling over a data-driven taxonomy. German (Deutsch) verbs; language-agnostic core.**

`konjugaton` generates exercises from every point in a combinatorial space —

```
verb × tense-mood × person × number × register × voice × polarity × knowledge-type × semantic-context
```

— grades your answers, and builds a learner model (`vocab → knowledge-type → score`, plus a per-skill Item-Response-Theory ability estimate). Adding a tense, a verb, or a whole new exercise type is a **data edit**, not a code change.

```bash
konjugaton catalog          # how big is the space, and along which axes?
konjugaton practice -n 10   # drill 10 adaptive exercises
konjugaton report           # where am I weak?
konjugaton tui              # full-screen terminal UI (needs the [tui] extra)
```

It is a faithful clone of [`namastion`](https://github.com/berstearns/namastion) (Hindi) — itself a clone of [`verbion`](https://github.com/berstearns/verbion) (French) — re-pointed at German: same layered architecture, same IRT learner model, same config-flag system, same exhaustive self-check discipline. The difference is the domain. German has **no gender agreement on the verb** and **one script**, so Hindi's biggest multipliers vanish; German's richness comes from elsewhere:

- **weak / strong / mixed** conjugation (ablaut: *gehen → ging → gegangen*),
- the **haben/sein** auxiliary split in the perfect tenses (*ich habe gemacht* vs *ich bin gegangen*),
- **separable prefixes** (*aufstehen → ich stehe auf*; Partizip II *aufgestanden*),
- the **du/ihr/Sie** register (the analogue of Hindi's honorific),
- **Konjunktiv I/II** and the **werden-Passiv** (*es wird gemacht*).

That makes the realizable space **41,660 coordinates**. See [docs/COMBINATORICS.md](docs/COMBINATORICS.md).

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
konjugaton practice --tense praesens -n 8
```

A non-interactive sample (great for seeing the engine without typing):

```bash
konjugaton practice --tense perfekt --no-interactive -n 5
konjugaton practice --voice passiv --no-interactive -n 5     # the werden-passive
konjugaton practice --only-mcq --no-interactive -n 5         # multiple choice, no typing
```

## What makes it "hyper-combinatorial"

Every axis is an independent dimension; the realizable space is their product,
minus the cells the engine cannot conjugate **and** the ungrammatical agreement
bundles. `konjugaton catalog` prints the live count. The axes shipped today:

| Axis | Values (today) |
|------|----------------|
| verb | 27 verbs (weak, strong, mixed, separable, + sein/haben/werden) |
| tense-mood | Präsens, Präteritum, Perfekt, Plusquamperfekt, Futur I, Futur II, Konjunktiv I, Konjunktiv II, Imperativ |
| person | 1, 2, 3 |
| number | singular, plural |
| register | neutral, du (informal sg), ihr (informal pl), Sie (formal) |
| voice | Aktiv, Passiv (the werden-passive — transitive verbs) |
| polarity | affirmative, negative (nicht) |
| knowledge-type | production (cloze), recognition (multiple choice) |
| semantic-context | Alltag, Reise, Arbeit, Studium, Gefühle |

person × number × register do not combine freely — German licenses only
**7 legal agreement bundles** (no "1st-person Sie", etc.); the imperative is
2nd-person only; the passive is transitive-and-indicative only. The engine never
emits an ungrammatical cell.

## The German engine, in brief

Conjugation is **"stem + endings"** adapted to German morphology:

- The **stem** is the infinitive minus `-en` (with any separable prefix stripped):
  *machen → mach*, *aufstehen → steh*.
- **Präsens** = stem + endings (-e/-st/-t/-en/-t/-en); strong verbs change the
  stem vowel in du/er (*du gibst, er sieht*); epenthetic e (*du arbeitest*) and
  s-drop (*du isst*) are handled in code.
- **Präteritum** = weak `stem+te` (*machte*) · strong ablaut stem (*ging, sah*).
- **Perfekt / Plusquamperfekt / Futur II** are periphrastic: a **haben/sein/werden**
  auxiliary (itself a catalog verb the engine conjugates) + the Partizip II /
  Infinitiv. The auxiliary is a per-verb property (motion/change-of-state → *sein*).
- **Konjunktiv I** = stem + -e/-est/… ; **Konjunktiv II** = strong ablaut+umlaut
  (*ginge, käme, wäre, hätte*) or *würde* + Infinitiv for weak/mixed.
- **Passiv** = werden (conjugated) + Partizip II (*wird gemacht*, *ist gemacht worden*).
- The **renderer** splits the separable prefix to the clause end in simple tenses
  (*ich stehe **auf***), keeps it bound in the Partizip II (*ich bin **auf**gestanden*),
  and places **nicht** after the finite verb (*ich habe nicht gemacht*).
- **sein/haben/werden** ship explicit, hand-verified irregular forms.

All weak/strong/mixed/separable/irregular forms are **locked as ground-truth
pytest cases** — correctness is non-negotiable.

## The learner model

1. **`vocab → knowledge-type → score`** — a recency-weighted mastery cell.
2. **IRT abilities** — a latent ability `θ` per *skill* `(verb-class, tense-mood, knowledge)`, updated online with a 3-parameter-logistic model. This drives **adaptive item selection** (Fisher information).
3. **Knowledge graph** *(experimental)* relates vocab nodes and diffuses scores.

## Settings, profiles & the session filter

Each learner is a **profile** at `~/konjugaton/{userid}/` (`config.yaml`, `state.json`,
output). The persistent **session filter** (`curriculum.*`) picks what you drill —
register, voice, tense-moods, question types — and is honoured by the CLI, TUI and
Android alike:

```bash
konjugaton practice --register du --voice aktiv     # informal active drill
konjugaton practice --only-mcq                      # recognition only, no typing
konjugaton config preset gentle --user me           # apply a bundle of flags
```

In the TUI, open the settings screen and type `register du`, `voice passiv`, `mcq`,
`typed`, then `back` — the session rebuilds with your filter immediately.

## Architecture in one diagram

```
cli / tui  ─►  services  ─►  engine  ─►  data  ─►  domain
                   └──────►  state   ─►  analytics ─► domain
```

Dependencies point inward. `domain/` imports nothing but the stdlib. See
[ARCHITECTURE.md](ARCHITECTURE.md).

## Extending the taxonomy

- **Add a verb** → one entry in `src/konjugaton/_data/verbs.yaml` (weak verbs need
  nothing beyond lemma/aux; strong/mixed ship their ablaut stems).
- **Add a context** → an entry in `contexts.yaml`.
- **Add a knowledge-type** → a `KnowledgeType` value + a branch in the generator.

## Development

```bash
just install     # uv venv + editable install with dev extras
just check       # lint + format-check + strict types + tests (what CI runs)
just sweep       # tour every (tense × voice) cell — see the combinatorics
just build       # compile the standalone Nuitka binary → dist/konjugaton
```

## License

MIT © 2026 — see [LICENSE](LICENSE).
