# MCP Selection Guide

Use this guide when configuring a Space, both in Core maintenance sessions and in
`space-curator`. Recommend the smallest set that serves the Space's recurring
tasks, including useful servers that are not yet configured. No MCP is mandatory.

## Selection and availability

1. Read the Space purpose, tasks and risk constraints before recommending tools.
2. Use exact IDs from the sanitized `mcp-inventory.json` when present. It records
   only server names and observed statuses from OpenCode's Core location, not
   credentials, endpoints, configuration bodies or raw connection errors.
3. Distinguish **connected**, **needs authentication**, **failed**, **disabled**,
   **pending**, **unknown** and **not configured**. The latter applies only when
   inventory retrieval succeeded; it does not prove a package is uninstalled.
   Availability in Core does not establish the effective configuration of a Space.
4. Explain why and when to use each server, prerequisites, possible charges and
   data/write risks. Separate required tools, optional tools and installation gaps.
5. Get approval for the exact `mcp` list before editing `SPACE.md`. Installation,
   authentication and external writes need separate approval. The restricted
   curator cannot perform them; the maintenance assistant can handle approved setup.

## Starting points

These are recommendations, not auto-installed dependencies or verified connection
statuses. Names below are suggested IDs; reuse the user's configured ID if different.
Check current official documentation before installation. This list is not exhaustive;
label suggestions outside it unverified until their provenance and requirements are checked.

| Suggested ID | Recurring need and usage trigger | Prerequisites, cost and risk | Official reference |
| --- | --- | --- | --- |
| `playwright` | Browser testing, reproducing UI bugs, checking rendered pages | Local browser/runtime; prefer isolated profiles. Pages and screenshots may contain sensitive data; browser actions can change remote systems. | [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) |
| `context7` | Current library documentation and API examples | Remote service; check current key/plan requirements. Do not send proprietary code or credentials in queries. | [Context7](https://github.com/upstash/context7) |
| `perplexity` | Current web research, sourced comparisons and deeper investigations | API key and usage billing. Queries leave the machine; deep research may be slower and costlier. | [Perplexity MCP](https://github.com/perplexityai/modelcontextprotocol) |
| `github` | Repository issues, pull requests and remote code context | GitHub authorization and repository scopes. Remote writes/publication require explicit approval; local Git alone may be sufficient. | [GitHub MCP](https://github.com/github/github-mcp-server) |
| `sentry` | Production errors, traces and incident investigation | Sentry account authorization; production events can contain personal or sensitive data. | [Sentry MCP](https://docs.sentry.io/product/sentry-mcp/) |
| `mcp-atlassian` | Jira work tracking and Confluence knowledge | Authorized Jira/Confluence access; some operations may consume Rovo credits. Verify the actual provider: an installed ID may name a third-party implementation. Restrict write scopes and private content. | [Atlassian Remote MCP](https://support.atlassian.com/atlassian-ai-gateway/docs/get-started-with-the-atlassian-remote-mcp-server) |
| `slack` | Finding decisions and team context | Workspace authorization and policy approval. Conversations may contain personal information; sending messages requires explicit approval. | [Slack MCP](https://docs.slack.dev/ai/slack-mcp-server/) |
| `cloudflare` | Cloudflare-specific operational tasks | Select the appropriate official server and account scopes. Infrastructure changes can affect production and billing. | [Cloudflare MCP](https://developers.cloudflare.com/agents/model-context-protocol/mcp-servers-for-cloudflare/) |

Do not infer a server's provenance or capabilities from its ID alone. The inventory
does not inspect implementations. Do not replace working connections just to match
these suggested names, and do not install a server solely because it is listed.

## Projection and client limits

Configure approved servers once in OpenCode's user or managed configuration. Keep
credentials outside Harnessia. List only approved IDs in `SPACE.md`, for example:

```yaml
mcp:
  - playwright
  - context7
```

Use `mcp: []` for none. Run `make prepare INSTANCE=<id> SPACE=<space-id>` from Core
after manual changes; successful `space-configure` edits prepare automatically.
Never hand-edit generated permissions. An allowed server is available for the
agent to choose, not a requirement to call it on every task.

OpenCode denies unselected MCP integrations and allows selected IDs in order.
Selection neither installs nor authenticates a server, and stronger managed policy
can still restrict access. Ordinary preparation does not query client availability.

Claude deliberately projects **zero MCP servers and denies MCP tool calls**, even
when OpenCode's selection is nonempty. No dummy process or tool schema is added.
To exclude inherited servers as well, start Claude from the Space with:

```sh
claude --setting-sources project --strict-mcp-config --mcp-config .claude/harnessia-mcp.json
```

Normal Claude startup may still load inherited MCP servers. An empty file or a
dummy server does not suppress that inheritance by itself. The strict empty catalog
adds no MCP tools; this is not a promise of zero total session tokens or a measured
token-saving benchmark. See the [Space Definition](space-definition.md) for the contract.

The optional `uv run --no-project --with 'PyYAML>=6,<7' python -m tests.smoke_claude_mcp`
smoke verifies generated Claude output against the installed CLI using synthetic
content and control requests only, with no user prompt or model request. It also
checks that a project MCP server is excluded by the strict empty catalog.
