from dataclasses import dataclass
from pathlib import Path

from .layout import CoreLayout
from .orchestration import discover_spaces
from .core import CORE_CONSUMER, load_core_definition
from .source_catalog import SourceIdentity, source_directory, source_location_map
from .source_git import git_result, run_git
from .space import HarnessiaError, load_instance_space


DEPENDENCY_FILES = {
    "Cargo.lock",
    "Cargo.toml",
    "Gemfile",
    "Gemfile.lock",
    "composer.json",
    "composer.lock",
    "go.mod",
    "go.sum",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "pyproject.toml",
    "uv.lock",
    "yarn.lock",
}


@dataclass(frozen=True)
class CapabilityUsage:
    kind: str
    path: Path
    consumers: tuple[str, ...]


@dataclass(frozen=True)
class CapabilityChange:
    kind: str
    path: Path
    consumers: tuple[str, ...]


@dataclass(frozen=True)
class SourceStatus:
    source: Path
    consumers: tuple[str, ...]
    git_error: str | None
    missing: bool
    revision: str | None
    branch: str | None
    dirty: bool | None
    working_paths: tuple[Path, ...]
    upstream: str | None
    ahead: int | None
    behind: int | None
    upstream_paths: tuple[Path, ...]
    working_capabilities: tuple[CapabilityChange, ...]
    upstream_capabilities: tuple[CapabilityChange, ...]
    working_dependencies: tuple[Path, ...]
    upstream_dependencies: tuple[Path, ...]


def _source_usage(root: Path) -> dict[Path, tuple[CapabilityUsage, ...]]:
    core = CoreLayout.at(root)
    collected: dict[Path, dict[tuple[str, Path], set[str]]] = {}
    core_definition = load_core_definition(root)
    for capability in core_definition.skills:
        source = SourceIdentity.from_selection(capability.source).reference
        source_items = collected.setdefault(source, {})
        source_items.setdefault(("skill", capability.path), set()).add(
            CORE_CONSUMER
        )
    for location in discover_spaces(core):
        definition = load_instance_space(
            core, location.instance, location.space_id
        )
        for kind, references in (
            ("skill", definition.skills),
            ("agent", definition.agents),
            ("command", definition.commands),
        ):
            for capability in references:
                source = SourceIdentity.from_selection(
                    capability.source, location.instance
                ).reference
                source_items = collected.setdefault(source, {})
                source_items.setdefault((kind, capability.path), set()).add(
                    location.consumer
                )

    return {
        source: tuple(
            CapabilityUsage(kind, path, tuple(sorted(consumers)))
            for (kind, path), consumers in sorted(
                items.items(), key=lambda item: (item[0][0], item[0][1].as_posix())
            )
        )
        for source, items in collected.items()
    }


def _changed_paths(source: Path) -> tuple[Path, ...]:
    tracked = run_git(
        source,
        "diff",
        "--no-renames",
        "--name-only",
        "--ignore-submodules=all",
        "-z",
        "HEAD",
    )
    untracked = run_git(
        source, "ls-files", "--others", "--exclude-standard", "-z"
    )
    return tuple(
        sorted(
            {Path(item) for item in (tracked + untracked).split("\0") if item},
            key=Path.as_posix,
        )
    )


def _paths_overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def _capability_changes(
    paths: tuple[Path, ...], usage: tuple[CapabilityUsage, ...]
) -> tuple[CapabilityChange, ...]:
    changes = []
    for capability in usage:
        if any(_paths_overlap(capability.path, path) for path in paths):
            changes.append(
                CapabilityChange(
                    capability.kind, capability.path, capability.consumers
                )
            )
    return tuple(changes)


