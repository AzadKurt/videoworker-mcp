"""Parse examples without loading a user's real MCP configuration."""

import json
import tomllib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for path in sorted((root / "examples").iterdir()):
    if path.suffix == ".json":
        json.loads(path.read_text(encoding="utf-8"))
    elif path.suffix == ".toml":
        tomllib.loads(path.read_text(encoding="utf-8"))
print("Example JSON and TOML are valid.")
