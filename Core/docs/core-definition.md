# Core Definition Reference

`HARNESSIA.md` is the portable capability selection for sessions that maintain Core. It is not a Space Definition and does not affect the capability selection inside any Space.

The maintained selection includes Caveman chat and relevant Matt Pocock maintenance methods. `AGENTS.md` routes maintenance sessions to the shared task/capability contract in `INSTRUCTIONS.md`; capability availability alone does not prove activation or authorize the actions described by an imported workflow.

## Schema

`HARNESSIA.md` is Markdown with a required YAML frontmatter mapping:

```yaml
---
version: 1
skills:
  - source: core/mattpocock-skills
    path: skills/engineering/codebase-design
---
```

| Field | Contract |
| --- | --- |
| `version` | Required integer `1`. |
| `skills` | Required ordered list. An empty list is valid. |
| `skills[].source` | A Core Source identified as `core/<source-id>`. Instance Sources are rejected. |
| `skills[].path` | A skill directory relative to its Source. It must contain `SKILL.md` directly. |

References contain exactly `source` and `path`. Absolute paths, home expansion, parent segments, missing targets, duplicate effective IDs and resolved boundary escapes fail validation. Effective skill IDs come from `SKILL.md` frontmatter.

Agents, commands, MCP servers, memory and custom Core capabilities are not part of version 1.

## Effective Core Context

The engine resolves the Core Definition into one client-agnostic `EffectiveCoreContext`. It contains the validated definition and imported skill inventory, with no OpenCode or Claude format decisions. Core has no custom capability overlay.

## OpenCode adapter

The adapter writes relative links under `.opencode/skills/<skill-id>`. The directory carries a Harnessia ownership marker. Existing manual content or an invalid marker blocks preparation without being replaced.

OpenCode can discover Core skills from a descendant directory. Prepared Spaces remain isolated because their generated permissions deny all skills before allowing only their effective IDs.

## Claude adapter

The adapter generates one isolated plugin under `.claude/skills/harnessia-core/`. Its `skills/` directory contains relative links only to the selected Source skill directories; capability bodies remain in their Sources. The generated manifest enumerates the same effective IDs. Claude loads the plugin only when Core is the primary directory. Opening a Space directly does not inherit it from Core. Claude applies its normal one-time project trust approval before loading a local plugin; non-interactive commands report the plugin as suppressed until that approval exists.

Source-owned Claude manifests and standard plugin components are not inputs to this projection and cannot broaden it. Harnessia validates the selected skills themselves, then owns the wrapper manifest and links. It does not copy skill bodies, register a marketplace or install a global plugin.

## Preparation and Source lifecycle

`make prepare-core` validates both adapters before replacing either projection. A validation or write failure preserves both previous projections. Aggregate preparation validates every selected Consumer before writing the first one. `make prepare-all` always includes Core and every registered Space; `make prepare-instance INSTANCE=<id>` includes only the Spaces in that Instance. `make sources-check`, `make sources-status` and `make sources-reconcile` include Core as a Consumer; `make verify` performs read-only tests and checks.
