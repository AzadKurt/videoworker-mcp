# Dependency licenses

Review snapshot: 3 November 2026, Python 3.12 on Windows. Runtime dependencies are installed separately by pip; the connector wheel does not vendor them. Linux/macOS resolve a platform-specific subset. Versions below describe the review environment, not a lockfile or a promise about future resolutions.

| Distribution              | Reviewed version | Declared license |
| ------------------------- | ---------------- | ---------------- |
| annotated-types           | 0.8.0            | MIT              |
| anyio                     | 4.15.1           | MIT              |
| attrs                     | 26.1.0           | MIT              |
| certifi                   | 2026.10.23       | MPL-2.0          |
| click                     | 8.5.0            | BSD-3-Clause     |
| h11                       | 0.16.0           | MIT              |
| httpcore                  | 1.0.9            | BSD-3-Clause     |
| httpcore2                 | 2.16.0           | BSD-3-Clause     |
| httpx                     | 0.28.1           | BSD-3-Clause     |
| httpx2                    | 2.16.0           | BSD-3-Clause     |
| idna                      | 3.20             | BSD-3-Clause     |
| jsonschema                | 4.26.0           | MIT              |
| jsonschema-specifications | 2025.9.1         | MIT              |
| mcp                       | 2.3.0            | MIT              |
| mcp-types                 | 2.3.0            | MIT              |
| opentelemetry-api         | 1.45.2           | Apache-2.0       |
| pydantic                  | 2.14.2           | MIT              |
| pydantic_core             | 2.50.2           | MIT              |
| PyJWT                     | 2.15.1           | MIT              |
| python-multipart          | 0.0.33           | Apache-2.0       |
| pywin32                   | 312              | PSF              |
| referencing               | 0.37.0           | MIT              |
| rpds-py                   | 2026.9.1         | MIT              |
| sse-starlette             | 3.6.0            | BSD-3-Clause     |
| starlette                 | 1.10.0           | BSD-3-Clause     |
| truststore                | 0.10.5           | MIT              |
| typing-inspection         | 0.4.4            | MIT              |
| typing_extensions         | 4.16.0           | PSF-2.0          |
| uvicorn                   | 0.54.0           | BSD-3-Clause     |

License declarations were read from installed distribution metadata. Keep each dependency's own license/notices when redistributing it. Certifi declares MPL-2.0 for its certificate bundle; this release does not modify or bundle it. pywin32 is Windows-only. The project's MIT license applies to the connector's original code, not to dependencies.
