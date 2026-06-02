"""The :class:`ConjugatedForm` value object returned by the conjugator.

German splits the verb across the clause (V2 order): a **finite** element in
second position and a clause-final **tail** of non-finite material — the Partizip
II (*gemacht*), an Infinitiv (*machen*), a detached separable prefix (*auf*), or a
stack (*gemacht haben*, *gemacht worden*). Keeping the two parts separate lets the
renderer place ``nicht`` between them and assemble the right word order.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConjugatedForm:
    """A conjugated German verb complex: a finite head + a clause-final tail."""

    finite: str
    tail: str = ""

    @property
    def surface(self) -> str:
        """The contiguous verb complex (finite + tail), e.g. 'habe gemacht', 'stehe auf'."""
        return f"{self.finite} {self.tail}".strip() if self.tail else self.finite

    @property
    def has_tail(self) -> bool:
        return bool(self.tail)

    @classmethod
    def simple(cls, finite: str) -> ConjugatedForm:
        return cls(finite=finite)

    @classmethod
    def periphrastic(cls, finite: str, tail: str) -> ConjugatedForm:
        return cls(finite=finite, tail=tail)
