# Harnessia Core

[Español](README-ES.md)

Harnessia creates Spaces for AI collaboration. Each Space keeps its rules and capabilities separate from the projects and documentation it supports. You choose what each Space needs; Harnessia validates the selection and generates the configuration for OpenCode and Claude Code.

Capabilities stay in their original Sources. Harnessia links to them instead of copying or rewriting them.

**The entire Harnessia Core project is in `Core/`, including these operating guides and the license.** Git lives one level above it. Only `Core/` and the root `.gitignore` are versioned; every other sibling directory is excluded by default. Unless stated otherwise, all paths and commands in this guide are relative to `Core/`, not the Git repository root.

`Core/docs/` contains both maintained product references and local working material. Reference files and `docs/adr/` are versioned; private inputs, reviewed local outputs and work in progress belong to `docs/sources/`, `docs/deliverables/` and `docs/wip/` respectively. **`Core/.gitignore` excludes those three subdirectories; their contents are never published.** IDE settings belong to ignored `Core/.idea/`. Capability repositories and generated client projections also stay in Core.

## Concepts at a glance

| Concept | Meaning |
| --- | --- |
| **Core** | The central Harnessia project in `Core/`. It contains the engine, shared context, shared Sources and documentation. |
| **Instance** | A local container for related Spaces, Sources and optional shared configuration and context. It can live anywhere and need not be a Git repository. |
| **Space** | A purpose-specific AI collaboration environment inside an Instance. Open it directly in the AI client. |
| **Project Workspace** | An optional directory inside a Space for one project or initiative, such as `work/<project-id>/`. |
| **Source** | A repository or maintained directory that provides reusable AI capabilities. Core or one Instance owns it. |
| **Capability** | A reusable skill, agent or command selected from a Source without copying it. |
| **Definition** | The client-agnostic capability selection: `HARNESSIA.md` for Core or `SPACE.md` for a Space. |
| **Consumer** | Core or a Space when it selects Capabilities from Sources. |
| **Client Projection** | Generated OpenCode or Claude Code configuration for one Consumer. |

Core, Instance and Space form the context hierarchy, not a nested filesystem layout:

```text
Core
└── Instance
    └── Space
```

Context is inherited in that order; later layers have higher priority. The repository versions `Core/`, not local Instances. An Instance can exist without being registered. The CLI discovers Instances only through the ignored `.harnessia/instances.yaml` registry inside Core. Core ships without Instances or local working links; names and paths below are examples.

## Get started

