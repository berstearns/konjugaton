"""Bundled reference data as an importable package.

Being a real package (not just a directory) is what lets
``importlib.resources.files("konjugaton._data")`` resolve the YAML both in a
normal install and inside a Nuitka/PyInstaller binary, where only recognised
packages are bundled.
"""
