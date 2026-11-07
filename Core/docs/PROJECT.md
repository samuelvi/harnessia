# Harnessia Implementation and Maintenance Record

Status: initial implementation and operational acceptance completed on 2026-10-26. This file preserves dated Core delivery observations; the [README](../README.md), [current design](DESIGN.md), [Core Definition](core-definition.md) and [Space Definition](space-definition.md) references describe current behavior. Historical Instance and Consumer counts are acceptance measurements, not a current installation inventory. Instance-owned configuration and project evidence remain outside Core.

## Initial delivery — 2026-10-26

Harnessia delivered isolated, purpose-specific AI Spaces built from reusable capability Sources. Each maintained `SPACE.md` resolved into one client-agnostic `EffectiveSpace`, then into fail-closed OpenCode and Claude Code projections without copying or translating capability bodies.

The accepted system included:

- portable shared and Space-local context, Agent Skills and bounded `MEMORY.md`;
- OpenCode-native agents, commands and default-deny skill and MCP policies;
- Claude context, linked skills, safety settings and an empty strict MCP catalog;
- atomic projection replacement with ownership checks and rollback;
- pinned Source bootstrap, read-only checks, dynamic status and fetch, reviewed fast-forward pull, and explicit reconciliation;
- dynamic discovery and preparation of all nine Spaces.

All nine migrations were checked against the former presets. Unsupported or redundant presets received explicit dispositions rather than creating another preset abstraction. Space identities and capability selections belong to their owning Instances and are not a Core inventory.

Initial acceptance evidence:

- All 69 engine tests passed. `make verify` validated all sixteen Source pins, prepared all nine Spaces and recognized generated ownership markers for both clients.
- Claude Code 2.1.220 passed installation diagnostics. An authenticated Space smoke loaded the maintained instruction phrase and selected `codebase-design` skill.
- Normal Claude startup detected inherited MCP servers; the documented strict empty-catalog invocation blocked an inherited Context7 tool with `MCP_BLOCKED`.
- The project rename preserved Source revisions and moved the active OpenCode session to the final project directory.

## Source repair and updates

The initial audit found eighteen top-level Sources. Thirteen stale former-submodule pointers were restored at their exact upstream commits without changing Source content; `open-design` was attached from detached HEAD to `main` at its existing revision; CTO OS was restored to its upstream `*-skill` layout without changing effective skill IDs. The repair manifest recorded the original pointers, revisions and content hashes at that checkpoint.

Nine reviewed fast-forwards were applied on 2026-10-26 and four on 2026-10-27. At that checkpoint, all sixteen reproducible Git Sources were clean, matched their fetched upstream references and manifest pins, and reported `ahead=0`, `behind=0`. Two intentionally unversioned Sources remained local.

These are historical repair observations. The obsolete local recovery artifacts and runtime logs were removed during the 2026-11-05 cleanup; they are not retained as a current evidence register.

## Subsequent maintenance — 2026-10-27

The first maintenance pass added shared Core instructions to every projection, centralized `.work/` and worktree policy, and retained AUTO-specific Docker worktree guidance locally. The resulting suite had 70 passing tests and `make verify` covered all sixteen pins and nine Spaces.

The next pass added the dedicated `HARNESSIA.md` Core Definition, shared skill resolution, `EffectiveCoreContext`, separate Core adapters, Consumer-aware Source reporting and transactional Core preparation. The Core Definition selected the 27 promoted Matt Pocock skills only from `profiles/common/sources/external/`; it did not turn Core into a Space or broaden any Space allowlist.

That pass ended with 87 passing tests. `make verify` validated sixteen pins and ten Consumers, then prepared Core and all nine Spaces. A Claude fixture detected the local `@skills-dir` plugin from Core but not from a nested Space. The generated plugin passed strict validation; direct invocation loaded selected `codebase-design` and rejected unselected `migrate-to-shoehorn`.

The architectural rationale is preserved in [ADR 0001](adr/0001-core-context-client-adapters.md).

## Core and Instance separation — 2026-10-28

The first incremental separation introduced explicit `CoreLayout` and `InstanceLayout` modules before moving maintained content. A split-layout integration fixture proved that an Instance at an unrelated filesystem path can resolve capabilities from Core, compose optional Instance context and generate OpenCode and Claude projections. A strict ignored local registry records expected Instances even when their paths are missing, and the Make interface can register, list and prepare them. Source checks, status, aggregate preparation and reconciliation include registered Instance Consumers and fail closed when a registered path is unavailable.

