# ADR 0001: Core context client adapters

Status: accepted on 2026-10-27; Source location amended by [ADR 0002](0002-logical-source-ownership.md); Source-owned Claude manifest requirement superseded by [ADR 0003](0003-generated-core-claude-plugin.md).

## Context

Core maintenance sessions need a portable, reviewable capability selection. A pointer in `AGENTS.md` does not register Agent Skills. Reusing `SPACE.md` would misrepresent Core as a purpose-specific Space, while client-specific configuration would make one client the source of truth.

Core skills must remain in a Core Source, be available in OpenCode and Claude, and not broaden any Space allowlist.

## Decision

Use `HARNESSIA.md` as the Core Definition. Resolve it into one client-agnostic `EffectiveCoreContext`, then pass that context to separate OpenCode and Claude adapters.

The OpenCode adapter projects relative links for the selected skills under `.opencode/skills/`. Prepared Spaces continue denying all skills before allowing only their own effective IDs.

The Claude adapter generates an isolated skills-directory plugin under `.claude/skills/`. Its default `skills/` directory contains relative links only to selected Source skills. The original design also checked Source plugin metadata before writing; [ADR 0003](0003-generated-core-claude-plugin.md) supersedes that requirement. The wrapper prevents unselected siblings from being exposed by Claude's skill scan. Claude loads it only when Core is the primary directory.

Both adapters are validated and replaced in one transaction. Core is a Source Consumer, not a Space.

## Consequences

- One portable definition controls both clients.
- Capability bodies remain in their Source.
- The original design allowed a Source plugin manifest change to block check or reconciliation; [ADR 0003](0003-generated-core-claude-plugin.md) removed that coupling.
- Claude Core skills use a plugin namespace and generated wrapper; OpenCode Core skills retain their normal IDs.
- The original Source manifest requirement is superseded. The adapter still does not copy skill bodies or expose flat Core skills.
- Core and Space projections have separate ownership and isolation contracts.

## Rejected alternatives

- A Core `opencode.jsonc` would make OpenCode configuration canonical and would not solve Claude registration.
- Flat Core `.claude/skills/` links would be inherited by Spaces.
- A globally installed Claude plugin would affect unrelated repositories and move state outside Harnessia.
- Treating Core as a Space would invent working-content and custom-overlay semantics that do not apply.
