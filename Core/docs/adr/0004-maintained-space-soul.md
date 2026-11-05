# ADR 0004: Maintained Space SOUL

Status: accepted on 2026-10-28.

## Context

Each Space previously exposed a generated `SOUL.md` symlink to Core while an optional Space-specific SOUL lived under `capabilities/custom/`. The root filename looked Space-owned but could not be maintained, required ignored attachment state and duplicated a concept across two paths.

A Space needs a visible place where a user may explicitly retain durable preferences about collaboration style and judgment. Those preferences are distinct from operational rules in `INSTRUCTIONS.md` and facts, decisions or checkpoints in `MEMORY.md`.

## Decision

Every Space owns a required regular `SOUL.md`. It may start empty. Harnessia validates and loads it after Core and optional Instance SOUL context, but never generates, rewrites or learns preferences into it.

An AI client may update the file only when the user explicitly asks to retain a durable collaboration preference. Ordinary conversation must not be interpreted as permission to change it.

Client projections reference Core, optional Instance and Space SOUL files directly. `instance attach` replaces a missing or legacy symlinked Space SOUL with an empty regular file and preserves an existing regular file unchanged. Space SOUL files are maintained content and are not ignored by Instance policy. `capabilities/custom/SOUL.md` is no longer active context.

## Consequences

- Core → Instance → Space SOUL ownership is visible in the filesystem.
- Moving Core or an Instance no longer requires repairing Space SOUL links.
- Empty Space SOUL files provide an explicit extension point without duplicating Core content.
- Users can review changes to collaboration preferences independently from operating instructions and memory.
