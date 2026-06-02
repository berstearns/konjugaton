"""CLI-level gates, including the locale/encoding regression.

German umlauts (ä/ö/ü/ß) are multi-byte UTF-8, so an ASCII locale would crash on
the first *Präsens* if the app didn't force UTF-8 IO. These tests reproduce the
worst case (ASCII IO) in a subprocess so it's caught fast, in pytest, on every
commit — not only in the slower binary CI job.
"""

from __future__ import annotations

import os
import subprocess
import sys


def _run(*args: str, **env_overrides: str) -> subprocess.CompletedProcess[bytes]:
    env = {**os.environ, **env_overrides}
    return subprocess.run(
        [sys.executable, "-m", "konjugaton", *args],
        capture_output=True,
        env=env,
        check=False,
    )


def test_emits_utf8_under_ascii_locale() -> None:
    result = _run("catalog", PYTHONIOENCODING="ascii", LC_ALL="C", LANG="C", PYTHONUTF8="0")
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    # An umlaut byte proves UTF-8 was actually emitted (Präsens/Präteritum/… in the
    # tense-mood axis). \xc3 leads the Latin-1 Supplement (ä=\xc3\xa4, ü=\xc3\xbc).
    assert b"\xc3" in result.stdout


def test_selfcheck_exits_zero_even_with_ascii_io() -> None:
    result = _run("selfcheck", PYTHONIOENCODING="ascii", LC_ALL="C")
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert b"selfcheck passed" in result.stdout


def test_unknown_command_exits_nonzero() -> None:
    result = _run("does-not-exist")
    assert result.returncode != 0
