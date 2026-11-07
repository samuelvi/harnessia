# Space Definition Reference

`SPACE.md` is Markdown with required YAML frontmatter. Preparation rejects unknown top-level and capability-reference fields.

## Schema

| Field | Contract |
| --- | --- |
| `version` | Integer `2`. |
| `skills` | Required list of mappings containing exactly `source` and `path`. An empty list is valid. |
| `skills[].source` | `core/<source-id>` or `instance/<source-id>`. The latter resolves only inside the owning Instance. |
| `skills[].path` | Skill directory relative to its Source. The directory must contain `SKILL.md`. |
| `agents` | Optional list using the same `source` and `path` mapping. |
| `agents[].path` | OpenCode agent Markdown file relative to its Source. Its filename is the agent ID. |
| `commands` | Optional list using the same `source` and `path` mapping. |
| `commands[].path` | OpenCode command Markdown file relative to its Source. Its filename is the command ID. |
| `mcp` | Optional ordered list of logical MCP server IDs. OpenCode projects the selection; Claude always projects an empty catalog and denies MCP calls, without rejecting the selection. |

Every Source reference and capability path uses POSIX separators. Absolute paths, home expansion, parent segments, missing targets, cross-Instance access and resolved boundary escapes are rejected.

The Space ID is its directory name. The owning Instance comes from the registered layout. `SPACE.md` does not repeat either identity; `id`, `instance` and `profile` are unsupported fields.

## Skill contract

Imported and custom skills use the Agent Skills directory contract:

- exact file name `SKILL.md`;
- frontmatter fields `name` and `description`;
- `name` uses 1–64 lowercase alphanumeric or hyphen characters;
- a custom skill's `name` matches its directory; imported skill directories may differ from their effective frontmatter name;
- `description` is non-empty and at most 1024 characters.

Imported IDs must be unique. Valid custom skills under `capabilities/custom/skills/` activate automatically and replace imported skills with the same ID. Supporting files may exist below a skill directory; category directories above a skill are invalid.

### Assisted skill and MCP configuration

`make space-configure INSTANCE=<id> SPACE=<space-id>` is the interactive authoring path for the `skills` and `mcp` fields. It requires a terminal, OpenCode Mini and a regular, non-symlinked target `SPACE.md`. Harnessia generates a per-run JSONL catalog containing valid skills only from Core and the owning Instance; other Instances, external searches and unregistered skill Sources are outside the assistant's scope. Catalog entries include the exact `source` and `path`, effective ID, description, definition file, current-selection state and whether the Source is pinned or local. A best-effort, 15-second `opencode api get /api/mcp` request in Core adds only validated server IDs and known statuses to `mcp-inventory.json`; failure means unknown availability, not an empty installation. Raw output and credentials are never persisted. This request may start OpenCode's background service through normal CLI discovery.

The restricted `space-curator` agent uses the Space purpose and asks only for missing task, deliverable, technology, workflow and risk context. It shortlists skills from the index, reads only finalist `SKILL.md` bodies and follows the [MCP selection guide](mcp-guide.md). It proposes a minimal required set plus optional and rejected alternatives, including useful MCP servers not configured yet, with availability, usage triggers, authentication, cost and data/write risks. It must receive approval for the exact lists before editing. It cannot use shell, web, MCP tools or subagents, install or authenticate servers; OpenCode asks before every edit. MCP installation remains a separate approved maintenance operation.

The assistant may change only `skills` and `mcp`; the Markdown body and every other frontmatter field must remain semantically unchanged. It does not prepare projections itself. Once OpenCode Mini exits with status zero, Harnessia validates the proposal and prepares both clients. No change is a successful cancellation and performs no preparation. A missing TTY or executable fails before launch. Interruption, non-zero exit, deletion, invalid Definition, invalid capability selection, a change outside `skills` and `mcp` or preparation failure restores the original `SPACE.md`; transactional projection generation preserves the previous client output.

The curator's file scope is instruction-enforced: its read/search tools and external-directory access are broad, and every edit asks for approval. The deterministic guard validates only the target Definition; it is not a filesystem sandbox and cannot restore unrelated edits. Do not approve changes to other files in this session.

Ignored run evidence lives under `Core/.harnessia/space-configure/<Instance>/<Space>/<run-id>/`, separate from versioned product documentation and private working drafts. Every started run contains `SPACE.before.md`, `skills.jsonl` and sanitized `mcp-inventory.json`; a changed Definition also produces `SPACE.proposed.md`, or a marker when the assistant removed or made the file unreadable. `HARNESSIA_OPENCODE` may name an alternate executable; otherwise Harnessia resolves `opencode` from `PATH`.

## Agent contract

Selected agents remain unchanged at their Source. Each file requires YAML frontmatter with a non-empty `description` and `mode` set to `primary`, `subagent`, or `all`. The lowercase Markdown filename is its effective ID.

Imported IDs must be unique. Custom agents under `capabilities/custom/agents/<agent-id>.md` are discovered automatically and replace imported agents with the same ID.

## Command contract

Imported commands and custom commands under `capabilities/custom/commands/` are validated. A custom command replaces an imported command with the same ID. Markdown bodies remain native OpenCode prompt templates; frontmatter may use `description`, `agent`, `model`, `subagent`, or deprecated `subtask`. Native shell substitutions produce a warning.

## Space directory

A Space is an AI collaboration pseudo-project, not the real project itself. It keeps maintained rules, capability selection and generated client configuration together while optional links connect the external project and its supporting documentation.

