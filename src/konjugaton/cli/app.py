"""The ``konjugaton`` command-line interface (Typer).

Thin presentation layer: parse flags into an AxisSelection, load the user's
settings, call the services, render with rich. Per-user state, config and
learner-output all live under ~/konjugaton/{user}/.
"""

from __future__ import annotations

import contextlib
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from konjugaton import __version__
from konjugaton.analytics import (
    ABILITY_COLUMNS,
    MASTERY_COLUMNS,
    ability_rows,
    irt,
    mastery_rows,
    summary,
)
from konjugaton.domain import (
    Item,
    KnowledgeType,
    Number,
    Person,
    Polarity,
    Register,
    TenseMood,
    VerbClass,
    Voice,
)
from konjugaton.engine import AxisSelection
from konjugaton.services import (
    CatalogService,
    Grade,
    GradedResponse,
    LearnerLogger,
    PracticeService,
    SessionOrder,
    mistake_markup,
    run_selfcheck,
    selection_from_settings,
)
from konjugaton.settings import (
    PRESET_NAMES,
    Settings,
    apply_preset,
    config_path,
    default_user,
    load_settings,
    save_settings,
    state_path,
)
from konjugaton.state import JsonStateRepository

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="konjugaton — hyper-combinatorial Hindi grammar practice (देवनागरी + romanization).",
)
config_app = typer.Typer(help="Inspect and edit user settings (config.yaml).", no_args_is_help=True)
app.add_typer(config_app, name="config")
console = Console()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _resolve_state(state_opt: Path | None, user: str) -> Path:
    return state_opt if state_opt is not None else state_path(user)


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"konjugaton {__version__}")


@app.command()
def catalog() -> None:
    """Describe the combinatorial exercise space and its size."""
    service = CatalogService.default()
    table = Table(title="Practice axes", show_lines=False)
    table.add_column("axis", style="cyan")
    table.add_column("size", justify="right", style="bold")
    table.add_column("values", style="dim")
    for axis in service.axes():
        sample = ", ".join(axis.values[:6]) + ("  …" if len(axis.values) > 6 else "")
        table.add_row(axis.name, str(axis.size), sample)
    console.print(table)
    total = service.total_space_size()
    console.print(
        f"\nTotal realizable exercise space: [bold green]{total:,}[/] coordinates "
        "(product of axes, minus cells the engine cannot conjugate and "
        "ungrammatical agreement bundles)."
    )


@app.command()
def verbs(
    verb_class: VerbClass | None = typer.Option(
        None, "--class", "-c", help="Filter by verb class."
    ),
) -> None:
    """List the verb inventory."""
    service = CatalogService.default()
    table = Table(title="Verbs")
    for col in ("lemma", "class", "aux", "sep", "translation", "freq"):
        table.add_column(col)
    for verb in sorted(service.catalog.verbs.values(), key=lambda v: v.frequency_rank):
        if verb_class is not None and verb.verb_class is not verb_class:
            continue
        table.add_row(
            verb.lemma,
            verb.verb_class.value,
            verb.auxiliary.value,
            verb.separable_prefix or "—",
            verb.translation,
            str(verb.frequency_rank),
        )
    console.print(table)


def _present_item(index: int, item: Item) -> None:
    console.print(f"\n[bold]{index}.[/] {item.prompt}")
    tags = (
        f"[cyan]{item.lemma_hint}[/] ({item.metadata.get('translation', '')}) · "
        f"[bold]{item.task}[/]"
    )
    console.print(f"   [dim]{tags}[/]  [dim]b={item.irt.difficulty}[/]")
    if item.is_multiple_choice:
        for letter, choice in zip("abcd", item.choices, strict=False):
            console.print(f"     [yellow]{letter})[/] {choice}")


def _read_answer(item: Item) -> str:
    if item.is_multiple_choice:
        raw: str = typer.prompt("   your choice (letter or text)").strip()
        mapping = dict(zip("abcd", item.choices, strict=False))
        return mapping.get(raw.lower(), raw)
    return typer.prompt("   your answer")


