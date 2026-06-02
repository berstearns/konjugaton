"""User settings schema — the config.yaml contract.

Hyper-granular by design: each learner-experience lever is its own field, so it
round-trips to YAML and is editable by hand or in the TUI settings screen. The
flags are organised by the lever they pull (acceptance, feedback, scheduling,
adaptivity, curriculum, items, scaffolding, motivation, output, display, ...).

Status convention in comments:
    [active]  — wired into engine behaviour today
    [declared]— validated config knob; engine hook arrives incrementally
This mirrors the project's "declare the axis, implement progressively" pattern.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_STRICT = ConfigDict(extra="forbid")

#: Default romanization-tolerance map for Hindi: variant → accepted typed
#: sequences. First sequence is canonical (everything collapses to it). Typing
#: "aa" or "a" both satisfy a canonical "a" when ignore_accents is on; "ee"→"i",
#: "oo"→"u", "v"→"w", and the chandrabindu nasal "n"/"m" variants unify.
DEFAULT_TRANSLITERATION: dict[str, list[str]] = {
    "a": ["a", "aa"],
    "i": ["i", "ee", "ii"],
    "u": ["u", "oo", "uu"],
    "n": ["n", "ñ", "ṅ", "ṇ"],
    "t": ["t", "ṭ"],
    "d": ["d", "ḍ"],
    "r": ["r", "ṛ"],
    "sh": ["sh", "ś", "ṣ"],
    "w": ["w", "v"],
}


# --- A · Answer acceptance -------------------------------------------------
class GradingSettings(BaseModel):
    model_config = _STRICT

    similarity_tolerance: int = Field(default=0, ge=0, le=10)  # [active] length-scaled
    ignore_accents: bool = False  # [active] romanization-variant folding
    ignore_case: bool = True  # [active]
    ignore_punctuation: bool = True  # [active]
    transliteration: dict[str, list[str]] = Field(  # [active]
        default_factory=lambda: {k: list(v) for k, v in DEFAULT_TRANSLITERATION.items()}
    )
    require_subject_pronoun: bool = False  # [declared] type "मैं करता हूँ" not "करता हूँ"
    accept_either_script: bool = False  # [declared] accept the form in either script
    partial_credit_periphrastic: bool = False  # [declared] participle right, aux wrong
    first_attempt_typo_grace: bool = False  # [declared] one free typo


# --- B · Feedback ----------------------------------------------------------
class FeedbackSettings(BaseModel):
    model_config = _STRICT

    timing: Literal["immediate", "end_of_session"] = "immediate"  # [declared]
    show_correct_on_error: bool = True  # [active]
    show_full_sentence: bool = True  # [active]
    show_translation: bool = True  # [active]
    show_romanization: bool = True  # [active] show the roman twin of a Devanagari answer
    char_diff_on_error: bool = True  # [active] highlight where the answer diverged
    show_literal_gloss: bool = False  # [declared] English-literal structure
    grammar_hint_on_error: bool = False  # [declared]
    show_item_difficulty: bool = False  # [active] surfaces IRT b
    hint_after_seconds: int = Field(default=0, ge=0)  # [declared] 0 = off


# --- C · Scheduling & memory ----------------------------------------------
class SchedulingSettings(BaseModel):
    model_config = _STRICT

    spaced_repetition: bool = False  # [declared]
    sr_algorithm: Literal["leitner", "sm2", "fsrs"] = "leitner"  # [declared]
    interleave: bool = True  # [declared] interleaving > blocking
    requeue_missed: bool = True  # [declared] re-test misses this session
    requeue_delay_items: int = Field(default=3, ge=1)  # [declared]
    new_vs_review_ratio: float = Field(default=0.5, ge=0.0, le=1.0)  # [declared]
    max_consecutive_same_lemma: int = Field(default=2, ge=1)  # [declared]
    mastery_threshold_ewma: float = Field(default=0.85, ge=0.0, le=1.0)  # [declared]
    retire_mastered: bool = False  # [declared]


# --- D · Adaptivity & difficulty ------------------------------------------
class AdaptivitySettings(BaseModel):
    model_config = _STRICT

    enabled: bool = True  # [active]
    selection: Literal["information", "success_rate", "random"] = "information"  # [active]
    target_success_rate: float = Field(default=0.8, ge=0.0, le=1.0)  # [declared]
    difficulty_floor: float = Field(default=-3.0, ge=-5.0, le=5.0)  # [declared]
    difficulty_ceiling: float = Field(default=3.0, ge=-5.0, le=5.0)  # [declared]
    ramp_with_streak: bool = False  # [declared]


# --- E · Curriculum & focus -----------------------------------------------
class CurriculumSettings(BaseModel):
    model_config = _STRICT

    # Empty list = "all values of this axis". [active] via selection_from_settings.
    tense_moods: list[str] = Field(default_factory=list)
    persons: list[str] = Field(default_factory=list)
    numbers: list[str] = Field(default_factory=list)
    registers: list[str] = Field(default_factory=list)
    voices: list[str] = Field(default_factory=list)
    polarities: list[str] = Field(default_factory=list)
    knowledge: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)
    frequency_bias: float = Field(default=0.3, ge=0.0, le=1.0)  # [declared] common first
    weak_axis_weighting: float = Field(default=0.5, ge=0.0, le=1.0)  # [declared]
    negation_frequency: float = Field(default=0.25, ge=0.0, le=1.0)  # [declared]
    passive_focus: bool = False  # [declared] bias toward werden-passive
    progressive_unlock: bool = False  # [declared]
    focus: Literal["mixed", "weak", "new", "exam"] = "mixed"  # [declared]


# --- F · Item construction -------------------------------------------------
class ItemSettings(BaseModel):
    model_config = _STRICT

    production_ratio: float = Field(default=0.5, ge=0.0, le=1.0)  # [active] prod vs recog
    transliteration_ratio: float = Field(default=0.2, ge=0.0, le=1.0)  # [declared]
    mc_choices: int = Field(default=4, ge=2, le=6)  # [declared]
    distractor_strategy: Literal["mixed", "agreement", "tam", "near_form", "random"] = "mixed"
    cloze_show_lemma: bool = True  # [declared]
    show_subject_pronoun: bool = True  # [active]
    context_richness: Literal["minimal", "sentence"] = "sentence"  # [declared]


# --- G · Scaffolding & explanation ----------------------------------------
class ScaffoldingSettings(BaseModel):
    model_config = _STRICT

    pollinate_on_error: bool = False  # [declared] i+1 micro-step chain to the answer
    show_conjugation_table_on_miss: bool = False  # [declared]
    show_pattern_family: bool = False  # [declared] "this is a देना-type verb"
    contrastive_gloss: bool = False  # [declared] HI-vs-EN literal contrast
    track_grammar_tags: bool = True  # [declared] accumulated grammar-tag index


# --- H · Motivation & flow -------------------------------------------------
class MotivationSettings(BaseModel):
    model_config = _STRICT

    streaks: bool = True  # [declared]
    daily_goal_items: int = Field(default=0, ge=0)  # [declared] 0 = off
    points: bool = False  # [declared]
    lives: int = Field(default=0, ge=0)  # [declared] 0 = unlimited
    celebrate_milestones: bool = True  # [declared]


# --- I · Output & analytics ------------------------------------------------
class OutputSettings(BaseModel):
    model_config = _STRICT

    enabled: bool = True  # [active]
    dir: str = "~/konjugaton/{userid}"  # [active] {userid} + ~ expanded
    log_responses: bool = True  # [active]
    log_items: bool = True  # [active]
    log_calculations: bool = True  # [active] P(correct), theta/EWMA deltas
    log_timing: bool = True  # [declared] response latency
    snapshot_state: bool = True  # [active]
    formats: list[str] = Field(default_factory=lambda: ["jsonl", "csv"])  # [active]


# --- J · Display, locale, accessibility -----------------------------------
class DisplaySettings(BaseModel):
    model_config = _STRICT

    ui_language: Literal["en", "hi"] = "en"  # [declared]
    script: Literal["devanagari", "romanized", "both"] = "both"  # [declared] display preference
    theme: Literal["auto", "light", "dark", "high_contrast"] = "auto"  # [declared]
    color_feedback: bool = True  # [active]
    devanagari_input_helper: bool = True  # [declared] show how to type in Devanagari
    keyboard_layout: Literal["qwerty", "inscript", "phonetic"] = "qwerty"  # [declared]


# --- Keybindings (TUI shortcuts — text-based, vim-remappable) ---------------
class ShortcutSettings(BaseModel):
    """TUI key shortcuts. Use any Textual key string (e.g. ctrl+l, ctrl+h, f3).

    Applied at TUI launch as priority bindings (fire even while typing).
    """

    model_config = _STRICT

    prev: str = "ctrl+left"
    next: str = "ctrl+right"
    hint: str = "ctrl+g"
    settings: str = "ctrl+o"
    quit: str = "ctrl+q"


# --- K · Audio & pronunciation --------------------------------------------
class AudioSettings(BaseModel):
    model_config = _STRICT

    tts: bool = False  # [declared] speak prompt/answer
    tts_voice: str = "hi-IN"  # [declared]
    show_ipa: bool = False  # [declared]
    listening_mode: bool = False  # [declared] hear → type
    dictation: bool = False  # [declared]


# --- L · Input ergonomics --------------------------------------------------
class InputSettings(BaseModel):
    model_config = _STRICT

    autotrim: bool = True  # [active] strip surrounding whitespace
    transliterate_input: bool = False  # [declared] type roman → Devanagari live
    submit_key: Literal["enter", "tab"] = "enter"  # [declared]
    reveal_answer_after_attempts: int = Field(default=0, ge=0)  # [declared] 0 = off


# --- M · Multi-language (forward-looking; engine is HI-only today) ---------
class LanguageSettings(BaseModel):
    model_config = _STRICT

    target: str = "hi"  # [declared]
    source: str = "en"  # [declared] gloss/translation language
    show_l2_glosses: bool = True  # [active] show English translation


# --- N · Error analysis ----------------------------------------------------
class ErrorAnalysisSettings(BaseModel):
    model_config = _STRICT

    cluster_by_skill: bool = True  # [declared]
    surface_top_pattern: bool = True  # [declared]
    confusion_pairs: bool = False  # [declared] track which forms get mixed up
    track_gender_errors: bool = True  # [declared] gender agreement is a key Hindi error


class LearnerSettings(BaseModel):
    """Learner background — feeds personalisation (L1 contrast, theta priors)."""

    model_config = _STRICT

    l1: str = ""  # native language code, e.g. "en", "es"
    nationality: str = ""
    age: int = Field(default=0, ge=0)  # 0 = unset
    sex: str = ""  # "" | m | f | other
    assessment_theta: float = 0.0  # prior ability from a placement test (0 = none)


class SessionSettings(BaseModel):
    model_config = _STRICT

    default_count: int = Field(default=10, ge=1)  # [active]
    default_order: str = "adaptive"  # [active]
    time_limit_seconds: int = Field(default=0, ge=0)  # [declared] 0 = none
    warmup_easy_items: int = Field(default=0, ge=0)  # [declared]
    cooldown_items: int = Field(default=0, ge=0)  # [declared]
    block_size: int = Field(default=5, ge=1)  # [declared] for interleave blocks


class Settings(BaseModel):
    model_config = _STRICT

    version: int = 1
    #: Named preset this config was derived from (informational; "custom" if hand-tuned).
    preset: str = "custom"
    grading: GradingSettings = Field(default_factory=GradingSettings)
    feedback: FeedbackSettings = Field(default_factory=FeedbackSettings)
    scheduling: SchedulingSettings = Field(default_factory=SchedulingSettings)
    adaptivity: AdaptivitySettings = Field(default_factory=AdaptivitySettings)
    curriculum: CurriculumSettings = Field(default_factory=CurriculumSettings)
    items: ItemSettings = Field(default_factory=ItemSettings)
    scaffolding: ScaffoldingSettings = Field(default_factory=ScaffoldingSettings)
    motivation: MotivationSettings = Field(default_factory=MotivationSettings)
    output: OutputSettings = Field(default_factory=OutputSettings)
    display: DisplaySettings = Field(default_factory=DisplaySettings)
    shortcuts: ShortcutSettings = Field(default_factory=ShortcutSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    input: InputSettings = Field(default_factory=InputSettings)
    language: LanguageSettings = Field(default_factory=LanguageSettings)
    error_analysis: ErrorAnalysisSettings = Field(default_factory=ErrorAnalysisSettings)
    learner: LearnerSettings = Field(default_factory=LearnerSettings)
    session: SessionSettings = Field(default_factory=SessionSettings)
