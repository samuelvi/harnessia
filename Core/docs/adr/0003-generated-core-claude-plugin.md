# ADR 0003: Generated Core Claude plugin

Status: accepted on 2026-10-28; supersedes the Source-owned Claude manifest requirement in [ADR 0001](0001-core-context-client-adapters.md).

## Context

The first Core Claude adapter used each Source's `.claude-plugin/plugin.json` as a second declaration of the skills already selected by `HARNESSIA.md`. Every Source had to keep both declarations exactly synchronized and remove standard Claude component locations, even though Harnessia generated an isolated wrapper containing only selected skill links.

That coupling made a Source responsible for Harnessia projection policy and caused unrelated Claude metadata to block Source checks and reconciliation.

## Decision

Harnessia generates one owned plugin named `harnessia-core` from the validated Effective Core Context.

- Its manifest explicitly lists every selected effective skill ID.
- Its `skills/` directory contains relative links only to those validated Source skill directories.
- Source-owned Claude manifests and standard plugin components are not projection inputs.
- OpenCode continues projecting the same effective selection as direct skill links.

## Consequences

`HARNESSIA.md` remains the sole Core capability selection. Sources no longer need Claude-specific metadata for Harnessia, and their unrelated plugin components cannot broaden Core. The generated wrapper still avoids copying capability bodies and remains local to sessions opened from Core.
