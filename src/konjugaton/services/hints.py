"""Hints for a learner who's stuck ("I don't know what the perfect is").

Rule-based today; ``generate_hint`` is the seam where an LLM backend would plug
in (gated by ``scaffolding.llm_hints`` + an optional dependency), using the
learner's free-text feedback as the question. Until then it returns the
deterministic rule hint, so the feature works offline with no credentials.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from konjugaton.engine.labels import number_of, person_of, register_of, tense_of

if TYPE_CHECKING:
    from konjugaton.domain import Item
    from konjugaton.settings.models import Settings

_TENSE_HINTS: dict[str, str] = {
    "praesens": "Präsens = stem + present endings (-e/-st/-t/-en/-t/-en); strong verbs "
    "change the stem vowel in du/er (du gibst, er sieht).",
    "praeteritum": "Präteritum = weak: stem+te (machte); strong: ablaut stem (ging, sah).",
    "perfekt": "Perfekt = haben/sein (Präsens) + Partizip II: ich habe gemacht, ich bin gegangen.",
    "plusquamperfekt": "Plusquamperfekt = haben/sein (Präteritum) + Partizip II (ich hatte gemacht).",  # noqa: E501
    "futur1": "Futur I = werden (Präsens) + Infinitiv: ich werde machen.",
    "futur2": "Futur II = werden + Partizip II + haben/sein: ich werde gemacht haben.",
    "konjunktiv1": "Konjunktiv I = stem + -e/-est/-e/-en/-et/-en (reported speech): er mache.",
    "konjunktiv2": "Konjunktiv II = strong ablaut+umlaut (ginge, käme) or würde + Infinitiv.",
    "imperativ": "Imperativ (2nd person): du mach! · ihr macht! · machen Sie!",
}


def rule_hint(item: Item) -> str:
    """A deterministic, offline hint for the item's tense-mood + its specifics."""
    coord = item.coordinate
    parts: list[str] = []
    if coord.tense_mood.value in _TENSE_HINTS:
        parts.append(_TENSE_HINTS[coord.tense_mood.value])
    polarity = (
        "negative (nicht after the finite verb)"
        if coord.polarity.value == "negative"
        else "affirmative"
    )
    register = f" {register_of(coord.register)}" if coord.register.value != "neutral" else ""
    voice = " Passiv (werden + Partizip II)" if coord.voice.value == "passiv" else ""
    parts.append(
        f"Here: {item.lemma_hint}, {tense_of(coord.tense_mood)}, "
        f"{person_of(coord.person)}·{number_of(coord.number)}{register}, {polarity}.{voice}"
    )
    return " ".join(parts) if parts else "No hint available."


def generate_hint(item: Item, settings: Settings, feedback: str | None = None) -> str:
    """Hint for the learner; LLM-backed when configured, else rule-based.

    ``feedback`` is the learner's free-text question. The LLM path is a declared
    seam: when ``settings.scaffolding.llm_hints`` is on and a backend is wired,
    delegate here. For now we always return the rule hint.
    """
    _ = (settings, feedback)  # reserved for the LLM path
    return rule_hint(item)
