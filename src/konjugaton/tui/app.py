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
from textual.widgets import Button, Footer, Header, Input, OptionList, Static
from textual.widgets.option_list import Option

from konjugaton.analytics import irt
from konjugaton.domain import TenseMood
from konjugaton.services import (
    ConjugationTableService,
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

    from konjugaton.domain import ConjugationTable, Item
    from konjugaton.services import GradedResponse


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


class SettingsScreen(Screen["Settings | None"]):
    """A settings console: type commands, see the config, save to YAML.

    Dismisses with the (possibly preset-swapped) ``Settings`` so the app can
    rebuild against them; the ``_after_settings`` callback consumes that result.
    """

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "back", "Back")]

    def action_back(self) -> None:
        self.dismiss(self._settings)

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
            self.dismiss(self._settings)
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


#: Home-menu actions, keyed by the digit that selects them (1-4).
_HOME_ACTIONS: dict[str, str] = {"1": "practice", "2": "table", "3": "settings", "4": "quit"}


class HomeScreen(Screen["str | None"]):
    """The top-level menu — the TUI's equivalent of the Android home screen.

    Dismisses with one of ``practice`` / ``table`` / ``settings`` / ``quit``; the
    app's ``_after_home`` callback dispatches. Pressing Escape resumes practice.
    """

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "resume", "Practice")]

    def __init__(self, user: str) -> None:
        super().__init__()
        self._user = user

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("[b]konjugaton[/] — wähle einen Modus", id="home_title"),
            Button("1 · Üben — gemischtes adaptives Drill", id="practice", variant="primary"),
            Button("2 · Konjugationstabelle — ein Verb, eine Zeit", id="table"),
            Button("3 · Einstellungen", id="settings"),
            Button("4 · Beenden", id="quit"),
            Static("[dim]click a button, or press 1-4 · ↑↓+Enter · Esc resumes practice[/]"),
            id="home_main",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"konjugaton · menü · {self._user}"
        self.query_one("#practice", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id)

    def on_key(self, event: Key) -> None:
        action = _HOME_ACTIONS.get(event.key)
        if action is not None:
            event.stop()
            self.dismiss(action)

    def action_resume(self) -> None:
        self.dismiss("practice")


