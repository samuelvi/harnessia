from dataclasses import dataclass, replace
from pathlib import Path
import os
import re
import subprocess
from tempfile import TemporaryDirectory
from uuid import uuid4

import yaml

from .check import check_all
from .instances import consumer_instance_layouts
from .layout import CoreLayout, InstanceLayout
from .prepare import prepare_all
from .core import CORE_CONSUMER
from .source_git import git_result, git_sources, run_git
from .space import HarnessiaError, PORTABLE_ID


MANIFEST_NAME = "SOURCES.yaml"
MANIFEST_FIELDS = {"version", "sources"}
SOURCE_FIELDS = {"id", "url", "branch", "revision"}
REVISION = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class SourceSpec:
    path: Path
    directory: Path
    catalog_root: Path
    manifest: Path
    source_id: str
    url: str
    branch: str
    revision: str


@dataclass(frozen=True)
class CloneResult:
    cloned: tuple[Path, ...]
    current: tuple[Path, ...]


@dataclass(frozen=True)
class CheckResult:
    sources: tuple[Path, ...]
    consumers: tuple[str, ...]
    local_unversioned: tuple[Path, ...]


@dataclass(frozen=True)
class ReconcileChange:
    source: Path
    old_revision: str
    new_revision: str


@dataclass(frozen=True)
class ReconcileResult:
    changes: tuple[ReconcileChange, ...]
    current: tuple[Path, ...]
    consumers: tuple[str, ...]
    projections: int


def _mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise HarnessiaError(f"{label} must be a mapping")
    return value


def _exact_fields(data: dict, fields: set[str], label: str) -> None:
    unknown = set(data) - fields
    if unknown:
        raise HarnessiaError(f"{label} has unsupported field '{sorted(unknown)[0]}'")
    missing = fields - set(data)
    if missing:
        raise HarnessiaError(f"{label} is missing required field '{sorted(missing)[0]}'")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\n" in value or "\0" in value:
        raise HarnessiaError(f"{label} must be a non-empty single-line string")
    return value


def _load_yaml(path: Path) -> object:
    if not path.is_file():
        raise HarnessiaError(f"{path}: Source manifest does not exist")
    try:
        return yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as error:
        raise HarnessiaError(f"{path}: cannot read Source manifest: {error}") from error


def _load_source_manifest(
    path: Path,
    *,
    catalog_root: Path,
    scope: str,
) -> tuple[SourceSpec, ...]:
    data = _mapping(_load_yaml(path), str(path))
    _exact_fields(data, MANIFEST_FIELDS, str(path))
    if data["version"] != 2:
        raise HarnessiaError(f"{path}: version must be 2")
    if not isinstance(data["sources"], list):
        raise HarnessiaError(f"{path}: sources must be a list")

    specs = []
    seen = set()
    for index, raw in enumerate(data["sources"]):
        label = f"{path}: sources[{index}]"
        source = _mapping(raw, label)
        _exact_fields(source, SOURCE_FIELDS, label)
        source_id = _text(source["id"], f"{label}.id")
        if not PORTABLE_ID.fullmatch(source_id):
            raise HarnessiaError(f"{label}.id must be a portable Source ID")
        source_path = Path(scope, source_id)
        directory = catalog_root / source_id
        if source_path in seen:
            raise HarnessiaError(f"{label} duplicates {source_path.as_posix()}")
        seen.add(source_path)
        url = _text(source["url"], f"{label}.url")
        if url.startswith("-"):
            raise HarnessiaError(f"{label}.url must not start with '-'")
        branch = _text(source["branch"], f"{label}.branch")
        if branch.startswith("-") or branch in {"HEAD", "@"}:
            raise HarnessiaError(f"{label}.branch is not a valid branch name")
        revision = _text(source["revision"], f"{label}.revision")
        if not REVISION.fullmatch(revision):
            raise HarnessiaError(f"{label}.revision must be a full lowercase Git SHA-1")
        specs.append(
            SourceSpec(
                path=source_path,
                directory=directory,
                catalog_root=catalog_root,
                manifest=path,
                source_id=source_id,
                url=url,
                branch=branch,
                revision=revision,
            )
        )
    return tuple(specs)


def load_source_manifest(root: Path) -> tuple[SourceSpec, ...]:
    root = root.resolve()
    core = CoreLayout.at(root)
    return _load_source_manifest(
        core.source_manifest,
        catalog_root=core.sources,
        scope="core",
    )


def load_instance_source_manifest(instance: InstanceLayout) -> tuple[SourceSpec, ...]:
    return _load_source_manifest(
        instance.source_manifest,
        catalog_root=instance.sources,
        scope=f"instance/{instance.id}",
    )


def load_source_manifests(core: CoreLayout) -> tuple[SourceSpec, ...]:
    specs = list(load_source_manifest(core.directory))
    for instance in consumer_instance_layouts(core):
        specs.extend(load_instance_source_manifest(instance))
    seen: dict[Path, Path] = {}
    for spec in specs:
        if spec.path in seen:
            raise HarnessiaError(
                f"{spec.manifest}: duplicate Source '{spec.path}' also in "
                f"{seen[spec.path]}"
            )
        seen[spec.path] = spec.manifest
    return tuple(specs)