@app.command()
def practice(  # noqa: PLR0912, PLR0915 - CLI surface + interactive loop
    count: int = typer.Option(10, "--count", "-n", help="Number of exercises."),
    user: str = typer.Option(default_user(), "--user", "-u", help="Learner profile id."),
    tense: TenseMood | None = typer.Option(None, help="Restrict to one tense-mood."),
    person: Person | None = typer.Option(None),
    number: Number | None = typer.Option(None),
    register: Register | None = typer.Option(None, help="neutral / du / ihr / sie_formal."),
    voice: Voice | None = typer.Option(None, help="aktiv or passiv (werden-passive)."),
    polarity: Polarity | None = typer.Option(None),
    knowledge: KnowledgeType | None = typer.Option(None),
    context: str | None = typer.Option(None, help="Semantic context id."),
    only_mcq: bool = typer.Option(
        False, "--only-mcq", help="Multiple-choice only (no typing) — recognition items."
    ),
    order: SessionOrder = typer.Option(SessionOrder.ADAPTIVE, help="Item ordering."),
    seed: int | None = typer.Option(None, help="Deterministic generation."),
    state_opt: Path | None = typer.Option(None, "--state", help="Override state file."),
    save: bool = typer.Option(True, "--save/--no-save"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive"),
) -> None:
    """Run a practice session over a slice of the combinatorial space."""
    settings = load_settings(user)
    service = PracticeService.default(seed=seed, settings=settings)
    logger = LearnerLogger(settings, user)
    catalog_obj = service.catalog_service.catalog

    # Explicit flags win; unset axes fall back to the persistent curriculum
    # filter (settings.curriculum.*), so `config set` / the TUI settings screen
    # govern the CLI too. `--only-mcq` is sugar for `--knowledge recognition`.
    if only_mcq:
        knowledge = KnowledgeType.RECOGNITION
    base = AxisSelection(
        tense_moods=(tense,) if tense else (),
        persons=(person,) if person else (),
        numbers=(number,) if number else (),
        registers=(register,) if register else (),
        voices=(voice,) if voice else (),
        polarities=(polarity,) if polarity else (),
        knowledge=(knowledge,) if knowledge else (),
        contexts=(context,) if context else (),
    )
    selection = selection_from_settings(settings, base)

    repo = JsonStateRepository(_resolve_state(state_opt, user))
    state = repo.load()
    items = service.build_session(selection, count, state=state, order=order)
    if not items:
        console.print("[yellow]No exercises match those filters.[/]")
        raise typer.Exit(code=1)

    correct = 0
    for i, item in enumerate(items, start=1):
        logger.log_item(item)
        _present_item(i, item)
        if not interactive:
            console.print(f"   [green]→ {item.answer}[/]   ([dim]{item.full_sentence}[/])")
            continue
        given = _read_answer(item)

        # Capture the IRT calculations around the update for the learner log.
        theta_before = state.ability(item.skill)
        p_correct = irt.probability_correct(theta_before, item.irt)
        information = irt.information(theta_before, item.irt)
        ewma_before = state.cell(item.coordinate.lemma, item.coordinate.knowledge).ewma

        graded = service.grade(item, given)
        if graded.grade is Grade.CORRECT:
            console.print("   [bold green]✓ सही (correct)[/]")
        elif graded.grade is Grade.NEAR:
            console.print(
                f"   [green]≈ Accepted[/] [dim](within tolerance, edits={graded.distance}) "
                f"→ {item.answer}[/]"
            )
        elif graded.grade is Grade.ACCENT_SLIP:
            console.print(f"   [yellow]≈ Right form, watch the diacritics → {item.answer}[/]")
        else:
            console.print(f"   [bold red]✗[/] उत्तर (answer): [bold]{item.answer}[/]")
        console.print(f"     [dim]{item.full_sentence}[/]")
        if settings.feedback.char_diff_on_error and graded.grade is not Grade.CORRECT:
            diff = mistake_markup(graded.given, item.answer, service.grader.normalize)
            for line in diff.split("\n"):
                console.print(f"     {line}")
        if graded.is_correct:
            correct += 1

        state.record(item, correct=graded.is_correct, timestamp=_now())
        theta_after = state.ability(item.skill)
        ewma_after = state.cell(item.coordinate.lemma, item.coordinate.knowledge).ewma
        logger.log_response(
            _response_record(
                user,
                item,
                graded,
                p_correct,
                information,
                theta_before,
                theta_after,
                ewma_before,
                ewma_after,
                catalog_obj.verbs[item.coordinate.lemma].verb_class.value,
            )
        )

    if interactive:
        console.print(f"\n[bold]Score: {correct}/{len(items)}[/]")
        if save:
            repo.save(state)
            console.print(f"[dim]State saved → {repo.path}[/]")
        snapshot = logger.snapshot_state(state)
        logger.log_session({"user": user, "items": len(items), "correct": correct})
        if logger.enabled:
            console.print(f"[dim]Learner logs → {logger.directory}[/]")
        if snapshot is not None:
            console.print(f"[dim]State snapshot → {snapshot}[/]")


def _response_record(
    user: str,
    item: Item,
    graded: GradedResponse,
    p_correct: float,
    information: float,
    theta_before: float,
    theta_after: float,
    ewma_before: float,
    ewma_after: float,
    verb_class: str,
) -> dict[str, object]:
    coord = item.coordinate
    return {
        "schema_version": 3,
        "timestamp": _now(),
        "user": user,
        "lemma": coord.lemma,
        "verb_class": verb_class,
        "tense_mood": coord.tense_mood.value,
        "person": coord.person.value,
        "number": coord.number.value,
        "register": coord.register.value,
        "voice": coord.voice.value,
        "polarity": coord.polarity.value,
        "knowledge": coord.knowledge.value,
        "context": coord.context,
        "prompt": item.prompt,
        "correct_answer": item.answer,
        "user_answer": graded.given,
        "grade": graded.grade.value,
        "is_correct": graded.is_correct,
        "distance": graded.distance,
        "normalized_user_answer": graded.normalized_given,
        "normalized_correct_answer": graded.normalized_answer,
        "irt_a": item.irt.discrimination,
        "irt_b": item.irt.difficulty,
        "irt_c": item.irt.guessing,
        "p_correct": round(p_correct, 4),
        "information": round(information, 4),
        "theta_before": round(theta_before, 4),
        "theta_after": round(theta_after, 4),
        "ewma_before": round(ewma_before, 4),
        "ewma_after": round(ewma_after, 4),
    }


@app.command()
def selfcheck() -> None:
    """Exhaustively validate the engine + data over every realizable coordinate.

    Exits non-zero on any failure. Built to be run against the *compiled binary*
    in a clean environment — the gate that catches packaging/combinatorial bugs.
    """
    report = run_selfcheck()
    console.print(
        f"checked [bold]{report.coordinates_checked:,}[/] coordinates · "
        f"{report.verbs} verbs · {report.tams} TAMs"
    )
    if report.ok:
        console.print("[bold green]✓ selfcheck passed[/]")
        return
    console.print(f"[bold red]✗ {len(report.failures)} failure(s):[/]")
    for failure in report.failures:
        console.print(f"  [red]•[/] {failure}")
    raise typer.Exit(code=1)


@app.command()
def report(
    user: str = typer.Option(default_user(), "--user", "-u"),
    state_opt: Path | None = typer.Option(None, "--state"),
    top: int = typer.Option(10, "--top", help="Rows to show in each table."),
) -> None:
    """Show mastery and ability reports from saved state."""
    repo = JsonStateRepository(_resolve_state(state_opt, user))
    state = repo.load()

    stats = summary(state)
    if stats["attempts"] == 0:
        console.print("[yellow]No practice recorded yet. Run `konjugaton practice`.[/]")
        return

    console.print(
        f"[bold]Overall[/] · vocab seen: {stats['vocab_seen']} · skills: {stats['skills_seen']} "
        f"· attempts: {stats['attempts']} · accuracy: {stats['accuracy']:.0%}"
    )
    catalog_obj = CatalogService.default().catalog

    mastery_table = Table(title=f"Weakest {top} (vocab x knowledge)")
    for col in MASTERY_COLUMNS:
        mastery_table.add_column(col)
    for row in mastery_rows(state, catalog_obj)[:top]:
        mastery_table.add_row(*row.as_cells())
    console.print(mastery_table)

    ability_table = Table(title="Skill abilities (theta, lowest first)")
    for col in ABILITY_COLUMNS:
        ability_table.add_column(col)
    for row in ability_rows(state)[:top]:
        ability_table.add_row(*row.as_cells())
    console.print(ability_table)


# --- config sub-app --------------------------------------------------------


@config_app.command("path")
def config_path_cmd(user: str = typer.Option(default_user(), "--user", "-u")) -> None:
    """Print the path to the user's config.yaml."""
    console.print(str(config_path(user)))


@config_app.command("show")
def config_show(user: str = typer.Option(default_user(), "--user", "-u")) -> None:
    """Print the user's current settings as YAML."""
    settings = load_settings(user)
    text = yaml.safe_dump(settings.model_dump(), allow_unicode=True, sort_keys=False)
    console.print(text, markup=False)


def _coerce(value: str) -> bool | int | float | str:
    low = value.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    with contextlib.suppress(ValueError):
        return int(value)
    with contextlib.suppress(ValueError):
        return float(value)
    return value


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Dotted key, e.g. grading.similarity_tolerance"),
    value: str = typer.Argument(..., help="New scalar value (true/false/int/float/string)."),
    user: str = typer.Option(default_user(), "--user", "-u"),
) -> None:
    """Set a single scalar setting (lists/maps: edit config.yaml or use the TUI)."""
    settings = load_settings(user)
    data = settings.model_dump()
    parts = key.split(".")
    node: object = data
    for part in parts[:-1]:
        if not isinstance(node, dict) or part not in node:
            console.print(f"[red]unknown key:[/] {key}")
            raise typer.Exit(code=1)
        node = node[part]
    leaf = parts[-1]
    if not isinstance(node, dict) or leaf not in node:
        console.print(f"[red]unknown key:[/] {key}")
        raise typer.Exit(code=1)
    node[leaf] = _coerce(value)
    data["preset"] = "custom"
    try:
        updated = Settings.model_validate(data)
    except ValidationError as exc:
        console.print(f"[red]invalid value for {key}:[/]\n{exc}")
        raise typer.Exit(code=1) from exc
    save_settings(updated, user)
    console.print(f"[green]set[/] {key} = {node[leaf]!r}  →  {config_path(user)}")