The physical cut then moved the sole Git repository to `Core/` and all nine Spaces to two external Instances. Existing working-content bindings were preserved, Core context links were repaired, both Instances were registered locally, and all nine projections were regenerated from their final locations. `make sources-check` validated sixteen pins and ten Consumers. The embedded adapter remained temporarily as compatibility code, but no migrated Space depended on it. The resulting suite had 105 passing tests.

## Source ownership and Instance orchestration — 2026-10-28

The next phases removed Profile paths from the active Source model. Definitions now select logical `core/<id>` or `instance/<id>` Sources. Fourteen pinned and all shared Sources moved to `Core/sources/`; each external Instance received an owner-local Source catalog and manifest, including its prior local unversioned Sources. All sixteen Git revisions, origins and branches remained unchanged.

Core gained explicit Instance creation and attachment. Attachment preflights the registry, preserves existing ignore policy inside a managed block, registers the absolute path and initializes missing Space SOUL files without replacing maintained ones. Read-only `check --instance` and `check --all` operations validate effective contexts and both client plans, including projection ownership, without writing. The first aggregate check preserved the baseline of 27 Core skills, two Instances and nine Spaces. Reconciliation left all sixteen pins unchanged, regenerated all ten Consumers and the resulting suite had 117 passing tests.

## Core–Instance–Space simplification — 2026-10-28

The final simplification removed Profile as a concept rather than renaming it. `SPACE.md` version 2 derives its Space ID from the directory and its owning Instance from the registered layout. Definitions and manifests accept only logical `core/<source-id>` and `instance/<source-id>` references and version 2 manifests; physical `profiles/` paths, version 1 manifests and embedded Instances are rejected.

Instance creation and attachment now own the complete lifecycle, so the standalone registration command was removed. The public Make surface uses `prepare`, `prepare-core`, `prepare-instance`, `prepare-all`, `check`, Instance lifecycle commands and Source lifecycle commands. `prepare-instance` targets one Instance, `prepare-all` always covers Core and every registered Space, and `check` may target one Instance or validate everything. Alternate Core terminology and its duplicate Consumer alias were removed. All nine maintained Spaces were migrated without changing their capability selections. The simplified suite has 113 passing tests.

## Top-level repository layout — 2026-10-28

The redundant `engine/` directory was removed. Its `app/`, `tests/` and `logs/` directories now live directly under Core, and the Make commands run from Core without changing directory. Runtime and recovery logs use `logs/`. Two identical sets of ignored legacy `.mcprules-*` files were also removed: no active Harnessia client or contract used their obsolete Memory Bank and mode-switching rules.

## Context and orchestration simplification — 2026-10-28

Active Markdown inheritance is explicit. One context module validates and orders Core SOUL, optional Instance SOUL, maintained Space SOUL, Core instructions, optional Instance instructions, Space instructions and optional Space memory. Client projections reference the Core SOUL directly rather than through generated Space links. `INDEX.md`, Definitions, READMEs and documentation remain non-active navigation or reference material. Characterization tests cover both the effective-context interface and the generated OpenCode and Claude paths.

Consumer discovery, effective resolution and projection planning now share one orchestration seam. Aggregate Core or Instance preparation validates every requested Consumer before writing the first projection, while replacement and rollback remain atomic per Consumer. Source reconciliation reuses the same check and preparation paths. Source identity is represented internally as owner plus Source ID, missing selected Instance Sources resolve to the correct owner catalog, and shared Git operations no longer depend on private functions across modules.

The Core Claude adapter now generates one owned `harnessia-core` plugin from `HARNESSIA.md`; Source-owned Claude manifests and components cannot broaden or block it. The generated plugin contained 27 relative, valid skill links. Regenerating all Consumers left all 310 generated entries across the nine Space projections byte-identical. `make verify` is now read-only and passed 120 tests, sixteen pinned Sources, ten Consumers, two Instances and nine Spaces.

## Maintained Space SOUL — 2026-10-28

The nine generated Space SOUL links were replaced with empty maintained regular files. Client projections now load Core, optional Instance and Space SOUL paths directly; attachment initializes missing or legacy linked Space SOUL files, preserves regular files and removes obsolete generated Core-link state. Instance ignore policy no longer excludes Space SOUL files. All nine OpenCode and Claude projections were regenerated with the new order, and `make verify` passed 122 tests, sixteen pinned Sources, ten Consumers, two Instances and nine Spaces.

## Space creation lifecycle — 2026-10-28

