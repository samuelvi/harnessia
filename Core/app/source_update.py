from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json

from .source_git import SourceRepository, git_result, git_sources, run_git
from .space import HarnessiaError


@dataclass(frozen=True)
class FetchResult:
    sources: tuple[Path, ...]
    skipped: tuple[Path, ...]


@dataclass(frozen=True)
class PullChange:
    source: Path
    old_revision: str
    new_revision: str


@dataclass(frozen=True)
class PullResult:
    changes: tuple[PullChange, ...]
    current: tuple[Path, ...]
    skipped: tuple[Path, ...]
    log: Path


@dataclass(frozen=True)
class _PullCandidate:
    source: SourceRepository
    branch: str
    upstream: str
    old_revision: str
    new_revision: str
    ahead: int
    behind: int


def fetch_sources(root: Path) -> FetchResult:
    root = root.resolve()
    repositories, skipped = git_sources(root)
    missing_remotes = []
    for repository in repositories:
        remotes = run_git(repository.directory, "remote").split()
        if not remotes:
            missing_remotes.append(f"{repository.source}: no Git remote")
    if missing_remotes:
        raise HarnessiaError(
            "Source fetch preflight failed:\n" + "\n".join(missing_remotes)
        )
    for repository in repositories:
        run_git(
            repository.directory,
            "fetch",
            "--all",
            "--prune",
            "--recurse-submodules=no",
        )
    return FetchResult(
        sources=tuple(repository.source for repository in repositories),
        skipped=skipped,
    )


def _pull_candidate(repository: SourceRepository) -> _PullCandidate:
    directory = repository.directory
    branch = run_git(directory, "branch", "--show-current").strip()
    if not branch:
        raise HarnessiaError(f"{repository.source}: detached HEAD")
    status = run_git(
        directory,
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
        "--ignore-submodules=all",
    ).strip()
    if status:
        raise HarnessiaError(f"{repository.source}: worktree is not clean")
    upstream = run_git(
        directory,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
        check=False,
    ).strip()
    if not upstream:
        raise HarnessiaError(f"{repository.source}: current branch has no upstream")
    old_revision = run_git(directory, "rev-parse", "HEAD").strip()
    new_revision = run_git(directory, "rev-parse", upstream).strip()
    counts = run_git(
        directory, "rev-list", "--left-right", "--count", f"HEAD...{upstream}"
    ).split()
    if len(counts) != 2:
        raise HarnessiaError(f"{repository.source}: unexpected Git revision count")
    ahead, behind = int(counts[0]), int(counts[1])
    if ahead and behind:
        raise HarnessiaError(
            f"{repository.source}: branch has diverged from {upstream}"
        )
    if behind:
        ancestor = git_result(
            directory, "merge-base", "--is-ancestor", "HEAD", new_revision
        )
        if ancestor.returncode:
            raise HarnessiaError(
                f"{repository.source}: {upstream} is not a fast-forward"
            )
    return _PullCandidate(
        source=repository,
        branch=branch,
        upstream=upstream,
        old_revision=old_revision,
        new_revision=new_revision,
        ahead=ahead,
        behind=behind,
    )


def _write_pull_log(root: Path, candidates: tuple[_PullCandidate, ...]) -> Path:
    now = datetime.now(timezone.utc)
    path = root / "logs" / (
        f"{now.strftime('%Y-%m-%dT%H%M%S.%fZ')}-sources-pull.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "created_at": now.isoformat().replace("+00:00", "Z"),
                "sources": [
                    {
                        "source": candidate.source.source.as_posix(),
                        "branch": candidate.branch,
                        "upstream": candidate.upstream,
                        "old_revision": candidate.old_revision,
                        "new_revision": candidate.new_revision,
                        "ahead": candidate.ahead,
                        "behind": candidate.behind,
                    }
                    for candidate in candidates
                ],
            },
            indent=2,
        )
        + "\n"
    )
    return path


def pull_sources(root: Path) -> PullResult:
    root = root.resolve()
    repositories, skipped = git_sources(root)
    errors = []
    candidates = []
    for repository in repositories:
        try:
            candidates.append(_pull_candidate(repository))
        except HarnessiaError as error:
            errors.append(str(error))
    if errors:
        raise HarnessiaError("Source pull preflight failed:\n" + "\n".join(errors))

    planned = tuple(candidates)
    log = _write_pull_log(root, planned)
    changes = []
    current = []
    for candidate in planned:
        if not candidate.behind:
            current.append(candidate.source.source)
            continue
        try:
            run_git(
                candidate.source.directory,
                "merge",
                "--ff-only",
                candidate.new_revision,
            )
        except HarnessiaError as error:
            raise HarnessiaError(f"{error}; recovery log: {log}") from error
        actual = run_git(candidate.source.directory, "rev-parse", "HEAD").strip()
        if actual != candidate.new_revision:
            raise HarnessiaError(
                f"{candidate.source.source}: expected {candidate.new_revision}, got {actual}; "
                f"recovery log: {log}"
            )
        changes.append(
            PullChange(
                source=candidate.source.source,
                old_revision=candidate.old_revision,
                new_revision=actual,
            )
        )
    return PullResult(
        changes=tuple(changes),
        current=tuple(current),
        skipped=skipped,
        log=log,
    )


def render_fetch_result(result: FetchResult) -> str:
    lines = [f"Fetched {len(result.sources)} Git Sources."]
    if result.skipped:
        lines.append(
            "Skipped unversioned Sources: "
            + ", ".join(source.as_posix() for source in result.skipped)
        )
    lines.append("Run `make sources-status` before `make sources-pull`.")
    return "\n".join(lines)


def render_pull_result(result: PullResult) -> str:
    lines = [
        f"Fast-forwarded {len(result.changes)} Git Sources; "
        f"{len(result.current)} already current."
    ]
    for change in result.changes:
        lines.append(
            f"  {change.source.as_posix()}: "
            f"{change.old_revision[:12]} -> {change.new_revision[:12]}"
        )
    if result.skipped:
        lines.append(
            "Skipped unversioned Sources: "
            + ", ".join(source.as_posix() for source in result.skipped)
        )
    lines.append(f"Recovery log: {result.log}")
    lines.append("Run `make sources-reconcile` to validate Spaces and update pins.")
    return "\n".join(lines)
