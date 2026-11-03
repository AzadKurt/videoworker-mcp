"""Initialize an installed connector over actual stdio; never call the API."""

import asyncio
import sys
import tempfile
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters


async def check():
    with tempfile.TemporaryDirectory(prefix="videoworker-stdio-") as directory:
        root = Path(directory).resolve()
        key = root / "key"
        key.write_text("fk_install_smoke_not_a_real_key")
        key.chmod(0o600)
        server = StdioServerParameters(
            command=sys.executable,
            args=["-m", "videoworker_mcp"],
            env={
                "VIDEO_WORKER_API_URL": "https://videoworker.dev",
                "VIDEO_WORKER_API_KEY_FILE": str(key),
                "VIDEO_WORKER_UPLOAD_ROOT": str(root),
                "VIDEO_WORKER_DOWNLOAD_ROOT": str(root),
            },
        )
        async with Client(server) as client:
            tools = await client.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "get_usage",
                "list_jobs",
                "upload_file",
                "create_job",
                "get_job",
                "download_result",
                "cancel_job",
                "delete_job_outputs",
            }
    print(
        "Installed stdio connector initialized; all eight tools discovered. No API calls."
    )


if __name__ == "__main__":
    asyncio.run(check())
