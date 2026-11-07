# Harnessia Core

[Español](README-ES.md)

Harnessia creates focused AI workspaces called Spaces. A Space is a pseudo-project that keeps the rules and capabilities for AI collaboration separate from the real project and its supporting documentation. You choose what each Space needs; Harnessia validates it and generates the configuration for OpenCode and Claude Code.

Capabilities stay in their original Sources. Harnessia links to them instead of copying or rewriting them.

**The entire Harnessia Core project is in `Core/`, including these operating guides and the license.** Git lives one level above it. Only `Core/` and the root `.gitignore` are versioned; every other sibling directory is excluded by default. Unless stated otherwise, all paths and commands in this guide are relative to `Core/`, not the Git repository root.

`Core/docs/` contains both maintained product references and local working material. Reference files and `docs/adr/` are versioned; private inputs, reviewed local outputs and work in progress belong to `docs/sources/`, `docs/deliverables/` and `docs/wip/` respectively. **`Core/.gitignore` excludes those three subdirectories; their contents are never published.** IDE settings belong to ignored `Core/.idea/`. Capability repositories and generated client projections also stay in Core.

## Concepts at a glance

| Concept | Meaning |
| --- | --- |
| **Core** | The central Harnessia project in `Core/`. It contains the engine, shared context, shared Sources and documentation. |
| **Instance** | A registered local container for related Spaces, Sources and optional shared context. It can live anywhere and does not need to be a Git repository. |
| **Space** | A purpose-specific AI collaboration pseudo-project inside one Instance. It defines the rules and capabilities for working with a real project and its supporting documentation. |
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

Context is inherited in that order; later layers have higher priority. The repository versions the `Core/` project, not local Instances. Instances are registered in ignored `.harnessia/instances.yaml` inside Core; only explicitly registered Instances are discovered. Core includes no installed Instances or bindings to external workspaces; names and paths below are examples.

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

- `INSTANCE` is the registered, case-sensitive Instance name, such as `Work`.
- `INSTANCE_PATH` is its absolute directory, such as `$HOME/Harnessia/Work`. The template deliberately has no default for this value.
- `SPACE` is the lowercase Space ID, such as `atlas`.

The script is fail-closed and performs the following sequence:

- If the Instance directory is absent, `instance-create` creates its minimum structure and registers it. If the directory already exists, `instance-attach` validates and registers it without recreating it. An existing directory must already be a valid Instance.
- `sources-clone` installs missing pinned Sources so the curator can consider their skills.
- If the Space path is absent, `space-create` creates and prepares it. A regular directory without `SPACE.md` is initialized by `space-attach`, which adds only missing Harnessia files and preserves all prior content. A path with a regular `SPACE.md` is already initialized and creation is skipped. Other collisions are preserved and reported.
- `space-configure` requires the registered Instance and existing Space. It opens the curator, recommends skills and purpose-specific MCP servers, applies only an explicitly approved selection and prepares both client projections. It can recommend missing servers but never installs or authenticates them.
- `check` finishes with a read-only validation of the target Instance.

`INSTANCE` and `SPACE` are not interchangeable: use `INSTANCE=Work SPACE=atlas`, not the reverse. Instance names are case-sensitive; Space IDs use lowercase letters, digits and single hyphens.

The template may also be run without copying it by supplying all values through the environment:

