"""Binary entry point for Nuitka / PyInstaller.

Compiling a standalone script (rather than the package's ``__main__.py``) avoids
the package-``__main__`` ambiguity Nuitka warns about, and keeps the compiled
entry trivially simple: import the Typer app and run it.
"""

from __future__ import annotations

from konjugaton.cli.app import main

if __name__ == "__main__":
    main()