@config_app.command("preset")
def config_preset(
    name: str = typer.Argument(..., help=f"One of: {', '.join(PRESET_NAMES)}"),
    user: str = typer.Option(default_user(), "--user", "-u"),
) -> None:
    """Apply a named preset bundle to the user's config."""
    if name not in PRESET_NAMES:
        console.print(f"[red]unknown preset[/] {name!r}; choose: {', '.join(PRESET_NAMES)}")
        raise typer.Exit(code=1)
    save_settings(apply_preset(name), user)
    console.print(f"[green]applied preset[/] {name}  →  {config_path(user)}")


@app.command()
def tui(
    user: str = typer.Option(default_user(), "--user", "-u"),
    state_opt: Path | None = typer.Option(None, "--state"),
) -> None:
    """Launch the interactive terminal UI (Textual)."""
    try:
        from konjugaton.tui.app import run_tui  # noqa: PLC0415
    except ModuleNotFoundError as exc:
        console.print(
            "[yellow]The TUI needs Textual, which isn't installed.[/]\n"
            "Install it with:  [bold]pip install 'konjugaton[tui]'[/]"
        )
        raise typer.Exit(code=1) from exc
    run_tui(user=user, state_file=_resolve_state(state_opt, user))


@app.command()
def assess(
    count: int = typer.Option(20, "--count", "-n", help="Max questions."),
    user: str = typer.Option(default_user(), "--user", "-u"),
    minutes: float = typer.Option(0.0, "--minutes", help="Time box in minutes (0 = none)."),
    tense: TenseMood | None = typer.Option(None),
    register: Register | None = typer.Option(None),
    seed: int | None = typer.Option(None),
    state_opt: Path | None = typer.Option(None, "--state"),
    save: bool = typer.Option(True, "--save/--no-save"),
) -> None:
    """Assessment mode: time-bounded, breadth-guided, NO per-item feedback.

    Picks questions to cover as many distinct skills as possible (vs `practice`,
    which is depth-guided/adaptive). Reports a score + coverage at the end only.
    """
    settings = load_settings(user)
    service = PracticeService.default(seed=seed, settings=settings)
    logger = LearnerLogger(settings, user)

    selection = AxisSelection(
        tense_moods=(tense,) if tense else (), registers=(register,) if register else ()
    )
    items = service.build_assessment(selection, count)
    if not items:
        console.print("[yellow]No exercises match those filters.[/]")
        raise typer.Exit(code=1)

    repo = JsonStateRepository(_resolve_state(state_opt, user))
    state = repo.load()
    deadline = time.monotonic() + minutes * 60 if minutes > 0 else None

    correct = 0
    answered = 0
    skills: set[str] = set()
    for i, item in enumerate(items, start=1):
        if deadline is not None and time.monotonic() >= deadline:
            console.print("[dim]— time up —[/]")
            break
        console.print(f"\n[bold]{i}.[/] {item.prompt}")
        console.print(f"   [dim]{item.lemma_hint} · {item.task}[/]")
        given = _read_answer(item)  # graded silently — no feedback in assessment
        theta_before = state.ability(item.skill)
        p_correct = irt.probability_correct(theta_before, item.irt)
        information = irt.information(theta_before, item.irt)
        ewma_before = state.cell(item.coordinate.lemma, item.coordinate.knowledge).ewma
        graded = service.grade(item, given)
        state.record(item, correct=graded.is_correct, timestamp=_now())
        logger.log_response(
            _response_record(
                user,
                item,
                graded,
                p_correct,
                information,
                theta_before,
                state.ability(item.skill),
                ewma_before,
                state.cell(item.coordinate.lemma, item.coordinate.knowledge).ewma,
                item.skill.verb_class.value,
            )
        )
        answered += 1
        correct += int(graded.is_correct)
        skills.add(item.skill.key)

    console.print(
        f"\n[bold]Assessment[/] · answered {answered} · correct {correct} "
        f"· accuracy {correct / answered:.0%} · skills covered {len(skills)}"
        if answered
        else "\n[yellow]No answers recorded.[/]"
    )
    if save and answered:
        repo.save(state)
        logger.snapshot_state(state)
        logger.log_session(
            {"user": user, "items": answered, "correct": correct, "via": "assessment"}
        )
        console.print(f"[dim]State + logs → {logger.directory}[/]")


