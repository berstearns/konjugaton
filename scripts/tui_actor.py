#!/usr/bin/env python
"""Scripted TUI action-taker — spin up konjugaton's real Textual TUI and act in it.

This is the "literal" simulator: it boots the actual TUI headlessly via Textual's
``App.run_test()`` Pilot harness, then for each item reads the prompt, types an
answer into the input widget, and presses Enter — exactly as a human would. The
agent is an *oracle*: it types the correct answer, deliberately wrong every Nth.

Because the TUI logs through LearnerLogger, the run produces a real events.jsonl
generated *through the UI* (not the CLI), under $KONJUGATON_HOME/<user>/.

    python scripts/tui_actor.py [user] [--errors-every N] [--per-item-pause S]
"""

from __future__ import annotations

import argparse
import asyncio

from textual.widgets import Input

from konjugaton.settings import state_path
from konjugaton.tui.app import KonjugatonApp


async def drive(user: str, errors_every: int, pause: float) -> tuple[int, int]:
    app = KonjugatonApp(user=user, state_file=state_path(user))
    answered = 0
    async with app.run_test() as pilot:
        await pilot.pause()
        nxt = app._settings.shortcuts.next  # config-driven "next item" key
        total = len(app._items)
        for i in range(total):
            if app._index >= total:
                break
            item = app._items[app._index]
            wrong = errors_every and (i % errors_every == errors_every - 1)
            app.query_one("#answer", Input).value = "zzz" if wrong else item.answer
            await pilot.press("enter")  # grade + record (no auto-advance)
            await pilot.pause(0.1)
            await pilot.press(nxt)  # go forward to the next item
            await pilot.pause(pause)
            answered += 1
        await pilot.pause(0.3)
        return answered, app._correct


def main() -> None:
    parser = argparse.ArgumentParser(description="Drive the konjugaton TUI headlessly.")
    parser.add_argument("user", nargs="?", default="kela-tui")
    parser.add_argument("--errors-every", type=int, default=5)
    parser.add_argument("--per-item-pause", type=float, default=0.3)
    args = parser.parse_args()

    answered, correct = asyncio.run(drive(args.user, args.errors_every, args.per_item_pause))
    print(f"TUI actor: user={args.user!r} answered={answered} correct={correct}")
    print(f"logs → {state_path(args.user).parent}")


if __name__ == "__main__":
    main()