| Path | Contract |
| --- | --- |
| `SPACE.md` | Maintained Definition and capability selection. |
| `INSTRUCTIONS.md` | Maintained Space instructions, loaded after Core and optional Instance instructions. |
| `SOUL.md` | Required maintained regular file for explicit durable preferences about Space-specific collaboration style and judgment. It may be empty. |
| `MEMORY.md` | Optional maintained memory, limited to 32 KiB and loaded after instructions. |
| `INDEX.md` | Optional local navigation. It is not active context or capability selection. |
| `capabilities/custom/` | Optional local skills, agents and commands. |
| `project`, `documentation` | Optional machine-local symlinks to the real project and its supporting documentation. These external working directories remain separate from the Space; Instance ignore policy excludes the links from a future repository. |
| `opencode.jsonc`, `CLAUDE.md`, `.opencode/`, `.claude/` | Generated Client Projections; do not edit. |

`make space-create INSTANCE=<id> SPACE=<space-id>` creates this minimum maintained structure inside an available registered Instance: a version 2 `SPACE.md` with an empty skill selection, an empty `SOUL.md` and a minimal `INSTRUCTIONS.md`. It then validates and prepares the new Space. The target must not exist; Harnessia never merges with or overwrites an existing path. A creation or preparation failure removes the newly created scaffold and leaves no partial Space.

`make space-attach INSTANCE=<id> SPACE=<space-id>` initializes and prepares an existing regular directory that has no `SPACE.md`. Existing content and regular maintained `SOUL.md` or `INSTRUCTIONS.md` files are preserved; only the absent maintained files are added. Symlinked or non-regular maintained paths fail before any write. Preparation failure removes only files created by the attachment and restores the directory's prior state.

Core, Instance and Space SOUL files and Core, Instance and Space `INSTRUCTIONS.md` files must be maintained regular files when required or present. A Space SOUL may start empty. Record only explicit durable user preferences about collaboration style and judgment, update it only at the user's explicit request and never infer preferences from ordinary conversation. `instance attach` atomically replaces a missing or symlinked Space SOUL with an empty regular file while preserving every existing regular Space SOUL.

Optional `MEMORY.md` must be a maintained regular file. It cannot be symlinked, generated or external, and preparation never creates, summarizes or modifies it. Keep only verified durable facts, explicit decisions and the latest useful checkpoint; current code, tests and user direction take precedence. Replace stale entries and never store transcripts, secrets, credentials, personal data, absolute paths or speculation. Loading memory adds no MCP, process, network request or model call.

Optional `project` and `documentation` links must resolve to directories outside the Space. Preparation validates only their boundaries and never inspects or activates AI files in linked content. Broken links fail validation; they are machine-local bindings and must be repaired after their targets move.

## Effective Space

Preparation resolves one client-agnostic effective Space. Its active Markdown is ordered from lowest to highest priority: Core SOUL, optional Instance SOUL, Space SOUL, Core instructions, optional Instance instructions, Space instructions and optional Space memory. Client adapters consume the same ordered paths without changing maintained content.

This inheritance is role-based, not a scan of every Markdown file. `INDEX.md` is navigation, `SPACE.md` is a Definition, and README or linked documentation is reference material. They never become active instructions merely because they exist at more than one level.

## OpenCode projection

The generated `opencode.jsonc` contains:

1. Core SOUL, optional Instance SOUL, Space SOUL, Core instructions, optional Instance instructions, Space instructions, then optional Space memory;
2. relative Source catalog paths in imported-first, custom-last order;
3. ordered skill permissions denying `*`, then allowing each effective skill ID;
4. ordered integration policies denying `mcp:*`, then allowing each selected `mcp:<server-id>`.

Selected agents and commands are projected as relative symlinks under `.opencode/agents/` and `.opencode/commands/`. Generated directories are replaced only when they carry the Harnessia ownership marker.

## Claude Code projection

`CLAUDE.md` imports the effective instruction files in canonical order. `.claude/skills/` contains one relative directory link per effective skill. Generated settings enable strict sandbox behavior, deny MCP tools and exclude instruction discovery beneath linked `project` and `documentation` paths.

Every Space receives an empty `.claude/harnessia-mcp.json`, even when `mcp` selects servers for OpenCode. Claude Code CLI and Desktop discover the instruction and settings projection automatically; the empty catalog is supplied explicitly for strict CLI startup. Generated permissions deny MCP tool calls, although inherited servers may still load. Strict CLI isolation uses `--setting-sources project --strict-mcp-config --mcp-config .claude/harnessia-mcp.json`. No dummy server or MCP tool schema is generated. Claude has no exact project skill allowlist, so personal and nested skills may remain visible. The Core plugin is not inherited when a Space is the primary directory. OpenCode agents and commands are not translated.

Preparation validates all inputs before writing. Aggregate preparation validates every requested Consumer before writing any of them. Each Consumer then atomically replaces only files and directories carrying Harnessia ownership markers; failure in either client restores that Consumer's prior projections. Manual client content is preserved and blocks only conflicting output.

## MCP and environment

Harnessia selects MCP servers by ID only. It does not define endpoints, install servers, authenticate accounts, or store credentials. Configure each selected server in OpenCode's user or managed configuration, then list its ID under `mcp` in `SPACE.md`.

OpenCode configuration may obtain secrets through `{env:NAME}` or `{file:path}`. Harnessia never reads, sources, generates, copies, or logs `.env` files. Missing credentials appear as OpenCode or MCP connection failures rather than preparation failures.

Global, system, managed or OpenCode Console policy has higher authority than generated Space policy and may restrict or override it.

Ordered MCP allowlists require OpenCode 2.1.4 or newer. After upgrading OpenCode, restart its background service before verifying a Space.

## Diagnostics

Each run mirrors `INFO` and `WARNING` lines to the terminal and one UTC-timestamped file under `Core/logs/`, ignored by Git. Validation failures identify the affected path and rule, stop generation, and preserve any previous projection.
