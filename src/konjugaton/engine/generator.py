"""Turn a :class:`Coordinate` into a concrete, gradable :class:`Item`.

Difficulty is seeded heuristically from the cell's features (tense-mood, verb
class, register, voice, polarity, knowledge); once response data exists,
:mod:`konjugaton.analytics.irt` can calibrate real parameters and replace it.

Two knowledge types: **production** (a cloze; the learner types the verb complex)
and **recognition** (multiple choice over plausible wrong forms).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from konjugaton.domain import (
    Agreement,
    Coordinate,
    IrtParameters,
    Item,
    KnowledgeType,
    Polarity,
    Register,
    TenseMood,
    Voice,
)
from konjugaton.engine import render
from konjugaton.engine.conjugator import supported_tense_moods
from konjugaton.engine.labels import (
    number_of,
    person_of,
    polarity_of,
    register_of,
    tense_of,
    voice_of,
)

if TYPE_CHECKING:
    import random

    from konjugaton.data import Catalog
    from konjugaton.domain import Verb, VerbClass
    from konjugaton.engine.conjugator import Conjugator

_BLANK = "_____"

_TENSE_BASE: dict[TenseMood, float] = {
    TenseMood.PRAESENS: 0.0,
    TenseMood.PRAETERITUM: 0.4,
    TenseMood.PERFEKT: 0.5,
    TenseMood.PLUSQUAMPERFEKT: 0.8,
    TenseMood.FUTUR1: 0.5,
    TenseMood.FUTUR2: 1.0,
    TenseMood.KONJUNKTIV1: 1.1,
    TenseMood.KONJUNKTIV2: 1.2,
    TenseMood.IMPERATIV: 0.3,
}
_CLASS_DELTA: dict[str, float] = {"weak": 0.0, "strong": 0.4, "mixed": 0.5, "irregular": 0.6}
_KNOWLEDGE_DELTA: dict[KnowledgeType, float] = {
    KnowledgeType.PRODUCTION: 0.3,
    KnowledgeType.RECOGNITION: -0.3,
}


class ExerciseGenerator:
    """Build items from coordinates, using the conjugator and catalog data."""

    def __init__(self, catalog: Catalog, conjugator: Conjugator) -> None:
        self._catalog = catalog
        self._conjugator = conjugator

    def generate(self, coordinate: Coordinate, rng: random.Random) -> Item:
        verb = self._catalog.verb(coordinate.lemma)
        agr = _agreement(coordinate)
        form = self._conjugator.conjugate_voice(verb, coordinate.tense_mood, agr, coordinate.voice)
        answer = render.predicate(
            form, coordinate.tense_mood, coordinate.polarity, coordinate.register
        )
        clause = render.attach_subject(agr, answer, tense_mood=coordinate.tense_mood)

        ctx = self._catalog.contexts[coordinate.context]
        template = rng.choice(ctx.templates)
        subject = (
            "" if coordinate.tense_mood is TenseMood.IMPERATIV else render.subject_pronoun(agr)
        )
        full_sentence = template.replace("{subject} {verb}", clause).strip()
        cloze = template.replace("{subject}", subject).replace("{verb}", _BLANK).strip()

        choices: tuple[str, ...] = ()
        if coordinate.knowledge is KnowledgeType.RECOGNITION:
            choices = self._build_choices(verb, coordinate, agr, answer, rng)

        return Item(
            coordinate=coordinate,
            skill=coordinate.skill(verb.verb_class),
            prompt=cloze,
            answer=answer,
            irt=self._irt(verb.verb_class, coordinate, n_choices=len(choices)),
            accepted=(answer,),
            choices=choices,
            lemma_hint=verb.lemma,
            task=self._task(coordinate),
            full_sentence=full_sentence,
            metadata={
                "polarity": coordinate.polarity.value,
                "voice": coordinate.voice.value,
                "translation": verb.translation,
            },
        )

    # -- multiple-choice distractors ----------------------------------------

    def _build_choices(
        self,
        verb: Verb,
        coordinate: Coordinate,
        agr: Agreement,
        answer: str,
        rng: random.Random,
    ) -> tuple[str, ...]:
        distractors = self._distractors(verb, coordinate, agr, answer, rng)
        options = [answer, *distractors]
        rng.shuffle(options)
        return tuple(options)

    def _distractors(
        self,
        verb: Verb,
        coordinate: Coordinate,
        agr: Agreement,
        answer: str,
        rng: random.Random,
        k: int = 3,
    ) -> list[str]:
        """Wrong-but-tempting forms: same verb+voice, wrong agreement or wrong tense."""
        from konjugaton.engine.permutations import all_agreements  # noqa: PLC0415

        tm, voice, pol, reg = (
            coordinate.tense_mood,
            coordinate.voice,
            coordinate.polarity,
            coordinate.register,
        )
        candidates: list[str] = []
        # Wrong agreement (other legal bundles for this tense).
        for alt in all_agreements():
            if alt == agr or not self._conjugator.realizable_agreement(tm, alt):
                continue
            form = self._conjugator.conjugate_voice(verb, tm, alt, voice)
            candidates.append(render.predicate(form, tm, pol, alt.register))
        # Wrong tense (same agreement).
        for alt_tm in supported_tense_moods():
            if alt_tm == tm or not self._conjugator.realizable_voice(verb, alt_tm, voice):
                continue
            if not self._conjugator.realizable_agreement(alt_tm, agr):
                continue
            form = self._conjugator.conjugate_voice(verb, alt_tm, agr, voice)
            candidates.append(render.predicate(form, alt_tm, pol, reg))

        unique = [c for c in dict.fromkeys(candidates) if c != answer]
        rng.shuffle(unique)
        return unique[:k]

    # -- task string + IRT seed ---------------------------------------------

    def _task(self, c: Coordinate) -> str:
        bits = [tense_of(c.tense_mood), f"{person_of(c.person)}·{number_of(c.number)}"]
        if c.register is not Register.NEUTRAL:
            bits.append(register_of(c.register))
        if c.voice is Voice.PASSIV:
            bits.append(voice_of(c.voice))
        bits.append(polarity_of(c.polarity))
        return " · ".join(bits)

    def _irt(self, verb_class: VerbClass, coordinate: Coordinate, n_choices: int) -> IrtParameters:
        b = _TENSE_BASE.get(coordinate.tense_mood, 0.5)
        b += _CLASS_DELTA[verb_class.value]
        if coordinate.polarity is Polarity.NEGATIVE:
            b += 0.15
        if coordinate.voice is Voice.PASSIV:
            b += 0.4
        b += _KNOWLEDGE_DELTA.get(coordinate.knowledge, 0.0)
        b = max(-3.0, min(3.0, b))
        guessing = 1.0 / n_choices if n_choices else 0.0
        return IrtParameters(
            difficulty=round(b, 3), discrimination=1.0, guessing=round(guessing, 3)
        )


def _agreement(c: Coordinate) -> Agreement:
    return Agreement(person=c.person, number=c.number, register=c.register)
