# Release 0.1.0

The standalone connector lives at <https://github.com/AzadKurt/videoworker-mcp>.
The owner selected MIT on 3 November 2026. This release contains no private
backend, credentials, databases, runtime logs or media.

## Release checklist

1. Run pytest, Ruff lint/format and parse all example JSON/TOML files.
2. Build the sdist and wheel, inspect contents and run `twine check`.
3. Install in a clean environment outside the source checkout; initialize actual
   stdio and discover all eight tools. Never use a customer key in CI.
4. Push the reviewed commit and tag `v0.1.0`. GitHub Actions tests Windows/Linux,
   builds and checks the package, then publishes artifacts and SHA256SUMS.
5. Verify public wheel installation from README. Never replace a released tag or
   artifact with different bytes; issue a new version.

## Channels and limits

GitHub releases are the initial distribution channel. PyPI is not published yet.
It needs the owner's PyPI account and a project-bound Trusted Publisher; see
[distribution notes](docs/distribution.md). Do not advertise a bare PyPI install
until a real publication is verified.

`glama.json` identifies the maintainer; it alone does not create a directory
listing. On 3 November the repository was submitted and Glama confirmed review
submission; the listing was then approved and verified publicly at
<https://glama.ai/mcp/servers/AzadKurt/videoworker-mcp>. The hosted endpoint is published separately
in the official MCP Registry as `io.github.AzadKurt/videoworker` version 0.1.0.

## Verified publication

The `v0.1.0` workflow passed on Linux and Windows and published the release wheel,
source archive and SHA256SUMS. Clean installation from the public GitHub wheel
URL, outside the source checkout, initialized real stdio and discovered all
eight tools without API calls. Wheel SHA256:
`5a0deb24a1c04305b23da22b702144f4018b071487bfdbddf9ab98add60d23fa`.

Release workflow: <https://github.com/AzadKurt/videoworker-mcp/actions/runs/41554034517>.
Registry publication: <https://github.com/AzadKurt/videoworker-mcp/actions/runs/41554034889>.

Tests cover controlled HTTP/file operations, real MCP SDK discovery and actual
stdio from an installed package. They do not claim every client/version, large
production transfers or every OAuth client was manually accepted. Hosted OAuth
has separately been tested with Codex and cannot access local paths.

The initial connector was split from the private service repository. From this
release, this repo is the source of truth for the distributed connector. The
service's older local copy remains for compatibility; shared fixes must be
ported deliberately until the service imports a versioned package. The hosted
remote MCP component is separate.