class VerbPickScreen(Screen["str | None"]):
    """Pick the verb whose table to drill. Dismisses with the lemma (or None)."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "cancel", "Back to menu")]

    def __init__(self, service: ConjugationTableService) -> None:
        super().__init__()
        self._service = service

    def compose(self) -> ComposeResult:
        yield Header()
        options = [
            Option(f"{v.lemma}  —  {v.translation}  [dim]({v.verb_class.value})[/]", id=v.lemma)
            for v in self._service.verbs()
        ]
        yield Vertical(
            Static("[b]Konjugationstabelle[/] · wähle ein Verb  [dim](Esc → menü)[/]"),
            OptionList(*options, id="verbpick"),
            id="pick_main",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "konjugaton · tabelle · verb"
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def action_cancel(self) -> None:
        self.dismiss(None)


class TenseMoodPickScreen(Screen["TenseMood | None"]):
    """Pick the tense-mood for the chosen verb. Dismisses with the TenseMood."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "cancel", "Back to verb")]

    def __init__(self, service: ConjugationTableService, lemma: str) -> None:
        super().__init__()
        self._lemma = lemma
        self._tense_moods = service.available_tense_moods(lemma)
        self._label = dict(_tense_labels(self._tense_moods))

    def compose(self) -> ComposeResult:
        yield Header()
        options = [Option(self._label[tm], id=str(i)) for i, tm in enumerate(self._tense_moods)]
        yield Vertical(
            Static(f"[b]{self._lemma}[/] · wähle eine Zeit/Modus  [dim](Esc → verb)[/]"),
            OptionList(*options, id="tmpick"),
            id="pick_main",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"konjugaton · tabelle · {self._lemma} · zeit"
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(self._tense_moods[event.option_index])

    def action_cancel(self) -> None:
        self.dismiss(None)


class TableScreen(Screen[None]):
    """Fill one verb's full conjugation table, cell by cell.

    Each cell is graded by the app's configured grader and recorded into learner
    state exactly like a drill item, so table practice feeds mastery and reports.
    Escape (or finishing the last cell) returns to the menu.
    """

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "leave", "Menu")]

    def __init__(self, app: KonjugatonApp, table: ConjugationTable) -> None:
        super().__init__()
        self._app = app
        self._table = table
        self._index = 0
        self._correct = 0
        self._answered = 0
        self._verdicts: dict[int, tuple[str, str]] = {}
        self._shown_at: float = 0.0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("", id="table_grid"),
            Input(placeholder="konjugierte Form… (Enter; leeres Enter zeigt)", id="cell"),
            Static("", id="table_feedback"),
            id="table_main",
        )
        yield Footer()

    def on_mount(self) -> None:
        self._app.title = f"konjugaton · tabelle · {self._table.lemma} · {self._table.tense_label}"
        self._render_table()

    def _grid(self) -> str:
        head = (
            f"[b]{self._table.lemma}[/] [dim]({self._table.translation})[/]  ·  "
            f"[cyan]{self._table.tense_label}[/]\n"
        )
        lines = []
        for i, cell in enumerate(self._table.cells):
            if i in self._verdicts:
                state, shown = self._verdicts[i]
                lines.append(f"  {cell.subject:8} {state} {shown}")
            elif i == self._index:
                lines.append(f"  {cell.subject:8} [b]_____[/]   [dim]← type this one[/]")
            else:
                lines.append(f"  [dim]{cell.subject:8} ·····[/]")
        return head + "\n".join(lines)

    def _render_table(self) -> None:
        self.query_one("#table_grid", Static).update(self._grid())
        cell_input = self.query_one("#cell", Input)
        if self._index >= len(self._table.cells):
            cell_input.disabled = True
            self.query_one("#table_feedback", Static).update(
                f"[b]Tabelle fertig — {self._correct}/{len(self._table.cells)}[/]   "
                "[dim](Esc → menü)[/]"
            )
            self._app.persist_table_session(len(self._table.cells), self._correct)
            return
        cell = self._table.cells[self._index]
        self.query_one("#table_feedback", Static).update(
            f"[dim]fill the {cell.subject!r} form of "
            f"{self._table.lemma} ({self._table.tense_label})[/]"
        )
        cell_input.disabled = False
        cell_input.value = ""
        cell_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._index >= len(self._table.cells):
            return
        cell = self._table.cells[self._index]
        given = event.value.strip()
        if not given:  # empty Enter = reveal this cell, no record
            self._verdicts[self._index] = ("[yellow]≈[/]", f"[dim]{cell.answer}[/]")
            self._index += 1
            self._render_table()
            return
        graded = self._app.table_service.grade(cell.item, given)
        if graded.grade is Grade.CORRECT:
            verdict = ("[green]✓[/]", f"[green]{cell.answer}[/]")
        elif graded.grade is Grade.NEAR:
            verdict = ("[green]≈[/]", f"[green]{cell.answer}[/] [dim](edits={graded.distance})[/]")
        elif graded.grade is Grade.ACCENT_SLIP:
            verdict = ("[yellow]≈[/]", f"[yellow]{cell.answer}[/] [dim](Umlaut)[/]")
        else:
            verdict = ("[red]✗[/]", f"[red]{cell.answer}[/] [dim](du: {given})[/]")
        self._verdicts[self._index] = verdict
        self._answered += 1
        self._correct += int(graded.is_correct)
        self._app.record_table_cell(cell.item, graded)
        self._index += 1
        self._render_table()

    def action_leave(self) -> None:
        if self._answered and self._index < len(self._table.cells):
            self._app.persist_table_session(self._answered, self._correct)
        self.dismiss(None)


