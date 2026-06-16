# konjugaton — German-specific ideas

Cross-app ideas live in `../general/general-ideas.md`.

---

## Feedback field + LLM hint
→ See general idea #1. German-specific wording: "Ich weiß nicht, wann man
_sein_ statt _haben_ im Perfekt benutzt."

---

## German-specific axes worth adding

### Separable-prefix verbs (Trennbare Verben)
`aufmachen`, `ankommen`, `zurückgehen` — the prefix detaches and moves to
sentence-final position in finite clauses. The engine currently treats the whole
lemma as atomic; a separable-prefix flag per verb would let us drill both the
correct split position and the spelling.

### Modal verbs + infinitive complement
`können`, `müssen`, `dürfen` + bare infinitive — common constructions but not
currently part of the combinatorial space (the engine focuses on finite tenses of
lexical verbs). Worth a dedicated mode or a standalone `modal` command.

### Strong-verb ablaut families
Group strong verbs by their vowel-change pattern (e.g. `ei→ie→ie` for
`bleiben/blieb/geblieben`, `a→u→a` for `fahren/fuhr/gefahren`). A drill that
clusters verbs by pattern lets learners internalize the family rather than
memorising individually.

### Konjunktiv I (reported speech)
`konjunktiv1` exists in the enum but may have sparse coverage in the verb data.
Audit which verbs realize it distinctly from Konjunktiv II and flag the rest as
`würde + infinitiv` replacements.

### Genus / article drill
Not verb morphology, but a natural companion: `der/die/das` + noun. Could be a
separate command (`konjugaton noun`) rather than part of the verb-drilling space.