The public `make space-create INSTANCE=<id> SPACE=<space-id>` command now creates the minimum maintained Space files and immediately prepares both client projections. Creation is fail-closed: an existing target is preserved and rejected, while a preparation failure removes only the newly created scaffold. Instance names now preserve capitalization instead of imposing lowercase aliases. Case-only reattachment migrates that legacy spelling without permitting unrelated names for one path. `make verify` passed 126 tests, sixteen pinned Sources, ten existing Consumers, two Instances and nine existing Spaces; the command tests use temporary Instances and do not change the maintained inventory.

## Assisted skill configuration — 2026-10-28

The public `make space-configure INSTANCE=<id> SPACE=<space-id>` command now opens OpenCode Mini with a dedicated restricted curator. A deterministic JSONL catalog exposes only validated skills from Core and the target Instance, with exact references, descriptions, current selection and pinned or local Source state. The agent asks only for missing context, proposes a minimal reviewed selection and cannot use shell, web, subagents or unrelated OpenCode skills; every edit requires human approval.

Harnessia snapshots the client-agnostic Definition before launch and remains responsible for validation and preparation after the session. Tests prove successful no-change cancellation, valid dual-client preparation, non-zero exit rollback, deleted or invalid Definition rollback, preservation of prior projections, rejection of changes outside `skills`, TTY and executable preflight, CLI wiring, Instance isolation and invalid-candidate filtering. All model-facing tests use a fake executable and make no model request.

The installed OpenCode 2.1.4 CLI discovered the maintained `space-curator` agent before model resolution. A real catalog smoke against an external Space indexed 1,796 valid Core and owning-Instance candidates, skipped 13 invalid definitions and retained all 46 imported references; its forty-seventh effective skill was an existing Space-local custom skill, not a `SPACE.md` reference. No maintained Space was changed. `make verify` passed 139 tests, sixteen pinned Sources, ten Consumers, two Instances and nine Spaces.

## Commented setup template — 2026-10-29

Core gained the reusable `templates/space-setup.sh` quick-setup template, referenced from both READMEs. Its three commented values distinguish the registered Instance name, its explicit absolute path and the lowercase Space ID. The script creates or attaches the Instance, installs missing pinned Sources, creates an absent Space, opens the restricted curator and finishes with a read-only Instance check. Existing initialized Instances and Spaces are attached or reused rather than recreated.

The template has no default Instance path and rejects empty, relative and documentation-placeholder paths before invoking Make. It recognizes an initialized Space through a regular, non-symlinked `SPACE.md`; an existing regular directory without one is attached by creating only its missing Harnessia files, while other collisions are preserved and reported. Attachment rollback removes only those new files. Instance directory creation errors are translated into a single Harnessia error instead of exposing a Python traceback. Regression tests cover the reported placeholder-path failure and safe initialization of an incomplete Space directory. The neutral demo Space name is `atlas`. `make verify` passed 146 tests, sixteen pinned Sources, eleven Consumers, two Instances and ten valid Spaces.

## Feedback Sources and Core skill discovery — 2026-11-03

Five reviewed repositories were added to Core `SOURCES.yaml` and cloned at pinned revisions: `anthropics-knowledge-work-plugins`, `refoundai-lenny-skills`, `softaworks-agent-toolkit`, `vercel-skills` and `codesigils-skill-discovery`. The first three make performance-review, feedback, coaching and difficult-conversation capabilities available for later Space selection; cloning them does not activate their complete skill sets, plugins or connectors.

Core now selects `find-skills` and `skill-discovery` alongside its 27 existing skills. Both client projections were regenerated with 29 selected skills. Repository instructions constrain discovery to evidence-based inspection and approved additions through Harnessia's Source lifecycle, without global skill installation. This does not change the local-only Space curator. Discovery skill instructions and supporting references received static inspection; no behavioral model evaluation or candidate scripts were run.

`make verify` passed all 146 tests and validated 21 pinned Sources, 13 Consumers, two Instances and twelve initialized Spaces. Both discovery skill links resolve to their pinned Sources in the Core OpenCode and Claude projections; all recommended feedback skill paths exist in clean Source checkouts.

## Container and browser Sources — 2026-11-04

Core pins `docker-skills` at `090ff3d39db5f8bc55d4e951c26218e7c95ea2d3` and `microsoft-playwright-cli` at `db2a0fad3a768319a16e3a2bb8078cf62e690b07`. Both checkouts were clean on their declared `main` branches. Source installation does not install runtime packages, browser binaries, plugins or hooks. Consumers select these capabilities independently; installation does not activate them in Core or authorize runtime operations.

Historical acceptance passed all 146 tests, 23 pinned Sources, 15 Consumers, two Instances and fourteen Spaces. Runtime experiments and Space-specific delivery evidence belong to the owning Instance, not this Core record.

## Local cleanup and standalone Core — 2026-11-05

