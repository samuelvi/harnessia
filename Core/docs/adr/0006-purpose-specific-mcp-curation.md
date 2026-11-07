# ADR 0006: Purpose-Specific MCP Curation

Status: accepted on 2026-11-07. Extends [ADR 0005](0005-local-assisted-skill-curation.md).

## Context

The skill-only curator cannot recommend the integrations needed by a Space's
purpose. A global MCP connection is neither a per-Space authorization nor a reason
to expose every tool. Claude's rejection of nonempty MCP selections also prevents
joint preparation of a valid OpenCode allowlist.

## Decision

Extend `space-configure` to recommend skills and MCP servers and accept approved
changes to those two fields only. Keep skill discovery local. Give the curator a
maintained MCP guide and a best-effort sanitized OpenCode inventory containing only
IDs and observed statuses. Missing useful services can be recommended, but neither
configuration nor installation is inferred from a recommendation. The curator
cannot call MCP tools, install, authenticate or change client configuration.

Keep endpoints and secrets outside Harnessia. Availability failures do not block
curation or ordinary preparation, and no raw connection errors are persisted.
Unsupported suggestions need current official-documentation checks in a separate
maintenance session before installation.

Project the approved MCP IDs into OpenCode's default-deny policy. Claude accepts
the Definition but always projects zero MCP servers and denies MCP calls. Use its
documented strict empty-catalog startup to exclude inherited servers. A dummy
server adds a runtime dependency without solving inheritance and is unnecessary.

## Consequences

- Skills and MCP selections share the existing approval and rollback transaction.
- MCP use remains optional, scoped to purpose and explicit per Space.
- Core inventory is an observation, not a guarantee of a Space's effective access.
- Installation and authentication need separate approval outside the curator.
- Claude remains MCP-free under strict startup; this does not add Claude MCP support.
- No token benchmark or claim of zero total session context is implied.