You need `make`, Git and [`uv`](https://docs.astral.sh/uv/). Generated configurations support OpenCode 2.1.4 or newer and Claude Code 2.1.220 or newer. The interactive capability configuration command additionally requires the `opencode` CLI and a terminal.

From the cloned repository root, enter `Core/` before running any Harnessia command:

```sh
cd Core
```

The Makefile and setup template are inside `Core/`, not at the Git repository root. Do not repeat `cd Core` if your terminal is already in that directory.

### Quick setup

Core provides the commented [`templates/space-setup.sh`](templates/space-setup.sh) template for the complete flow. Copy it into ignored working material, edit the three configuration values at the top and run it from there:

```sh
mkdir -p docs/wip
cp templates/space-setup.sh docs/wip/space-setup.sh
${EDITOR:-vi} docs/wip/space-setup.sh
bash docs/wip/space-setup.sh
```

The configuration section explains each value:

- `INSTANCE` is the case-sensitive Instance name. The template defaults to `Default`; the engine gives that name no special meaning.
- `INSTANCE_PATH` is the Instance's absolute directory. Set it explicitly; the template has no path default.
- `SPACE` is the lowercase Space ID. The template defaults to `atlas`.

The script is fail-closed and performs the following sequence:

- If the Instance directory is absent, `instance-create` creates its minimum structure and registers it. If the directory already exists, `instance-attach` validates and registers it without recreating it. An existing directory must already be a valid Instance.
- `sources-clone INSTANCE=<id>` installs missing pinned Sources from Core and the selected Instance so the curator can consider their skills.
- If the Space path is absent, `space-create` creates and prepares it. A regular directory without `SPACE.md` is initialized by `space-attach`, which adds only missing Harnessia files and preserves all prior content. A path with a regular `SPACE.md` is already initialized and creation is skipped. Other collisions are preserved and reported.
- `space-configure` requires the registered Instance and existing Space. It opens the curator, recommends skills and purpose-specific MCP servers, applies only an explicitly approved selection and prepares both client projections. It can recommend missing servers but never installs or authenticates them.
- `check` finishes with a read-only validation of the target Instance.

`INSTANCE` names the container; `SPACE` names a Space inside it. Space IDs use lowercase letters, digits and single hyphens.

The template may also be run without copying it by supplying all values through the environment:

```sh
INSTANCE=Default INSTANCE_PATH="$HOME/Harnessia/Default" SPACE=atlas \
  bash templates/space-setup.sh
```

To use a Space, open its directory directly in OpenCode or Claude Code. Harnessia does not provide or require a launcher.

## Everyday commands

| What you want to do | Command |
| --- | --- |
| Prepare the Core project for Harnessia maintenance sessions | `make prepare-core` |
| Prepare one Space | `make prepare INSTANCE=<id> SPACE=<space-id>` |
| Prepare every Space in one Instance | `make prepare-instance INSTANCE=<id>` |
| Prepare Core and every registered Space | `make prepare-all` |
| Create and register an Instance | `make instance-create INSTANCE=<id> INSTANCE_PATH=<path>` |
| Attach and register an Instance | `make instance-attach INSTANCE=<id> INSTANCE_PATH=<path>` |
| Create and prepare a Space | `make space-create INSTANCE=<id> SPACE=<space-id>` |
| Attach and prepare an existing Space directory | `make space-attach INSTANCE=<id> SPACE=<space-id>` |
| Interactively configure a Space's skills and MCP selection | `make space-configure INSTANCE=<id> SPACE=<space-id>` |
| Validate without changing generated files | `make check [INSTANCE=<id>]` |
| List registered Instances | `make instance-list` |
| Run the tests | `make test` |
| Run the complete read-only local verification | `make verify` |

`make prepare-core` is specifically for working on Harnessia itself. It reads the Core Definition in `HARNESSIA.md`, validates its selected maintenance skills and generates Core's client configuration: relative links under `.opencode/skills/` and one Claude plugin under `.claude/skills/harnessia-core/`. It does not prepare any Space.

`make prepare INSTANCE=<id> SPACE=<space-id>` resolves the active context and validates the capability selection in `SPACE.md` before generating both client projections for one existing Space. It does not create the Space, modify linked content, update Sources or start an AI client.

`make space-create INSTANCE=<id> SPACE=<space-id>` creates a new Space only when its target directory is absent. It writes a minimal `SPACE.md`, an empty maintained `SOUL.md` and a minimal `INSTRUCTIONS.md`, then validates and prepares the Space. If creation or preparation fails, Harnessia removes the new scaffold; it never overwrites an existing path.

`make space-attach INSTANCE=<id> SPACE=<space-id>` initializes an existing regular directory that has no `SPACE.md`. It preserves all existing content, accepts existing regular `SOUL.md` and `INSTRUCTIONS.md` files, creates only the missing maintained Space files and prepares both client projections. A collision with a symlink or non-regular maintained file is rejected before writing. If preparation fails, Harnessia removes only the files added by the attachment.

`make space-configure INSTANCE=<id> SPACE=<space-id>` opens OpenCode Mini with the restricted `space-curator` agent. Harnessia provides a JSONL index of valid skills from Core and the owning Instance, a sanitized MCP name/status inventory and the [MCP guide](docs/mcp-guide.md). The curator reads the purpose, asks only for missing context, recommends a minimal selection with optional/rejected alternatives and useful MCP installation gaps, and waits for explicit approval of the exact `skills` and `mcp` entries. It neither searches external skill Sources nor installs or authenticates MCP servers.

After OpenCode Mini exits successfully, Harnessia accepts changes only to `skills` and `mcp` in the target `SPACE.md`, validates the selection and prepares both client projections. No approved change means no preparation. Interruption, non-zero client exit, invalid selection, changes outside those fields or preparation failure restore the original Definition and prior projections. Each run keeps `SPACE.before.md`, `skills.jsonl`, sanitized `mcp-inventory.json` and, when applicable, `SPACE.proposed.md` under ignored `.harnessia/space-configure/<Instance>/<Space>/<run-id>/` inside Core. Inventory failure means unknown availability, not no servers. Set `HARNESSIA_OPENCODE` only when the executable is not the `opencode` found on `PATH`.

`INSTANCE` must match the capitalization in the registry. Reattaching the same path with only a capitalization change updates its registered spelling.

For the usual whole-system regeneration, use `make prepare-all`; it always validates Core and every registered Space before replacing any generated client configuration. To regenerate only the Spaces in one Instance, use `make prepare-instance INSTANCE=<id>`. `make check` validates without writing and may still use `INSTANCE=<id>` to limit its scope, while `make verify` runs the tests, Source checks and the full read-only check. Preparation does not update Sources, change linked content or start an AI client; only `space-configure` starts OpenCode Mini for its explicit interactive curation session. Logs go to ignored `logs/` inside Core.

## Source maintenance

Core and each Instance own their Sources. Reproducible Git Sources are pinned in the owner's `SOURCES.yaml`; local unversioned Sources may also exist but cannot be restored by `sources-clone`.

| Task | Command |
| --- | --- |
| Clone missing pinned Sources | `make sources-clone [INSTANCE=<id>]` |
| Validate Sources and everything that uses them | `make sources-check` |
| Show local and known upstream changes | `make sources-status` |
| Fetch remotes without changing worktrees | `make sources-fetch` |
| Fast-forward the reviewed revisions | `make sources-pull` |
| Validate, prepare and record changed revisions | `make sources-reconcile` |

With `INSTANCE=<id>`, cloning is limited to Core and that registered Instance. Without it, cloning includes all registered Instances. The other Source commands operate across all registered owners.

The update flow is explicit:

```sh
make sources-fetch
make sources-status
make sources-pull
make sources-reconcile
make verify
```

`sources-pull` stops before changing anything if a Source is dirty, detached, divergent or missing its upstream. Harnessia never resets or discards Source work.

Core selects Vercel's `find-skills` for ecosystem retrieval and Codesigils' `skill-discovery` for evidence-based candidate inspection. These capabilities support future maintenance conversations; they do not extend the local-only `space-configure` curator. The [repository instructions](AGENTS.md#skill-discovery) keep discovery separate from installation and require approved additions to follow the pinned Source lifecycle. Installing a Source does not activate all its skills or its plugin integrations; each Consumer selects only its declared capabilities.

Pinned Core Sources also include Docker's `docker-skills` and Microsoft's `microsoft-playwright-cli` for optional container and browser workflows. Consumers select their exact capabilities independently; cloning these repositories does not install Docker, the Playwright CLI, browser binaries or dependencies, start services, or authorize cleanup. Runtime installation and compatibility checks remain separate, explicit operations.

Google Chrome's `googlechrome-modern-web-guidance` Source provides `skills/modern-web-guidance` for modern HTML, CSS, browser APIs, accessibility and compatibility. Consumers select it independently. Its local guides follow the Source pin; its npm CLI does not, and downloading or executing a reviewed runtime requires separate approval.

## What a Space contains

An Instance may keep its collaboration rules in its own `INSTRUCTIONS.md`. Only that Instance's Spaces inherit them. The curator reads those rules when present; skill and MCP selections still require exact approval. New Spaces start with empty selections until configured.

A Space is separate from the projects it supports. `SOUL.md` records explicit durable collaboration preferences, `INSTRUCTIONS.md` defines operational rules and `SPACE.md` selects capabilities from `core/<source-id>` and `instance/<source-id>`. Optional [working links](docs/space-definition.md#working-links) connect external projects and documentation.

Harnessia resolves active context from lowest to highest priority: Core SOUL, optional Instance SOUL, Space SOUL, optional Instance instructions, Space instructions and optional Space memory. Core maintenance rules in `AGENTS.md` are not inherited by Spaces. Ordering does not enforce semantic conflict resolution or runtime permissions. A Space SOUL is a maintained regular file that may start empty; Harnessia never rewrites it, and an AI client should update it only when the user explicitly requests a durable preference.

`INDEX.md`, `SPACE.md`, READMEs and documentation remain navigation, definitions or reference material; Harnessia does not activate every Markdown file as an instruction. Core runs the orchestration and generates client-relative paths, so Core and Instances may live in unrelated filesystem locations.

OpenCode supports selected skills, agents, commands and MCP allowlists. Claude Code supports the shared instructions and skills; OpenCode agents and commands are not translated. Claude project settings deny MCP tools, but strict isolation from inherited MCP servers requires starting Claude from the Space with:

```sh
claude --setting-sources project --strict-mcp-config --mcp-config .claude/harnessia-mcp.json
```

MCP connections are configured once in OpenCode's user or managed configuration; each Space explicitly selects IDs under `mcp` in `SPACE.md`. The curator uses a sanitized name/status inventory and the [MCP selection guide](docs/mcp-guide.md), including recommendations for servers not configured yet. Manual changes require `make prepare INSTANCE=<id> SPACE=<space-id>`. Claude always receives an empty MCP catalog, even with a nonempty OpenCode selection: no dummy server or MCP tool schema is added.

The linked project and documentation remain external working content. Harnessia validates their boundaries but does not inspect them or treat their files as instructions or capabilities.

## Documentation

- [Documentation index](docs/INDEX.md)
- [Current architecture](docs/DESIGN.md)
- [Core Definition](docs/core-definition.md)
- [Space Definition](docs/space-definition.md)
- [Glossary](docs/GLOSSARY.md)
- [Dated implementation and maintenance record](docs/PROJECT.md)

## License

Copyright (c) 2026 Samuel Vicent. Harnessia Core is licensed under the [GNU General Public License, version 3 only](LICENSE) (`GPL-3.0-only`), without warranty. The full license is in `Core/LICENSE`. Third-party Sources retain their own licenses; Core's license does not relicense their content.

## Credits

Inspiration song: [Amnesia — Ibiza (1988)](https://www.youtube.com/watch?v=KSjLGw9CbGE&list=RDKSjLGw9CbGE)
