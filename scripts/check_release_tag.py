"""Refuse to put mismatched package bytes under a release tag."""

import sys
import tomllib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
if sys.argv[1:] != ["v" + project["project"]["version"]]:
    raise SystemExit("Release tag does not match pyproject.toml version")
print("Release tag matches package version.")
