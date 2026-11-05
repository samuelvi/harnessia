# Glossary

Harnessia maintains reusable AI capability sources and projects explicit selections into isolated, purpose-specific Spaces.

**Core** — The complete Harnessia project in the repository's `Core/` directory, including context composition, Source resolution, validation, client projection, operating guides, license and ignored local state. Git metadata and the repository-boundary ignore policy live in the parent root; Core owns all project-local ignore rules. Sibling local content is not versioned.
_Avoid_: Instance, Space

**Engine** — The implementation inside Core that validates Definitions, resolves effective contexts and generates Client Projections.
_Avoid_: Core when referring to the whole system

**Local Working Material** — Private inputs, reviewed local outputs and work in progress under `Core/docs/sources/`, `Core/docs/deliverables/` and `Core/docs/wip/`. Those three subdirectories are ignored, while maintained product references elsewhere in `Core/docs/` remain versioned.
_Avoid_: Core documentation, capability Sources

**Instance** — A local container explicitly registered with Core that contributes optional context and contains purpose-specific Spaces. Its registered name is case-sensitive and preserves capitalization; Work and Customer-A are examples, not fixed engine concepts or included workspaces.
_Avoid_: Profile, Space

**Source** — A capability-providing repository or maintained directory owned by Core or one Instance. Definitions identify it independently from its physical checkout path.
_Avoid_: Package, installed capability

**Source Owner** — Core or the single Instance whose catalog, manifest and lifecycle contain a Source. Ownership controls which Spaces may select it.
_Avoid_: Profile, visibility

**Source Manifest** — The owner-local `SOURCES.yaml` declaration of expected reproducible Git Sources and their exact revisions. Present unversioned Sources are discovered without manifest entries.
_Avoid_: Source registry, capability selection

**Capability** — A reusable AI asset referenced at its original Source location. Harnessia supports portable Agent Skills and OpenCode-native agents and commands.
_Avoid_: Copied asset, generated capability

**Space** — A purpose-specific AI collaboration pseudo-project inside one Instance. It defines the maintained rules and Capabilities for working with a real project and supporting documentation, which may be linked while remaining external working content.
_Avoid_: Real project, generated workspace, profile

**Space Definition** — The maintained `SPACE.md` inside a Space. Its YAML frontmatter is the sole client-agnostic capability selection.
_Avoid_: `INDEX.md`, client configuration

**Space Configuration Assistant** — The explicit OpenCode Mini session started by `space-configure` to curate one Space's `skills` field from valid Core and owning-Instance candidates. Harnessia, not the agent, validates and prepares the approved result.
_Avoid_: General work launcher, automatic Source discovery, autonomous editor

**Core Definition** — The maintained `HARNESSIA.md` in Core. It selects maintenance skills only from Core Sources.
_Avoid_: Alternate names, global Space Definition

**Effective Core Context** — The client-agnostic validated Core skill inventory resolved from the Core Definition and its Sources.
_Avoid_: OpenCode configuration, Claude plugin

**Effective Space Context** — The ordered active Markdown and validated Capability inventories resolved for one Space. Markdown follows Core → Instance → Space priority within its defined role; later paths have higher priority.
_Avoid_: Every Markdown file, Client Projection

**Consumer** — Core or a Space when selecting Capabilities from Sources.
_Avoid_: Space when referring to both Core and Spaces

**Attachment** — The explicit operation that registers an existing Instance path with Core, installs machine-local ignore policy and initializes missing or legacy symlinked Space SOUL files without replacing maintained ones.
_Avoid_: Registration as a separate lifecycle operation

**Client Projection** — Generated client-native configuration derived from an effective Core or Space context without copying or rewriting Capability content.
_Avoid_: Adapter, compiled capability tree

**Space SOUL** — The required maintained `SOUL.md` inside one Space. It may start empty and records only explicit durable user preferences about collaboration style and judgment; it is loaded after Core and optional Instance SOUL context.
_Avoid_: Generated Core link, operating instructions, automatic learning

**Space Memory** — The optional bounded `MEMORY.md` maintained inside one Space. It holds verified durable facts, decisions and one resumable checkpoint, not a transcript or document index.
_Avoid_: Global memory, knowledge base
