"""Run with python -m videoworker_mcp; configuration comes only from environment."""

import sys

from .client import Connector, Settings
from .server import build_server


def main():
    try:
        connector = Connector(Settings.from_env())
    except (ValueError, OSError):
        print(
            "videoworker MCP: configure service origin, private API key and existing media folders.",
            file=sys.stderr,
        )
        return 2
    try:
        build_server(connector).run(transport="stdio")
    finally:
        connector.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