The user authorized removal of obsolete plans, including deferred proposals, backups, configuration diagnostics and runtime/recovery logs. Core's machine-local Instance registry was emptied without changing any external Instance files. Documentation and test fixtures use neutral examples rather than a maintained inventory of real projects. Core remains able to attach arbitrary Instances explicitly; none is required for its own verification.

The user also requested a single initial Core commit instead of the mixed local history. No remote publication is part of this maintenance operation. Standalone `make verify` passed 147 tests and validated 21 pinned Core Sources, one Consumer, 29 Core skills, zero Instances and zero Spaces. A regression test confirms that unregistered external content is ignored, even when its Definition is invalid. Maintained relative Markdown links also resolved.

## License and public Source catalog — 2026-11-05

Core initially adopted MIT in the local pre-publication baseline; that decision is superseded by GPL-3.0-only below. Third-party Sources retained their own licenses. A private Source was removed from Core's catalog and relocated to its owning external Instance without changing its pinned revision or activating any capabilities. All 20 remaining catalog repositories were accessible through unauthenticated public lookups. Commit author identity was retained with the user's approval; the single initial commit was updated rather than retaining the former private URL in history. The Core ignore policy scoped local state, installed Sources and client projections to the project directory and removed obsolete embedded Space rules. No remote publication was included.

`make verify` passed 147 tests and validated 20 pinned Core Sources, one Consumer, 29 Core skills and no registered Instances or Spaces. The destination Instance's two pins matched their local revisions, branches and origins, and its existing Space projection plans passed read-only validation without registering the Instance or regenerating its projections. Maintained relative Markdown links resolved.

## GPL version 3 and repository entry points — 2026-11-05

The user selected GNU GPL version 3 only (`GPL-3.0-only`) for Harnessia Core, replacing the local MIT baseline before publication. At this checkpoint the complete license text and navigation READMEs were placed at the repository root. Their locations were superseded by the Core-only boundary below; the selected license and third-party ownership distinction are unchanged.

The Git working-tree root moved one level above `Core/`, preserving the existing origin configuration. That intermediate tree included `Core/` and four root metadata files: `.gitignore`, `README.md`, `README-ES.md` and `LICENSE`. A default-deny root ignore policy excluded all other siblings, with additional exclusions inside Core. Core READMEs remained the canonical operating guides and required commands to run from `Core/`. The context hierarchy was explicitly distinguished from the physical directory layout. No Instance content or Source checkout was moved, no Instance was registered, and no push was authorized.

`make verify` passed 149 tests and validated 20 pinned Core Sources, one Consumer, 29 Core skills and no registered Instances or Spaces. Two new tests cover root/Core entry points, license links and the layered ignore policy. Maintained relative Markdown links resolved. The complete license text matches the GNU Coreutils GPL version 3 reference.

A fresh local clone contained only Core and the root metadata, with no Instances, installed Sources or local registry. All 149 tests passed there with offline dependency resolution. This clean-clone check ran `make test`; the full `make verify` additionally requires installing the pinned Sources as documented.

## Core-only publication boundary and private working material — 2026-11-05

At this checkpoint the user clarified the boundary: all Harnessia project files belong in Core, with Git metadata and the repository-boundary `.gitignore` at the root. The license and canonical bilingual READMEs were kept in Core without duplicate root project files. Only `Core/` and the root `.gitignore` were versioned. Every sibling directory, including current and future local Instances, was excluded by default; exclusions for credentials and generated Core content did not broaden that boundary. The private documentation area and its local ignore policy were subsequently consolidated as recorded below.

Core's former `.work/` material initially moved to private root `docs/`, organized as `sources/` for original inputs, `deliverables/` for reviewed local outputs and `wip/` for plans, drafts and backups. Existing backups were preserved under `docs/wip/backups/`; maintained product documentation stayed in `Core/docs/`. At that stage the setup template resolved Core from either `Core/templates/` or a copy under root `docs/wip/`, independently of the caller's working directory. Both documentation areas and the template's copied location were later consolidated below.

The user explicitly retained runtime state inside Core: the unchanged registry remains at `Core/.harnessia/instances.yaml` and preparation and Source-update logs remain at `Core/logs/`. Assisted-configuration diagnostics now use ignored `Core/.harnessia/space-configure/`, so future operations do not recreate `Core/.work/`. No Instance was attached, and no existing Space or Source checkout was changed.

IDE configuration moved from root `.idea/` to explicitly ignored `Core/.idea/`. Its module scope and Git mapping were adjusted for Core and the parent repository; stale mappings to external projects were removed from the active IDE configuration, with the original configuration preserved in the private backup area. Capability Sources and client projections stay in Core because their resolution remains project-relative.

