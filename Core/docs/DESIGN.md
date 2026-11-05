# Engine Design

The published Git tree contains only `Core/` and the root `.gitignore`. All Harnessia project files, including READMEs, the license and local material, belong to Core. The root ignore policy only defines that boundary: it allows Core and itself but excludes every other sibling by default, including current and future local Instances. `Core/.gitignore` owns all project-local exclusions: IDE configuration, runtime state, logs, installed Sources, generated client projections, credentials, caches and the private `docs/sources/`, `docs/deliverables/` and `docs/wip/` subdirectories. Maintained references elsewhere in `Core/docs/` remain versioned; there is no separate root docs directory or duplicate root project metadata.

`Core/app/` contains the complete preparation engine. The physical layout separates the product and its local runtime state from private working material:

```text
Harnessia/
├── .gitignore          # Repository publication boundary only
└── Core/
    ├── .gitignore      # All project-local exclusions
    ├── app/            # Preparation engine
    ├── tests/          # Engine tests and smoke fixture
    ├── docs/
    │   ├── INDEX.md    # Maintained, versioned references and ADRs
    │   ├── sources/    # Ignored original inputs, not capability repositories
    │   ├── deliverables/ # Ignored reviewed local outputs
    │   └── wip/        # Ignored plans, drafts and backups
    ├── LICENSE         # GNU GPL version 3 only
    ├── .harnessia/     # Ignored registry and configuration diagnostics
    ├── logs/           # Ignored runtime logs
    └── .idea/          # Ignored IDE settings
```

Run all Make commands from `Core/`. `layout.py` separates the Core and Instance locations consumed by the engine. A `CoreLayout` owns the Core project directory, shared context, Source catalog and local runtime paths. Logs use `Core/logs/`; assisted-configuration diagnostics use `Core/.harnessia/space-configure/`. An `InstanceLayout` owns one Instance directory and its Spaces. Instances do not require their own Git repository and may live at arbitrary filesystem paths. The Core → Instance → Space hierarchy describes context precedence, not filesystem nesting.

`instances.py` owns the strict machine-local registry at ignored `Core/.harnessia/instances.yaml`. A missing registry means no Instances are registered. Core includes no installed Instances or external workspace bindings; registration is an explicit local operation. Registry names are case-sensitive and preserve their capitalization. Reattaching one path with a case-only name change migrates its legacy spelling, while attaching it under a different name remains an error. Paths are absolute, and absent paths remain registered and visible as missing. An available Instance is a regular directory with a regular `spaces/` directory. Registry writes are atomic. `instance_lifecycle.py` creates minimal Instances and attaches existing ones. Attachment initializes a missing or legacy symlinked Space `SOUL.md` as an empty regular file, preserves every existing regular Space SOUL and installs Instance ignore policy without excluding maintained SOUL files. `space_lifecycle.py` creates and prepares a minimal Space at an absent target or explicitly attaches an existing regular directory without a Definition. Space attachment preserves prior content, creates only missing maintained files and rolls back only those additions on failure; creation still rejects every existing target.

`core.py` owns the portable `HARNESSIA.md` contract and `space.py` owns `SPACE.md`. `context.py` validates working-content boundaries and resolves active Markdown in Core → Instance → Space priority order. `effective.py` combines those paths with capability inventories into a client-agnostic `EffectiveCoreContext` or `EffectiveSpace`. Each client adapter turns an effective context into a projection plan; `base.py` applies the plans for one Consumer in a fail-closed transaction.

`orchestration.py` is the discovery and planning seam shared by check, preparation and Source reconciliation. It discovers registered Spaces once and builds a `ConsumerPlan` containing effective IDs and both client projection plans. Aggregate preparation validates every requested Consumer plan before writing the first one, then retains per-Consumer transactional replacement and rollback. `prepare.py` owns application and logging; `check.py` validates the same plans without writing.

`source_resolver.py` is the Source seam used by capability resolution. Definitions name `core/<id>` or `instance/<id>`; callers do not know physical checkout paths. The resolver maps Core Sources to `Core/sources/<id>` and Instance Sources to the owning `<instance>/sources/<id>`, then enforces catalog and capability boundaries. No definition can address another Instance.

`source_bootstrap.py` owns the strict owner-local `SOURCES.yaml` contract, exact-revision cloning, read-only Consumer coherence checks and explicit reconciliation. Version 2 manifests declare Source IDs rather than storage paths. `source_catalog.py` represents identity as owner plus Source ID and maps it to the owner catalog, including missing selected Sources. `source_git.py` is the shared Git command and repository-discovery seam used by bootstrap, status and updates. Missing or invalid registered Instances fail checks, status, updates and reconciliation instead of being treated as having no Sources or Consumers. Clone never changes an existing directory; fetch never changes a worktree; pull never performs network access or reconciliation.

`skill_catalog.py` builds the deterministic catalog for assisted Space configuration. It traverses only `Core/sources/` and the target Instance's `sources/`, validates each discovered `SKILL.md` with the same contract used by preparation, and records its logical Source, relative path, effective ID, description, absolute definition file, current-selection flag and pinned or local Source state. Invalid skill definitions are skipped rather than exposed as candidates. It never asks global Instance discovery for another catalog.

`space_assistant.py` owns the interactive configuration transaction behind `space configure`. It validates the target, requires a TTY and an OpenCode executable, snapshots `SPACE.md`, writes the catalog under ignored `Core/.harnessia/space-configure/` evidence, and launches `opencode mini --agent space-curator`. The maintained agent may read and search local files, but shell, web access and subagents are denied; every edit asks for human approval. After Mini exits, the engine rejects any semantic change outside `skills`, validates and prepares an approved selection, and restores the original Definition on interruption, non-zero exit, invalid output or preparation failure. Projection application retains its independent rollback, so failed curation leaves both the Definition and prior client output intact.

`check` optionally targets one Instance; without a target it covers Core and every registered Instance and fails when any expected directory is unavailable. `make verify` runs tests, Source checks and this read-only check; writing remains explicit through preparation or reconciliation. Cross-Instance preparation is preflighted globally and remains transactional per Consumer rather than pretending filesystem writes can be globally atomic.

Maintained context remains outside the generated projection. Core `SOUL.md`, optional Instance `SOUL.md`, required Space `SOUL.md`, Core `INSTRUCTIONS.md`, optional Instance `INSTRUCTIONS.md`, Space-local `INSTRUCTIONS.md` and optional `MEMORY.md` are loaded in that order. Client projections reference each file directly; no Space SOUL link aliases Core. Linked `project` and `documentation` directories are working content rather than instruction sources: the engine validates their link boundaries but does not inspect, modify or activate their contents.

The Core adapters consume the same effective selection through different native seams. OpenCode projects direct skill links. Claude generates one `harnessia-core` plugin whose owned manifest and relative links enumerate only the effective Core skills. Source-owned Claude manifests and components are ignored, so they cannot broaden the projection. Space adapters retain their existing projections and isolation. OpenCode and Claude share context resolution and transactional output, not native formats. Agents, commands, permissions and startup requirements remain client-specific. The engine has no general work launcher, daemon, secret manager, automatic Source updater, private server or memory service; its only client launch is the explicit OpenCode Mini curation session.
