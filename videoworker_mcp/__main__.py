"""Run with python -m videoworker_mcp; configuration comes only from environment."""

import argparse
import sys
from importlib.metadata import version

from .client import Connector, Settings
from .server import build_server


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run videoworker's local MCP connector over stdio. FFmpeg runs remotely.",
        epilog="Setup and private key-file examples: https://github.com/AzadKurt/videoworker-mcp",
    )
    parser.add_argument(
        "--version", action="version", version=version("videoworker-mcp")
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate local configuration without connecting or starting MCP",
    )
    options = parser.parse_args(argv)
    try:
        settings = Settings.from_env()
    except (ValueError, OSError):
        print(
            "videoworker MCP: set VIDEO_WORKER_API_KEY_FILE to a private key file and "
            "VIDEO_WORKER_UPLOAD_ROOT / VIDEO_WORKER_DOWNLOAD_ROOT to existing absolute folders. "
            "See https://github.com/AzadKurt/videoworker-mcp#quick-start",
            file=sys.stderr,
        )
        return 2
    if options.check:
        print(
            "Local configuration is valid. API credentials and allowance have not been checked."
        )
        return 0
    connector = Connector(settings)
    try:
        build_server(connector).run(transport="stdio")
    finally:
        connector.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
