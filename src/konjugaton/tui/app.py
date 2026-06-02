"""Textual terminal UI — drilling plus a settings screen bound to config.yaml.

The settings screen reads the user's Settings on open and writes them back on
save, so it is bidirectional with the YAML by construction: edit in the TUI or
the file, both round-trip through the same store.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Static

from konjugaton.analytics import irt
from konjugaton.services import (
    Grade,
    LearnerLogger,
    PracticeService,
    SessionOrder,
    build_response_record,
    generate_hint,
    mistake_markup,
    selection_from_settings,
)
from konjugaton.settings import (
    PRESET_NAMES,
    Settings,
    apply_preset,
    load_settings,
    resolve_output_dir,
    save_settings,
)
from konjugaton.state import JsonStateRepository

if TYPE_CHECKING:
    from pathlib import Path

    from konjugaton.domain import Item


def _selection_sig(settings: Settings) -> tuple[tuple[str, ...], ...]:
    """A hashable snapshot of the session-filter settings, to detect changes."""
    c = settings.curriculum
    return (
        tuple(c.knowledge),
        tuple(c.tense_moods),
        tuple(c.persons),
        tuple(c.numbers),
        tuple(c.registers),
        tuple(c.voices),
        tuple(c.polarities),
        tuple(c.contexts),
    )


_KNOW_LABEL = {"production": "typed", "recognition": "multiple-choice"}


def _render_settings(settings: Settings, user: str) -> str:
    g = settings.grading
    o = settings.output
    c = settings.curriculum
    registers = " + ".join(c.registers) if c.registers else "all (ich/du/er/wir/ihr/Sie)"
    voices = " + ".join(c.voices) if c.voices else "all (aktiv + passiv)"
    types = " + ".join(_KNOW_LABEL.get(k, k) for k in c.knowledge) if c.knowledge else "all"
    return (
        f"[b]preset[/] {settings.preset}\n\n"
        f"[b]session filter[/]  (what you get drilled on — applies on [b]back[/])\n"
        f"  register      : [b]{registers}[/]\n"
        f"  voice         : [b]{voices}[/]\n"
        f"  question types: [b]{types}[/]\n\n"
        f"[b]grading[/]\n"
        f"  similarity_tolerance : {g.similarity_tolerance}   (0 strict … 10 loose)\n"
        f"  ignore_accents       : {g.ignore_accents}   (folds ä/ö/ü/ß)\n"
        f"  ignore_case          : {g.ignore_case}\n"
        f"  ignore_punctuation   : {g.ignore_punctuation}\n\n"
        f"[b]output[/]\n"
        f"  enabled              : {o.enabled}\n"
        f"  dir                  : {resolve_output_dir(settings, user)}\n\n"
        f"[b]shortcuts[/] (apply next launch)\n"
        f"  prev {settings.shortcuts.prev} · next {settings.shortcuts.next} · "
        f"hint {settings.shortcuts.hint} · settings {settings.shortcuts.settings} · "
        f"quit {settings.shortcuts.quit}\n\n"
        "[dim]session:[/]  register du|ihr|sie|all · voice aktiv|passiv|all · "
        "types mcq|typed|all · mcq · typed\n"
        "[dim]grading:[/]  accents on|off · case on|off · punct on|off · tol N\n"
        "[dim]other:[/]    bind next ctrl+l · preset <name> · save · back"
    )


class SettingsScreen(Screen[None]):
    """A settings console: type commands, see the config, save to YAML."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "app.pop_screen", "Back")]

    def __init__(self, settings: Settings, user: str) -> None:
        super().__init__()
        self._settings = settings
        self._user = user

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static(_render_settings(self._settings, self._user), id="settings_body"),
            Input(placeholder="settings command…", id="settings_cmd"),
            Static("", id="settings_status"),
            id="settings_main",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"konjugaton · settings · {self._user}"
        self.query_one("#settings_cmd", Input).focus()

    def _refresh(self, status: str = "") -> None:
        self.query_one("#settings_body", Static).update(
            _render_settings(self._settings, self._user)
        )
        self.query_one("#settings_status", Static).update(status)
        self.query_one("#settings_cmd", Input).value = ""

    def on_input_submitted(self, event: Input.Submitted) -> None:  # noqa: PLR0911, PLR0912, PLR0915 — command dispatch
        parts = event.value.strip().split()
        if not parts:
            return
        cmd, *args = parts
        g = self._settings.grading
        on_off = {"on": True, "off": False}

        if cmd == "back":
            self.app.pop_screen()
            return
        if cmd == "save":
            save_settings(self._settings, self._user)
            self._refresh("[green]saved to config.yaml[/]")
            return
        if cmd == "accents" and args and args[0] in on_off:
            g.ignore_accents = on_off[args[0]]
        elif cmd == "case" and args and args[0] in on_off:
            g.ignore_case = on_off[args[0]]
        elif cmd == "punct" and args and args[0] in on_off:
            g.ignore_punctuation = on_off[args[0]]
        elif cmd == "tol" and args and args[0].isdigit() and 0 <= int(args[0]) <= 10:
            g.similarity_tolerance = int(args[0])
        elif cmd == "map" and len(args) == 2:
            g.transliteration[args[0]] = args[1].split(",")
        elif cmd == "unmap" and len(args) == 1:
            g.transliteration.pop(args[0], None)
        elif cmd == "register" and args:
            regs = {
                "du": ["du"],
                "ihr": ["ihr"],
                "sie": ["sie_formal"],
                "formal": ["sie_formal"],
                "all": [],
                "both": [],
            }
            if args[0] not in regs:
                self._refresh("[red]register: du | ihr | sie | all[/]")
                return
            self._settings.curriculum.registers = regs[args[0]]
        elif cmd == "voice" and args:
            voices = {
                "aktiv": ["aktiv"],
                "active": ["aktiv"],
                "passiv": ["passiv"],
                "passive": ["passiv"],
                "all": [],
                "both": [],
            }
            if args[0] not in voices:
                self._refresh("[red]voice: aktiv | passiv | all[/]")
                return
            self._settings.curriculum.voices = voices[args[0]]
        elif cmd in ("mcq", "typed") and not args:
            self._settings.curriculum.knowledge = (
                ["recognition"] if cmd == "mcq" else ["production"]
            )
        elif cmd == "types" and args:
            alias = {
                "mcq": "recognition",
                "recog": "recognition",
                "recognition": "recognition",
                "typed": "production",
                "prod": "production",
                "production": "production",
            }
            tokens = [t for a in args for t in a.split(",") if t]
            if tokens == ["all"]:
                self._settings.curriculum.knowledge = []
            elif all(t in alias for t in tokens):
                self._settings.curriculum.knowledge = list(dict.fromkeys(alias[t] for t in tokens))
            else:
                self._refresh("[red]types: mcq | typed | all  (or a csv)[/]")
                return
        elif cmd == "bind" and len(args) == 2 and hasattr(self._settings.shortcuts, args[0]):
            setattr(self._settings.shortcuts, args[0], args[1])
            self._settings.preset = "custom"
            self._refresh(f"[green]bound {args[0]} → {args[1]} (save, applies next launch)[/]")
            return
        elif cmd == "preset" and args and args[0] in PRESET_NAMES:
            self._settings = apply_preset(args[0])
            self._refresh(f"[green]loaded preset {args[0]} (unsaved)[/]")
            return
        else:
            self._refresh(f"[red]unrecognised:[/] {event.value}")
            return
        self._settings.preset = "custom"
        self._refresh("[dim]changed (unsaved — type 'save')[/]")


