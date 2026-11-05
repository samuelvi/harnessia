# ADR 0001: Core context client adapters

Status: accepted on 2026-10-27; Source location amended by [ADR 0002](0002-logical-source-ownership.md); Source-owned Claude manifest requirement superseded by [ADR 0003](0003-generated-core-claude-plugin.md).

## Context

Core maintenance sessions need a portable, reviewable capability selection. A pointer in `AGENTS.md` does not register Agent Skills. Reusing `SPACE.md` would misrepresent Core as a purpose-specific Space, while client-specific configuration would make one client the source of truth.

Core skills must remain in a Core Source, be available in OpenCode and Claude, and not broaden any Space allowlist.

## Decision

Use `HARNESSIA.md` as the Core Definition. Resolve it into one client-agnostic `EffectiveCoreContext`, then pass that context to separate OpenCode and Claude adapters.

The OpenCode adapter projects relative links for the selected skills under `.opencode/skills/`. Prepared Spaces continue denying all skills before allowing only their own effective IDs.

The Claude adapter generates an isolated skills-directory plugin under `.claude/skills/`. Its default `skills/` directory contains relative links only to selected Source skills. Before writing, the adapter proves that the Source `.claude-plugin/plugin.json` exposes exactly the selection and that neither manifest fields nor standard plugin locations add other components. The wrapper is required because linking the Source directory directly would let Claude's default `skills/` scan discover unselected sibling skills. Claude loads the generated plugin only when Core is the primary directory, so sessions opened directly in a Space do not inherit it.

Both adapters are validated and replaced in one transaction. Core is a Source Consumer, not a Space.

## Consequences

- One portable definition controls both clients.
- Capability bodies remain in their Source.
- The original design allowed a Source plugin manifest change to block check or reconciliation; [ADR 0003](0003-generated-core-claude-plugin.md) removed that coupling.
- Claude Core skills use a plugin namespace and generated wrapper; OpenCode Core skills retain their normal IDs.
- Core Sources must provide a compatible Claude plugin manifest. There is no fallback that copies skill bodies or exposes flat Core skills.
- Core and Space projections have separate ownership and isolation contracts.

## Rejected alternatives

- A Core `opencode.jsonc` would make OpenCode configuration canonical and would not solve Claude registration.
- Flat Core `.claude/skills/` links would be inherited by Spaces.
- A globally installed Claude plugin would affect unrelated repositories and move state outside Harnessia.
- Treating Core as a Space would invent working-content and custom-overlay semantics that do not apply.