def _tense_labels(tense_moods: list[TenseMood]) -> list[tuple[TenseMood, str]]:
    """(tense_mood, display label) pairs — imported lazily to keep domain pure."""
    from konjugaton.engine.labels import tense_of  # noqa: PLC0415

    return [(tm, tense_of(tm)) for tm in tense_moods]


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
    #home_main { padding: 1 2; }
    #pick_main { padding: 1 2; }
    #table_main { padding: 1 2; }
    #prompt { text-style: bold; padding-bottom: 1; }
    #hint { color: $text-muted; padding-bottom: 1; }
    #feedback { padding-top: 1; }
    #note { color: $text-muted; }
    #settings_body { padding-bottom: 1; }
    #home_title { text-style: bold; padding-bottom: 1; }
    #home_main Button { width: 100%; margin-bottom: 1; }
    #verbpick, #tmpick { height: 1fr; }
    #table_grid { padding-bottom: 1; }
    #table_feedback { padding-top: 1; }
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
        self._table_service = ConjugationTableService.default(settings=self._settings)
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
        self._open_home()

    # -- top-level menu + mode routing --------------------------------------

    @property
    def table_service(self) -> ConjugationTableService:
        return self._table_service

    def _open_home(self) -> None:
        """Show the hub menu; ``_after_home`` dispatches the chosen mode."""
        self.push_screen(HomeScreen(self._user), self._after_home)

    def _after_home(self, action: str | None) -> None:
        if action == "table":
            self._start_table_flow()
        elif action == "settings":
            self.push_screen(SettingsScreen(self._settings, self._user), self._after_settings_home)
        elif action == "quit":
            self.exit()
        else:  # "practice" / Esc → reveal the drill underneath the (now-popped) menu
            self.title = f"konjugaton · {self._user}"
            self._render_item()

    def action_settings(self) -> None:
        self.push_screen(SettingsScreen(self._settings, self._user), self._after_settings)

    def _after_settings(self, result: Settings | None) -> None:
        # Settings may have changed (and `preset` swaps the object entirely).
        if isinstance(result, Settings):
            self._settings = result
        self._service = PracticeService.default(settings=self._settings)
        self._table_service = ConjugationTableService.default(settings=self._settings)
        # If the session filter changed, resample so the preference takes effect.
        sig = _selection_sig(self._settings)
        if sig != self._sel_sig:
            self._sel_sig = sig
            self._items = self._build_items()
            self._index = 0
            self._correct = 0
            self._answered.clear()
            self._feedback_at.clear()
        self._render_item()

    def _after_settings_home(self, result: Settings | None) -> None:
        # Settings opened from the menu: absorb changes, then return to the menu.
        self._after_settings(result)
        self._open_home()

    def _start_table_flow(self) -> None:
        self.push_screen(VerbPickScreen(self._table_service), self._after_verb)

    def _after_verb(self, lemma: str | None) -> None:
        if lemma is None:
            self._open_home()
            return
        self.push_screen(
            TenseMoodPickScreen(self._table_service, lemma),
            lambda tm: self._after_tense_mood(lemma, tm),
        )

    def _after_tense_mood(self, lemma: str, tense_mood: TenseMood | None) -> None:
        if tense_mood is None:
            self._start_table_flow()  # back up to the verb picker
            return
        table = self._table_service.build_table(lemma, tense_mood)
        self.push_screen(TableScreen(self, table), lambda _result: self._open_home())

    def record_table_cell(self, item: Item, graded: GradedResponse) -> None:
        """Record one table cell into learner state + the event log (like a drill)."""
        theta_before = self._state.ability(item.skill)
        p_correct = irt.probability_correct(theta_before, item.irt)
        information = irt.information(theta_before, item.irt)
        ewma_before = self._state.cell(item.coordinate.lemma, item.coordinate.knowledge).ewma
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

    def persist_table_session(self, items: int, correct: int) -> None:
        self._repo.save(self._state)
        self._learner_log.snapshot_state(self._state)
        self._learner_log.log_session(
            {"user": self._user, "items": items, "correct": correct, "via": "tui-table"}
        )

    def on_key(self, event: Key) -> None:
        """Dispatch config-driven shortcuts. Skips when a screen (menu/settings) is open."""
        if len(self.screen_stack) > 1:
            return
        if event.key == "escape":  # back to the hub menu from the drill
            event.stop()
            event.prevent_default()
            self._open_home()
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
            f"{sc.prev}/{sc.next} navigate · {sc.hint} hint · Tab→note · "
            f"{sc.settings} settings · Esc menu)[/]"
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