class KonjugatonApp(App[None]):
    """Single-pane drill with a settings screen and config-driven shortcuts.

    Shortcuts are dispatched in ``on_key`` from the user's config (not static
    BINDINGS), so they can be freely remapped — e.g. vim ctrl+h / ctrl+l —
    without Textual's class-level binding snapshot getting in the way. on_key
    sees ctrl-combos because the focused Input does not consume them.
    """

    CSS = """
    #main { padding: 1 2; }
    #settings_main { padding: 1 2; }
    #prompt { text-style: bold; padding-bottom: 1; }
    #hint { color: $text-muted; padding-bottom: 1; }
    #feedback { padding-top: 1; }
    #note { color: $text-muted; }
    #settings_body { padding-bottom: 1; }
    """
    BINDINGS: ClassVar[list[BindingType]] = []  # shortcuts handled in on_key (config-driven)

    def __init__(self, user: str, state_file: Path) -> None:
        super().__init__()
        self._user = user
        self._settings = load_settings(user)
        self._repo = JsonStateRepository(state_file)
        self._state = self._repo.load()
        self._learner_log = LearnerLogger(self._settings, user)
        self._service = PracticeService.default(settings=self._settings)
        self._sel_sig = _selection_sig(self._settings)
        self._items = self._build_items()
        self._index = 0
        self._correct = 0
        self._answered: set[int] = set()
        self._feedback_at: dict[int, str] = {}

    def _build_items(self) -> list[Item]:
        """Sample a fresh session honouring the curriculum filter (script/types/…)."""
        return self._service.build_session(
            selection_from_settings(self._settings),
            count=self._settings.session.default_count,
            state=self._state,
            order=SessionOrder.ADAPTIVE,
        )

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("", id="prompt"),
            Static("", id="hint"),
            Input(placeholder="deine Antwort… (Enter to answer; empty Enter to skip)", id="answer"),
            Static("", id="feedback"),
            Input(
                placeholder='note — e.g. "I don\'t know the perfect" — Tab here, Enter to log',
                id="note",
            ),
            id="main",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"konjugaton · {self._user}"
        self._render_item()

    def action_settings(self) -> None:
        self.push_screen(SettingsScreen(self._settings, self._user))

    def on_screen_resume(self) -> None:
        # Settings may have changed; rebuild the grader from current settings.
        self._service = PracticeService.default(settings=self._settings)
        # If the session filter (script / question-types / curriculum) changed,
        # resample a fresh session so the new preference takes effect immediately.
        sig = _selection_sig(self._settings)
        if sig != self._sel_sig:
            self._sel_sig = sig
            self._items = self._build_items()
            self._index = 0
            self._correct = 0
            self._answered.clear()
            self._feedback_at.clear()
        self._render_item()

    def on_key(self, event: Key) -> None:
        """Dispatch config-driven shortcuts. Skips when a screen (settings) is open."""
        if len(self.screen_stack) > 1:
            return
        sc = self._settings.shortcuts
        action = {
            sc.prev: "prev",
            sc.next: "next",
            sc.hint: "hint",
            sc.settings: "settings",
            sc.quit: "quit",
        }.get(event.key)
        if action is None:
            return
        event.stop()
        event.prevent_default()
        if action == "quit":
            self.exit()
        else:
            getattr(self, f"action_{action}")()

    def _render_item(self) -> None:
        if self._index >= len(self._items):
            self._finish()
            return
        item = self._items[self._index]
        self._learner_log.log_item(item)
        prompt = f"{self._index + 1}/{len(self._items)}   {item.prompt}"
        if item.is_multiple_choice:
            # Recognition: render the options so the learner can pick a letter.
            opts = "   ".join(
                f"[b]{letter})[/] {choice}"
                for letter, choice in zip("abcd", item.choices, strict=False)
            )
            prompt += f"\n\n{opts}"
        self.query_one("#prompt", Static).update(prompt)
        sc = self._settings.shortcuts
        how = "type a/b/c/d" if item.is_multiple_choice else "type the form"
        self.query_one("#hint", Static).update(
            f"{item.lemma_hint} · {item.task}   [dim]({how} · "
            f"{sc.prev}/{sc.next} navigate · {sc.hint} hint · Tab→note · {sc.settings} settings)[/]"
        )
        self.query_one("#feedback", Static).update(self._feedback_at.get(self._index, ""))
        self.query_one("#note", Input).value = ""
        answer = self.query_one("#answer", Input)
        answer.disabled = False
        answer.value = ""
        answer.placeholder = (
            "a/b/c/d (Enter to answer)"
            if item.is_multiple_choice
            else "deine Antwort… (Enter to answer; empty Enter to skip)"
        )
        answer.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "note":
            self._log_note(event.value)
            return
        if event.input.id != "answer":
            return
        if not event.value.strip():  # empty response = skip forward (no record)
            self.action_next()
            return
        if self._index in self._answered:  # already answered — don't double-count
            self.query_one("#feedback", Static).update(
                self._feedback_at[self._index]
                + f"   [dim](already answered — {self._settings.shortcuts.next})[/]"
            )
            return

        item = self._items[self._index]
        theta_before = self._state.ability(item.skill)
        p_correct = irt.probability_correct(theta_before, item.irt)
        information = irt.information(theta_before, item.irt)
        ewma_before = self._state.cell(item.coordinate.lemma, item.coordinate.knowledge).ewma

        # For MCQ, accept a typed letter (a/b/c/d) as well as the literal form.
        given = event.value
        if item.is_multiple_choice:
            mapping = dict(zip("abcd", item.choices, strict=False))
            given = mapping.get(given.strip().lower(), given)
        graded = self._service.grade(item, given)
        if graded.grade is Grade.CORRECT:
            message = "[green]✓ सही[/]"
        elif graded.grade is Grade.NEAR:
            message = f"[green]≈ accepted (edits={graded.distance}) → {item.answer}[/]"
        elif graded.grade is Grade.ACCENT_SLIP:
            message = f"[yellow]≈ diacritics → {item.answer}[/]"
        else:
            message = f"[red]✗ {item.answer}[/]"
        rendered = (
            f"{message}   [dim]{item.full_sentence}[/]   "
            f"[dim]({self._settings.shortcuts.next} to continue)[/]"
        )
        if self._settings.feedback.char_diff_on_error and graded.grade is not Grade.CORRECT:
            rendered += "\n" + mistake_markup(
                graded.given, item.answer, self._service.grader.normalize
            )
        self.query_one("#feedback", Static).update(rendered)
        self._feedback_at[self._index] = rendered
        self._answered.add(self._index)
        if graded.is_correct:
            self._correct += 1

        self._state.record(item, correct=graded.is_correct, timestamp=datetime.now(UTC).isoformat())
        self._learner_log.log_response(
            build_response_record(
                user=self._user,
                item=item,
                graded=graded,
                p_correct=p_correct,
                information=information,
                theta_before=theta_before,
                theta_after=self._state.ability(item.skill),
                ewma_before=ewma_before,
                ewma_after=self._state.cell(item.coordinate.lemma, item.coordinate.knowledge).ewma,
                verb_class=item.skill.verb_class.value,
            )
        )

    def _log_note(self, text: str) -> None:
        note = text.strip()
        if note and self._index < len(self._items):
            self._learner_log.log_feedback(
                user=self._user, item=self._items[self._index], text=note
            )
            self.query_one("#feedback", Static).update("[blue]note logged ✓[/]")
            self.query_one("#note", Input).value = ""

    def action_prev(self) -> None:
        if self._index > 0:
            self._index -= 1
            self._render_item()

    def action_next(self) -> None:
        self._index += 1
        self._render_item()  # _render_item calls _finish once past the end

    def action_hint(self) -> None:
        if self._index < len(self._items):
            hint = generate_hint(self._items[self._index], self._settings)
            self.query_one("#feedback", Static).update(f"[blue]hint:[/] {hint}")

    def _finish(self) -> None:
        self._repo.save(self._state)
        self._learner_log.snapshot_state(self._state)
        self._learner_log.log_session(
            {"user": self._user, "items": len(self._items), "correct": self._correct, "via": "tui"}
        )
        self.query_one("#prompt", Static).update(
            f"समाप्त (done) — score {self._correct}/{len(self._items)}"
        )
        self.query_one("#hint", Static).update(f"State saved → {self._repo.path}")
        self.query_one("#answer", Input).disabled = True


def run_tui(user: str, state_file: Path) -> None:
    KonjugatonApp(user=user, state_file=state_file).run()
