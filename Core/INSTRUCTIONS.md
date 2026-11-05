# Shared Space Instructions

## Space collaboration preferences

- Treat the active Space `SOUL.md` as maintained user-owned context for explicit, durable preferences about collaboration style and judgment.
- Update it only when the user explicitly asks to retain such a preference. Never infer preferences, learn from ordinary conversation or rewrite the file automatically.
- Keep operational rules in `INSTRUCTIONS.md` and verified facts, decisions and resumable checkpoints in `MEMORY.md`; do not duplicate them in `SOUL.md`.

## Working artifacts

- Manage documentation and working artifacts under `docs/` in the active Space, never inside its linked `project` repository unless they are maintained project deliverables.
- Use `docs/sources/` for original source materials and untouched templates, `docs/wip/` for drafts, plans, working evidence, caches, dumps, exports, generated reports, validation artifacts, scripts, checkpoints and backups, and `docs/deliverables/` for reviewed user-facing outputs. Store backups under `docs/wip/backups/`.
- Preserve a requested relative structure under the appropriate `docs/` area. Remap a temporary artifact proposed at `project/<relative-path>` or `<relative-path>` to `docs/wip/<relative-path>`; do not preserve the `project/` prefix.
- Create `docs/sources/`, `docs/wip/` or `docs/deliverables/` when the relevant category is first needed. Do not use a parallel `.work/` directory.
- Keep source code, repository-owned documentation, fixtures, tests, migrations and other intended repository deliverables in their proper maintained locations. Do not redirect them to the Space's `docs/` tree.

## Git repositories and worktrees

- Before modifying a linked project repository, inspect its current branch and status. Preserve every pre-existing user change and do not include it in unrelated work.
- Use the current checkout for simple, bounded work when it is clean. For broad, risky or parallel work, or when existing changes may overlap, explain why isolation is needed and obtain approval before creating a worktree. Never create one implicitly.
- Create user-facing worktrees for a linked project at `project/.worktrees/<worktree-name>`, never beside `project`, elsewhere in the Space or in a generic temporary directory.
- Before creating or moving a worktree, verify that `project` resolves to the intended Git repository, inspect its status and existing worktrees, and ensure `project/.worktrees/` is ignored by Git. Prefer the repository-local `.git/info/exclude` unless the user requests a tracked `.gitignore` change.
- Use a short worktree name describing the task or branch. After the operation, verify its resolved path, HEAD, branch or detached state, and clean status, then report its absolute path.
- Do not remove a worktree, discard its changes or delete its branch without explicit confirmation and a prior scope check.
