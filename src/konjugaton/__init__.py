"""konjugaton — hyper-combinatorial, IRT-scored grammar practice. Hindi first.

Layered architecture (dependencies point inward):

    cli / tui  ->  services  ->  engine  ->  data  ->  domain
                       \\------->  state  ->  analytics  ->  domain

``domain`` imports nothing but the stdlib. Each outer ring may import inner
rings, never the reverse.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
