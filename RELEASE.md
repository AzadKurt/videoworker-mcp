# Release candidate — 2 November 2026

Source copied from the private service repository's `39eaccc` connector package
and `tests/test_mcp_connector.py`. No service backend, credentials, private config,
databases, media or runtime logs are included. This checkout has its own `main`
branch and does not have a Git remote.

Suggested public repository name: `videoworker-mcp`. Suggested license: MIT for
our own connector code. A license has not yet been issued in this candidate;
choose the copyright holder and complete dependency-license review before public
release. Until then this is a review candidate, not an advertised open-source
release. Dependencies are installed separately, not vendored here.

Before publishing:

1. Review the exact tracked file list and the license decision.
2. Review dependency licenses for the pinned MCP SDK and HTTPX plus transitive
   dependencies; preserve required notices if any third-party code is distributed.
3. Test installation in a clean environment and real client discovery plus a tiny
   authorized production job. Resolve the connector's current 50-MiB download cap
   or clearly retain/document it. Do not claim all MCP clients were tested.
4. Establish one source of truth: until the split is released, connector fixes
   originate in the service repo and must be carried here deliberately. After
   release, import a versioned package into the service instead of editing two copies.
5. Publish the reviewed repository; package-registry release is a separate step.

The aim is transparent, installable agent tooling and useful examples. Public code
does not imply free hosted processing, expose hosted OAuth/auth internals, or
prove demand. Do not publish merely to imitate other companies.