@app.command()
def profile(user: str = typer.Option(default_user(), "--user", "-u")) -> None:
    """Show the learner background (set with `konjugaton config set learner.<field> <v>`)."""
    learner = load_settings(user).learner
    table = Table(title=f"Learner profile — {user}")
    table.add_column("field")
    table.add_column("value")
    for field_name, value in learner.model_dump().items():
        table.add_row(field_name, str(value) if value not in ("", 0, 0.0) else "[dim](unset)[/]")
    console.print(table)
    console.print("[dim]set e.g.:  konjugaton config set learner.l1 en --user " + user + "[/]")


@app.command()
def migrate(
    user: str = typer.Option(default_user(), "--user", "-u"),
    all_users: bool = typer.Option(False, "--all", help="Migrate every profile."),
    apply: bool = typer.Option(False, "--apply", help="Write changes (default: dry-run)."),
) -> None:
    """Migrate learner event logs to the current schema (dry-run unless --apply)."""
    from konjugaton.migrate import (  # noqa: PLC0415 - maintenance tool, keep off the hot path
        SCHEMA_VERSION,
        discover_event_logs,
        migrate_file,
        migrate_user,
    )

    reports = (
        [migrate_file(p, apply=apply) for p in discover_event_logs()]
        if all_users
        else [migrate_user(user, apply=apply)]
    )
    title = f"Migrate events.jsonl → schema v{SCHEMA_VERSION}" + ("" if apply else "   [DRY-RUN]")
    table = Table(title=title)
    for col in ("file", "records", "to migrate", "unparseable", "status", "backup"):
        table.add_column(col)
    pending = False
    for r in reports:
        if not r.exists:
            continue
        pending = pending or r.migrated > 0
        status = "written" if r.written else ("up-to-date" if r.migrated == 0 else "dry-run")
        table.add_row(
            str(r.path),
            str(r.total),
            str(r.migrated),
            str(r.unparseable),
            status,
            str(r.backup) if r.backup else "—",
        )
    console.print(table)
    if not apply and pending:
        console.print(
            "[yellow]dry-run — re-run with [bold]--apply[/] to write (a .bak is kept).[/]"
        )


def _force_utf8_io() -> None:
    """Emit UTF-8 no matter the ambient locale (minimal containers, env -i).

    Critical for konjugaton: Devanagari is multi-byte UTF-8, so an ASCII locale
    would otherwise crash on the first प्रॉम्प्ट.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(ValueError, OSError):
                reconfigure(encoding="utf-8")


def main() -> None:
    """Console-script entry point."""
    _force_utf8_io()
    app()


if __name__ == "__main__":
    main()