The agreed public operations were tested before changing their storage paths. `make verify` passed 150 tests, 20 pinned Core Sources, one Consumer, 29 Core skills and no registered Instances or Spaces. Tests cover registry placement, preparation logs, assisted-configuration diagnostics, execution of the copied setup template and the distinction between private root docs and versioned Core docs. No model call, external publication or push is part of this change.

A fresh local clone contained only `Core/` and the root `.gitignore`, apart from its own Git metadata. It contained no private working docs, Instances, IDE configuration, runtime state or installed Sources. All 150 tests passed there with offline dependency resolution; the full Source check was validated separately against the installed, pinned Core Sources.

## Consolidated Core documentation and private subdirectories — 2026-11-05

The user requested merging root `docs/` into `Core/docs/`. Its `sources/`, `deliverables/` and `wip/` directories moved alongside the maintained references and ADRs without name collisions or overwritten files. A file-hash, directory-identity and symlink inventory confirmed preservation of all inventoried non-Finder content. The obsolete root docs directory was removed.

The root `.gitignore` still excludes every sibling except Core. A tracked `Core/.gitignore` now explicitly excludes only `docs/sources/`, `docs/deliverables/` and `docs/wip/`; maintained product references elsewhere in `Core/docs/` remain versioned. The exclusion tests also prove that Core's allowed `.env.example` templates cannot expose a file inside private `docs/wip/`. The operating guides, repository instructions, glossary and architecture reference now use the consolidated locations. Runtime state and logs remain inside Core without changing their behavior.

The setup template resolves Core from `Core/templates/` or a copy directly under `Core/docs/wip/`. `make verify` passed 150 tests, 20 pinned Core Sources, one Consumer, 29 Core skills and no registered Instances or Spaces. Relative maintained-document links and bilingual shell examples validated. No private documentation content was added to Git or published.

## Project-local ignore rules — 2026-11-05

The root `.gitignore` was reduced to the publication boundary only: ignore all root entries except Core and the policy itself. Core's ignore file now owns all exclusions for local configuration, runtime state, installed Sources, client projections, credentials, caches and private documentation. Before/after checks preserved behavior for 34 representative paths, and expanded regression cases cover nested environment templates and private-folder exclusions. `make verify` passed 150 tests and validated 20 pinned Core Sources and one Consumer; no private files were included in Git.

## Accepted boundaries

- No general work launcher, daemon, private server, secret manager, background memory service or automatic updater. The explicit `space-configure` operation launches only its restricted OpenCode Mini curation session.
- Linked `project` and `documentation` targets remain external working content; preparation validates only their link boundaries.
- Cowork is unsupported, Gemini is deferred, and Doc Knowledge remains optional.
- Personal or account-level Claude skills may remain visible because Claude has no exact project skill allowlist. Ordinary Claude startup may load inherited MCP servers even though project settings deny their tools.
- `Core/docs/sources/`, `Core/docs/deliverables/`, `Core/docs/wip/`, `Core/.harnessia/`, `Core/logs/` and `Core/.idea/` are private ignored local material, not published project content. Maintained references elsewhere in `Core/docs/` remain versioned. No sibling folder is versioned by default.

There is no mandatory implementation or acceptance work left. Future changes are deliberate maintenance.
## Purpose-specific MCP curation — 2026-11-07

`space-configure` now recommends skills and MCP servers according to the Space's
purpose, including useful services not configured yet. The maintained curator and
Core maintenance instructions share `docs/mcp-guide.md`. A bounded, best-effort
OpenCode API request records only validated server IDs and known statuses; raw
configuration, connection errors and credentials are not persisted. Selection
approval remains separate from installation and authentication. The transaction
allows only `skills` and `mcp` changes and retains Definition/projection rollback.

Claude no longer rejects a nonempty OpenCode MCP selection: it still generates an
empty catalog and denies MCP calls. Strict startup needs no dummy server or tool
schema. A synthetic installed-CLI control-protocol smoke confirmed zero MCP servers
despite a project MCP configuration, without sending a user prompt or model request.
This is startup evidence, not a token benchmark or an interactive recommendation
quality evaluation.

`make verify` passed 158 tests and read-only validation of Core, the registered Work
Instance and fourteen Spaces. Explicit read-only validation of unregistered Personal
passed for both Spaces without changing registration. Live OpenCode discovery
confirmed the updated curator's default-deny permissions, edit approval and question
access. Local Work/Personal operating guides were updated outside the publication
boundary; their capability selections were preserved.