def _run_command(*arguments: str, cwd: Path) -> str:
    try:
        result = subprocess.run(
            arguments,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HarnessiaError(f"cannot run {' '.join(arguments)}: {error}") from error
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise HarnessiaError(f"{' '.join(arguments)}: {detail}")
    return result.stdout


def _require_within_root(root: Path, path: Path, label: Path) -> None:
    try:
        path.resolve(strict=True).relative_to(root)
    except ValueError as error:
        raise HarnessiaError(f"{label}: path resolves outside Core") from error
    except OSError as error:
        raise HarnessiaError(f"{label}: cannot resolve path: {error}") from error


def _validate_installed(
    root: Path, spec: SourceSpec, *, require_revision: bool
) -> str:
    directory = spec.directory
    if not directory.exists() and not directory.is_symlink():
        raise HarnessiaError(f"{spec.path}: Source directory does not exist")
    _require_within_root(spec.catalog_root, directory, spec.path)
    if not directory.is_dir() or directory.is_symlink():
        raise HarnessiaError(f"{spec.path}: Source must be a regular directory")
    top = run_git(directory, "rev-parse", "--show-toplevel").strip()
    if Path(top).resolve() != directory.resolve():
        raise HarnessiaError(f"{spec.path}: Git top-level does not match Source root")
    origin = run_git(directory, "remote", "get-url", "origin").strip()
    if origin != spec.url:
        raise HarnessiaError(
            f"{spec.path}: expected origin {spec.url!r}, found {origin!r}"
        )
    branch = run_git(directory, "branch", "--show-current").strip()
    if branch != spec.branch:
        found = branch or "detached HEAD"
        raise HarnessiaError(
            f"{spec.path}: expected branch {spec.branch!r}, found {found!r}"
        )
    upstream = run_git(
        directory,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
        check=False,
    ).strip()
    expected_upstream = f"origin/{spec.branch}"
    if upstream != expected_upstream:
        raise HarnessiaError(
            f"{spec.path}: expected upstream {expected_upstream!r}, "
            f"found {upstream or 'none'!r}"
        )
    status = run_git(
        directory,
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
        "--ignore-submodules=all",
    ).strip()
    if status:
        raise HarnessiaError(f"{spec.path}: worktree is not clean")
    revision = run_git(directory, "rev-parse", "HEAD").strip()
    if require_revision and revision != spec.revision:
        raise HarnessiaError(
            f"{spec.path}: expected revision {spec.revision}, found {revision}"
        )
    return revision


def _clone_source(root: Path, spec: SourceSpec) -> None:
    destination = spec.directory
    destination.parent.mkdir(parents=True, exist_ok=True)
    _require_within_root(spec.catalog_root, destination.parent, spec.path.parent)
    with TemporaryDirectory(
        prefix=f".{destination.name}-clone-", dir=destination.parent
    ) as temporary:
        checkout = Path(temporary) / "source"
        _run_command(
            "git",
            "clone",
            "--no-checkout",
            "--branch",
            spec.branch,
            "--single-branch",
            "--",
            spec.url,
            str(checkout),
            cwd=root,
        )
        run_git(checkout, "cat-file", "-e", f"{spec.revision}^{{commit}}")
        run_git(checkout, "checkout", "-B", spec.branch, spec.revision)
        run_git(
            checkout,
            "branch",
            "--set-upstream-to",
            f"origin/{spec.branch}",
            spec.branch,
        )
        temporary_spec = replace(spec, directory=checkout, catalog_root=checkout.parent)
        _validate_installed(root, temporary_spec, require_revision=True)
        if destination.exists() or destination.is_symlink():
            raise HarnessiaError(f"{spec.path}: Source directory appeared during clone")
        checkout.rename(destination)


def _raise_errors(title: str, errors: list[str]) -> None:
    if errors:
        raise HarnessiaError(title + ":\n" + "\n".join(errors))


def clone_sources(root: Path) -> CloneResult:
    root = root.resolve()
    specs = load_source_manifests(CoreLayout.at(root))
    missing = []
    current = []
    errors = []
    for spec in specs:
        directory = spec.directory
        if not directory.exists() and not directory.is_symlink():
            missing.append(spec)
            continue
        try:
            _validate_installed(root, spec, require_revision=True)
            current.append(spec.path)
        except HarnessiaError as error:
            errors.append(str(error))
    _raise_errors("Source clone preflight failed", errors)

    cloned = []
    for spec in missing:
        try:
            _clone_source(root, spec)
        except HarnessiaError as error:
            raise HarnessiaError(f"{spec.path}: clone failed: {error}") from error
        cloned.append(spec.path)
    return CloneResult(tuple(cloned), tuple(current))


def _validate_consumers(root: Path) -> tuple[str, ...]:
    core = CoreLayout.at(root)
    result = check_all(core)
    return (CORE_CONSUMER, *(space.consumer for space in result.spaces))


def _inventory_errors(root: Path, specs: tuple[SourceSpec, ...]) -> tuple[Path, ...]:
    repositories, unversioned = git_sources(root)
    configured = {spec.path for spec in specs}
    unlisted = sorted(
        (
            repository.source
            for repository in repositories
            if repository.source not in configured
        ),
        key=Path.as_posix,
    )
    if unlisted:
        raise HarnessiaError(
            "Git Sources missing from SOURCES.yaml:\n"
            + "\n".join(path.as_posix() for path in unlisted)
        )
    return unversioned


def check_sources(root: Path) -> CheckResult:
    root = root.resolve()
    specs = load_source_manifests(CoreLayout.at(root))
    errors = []
    for spec in specs:
        try:
            _validate_installed(root, spec, require_revision=True)
        except HarnessiaError as error:
            errors.append(str(error))
    try:
        unversioned = _inventory_errors(root, specs)
    except HarnessiaError as error:
        errors.append(str(error))
        unversioned = ()
    consumers = ()
    try:
        consumers = _validate_consumers(root)
    except HarnessiaError as error:
        errors.append(str(error))
    _raise_errors("Source check failed", errors)
    return CheckResult(tuple(spec.path for spec in specs), consumers, unversioned)


def _write_manifests(specs: tuple[SourceSpec, ...]) -> None:
    grouped: dict[Path, list[SourceSpec]] = {}
    for spec in specs:
        grouped.setdefault(spec.manifest, []).append(spec)

    staged: list[tuple[Path, Path]] = []
    replaced: list[tuple[Path, bytes]] = []
    try:
        for path, manifest_specs in grouped.items():
            sources = [
                {
                    "id": spec.source_id,
                    "url": spec.url,
                    "branch": spec.branch,
                    "revision": spec.revision,
                }
                for spec in manifest_specs
            ]
            content = yaml.safe_dump(
                {"version": 2, "sources": sources}, sort_keys=False
            )
            temporary = path.parent / f".{path.name}-reconcile-{uuid4().hex}"
            temporary.write_text(content)
            staged.append((temporary, path))
        for temporary, path in staged:
            replaced.append((path, path.read_bytes()))
            os.replace(temporary, path)
    except OSError as error:
        for temporary, _ in staged:
            if temporary.exists():
                temporary.unlink()
        for path, previous in reversed(replaced):
            rollback = path.parent / f".{path.name}-rollback-{uuid4().hex}"
            rollback.write_bytes(previous)
            os.replace(rollback, path)
        raise HarnessiaError(f"cannot update Source manifests: {error}") from error


def reconcile_sources(root: Path) -> ReconcileResult:
    root = root.resolve()
    core = CoreLayout.at(root)
    specs = load_source_manifests(core)
    errors = []
    revisions: dict[Path, str] = {}
    for spec in specs:
        try:
            revision = _validate_installed(root, spec, require_revision=False)
            upstream = spec.directory
            ancestor = git_result(
                upstream,
                "merge-base",
                "--is-ancestor",
                revision,
                f"origin/{spec.branch}",
            )
            if ancestor.returncode:
                raise HarnessiaError(
                    f"{spec.path}: current revision is not available from origin/{spec.branch}"
                )
            revisions[spec.path] = revision
        except HarnessiaError as error:
            errors.append(str(error))
    try:
        _inventory_errors(root, specs)
    except HarnessiaError as error:
        errors.append(str(error))
    consumers = ()
    try:
        consumers = _validate_consumers(root)
    except HarnessiaError as error:
        errors.append(str(error))
    _raise_errors("Source reconciliation failed", errors)

    updated = tuple(replace(spec, revision=revisions[spec.path]) for spec in specs)
    changes = tuple(
        ReconcileChange(old.path, old.revision, new.revision)
        for old, new in zip(specs, updated)
        if old.revision != new.revision
    )
    current = tuple(
        old.path
        for old, new in zip(specs, updated)
        if old.revision == new.revision
    )
    prepared = prepare_all(root)
    if changes:
        _write_manifests(updated)
    return ReconcileResult(
        changes=changes,
        current=current,
        consumers=consumers,
        projections=len(prepared.projections),
    )


def render_clone_result(result: CloneResult) -> str:
    return (
        f"Cloned {len(result.cloned)} Sources; "
        f"{len(result.current)} existing Sources already matched SOURCES.yaml."
    )


def render_check_result(result: CheckResult) -> str:
    lines = [
        f"Validated {len(result.sources)} pinned Sources and "
        f"{len(result.consumers)} Consumers without writing changes."
    ]
    if result.local_unversioned:
        lines.append(
            "Ignored local unversioned Sources: "
            + ", ".join(path.as_posix() for path in result.local_unversioned)
        )
    return "\n".join(lines)


def render_reconcile_result(result: ReconcileResult) -> str:
    space_count = sum(consumer != CORE_CONSUMER for consumer in result.consumers)
    lines = [
        f"Reconciled {len(result.changes)} Source revisions; "
        f"{len(result.current)} pins unchanged; prepared Core and "
        f"{space_count} Spaces."
    ]
    for change in result.changes:
        lines.append(
            f"  {change.source.as_posix()}: "
            f"{change.old_revision[:12]} -> {change.new_revision[:12]}"
        )
    return "\n".join(lines)
