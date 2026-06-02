"""Data-access boundary: validate bundled YAML, hand back pure domain objects."""

from __future__ import annotations

from konjugaton.data.loader import Catalog, DataError, load_catalog

__all__ = ["Catalog", "DataError", "load_catalog"]
