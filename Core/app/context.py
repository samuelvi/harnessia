import os
from pathlib import Path

from .space import HarnessiaError, SpaceDefinition


MAX_MEMORY_BYTES = 32 * 1024


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _optional_regular(path: Path, label: str) -> bool:
    if not path.exists() and not path.is_symlink():
        return False
    if not path.is_file() or path.is_symlink():
        raise HarnessiaError(f"{path}: {label} must be a maintained regular file")
    return True


def _relative(path: Path, directory: Path) -> Path:
    return Path(os.path.relpath(path, directory))


def _validate_working_links(definition: SpaceDefinition) -> None:
    for name in ("project", "documentation"):
        link = definition.directory / name
        if not link.exists() and not link.is_symlink():
            continue
        if not link.is_symlink():
            raise HarnessiaError(f"{link}: {name} must be a symbolic link")
        try:
            target = link.resolve(strict=True)
        except FileNotFoundError as error:
            raise HarnessiaError(f"{link}: {name} link is broken") from error
        if not target.is_dir():
            raise HarnessiaError(f"{link}: {name} must resolve to a directory")
        if _is_within(target, definition.directory):
            raise HarnessiaError(
                f"{link}: {name} must resolve outside the Space directory"
            )


def resolve_context_paths(definition: SpaceDefinition) -> tuple[Path, ...]:
    """Resolve active Markdown from lowest to highest priority."""
    core_soul = definition.core.directory / "SOUL.md"
    if not core_soul.is_file() or core_soul.is_symlink():
        raise HarnessiaError(
            f"{core_soul}: Core SOUL.md must be a maintained regular file"
        )

    space_soul = definition.directory / "SOUL.md"
    if not space_soul.is_file() or space_soul.is_symlink():
        raise HarnessiaError(
            f"{space_soul}: Space SOUL.md must be a maintained regular file"
        )

    core_instructions = definition.core.directory / "INSTRUCTIONS.md"
    if not core_instructions.is_file() or core_instructions.is_symlink():
        raise HarnessiaError(
            f"{core_instructions}: shared INSTRUCTIONS.md must be a maintained "
            "regular file"
        )

    space_instructions = definition.directory / "INSTRUCTIONS.md"
    if not space_instructions.is_file():
        raise HarnessiaError(f"{space_instructions}: INSTRUCTIONS.md is required")
    if space_instructions.is_symlink():
        raise HarnessiaError(
            f"{space_instructions}: INSTRUCTIONS.md must be a maintained regular file"
        )

    memory = definition.directory / "MEMORY.md"
    if _optional_regular(memory, "MEMORY.md"):
        if memory.stat().st_size > MAX_MEMORY_BYTES:
            raise HarnessiaError(f"{memory}: MEMORY.md must not exceed 32 KiB")

    _validate_working_links(definition)

    ordered = [_relative(core_soul, definition.directory)]

    instance_soul = definition.instance.directory / "SOUL.md"
    if _optional_regular(instance_soul, "Instance SOUL.md"):
        ordered.append(_relative(instance_soul, definition.directory))

    ordered.append(Path("SOUL.md"))

    ordered.append(_relative(core_instructions, definition.directory))

    instance_instructions = definition.instance.directory / "INSTRUCTIONS.md"
    if _optional_regular(instance_instructions, "Instance INSTRUCTIONS.md"):
        ordered.append(_relative(instance_instructions, definition.directory))

    ordered.append(Path("INSTRUCTIONS.md"))
    if memory.exists():
        ordered.append(Path("MEMORY.md"))
    return tuple(ordered)
