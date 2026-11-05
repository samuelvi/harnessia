from dataclasses import dataclass
from pathlib import Path
import os
import subprocess

from .layout import CoreLayout
from .source_catalog import source_locations
from .space import HarnessiaError


@dataclass(frozen=True)
class SourceRepository:
    source: Path
    directory: Path


def git_result(source: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        return subprocess.run(
            ["git", "-C", str(source), *arguments],
            capture_output=True,
            text=True,
            timeout=30,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HarnessiaError(f"{source}: cannot inspect Git state: {error}") from error


def run_git(source: Path, *arguments: str, check: bool = True) -> str:
    result = git_result(source, *arguments)
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "Git command failed"
        raise HarnessiaError(f"{source}: {detail}")
    return result.stdout


def git_sources(
    root: Path,
) -> tuple[tuple[SourceRepository, ...], tuple[Path, ...]]:
    repositories = []
    skipped = []
    errors = []
    for location in source_locations(CoreLayout.at(root)):
        source = location.reference
        directory = location.directory
        marker = directory / ".git"
        probe = git_result(directory, "rev-parse", "--show-toplevel")
        top_level = probe.stdout.strip()
        if not top_level:
            if marker.exists() or marker.is_symlink():
                detail = probe.stderr.strip() or "Git metadata is inaccessible"
                errors.append(f"{source}: {detail}")
            else:
                skipped.append(source)
            continue
        if Path(top_level).resolve() != directory.resolve():
            if marker.exists() or marker.is_symlink():
                errors.append(f"{source}: Git top-level does not match the Source root")
            else:
                skipped.append(source)
            continue
        repositories.append(SourceRepository(source, directory))
    if errors:
        raise HarnessiaError("Source Git preflight failed:\n" + "\n".join(errors))
    return tuple(repositories), tuple(skipped)
