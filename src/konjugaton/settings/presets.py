"""Preset bundles — named points in the hyper-combinatorial flag space.

With ~80 flags, asking a learner to configure from scratch is hostile. A preset
sets a coherent bundle in one move; the user can then override any single flag
(which flips ``preset`` to "custom"). Each preset is a research- or persona-
motivated *combination*, not a random pick.
"""

from __future__ import annotations

from collections.abc import Callable

from konjugaton.settings.models import Settings

PRESET_NAMES = ("default", "gentle", "exam_prep", "kids", "polyglot_power", "listening", "zen")


def _default() -> Settings:
    return Settings(preset="default")


def _gentle() -> Settings:
    """Forgiving on-ramp: lenient grading, heavy feedback + scaffolding, no clock."""
    s = Settings(preset="gentle")
    s.grading.similarity_tolerance = 3
    s.grading.ignore_accents = True
    s.grading.ignore_punctuation = True
    s.grading.accept_either_script = True
    s.grading.first_attempt_typo_grace = True
    s.feedback.char_diff_on_error = True
    s.feedback.show_romanization = True
    s.feedback.show_literal_gloss = True
    s.feedback.grammar_hint_on_error = True
    s.feedback.hint_after_seconds = 8
    s.scaffolding.pollinate_on_error = True
    s.scaffolding.show_conjugation_table_on_miss = True
    s.scaffolding.contrastive_gloss = True
    s.adaptivity.target_success_rate = 0.85
    s.items.production_ratio = 0.3
    s.curriculum.registers = ["du"]  # informal "du" first for newcomers
    s.session.warmup_easy_items = 3
    return s


def _exam_prep() -> Settings:
    """Strict + spaced + interleaved: the evidence-backed retention regime."""
    s = Settings(preset="exam_prep")
    s.grading.similarity_tolerance = 0
    s.grading.ignore_accents = False
    s.grading.require_subject_pronoun = True
    s.feedback.timing = "end_of_session"
    s.scheduling.spaced_repetition = True
    s.scheduling.interleave = True
    s.scheduling.retire_mastered = True
    s.adaptivity.target_success_rate = 0.7  # desirable difficulty
    s.adaptivity.ramp_with_streak = True
    s.items.production_ratio = 0.85
    s.curriculum.voices = ["aktiv", "passiv"]  # exam = full voice range
    s.scaffolding.track_grammar_tags = True
    return s


def _kids() -> Settings:
    """Gamified + gentle + recognition-heavy."""
    s = Settings(preset="kids")
    s.grading.similarity_tolerance = 4
    s.grading.ignore_accents = True
    s.items.production_ratio = 0.2
    s.items.context_richness = "minimal"
    s.motivation.streaks = True
    s.motivation.points = True
    s.motivation.daily_goal_items = 20
    s.motivation.lives = 3
    s.feedback.char_diff_on_error = True
    return s


def _polyglot_power() -> Settings:
    """Fast, contrastive, production-heavy — for experienced language learners."""
    s = Settings(preset="polyglot_power")
    s.grading.similarity_tolerance = 1
    s.grading.ignore_accents = False
    s.feedback.show_full_sentence = False
    s.feedback.show_item_difficulty = True
    s.scaffolding.contrastive_gloss = True
    s.scaffolding.track_grammar_tags = True
    s.scheduling.interleave = True
    s.curriculum.passive_focus = True  # drill the werden-passive
    s.items.production_ratio = 0.9
    s.items.mc_choices = 6
    s.display.devanagari_input_helper = True
    return s


def _listening() -> Settings:
    """Audio-first: hear the prompt, type the answer; lenient on spelling."""
    s = Settings(preset="listening")
    s.audio.tts = True
    s.audio.listening_mode = True
    s.audio.dictation = True
    s.audio.show_ipa = True
    s.grading.similarity_tolerance = 2
    s.grading.ignore_accents = True
    s.items.production_ratio = 0.8
    return s


def _zen() -> Settings:
    """No clock, no points, no pressure — high success target, gentle grading."""
    s = Settings(preset="zen")
    s.grading.similarity_tolerance = 3
    s.grading.ignore_accents = True
    s.motivation.streaks = False
    s.motivation.points = False
    s.motivation.lives = 0
    s.motivation.celebrate_milestones = False
    s.adaptivity.target_success_rate = 0.9
    s.session.time_limit_seconds = 0
    s.feedback.hint_after_seconds = 10
    return s


_REGISTRY: dict[str, Callable[[], Settings]] = {
    "default": _default,
    "gentle": _gentle,
    "exam_prep": _exam_prep,
    "kids": _kids,
    "polyglot_power": _polyglot_power,
    "listening": _listening,
    "zen": _zen,
}


def apply_preset(name: str) -> Settings:
    """Return a fresh Settings for the named preset (raises on unknown name)."""
    try:
        factory = _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"unknown preset {name!r}; choose from {', '.join(PRESET_NAMES)}"
        ) from None
    return factory()
