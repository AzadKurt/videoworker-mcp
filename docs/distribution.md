# Distribution and directory submissions

## Initial release: GitHub

Canonical repository: <https://github.com/AzadKurt/videoworker-mcp>.
The release workflow tests Windows/Linux, builds the package, verifies installed
stdio discovery and uploads a wheel, sdist and SHA256SUMS on version tags.
README uses a versioned wheel URL; installation does not require Git or checkout.

## PyPI follow-up

PyPI is not published yet. The owner must sign in to their own PyPI account,
enable the account's required two-factor authentication, and configure a pending
Trusted Publisher for the new project. Do not put a long-lived upload token in
the repository or send credentials in chat.

Suggested pending publisher: project `videoworker-mcp`, GitHub owner `AzadKurt`,
repository `videoworker-mcp`, workflow `publish-pypi.yml`, environment `pypi`.
The workflow below must be added only when that matching publisher is configured;
there is currently no automated PyPI upload from tag pushes.

The publisher workflow should use `workflow_dispatch`, a protected `pypi`
environment, `id-token: write`, a reviewed version tag and a pinned
`pypa/gh-action-pypi-publish` action. Build/check that exact tag, run the package
tests and installed stdio check, then publish through OIDC. Check PyPI metadata,
hashes and clean installation before changing README to `pip install` / `uvx`.
Check name availability at setup time; no name reservation is claimed here.

Official instructions:
<https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/>.

## Glama: open-source server listing

`glama.json` declares maintainer `AzadKurt` using Glama's published schema.
Submit via <https://glama.ai/mcp/servers> → Add Server:

- Repository: `https://github.com/AzadKurt/videoworker-mcp`
- Name: `videoworker`
- Description: `FFmpeg for AI agents: upload authorized local video, audio or
images, run remote processing jobs, and download results. Supports scoped API
keys, allowance checks, cancellation and result deletion.`
- Website: `https://videoworker.dev/mcp`
- Categories where offered: Image & Video Processing; Developer Tools.

A JSON ownership file is not a submitted/accepted listing. Glama runs its own
indexing/quality checks. The local server needs a private key file and authorized
media folders; do not publish test credentials, mount a personal media directory
for a directory crawler or imply the hosted backend is self-hostable.

The hosted OAuth connector is a separate connection type. Any authenticated
third-party health check needs its own least-privilege test account; no owner or
customer token should be shared with a directory.

Official submission guidance: <https://glama.ai/mcp/faq>.

## Official MCP Registry

The hosted remote endpoint can be registered without publishing a PyPI package.
`server.json` describes that **hosted** service, not stdio package installation.
The optional registry workflow uses GitHub Actions OIDC (no reusable credential),
and is dispatched separately after the hosted endpoint/metadata are checked.
The local connector's PyPI entry can follow once the package is actually released.

Official guidance:
<https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/remote-servers.mdx>
and <https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/github-actions.mdx>.

## Posts and advertising

Use the website as the primary conversion destination; link the public repository
as a secondary option for builders who want local file tools or source code.
Do not change an already running ad merely to add another destination. A new
organic post can link the release without changing campaign spend.
