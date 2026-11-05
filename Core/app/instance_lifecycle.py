from dataclasses import dataclass
from pathlib import Path
import os
from uuid import uuid4

from .instances import (
    RegisteredInstance,
    preflight_instance_registration,
    register_instance,
)
from .layout import INSTANCE_ID, CoreLayout, InstanceLayout
from .space import HarnessiaError, discover_instance_space_ids


INSTANCE_IGNORE_RULES = """# Harnessia machine-local state
.harnessia/
sources/

# Machine-local Space bindings
spaces/*/project
spaces/*/documentation

# Generated client projections
spaces/*/opencode.jsonc
spaces/*/CLAUDE.md
spaces/*/.claude/
spaces/*/.opencode/

# Operating-system files
.DS_Store
"""
INSTANCE_IGNORE_START = "# BEGIN Harnessia managed ignore rules"
INSTANCE_IGNORE_END = "# END Harnessia managed ignore rules"
INSTANCE_IGNORE = (
    f"{INSTANCE_IGNORE_START}\n{INSTANCE_IGNORE_RULES}{INSTANCE_IGNORE_END}\n"
)


@dataclass(frozen=True)
class AttachResult:
    instance: RegisteredInstance
    initialized_souls: tuple[Path, ...]


def _validate_id(instance_id: str) -> None:
    if not INSTANCE_ID.fullmatch(instance_id):
        raise HarnessiaError(
            "Instance ID must use letters, digits and single hyphens"
        )


def _validate_instance_directory(layout: InstanceLayout) -> None:
    if not layout.directory.is_dir() or layout.directory.is_symlink():
        raise HarnessiaError(
            f"{layout.directory}: Instance must be a regular directory"
        )
    if not layout.spaces.is_dir() or layout.spaces.is_symlink():
        raise HarnessiaError(
            f"{layout.spaces}: Instance spaces must be a regular directory"
        )
    manifest = layout.source_manifest
    if not manifest.is_file() or manifest.is_symlink():
        raise HarnessiaError(
            f"{manifest}: Instance Source manifest must be a regular file"
        )


def _managed_ignore(existing: str) -> str:
    starts = existing.count(INSTANCE_IGNORE_START)
    ends = existing.count(INSTANCE_IGNORE_END)
    if starts != ends or starts > 1:
        raise HarnessiaError("Instance .gitignore has malformed Harnessia markers")
    if starts == 1:
        start = existing.index(INSTANCE_IGNORE_START)
        end = existing.find(INSTANCE_IGNORE_END, start)
        if end < 0:
            raise HarnessiaError("Instance .gitignore has malformed Harnessia markers")
        end += len(INSTANCE_IGNORE_END)
        if end < len(existing) and existing[end] == "\n":
            end += 1
        return existing[:start] + INSTANCE_IGNORE + existing[end:]
    if existing == INSTANCE_IGNORE_RULES:
        return INSTANCE_IGNORE
    if not existing:
        return INSTANCE_IGNORE
    separator = "" if existing.endswith("\n\n") else "\n" if existing.endswith("\n") else "\n\n"
    return existing + separator + INSTANCE_IGNORE


def _replace_with_empty_file(path: Path) -> None:
    temporary = path.parent / f".{path.name}-attach-{uuid4().hex}"
    temporary.write_text("")
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def _remove_legacy_core_soul_link(layout: InstanceLayout) -> None:
    legacy = layout.local_state / "core/SOUL.md"
    if not legacy.is_symlink():
        return
    legacy.unlink()
    for directory in (legacy.parent, layout.local_state):
        try:
            directory.rmdir()
        except OSError:
            break


def attach_instance(
    core: CoreLayout, instance_id: str, path: Path
) -> AttachResult:
    _validate_id(instance_id)
    if not path.is_absolute():
        raise HarnessiaError("Instance path must be absolute")
    layout = InstanceLayout.at(instance_id, path)
    _validate_instance_directory(layout)

    core_soul = core.directory / "SOUL.md"
    if not core_soul.is_file() or core_soul.is_symlink():
        raise HarnessiaError(f"{core_soul}: Core SOUL.md must be a regular file")

    space_ids = discover_instance_space_ids(layout)
    for space_id in space_ids:
        soul = layout.spaces / space_id / "SOUL.md"
        if soul.exists() and not soul.is_symlink() and not soul.is_file():
            raise HarnessiaError(f"{soul}: Space SOUL.md must be a regular file")

    ignore = layout.directory / ".gitignore"
    if ignore.exists() and (not ignore.is_file() or ignore.is_symlink()):
        raise HarnessiaError(f"{ignore}: Instance ignore policy must be a regular file")
    try:
        ignore_content = ignore.read_text() if ignore.exists() else ""
    except OSError as error:
        raise HarnessiaError(f"{ignore}: cannot read Instance ignore policy: {error}") from error
    try:
        updated_ignore = _managed_ignore(ignore_content)
    except HarnessiaError as error:
        raise HarnessiaError(f"{ignore}: {error}") from error

    # Registry validation must happen before attachment changes any Instance file.
    preflight_instance_registration(core, instance_id, layout.directory)

    _remove_legacy_core_soul_link(layout)
    if updated_ignore != ignore_content:
        ignore.write_text(updated_ignore)

    initialized: list[Path] = []
    for space_id in space_ids:
        soul = layout.spaces / space_id / "SOUL.md"
        if soul.is_symlink() or not soul.exists():
            _replace_with_empty_file(soul)
            initialized.append(soul)

    registered = register_instance(core, instance_id, layout.directory)
    return AttachResult(registered, tuple(initialized))


def create_instance(
    core: CoreLayout, instance_id: str, path: Path
) -> AttachResult:
    _validate_id(instance_id)
    if not path.is_absolute():
        raise HarnessiaError("Instance path must be absolute")
    path = path.resolve()
    if path.exists() or path.is_symlink():
        raise HarnessiaError(f"{path}: Instance create target already exists")

    try:
        path.mkdir(parents=True)
    except OSError as error:
        raise HarnessiaError(
            f"{path}: cannot create Instance directory: {error}"
        ) from error
    try:
        (path / "spaces").mkdir()
        (path / "sources").mkdir()
        (path / "SOURCES.yaml").write_text("version: 2\nsources: []\n")
        (path / ".gitignore").write_text(INSTANCE_IGNORE)
        return attach_instance(core, instance_id, path)
    except Exception:
        # The target was absent before this operation and contains only our scaffold.
        for child in sorted(path.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            if child.is_symlink() or child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        path.rmdir()
        raise
