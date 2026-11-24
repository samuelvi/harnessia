# ADR 0005: Local Assisted Skill Curation

Status: accepted on 2026-10-28; the original skills-only scope was extended by [ADR 0006](0006-purpose-specific-mcp-curation.md).

## Context

A Space selects portable skills in client-agnostic `SPACE.md`, but Core and an Instance can expose thousands of candidates. A deterministic form can validate references but cannot judge which capabilities best fit a Space's purpose, while loading every skill body into one model context would be slow, costly and imprecise. Embedding a model SDK would also couple Harnessia to another runtime and duplicate the authentication and interaction already available in OpenCode.

The selection must remain reviewable: no external Source search or unrelated Instance candidates, no autonomous edit, no model-driven preparation and no loss of prior projections on cancellation or invalid output. Catalog scope and agent instructions do not form a filesystem sandbox.

## Decision

Harnessia exposes `make space-configure INSTANCE=<id> SPACE=<space-id>`. It builds a temporary JSONL index from valid skills in Core and the target Instance only, then opens OpenCode Mini with the maintained primary agent `space-curator`. The index carries enough metadata to shortlist candidates without loading every skill body; the agent reads only finalist definitions.

The agent asks for missing context, recommends the smallest sufficient set, separates required, optional and rejected candidates, and waits for explicit approval of the exact references. Its permissions allow local reading and search, ask before every edit, and deny shell, web and subagent use. The original edit scope was only `skills`; [ADR 0006](0006-purpose-specific-mcp-curation.md) adds `mcp`.

Harnessia remains the authority after the session. It records the attempted Definition, rejects changes outside the approved fields, performs normal validation and preparation only after a zero exit, and restores the snapshot after interruption, client failure, invalid output or preparation failure. Both projections continue to derive from the approved Definition.

## Consequences

- Users get semantic guidance without introducing an embedded model client or a second capability-selection format.
- Candidate visibility follows Source ownership exactly: Core plus one Instance, never another Instance or the web.
- The model can recommend and propose, but human approval and deterministic Harnessia validation remain separate gates.
- Large catalogs stay out of prompt context until filtering identifies finalists.
- OpenCode CLI and a TTY are runtime dependencies for assisted configuration only; ordinary preparation and generated Claude support do not depend on an interactive model session.
- Ignored `Core/.harnessia/space-configure/` evidence supports diagnosis and recovery without becoming maintained Space configuration. It moved out of `Core/.work/` on 2026-11-05; the transaction and ownership rules are unchanged.
