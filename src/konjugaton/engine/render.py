"""Surface rendering: negation, separable-prefix placement, subject attachment.

Kept apart from the conjugator: the conjugator produces morphology (a finite head
+ a clause-final tail), this module applies German syntax:

* **negation** — ``nicht`` is placed after the finite verb and before the tail
  (the Partizip II / Infinitiv / detached prefix): *ich mache nicht*, *ich habe
  nicht gemacht*, *ich stehe nicht auf*.
* **separable prefix** — already carried as the tail by the conjugator, so it
  lands clause-finally in simple tenses (*ich stehe auf*) and stays bound inside
  the Partizip II/Infinitiv in periphrastic ones (*ich bin aufgestanden*).
* **Imperativ** — no leading subject for du/ihr; the formal *Sie* is appended
  after the finite verb (*machen Sie!*, *stehen Sie auf!*).
* **subject** — German is verb-second; we keep subject-first so the verb complex
  is contiguous (the answerable cloze target).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from konjugaton.domain import SUBJECT_PRONOUN, Polarity, Register, TenseMood

if TYPE_CHECKING:
    from konjugaton.domain import Agreement, ConjugatedForm


def subject_pronoun(agr: Agreement) -> str:
    """The subject pronoun for an agreement bundle (ich/du/er/wir/ihr/Sie/sie)."""
    return SUBJECT_PRONOUN[(agr.person, agr.number, agr.register)]


def predicate(
    form: ConjugatedForm, tense_mood: TenseMood, polarity: Polarity, register: Register
) -> str:
    """The contiguous verb complex the learner types — finite (+Sie) (+nicht) (+tail)."""
    parts = [form.finite]
    if tense_mood is TenseMood.IMPERATIV and register is Register.SIE:
        parts.append("Sie")
    if polarity is Polarity.NEGATIVE:
        parts.append("nicht")
    if form.tail:
        parts.append(form.tail)
    return " ".join(parts)


def attach_subject(agr: Agreement, predicate_text: str, *, tense_mood: TenseMood) -> str:
    """Join subject + predicate (verb-second, subject-first). Imperatives drop it."""
    if tense_mood is TenseMood.IMPERATIV:
        return predicate_text
    return f"{subject_pronoun(agr)} {predicate_text}"
