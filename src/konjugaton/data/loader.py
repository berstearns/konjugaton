"""Load and validate the bundled data, returning a pure-domain :class:`Catalog`.

The catalog is the single read-only source of truth the engine queries. It is
cached, so the YAML is parsed and validated exactly once per process.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import TYPE_CHECKING, Any

import yaml

from konjugaton.data.models import ContextsFile, EndingsModel, VerbModel, VerbsFile
from konjugaton.domain import (
    ConjugationData,
    EndingTables,
    SemanticContext,
    Verb,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

_DATA_PACKAGE = "konjugaton._data"

#: Paradigm names whose tables ship in endings.yaml.
_PARADIGMS: tuple[str, ...] = (
    "praesens",
    "praeteritum_weak",
    "praeteritum_strong",
    "konjunktiv",
)


class DataError(RuntimeError):
    """Bundled data could not be located or read.

    Almost always a *packaging* problem (the binary was built without bundling
    ``konjugaton._data``), not a logic bug — so the message says so loudly instead
    of surfacing an opaque ModuleNotFoundError from deep in the import machinery.
    """


def _read_yaml(filename: str) -> Any:
    try:
        resource = resources.files(_DATA_PACKAGE).joinpath(filename)
        text = resource.read_text(encoding="utf-8")
    except (ModuleNotFoundError, FileNotFoundError, OSError) as exc:
        raise DataError(
            f"Could not load bundled data '{filename}' from package "
            f"'{_DATA_PACKAGE}'. This is a packaging/bundling problem: the data "
            f"files were not shipped with the build. For a Nuitka binary, ensure "
            f"`--include-package-data=konjugaton` and that konjugaton/_data is a "
            f"package (has __init__.py). Original cause: {exc!r}"
        ) from exc
    return yaml.safe_load(text)


def _to_verb(model: VerbModel) -> Verb:
    conj = model.conjugation
    conjugation = ConjugationData(
        praesens_stem_23=conj.praesens_stem_23 if conj else None,
        praeteritum_stem=conj.praeteritum_stem if conj else None,
        partizip2=conj.partizip2 if conj else None,
        konjunktiv2_stem=conj.konjunktiv2_stem if conj else None,
        irregular={p: dict(slots) for p, slots in (conj.irregular if conj else {}).items()},
    )
    return Verb(
        lemma=model.lemma,
        translation=model.translation,
        verb_class=model.verb_class,
        auxiliary=model.auxiliary,
        transitive=model.transitive,
        frequency_rank=model.frequency_rank,
        conjugation=conjugation,
        separable_prefix=model.separable_prefix,
        family=model.family,
        semantic_tags=tuple(model.semantic_tags),
    )


@dataclass(frozen=True, slots=True)
class Catalog:
    """All loaded reference data, indexed for the engine."""

    verbs: Mapping[str, Verb]
    endings: EndingTables
    contexts: Mapping[str, SemanticContext]

    def verb(self, lemma: str) -> Verb:
        return self.verbs[lemma]

    @property
    def lemmas(self) -> list[str]:
        return list(self.verbs)

    @property
    def context_ids(self) -> list[str]:
        return list(self.contexts)


@lru_cache(maxsize=1)
def load_catalog() -> Catalog:
    """Parse, validate and index the bundled data (cached for the process)."""
    verbs_file = VerbsFile.model_validate(_read_yaml("verbs.yaml"))
    endings_model = EndingsModel.model_validate(_read_yaml("endings.yaml"))
    contexts_file = ContextsFile.model_validate(_read_yaml("contexts.yaml"))

    verbs = {m.lemma: _to_verb(m) for m in verbs_file.verbs}

    dump = endings_model.model_dump()
    ending_tables = EndingTables(tables={p: dict(dump[p]) for p in _PARADIGMS})

    contexts = {
        c.id: SemanticContext(
            id=c.id,
            label_de=c.label_de,
            label_en=c.label_en,
            templates=tuple(c.templates),
            affinity=tuple(c.affinity),
        )
        for c in contexts_file.contexts
    }

    return Catalog(verbs=verbs, endings=ending_tables, contexts=contexts)