def _dependency_changes(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    return tuple(
        path
        for path in paths
        if path.name in DEPENDENCY_FILES
        or path.name.startswith("requirements")
        and path.suffix == ".txt"
    )


def _git_metadata_error(source: Path, fallback: str) -> str:
    marker = source / ".git"
    if marker.is_file():
        try:
            declaration = marker.read_text().strip()
        except OSError:
            declaration = ""
        if declaration.startswith("gitdir:"):
            target_text = declaration.removeprefix("gitdir:").strip()
            target = source / target_text
            if not target.exists():
                return f".git points to missing repository metadata ({target_text})"
    return fallback or "Git metadata is inaccessible"


def _inspect_source(
    source: Path, absolute: Path, usage: tuple[CapabilityUsage, ...]
) -> SourceStatus:
    consumers = tuple(
        sorted({consumer for item in usage for consumer in item.consumers})
    )
    probe = git_result(absolute, "rev-parse", "--show-toplevel")
    repository_root = probe.stdout.strip()
    if not repository_root or Path(repository_root).resolve() != absolute.resolve():
        git_error = None
        if (absolute / ".git").exists() or (absolute / ".git").is_symlink():
            git_error = _git_metadata_error(
                absolute,
                probe.stderr.strip()
                or "Git metadata does not identify this Source as its repository root",
            )
        return SourceStatus(
            source=source,
            consumers=consumers,
            git_error=git_error,
            missing=not absolute.exists(),
            revision=None,
            branch=None,
            dirty=None,
            working_paths=(),
            upstream=None,
            ahead=None,
            behind=None,
            upstream_paths=(),
            working_capabilities=(),
            upstream_capabilities=(),
            working_dependencies=(),
            upstream_dependencies=(),
        )

    revision = run_git(absolute, "rev-parse", "--short=12", "HEAD").strip()
    branch = run_git(
        absolute, "symbolic-ref", "--quiet", "--short", "HEAD", check=False
    ).strip() or "detached"
    dirty = bool(
        run_git(
            absolute,
            "status",
            "--porcelain=v1",
            "--untracked-files=normal",
            "--ignore-submodules=all",
        ).strip()
    )
    working_paths = _changed_paths(absolute)

    upstream = run_git(
        absolute,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
        check=False,
    ).strip() or None
    ahead = None
    behind = None
    upstream_paths: tuple[Path, ...] = ()
    if upstream:
        counts = run_git(
            absolute, "rev-list", "--left-right", "--count", f"HEAD...{upstream}"
        ).split()
        if len(counts) != 2:
            raise HarnessiaError(f"{source}: unexpected Git revision count")
        ahead, behind = (int(counts[0]), int(counts[1]))
        if behind:
            changed = run_git(
                absolute,
                "diff",
                "--no-renames",
                "--name-only",
                "--ignore-submodules=all",
                "-z",
                f"HEAD...{upstream}",
            )
            upstream_paths = tuple(
                sorted(
                    {Path(item) for item in changed.split("\0") if item},
                    key=Path.as_posix,
                )
            )

    return SourceStatus(
        source=source,
        consumers=consumers,
        git_error=None,
        missing=False,
        revision=revision,
        branch=branch,
        dirty=dirty,
        working_paths=working_paths,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        upstream_paths=upstream_paths,
        working_capabilities=_capability_changes(working_paths, usage),
        upstream_capabilities=_capability_changes(upstream_paths, usage),
        working_dependencies=_dependency_changes(working_paths),
        upstream_dependencies=_dependency_changes(upstream_paths),
    )


def inspect_sources(root: Path) -> tuple[SourceStatus, ...]:
    root = root.resolve()
    locations = source_location_map(CoreLayout.at(root))
    usage = _source_usage(root)
    sources = set(locations) | set(usage)
    return tuple(
        _inspect_source(
            source,
            locations.get(source, source_directory(CoreLayout.at(root), source)),
            usage.get(source, ()),
        )
        for source in sorted(sources, key=Path.as_posix)
    )


def _format_capability(change: CapabilityChange) -> str:
    consumers = ", ".join(change.consumers) or "no selected Consumer"
    return f"{change.kind}:{change.path.as_posix()} [{consumers}]"


def render_source_status(statuses: tuple[SourceStatus, ...]) -> str:
    lines = [
        "Read-only Source status. No fetch or update was performed; upstream data uses local Git refs."
    ]
    for status in statuses:
        consumers = ",".join(status.consumers) or "none"
        if status.revision is None:
            state = (
                "missing"
                if status.missing
                else f"git-unavailable: {status.git_error}"
                if status.git_error
                else "unversioned"
            )
            lines.append(
                f"{status.source.as_posix()} | {state} | consumers={consumers}"
            )
            continue

        worktree = (
            f"dirty:{len(status.working_paths)}" if status.dirty else "clean"
        )
        if status.upstream:
            update = "available" if status.behind else "none-known"
            upstream = (
                f"{status.upstream} ahead={status.ahead} behind={status.behind} "
                f"update={update}"
            )
        else:
            upstream = "none update=unknown"
        lines.append(
            f"{status.source.as_posix()} | {status.revision} {status.branch} | "
            f"{worktree} | upstream={upstream} | consumers={consumers}"
        )
        for label, changes in (
            ("working selected", status.working_capabilities),
            ("known upstream selected", status.upstream_capabilities),
        ):
            for change in changes:
                lines.append(f"  {label}: {_format_capability(change)}")
        for label, paths in (
            ("working dependencies", status.working_dependencies),
            ("known upstream dependencies", status.upstream_dependencies),
        ):
            if paths:
                lines.append(
                    f"  {label}: {', '.join(path.as_posix() for path in paths)}"
                )
    return "\n".join(lines)
