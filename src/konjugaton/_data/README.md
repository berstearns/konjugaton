# Bundled data

These YAML files are the **taxonomy**. The engine derives everything from them;
extending konjugaton is overwhelmingly a matter of editing data here. All three
are validated strictly at load (`extra="forbid"`) by the Pydantic schemas in
`konjugaton/data/models.py`, so a typo'd key is a startup error, not a silent bug.

Every surface form is stored in **both scripts** — Devanagari and a romanized
twin — because the romanized script is a first-class elicitation axis.

## `verbs.yaml`

```yaml
verbs:
  - lemma: <Devanagari infinitive>   # e.g. करना, बोलना, खाना
    lemma_roman: <romanized>         # e.g. karna, bolna, khana
    verb_class: regular | irregular  # irregular = suppletive perfective
    transitivity: transitive | intransitive   # drives the ने-ergative
    translation: <english gloss>
    frequency_rank: <int>            # lower = more common
    family: <str|null>               # e.g. jana / dena / lena (optional)
    semantic_tags: [<str>, ...]      # optional
    conjugation:                     # only what differs from the regular rule
      root: <str>                    # override the lemma-minus-ना root (rare)
      root_roman: <str>
      future_oblique: <str>          # future/subjunctive stem if ≠ root (हो, द, ल, पि)
      future_oblique_roman: <str>
      imperative_aap: <str>          # irregular आप imperative (कीजिए, दीजिए, …)
      imperative_aap_roman: <str>
      perfective:                    # IRREGULAR verbs only — suppletive forms
        devanagari: { "sg|m": किया, "sg|f": की, "pl|m": किए, "pl|f": कीं }
        romanized:  { "sg|m": kiya, "sg|f": ki, "pl|m": kiye, "pl|f": kin }
```

## `endings.yaml`

`paradigm → {devanagari, romanized} → key → suffix`. The regular engine.

* `imperfective`, `perfective`, `perfective_glide`, `progressive`, `hona_past`,
  `future_tail` key on `<number>|<gender>` (e.g. `sg|m`).
* `future`, `subjunctive`, `hona_present` key on `<person>|<number>|<honorific>`.
* `imperative` keys on `<honorific>`.

The conjugator composes the periphrastic TAMs (participle + होना auxiliary),
applies the vowel-final glide rule, and handles the तुम-feminine quirk and the
ने-ergative object agreement.

## `contexts.yaml`

Hindi is verb-final (SOV), so templates read `<context phrase> {subject} {verb}`.
Templates must contain the contiguous token `{subject} {verb}` (the renderer
attaches the subject pronoun there). Both `templates` (Devanagari) and
`templates_roman` are required.

```yaml
contexts:
  - id: <slug>
    label_hi: <Devanagari>
    label_en: <str>
    templates: ["रोज़ {subject} {verb}।", ...]
    templates_roman: ["roz {subject} {verb}.", ...]
    affinity: [<lemma>, ...]   # verbs that feel natural here (optional)
```