```sh
INSTANCE=Work INSTANCE_PATH="$HOME/Harnessia/Work" SPACE=atlas \
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

`make prepare INSTANCE=<id> SPACE=<space-id>` generates or updates the client configuration for one existing Space. It resolves the rules inherited from Core, its Instance and the Space, validates the capability selection in `SPACE.md` and generates the Harnessia-managed OpenCode and Claude Code projections for that Space. It does not create the Space, modify the linked real project or documentation, update Sources or start an AI client.

`make space-create INSTANCE=<id> SPACE=<space-id>` creates a new Space only when its target directory is absent. It writes a minimal `SPACE.md`, an empty maintained `SOUL.md` and a minimal `INSTRUCTIONS.md`, then validates and prepares the Space. If creation or preparation fails, Harnessia removes the new scaffold; it never overwrites an existing path.

`make space-attach INSTANCE=<id> SPACE=<space-id>` initializes an existing regular directory that has no `SPACE.md`. It preserves all existing content, accepts existing regular `SOUL.md` and `INSTRUCTIONS.md` files, creates only the missing maintained Space files and prepares both client projections. A collision with a symlink or non-regular maintained file is rejected before writing. If preparation fails, Harnessia removes only the files added by the attachment.

`make space-configure INSTANCE=<id> SPACE=<space-id>` opens OpenCode Mini with the restricted `space-curator` agent. Harnessia gives it a temporary JSONL index of valid skills found only in Core Sources and the target Instance's Sources; it never scans another Instance or searches for external Sources. The curator reads the current purpose, asks only for missing context, recommends the smallest sufficient selection, explains optional and rejected alternatives, and waits for explicit approval of the exact `skills` entries.

After OpenCode Mini exits successfully, Harnessia accepts only a change to the `skills` field of the target `SPACE.md`, validates the proposed references and prepares both OpenCode and Claude Code projections. No approved change means no preparation. Interruption, a non-zero client exit, an invalid selection or a change outside `skills` restores the original Definition and preserves the prior projections. Each run keeps `SPACE.before.md`, `skills.jsonl` and, when applicable, `SPACE.proposed.md` as ignored diagnostic material under `.harnessia/space-configure/<Instance>/<Space>/<run-id>/` inside Core. Set `HARNESSIA_OPENCODE` only when the executable is not the `opencode` found on `PATH`.

`INSTANCE` is the case-sensitive registered Instance name. Harnessia preserves its capitalization: an Instance registered as `Work`, for example, is selected with `INSTANCE=Work`. Reattaching the same path with only a capitalization change migrates a legacy lowercase name.

For the usual whole-system regeneration, use `make prepare-all`; it always validates Core and every registered Space before replacing any generated client configuration. To regenerate only the Spaces in one Instance, use `make prepare-instance INSTANCE=<id>`. `make check` validates without writing and may still use `INSTANCE=<id>` to limit its scope, while `make verify` runs the tests, Source checks and the full read-only check. Preparation does not update Sources, change linked content or start an AI client; only `space-configure` starts OpenCode Mini for its explicit interactive curation session. Logs go to ignored `logs/` inside Core.

## Source maintenance

Core and each Instance own their Sources. Reproducible Git Sources are pinned in the owner's `SOURCES.yaml`; local unversioned Sources may also exist but cannot be restored by `sources-clone`.

| Task | Command |
| --- | --- |
| Clone missing pinned Sources | `make sources-clone` |
| Validate Sources and everything that uses them | `make sources-check` |
| Show local and known upstream changes | `make sources-status` |
| Fetch remotes without changing worktrees | `make sources-fetch` |
| Fast-forward the reviewed revisions | `make sources-pull` |
| Validate, prepare and record changed revisions | `make sources-reconcile` |

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

## What a Space contains

A Space is not the real project. It is the pseudo-project you open in the AI client so the collaboration rules remain controlled and separate from working content. Inside it, `SOUL.md` records explicit durable preferences about collaboration style and judgment, `INSTRUCTIONS.md` defines operational rules, `SPACE.md` selects capabilities from `core/<source-id>` and `instance/<source-id>`, and the optional `project` and `documentation` links connect the real project and its supporting documentation.

Harnessia resolves active context from lowest to highest priority: Core SOUL, optional Instance SOUL, Space SOUL, Core instructions, optional Instance instructions, Space instructions and optional Space memory. The later layer wins when guidance conflicts. A Space SOUL is a maintained regular file that may start empty; Harnessia never rewrites it, and an AI client should update it only when the user explicitly requests a durable preference.

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
