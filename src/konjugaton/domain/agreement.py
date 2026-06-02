"""The :class:`Agreement` bundle — the subject features a German verb agrees with.

German verbs agree in **person and number only** (no gender, unlike Hindi). The
**register** (du/ihr/Sie) selects the pronoun and, for the formal *Sie*, the
verb form: *Sie machen* uses the 3rd-plural slot. So the verb's finite ending is
keyed by a 6-way ``person|number`` *slot*, with ``Sie`` mapped to ``3|pl``.
"""

from __future__ import annotations

from dataclasses import dataclass

from konjugaton.domain.enums import Number, Person, Register


@dataclass(frozen=True, slots=True)
class Agreement:
    """The (person, number, register) the verb agrees with."""

    person: Person
    number: Number
    register: Register

    @property
    def key(self) -> str:
        """Stable string key for logs."""
        return f"{self.person.value}|{self.number.value}|{self.register.value}"

    @property
    def slot(self) -> str:
        """The ``person|number`` ending slot; the formal Sie uses the 3|pl form."""
        if self.register is Register.SIE:
            return f"{Person.P3.value}|{Number.PLURAL.value}"
        return f"{self.person.value}|{self.number.value}"

    def __str__(self) -> str:
        return self.key
