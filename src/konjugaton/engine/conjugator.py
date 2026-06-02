"""The conjugator: turn (verb, tense-mood, agreement) into a German verb complex.

Strategy — "stem + ending", adapted to German's weak/strong/mixed morphology and
its periphrastic (auxiliary-based) tenses:

* finite forms = stem (with strong 2sg/3sg change) + personal ending, with the
  epenthetic-e (arbeit→arbeitest) and s-drop (iss→isst) orthography in code;
* periphrastic tenses conjugate an auxiliary (haben/sein/werden) — themselves
  ordinary catalog verbs — and append a non-finite tail (Partizip II / Infinitiv);
* the separable prefix is carried as the clause-final ``tail`` and re-bound inside
  the Partizip II/Infinitiv by the renderer's word-order rules.

sein/haben/werden are too suppletive to derive and ship explicit form maps.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from konjugaton.domain import (
    Agreement,
    Auxiliary,
    ConjugatedForm,
    Number,
    Person,
    Register,
    TenseMood,
    VerbClass,
    Voice,
)

if TYPE_CHECKING:
    from konjugaton.domain import EndingTables, Verb

#: Tense-moods the engine realizes, in display order.
_ORDER: tuple[TenseMood, ...] = (
    TenseMood.PRAESENS,
    TenseMood.PRAETERITUM,
    TenseMood.PERFEKT,
    TenseMood.PLUSQUAMPERFEKT,
    TenseMood.FUTUR1,
    TenseMood.FUTUR2,
    TenseMood.KONJUNKTIV1,
    TenseMood.KONJUNKTIV2,
    TenseMood.IMPERATIV,
)

#: Tenses in which the werden-passive is realized (transitive verbs only).
_PASSIVE_TENSES: frozenset[TenseMood] = frozenset(
    {
        TenseMood.PRAESENS,
        TenseMood.PRAETERITUM,
        TenseMood.PERFEKT,
        TenseMood.PLUSQUAMPERFEKT,
        TenseMood.FUTUR1,
    }
)

_SIBILANT = frozenset("sßzx")
_DENTAL = frozenset("td")
_UMLAUT = frozenset("äöü")


class ConjugationError(RuntimeError):
    """Raised when a form is requested that the data cannot realize."""


def supported_tense_moods() -> list[TenseMood]:
    return list(_ORDER)


class Conjugator:
    """Stateless (w.r.t. learner) conjugation engine over a fixed catalog."""

    def __init__(self, endings: EndingTables, verbs: dict[str, Verb] | None = None) -> None:
        self._endings = endings
        self._verbs = verbs or {}

    # -- capability queries -------------------------------------------------

    def supports(self, tm: TenseMood) -> bool:
        return tm in _ORDER

    def can_conjugate(self, verb: Verb, tm: TenseMood) -> bool:  # noqa: ARG002 — all verbs realize all tenses
        return self.supports(tm)

    def realizable_agreement(self, tm: TenseMood, agr: Agreement) -> bool:
        """The imperative inflects in the 2nd person only (du/ihr/Sie)."""
        if tm is TenseMood.IMPERATIV:
            return agr.register in (Register.DU, Register.IHR, Register.SIE)
        return True

    def realizable_voice(self, verb: Verb, tm: TenseMood, voice: Voice) -> bool:
        if voice is Voice.AKTIV:
            return True
        return verb.transitive and tm in _PASSIVE_TENSES

    # -- finite paradigms ---------------------------------------------------

    def _praesens(self, verb: Verb, agr: Agreement) -> str:  # noqa: PLR0911 — slot dispatch
        slot = agr.slot
        irr = verb.conjugation.irregular.get("praesens")
        if irr:
            return irr[slot]
        base = verb.stem
        stem23 = verb.conjugation.praesens_stem_23 or base
        if slot == "1|sg":
            return base + "e"
        if slot == "2|sg":
            s = stem23
            if s[-1] in _SIBILANT:
                return s + "t"
            if s[-1] in _DENTAL:
                return s + "est"
            return s + "st"
        if slot == "3|sg":
            s = stem23
            return s + ("et" if s[-1] in _DENTAL else "t")
        if slot == "2|pl":
            return base + ("et" if base[-1] in _DENTAL else "t")
        return base + "en"  # 1|pl, 3|pl

    def _praeteritum(self, verb: Verb, agr: Agreement) -> str:
        slot = agr.slot
        irr = verb.conjugation.irregular.get("praeteritum")
        if irr:
            return irr[slot]
        if verb.verb_class is VerbClass.STRONG:
            stem = verb.conjugation.praeteritum_stem
            if stem is None:
                raise ConjugationError(f"{verb.lemma}: strong verb missing praeteritum_stem")
            return stem + self._endings.ending("praeteritum_strong", slot)
        # weak or mixed: (mixed) ablaut stem or (weak) base stem, + (e)te + endings
        base = (
            verb.conjugation.praeteritum_stem if verb.verb_class is VerbClass.MIXED else verb.stem
        )
        if base is None:
            raise ConjugationError(f"{verb.lemma}: mixed verb missing praeteritum_stem")
        connector = "ete" if base[-1] in _DENTAL else "te"
        return base + connector + self._endings.ending("praeteritum_weak", slot)

    def _konjunktiv1(self, verb: Verb, agr: Agreement) -> str:
        irr = verb.conjugation.irregular.get("konjunktiv1")
        if irr:
            return irr[agr.slot]
        return verb.stem + self._endings.ending("konjunktiv", agr.slot)

    def _konjunktiv2(self, verb: Verb, agr: Agreement) -> str | None:
        """K2 finite, or None for weak/mixed (caller falls back to würde+Infinitiv)."""
        irr = verb.conjugation.irregular.get("konjunktiv2")
        if irr:
            return irr[agr.slot]
        k2 = verb.conjugation.konjunktiv2_stem
        if k2 is not None:
            return k2 + self._endings.ending("konjunktiv", agr.slot)
        return None

    def _partizip2(self, verb: Verb) -> str:
        prefix = verb.separable_prefix or ""
        p2 = verb.conjugation.partizip2
        if p2 is None:  # weak: ge + stem + (e)t
            base = verb.stem
            p2 = "ge" + base + ("et" if base[-1] in _DENTAL else "t")
        return prefix + p2

    def _aux(self, verb: Verb) -> Verb:
        lemma = "haben" if verb.auxiliary is Auxiliary.HABEN else "sein"
        return self._verbs[lemma]

    # -- main entry points --------------------------------------------------

    def conjugate(self, verb: Verb, tm: TenseMood, agr: Agreement) -> ConjugatedForm:  # noqa: PLR0911 — tense dispatch
        if not self.realizable_agreement(tm, agr):
            raise ConjugationError(f"{verb.lemma}: cannot realize {tm.value} for {agr.key}")
        sep = verb.separable_prefix or ""
        if tm is TenseMood.PRAESENS:
            return ConjugatedForm(self._praesens(verb, agr), tail=sep)
        if tm is TenseMood.PRAETERITUM:
            return ConjugatedForm(self._praeteritum(verb, agr), tail=sep)
        if tm is TenseMood.KONJUNKTIV1:
            return ConjugatedForm(self._konjunktiv1(verb, agr), tail=sep)
        if tm is TenseMood.KONJUNKTIV2:
            k2 = self._konjunktiv2(verb, agr)
            if k2 is not None:
                return ConjugatedForm(k2, tail=sep)
            wuerde = self._konjunktiv2(self._verbs["werden"], agr)
            assert wuerde is not None
            return ConjugatedForm(wuerde, tail=verb.lemma)  # würde + Infinitiv
        if tm is TenseMood.PERFEKT:
            return ConjugatedForm(self._praesens(self._aux(verb), agr), tail=self._partizip2(verb))
        if tm is TenseMood.PLUSQUAMPERFEKT:
            return ConjugatedForm(
                self._praeteritum(self._aux(verb), agr), tail=self._partizip2(verb)
            )
        if tm is TenseMood.FUTUR1:
            return ConjugatedForm(self._praesens(self._verbs["werden"], agr), tail=verb.lemma)
        if tm is TenseMood.FUTUR2:
            aux_inf = verb.auxiliary.value  # haben / sein
            tail = f"{self._partizip2(verb)} {aux_inf}"
            return ConjugatedForm(self._praesens(self._verbs["werden"], agr), tail=tail)
        if tm is TenseMood.IMPERATIV:
            return self._imperativ(verb, agr)
        raise ConjugationError(f"unsupported tense-mood: {tm.value}")  # pragma: no cover

    def _imperativ(self, verb: Verb, agr: Agreement) -> ConjugatedForm:
        sep = verb.separable_prefix or ""
        irr = verb.conjugation.irregular.get("imperativ")
        if agr.register is Register.DU:
            if irr and "2|sg" in irr:
                form = irr["2|sg"]
            else:
                s23 = verb.conjugation.praesens_stem_23
                use_s23 = bool(s23) and not any(c in _UMLAUT for c in s23 or "")
                if use_s23:
                    form = s23 or verb.stem
                else:
                    form = verb.stem + ("e" if verb.stem[-1] in _DENTAL else "")
            return ConjugatedForm(form, tail=sep)
        if agr.register is Register.IHR:
            form = irr["2|pl"] if (irr and "2|pl" in irr) else self._praesens(verb, agr)
            return ConjugatedForm(form, tail=sep)
        # Sie (formal): 3pl form; the renderer appends "Sie".
        form = irr["3|pl"] if (irr and "3|pl" in irr) else self._praesens(verb, agr)
        return ConjugatedForm(form, tail=sep)

    def conjugate_voice(
        self, verb: Verb, tm: TenseMood, agr: Agreement, voice: Voice
    ) -> ConjugatedForm:
        if not self.realizable_voice(verb, tm, voice):
            raise ConjugationError(f"{verb.lemma}: cannot realize {voice.value} {tm.value}")
        if voice is Voice.AKTIV:
            return self.conjugate(verb, tm, agr)
        werden = self._verbs["werden"]
        sein = self._verbs["sein"]
        pii = self._partizip2(verb)
        if tm is TenseMood.PRAESENS:
            return ConjugatedForm(self._praesens(werden, agr), tail=pii)
        if tm is TenseMood.PRAETERITUM:
            return ConjugatedForm(self._praeteritum(werden, agr), tail=pii)
        if tm is TenseMood.PERFEKT:
            return ConjugatedForm(self._praesens(sein, agr), tail=f"{pii} worden")
        if tm is TenseMood.PLUSQUAMPERFEKT:
            return ConjugatedForm(self._praeteritum(sein, agr), tail=f"{pii} worden")
        if tm is TenseMood.FUTUR1:
            return ConjugatedForm(self._praesens(werden, agr), tail=f"{pii} werden")
        raise ConjugationError(f"unsupported passive tense: {tm.value}")  # pragma: no cover


def default_agreement(person: Person, number: Number, register: Register) -> Agreement:
    return Agreement(person=person, number=number, register=register)
