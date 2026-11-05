# ADR 0002: Logical Source ownership

Status: accepted on 2026-10-28.

## Context

The first Core and Instance split left Source identity encoded as a five-part physical path under `profiles/`. That path mixed ownership, trust classification and storage. It also prevented an Instance from owning a Source without placing the checkout inside Core.

Filesystem discovery alone cannot describe a missing expected Git Source or recreate its remote and revision. Definitions still need a stable identifier, while manifests need reproducibility metadata.

## Decision

Definitions identify Sources as `core/<source-id>` or `instance/<source-id>`.

- Core Sources live under `Core/sources/<source-id>` and are declared by `Core/SOURCES.yaml` when reproducible.
- Instance Sources live under `<instance>/sources/<source-id>` and are declared by that Instance's `SOURCES.yaml` when reproducible.
- Present unversioned Source directories are discovered without requiring manifest entries.
- Core resolves every reference. A Space may use Core Sources and Sources owned by its Instance, never Sources owned by another Instance.
- `internal` and `external` are not identity or storage dimensions. Remote URL and repository access policy remain manifest and operator concerns.

## Consequences

Definitions survive Source checkout relocation within their owner. Core and Instances can move independently after reattachment. Expected missing repositories remain reconstructable from owner-local manifests. Existing path-based definitions and manifests require an explicit migration, but capability paths inside each Source remain unchanged.
