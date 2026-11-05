from dataclasses import dataclass
from pathlib import Path

from .layout import CoreLayout, InstanceLayout
from .prepare import PrepareResult, prepare_instance
from .space import HarnessiaError, PORTABLE_ID


@dataclass(frozen=True)
class CreateSpaceResult:
    directory: Path
    preparation: PrepareResult


@dataclass(frozen=True)
class AttachSpaceResult:
    directory: Path
    initialized_files: tuple[Path, ...]
    preparation: PrepareResult


def _validate_space_id(space_id: str) -> None:
    if not PORTABLE_ID.fullmatch(space_id):
        raise HarnessiaError(
            "Space ID must use lowercase letters, digits and single hyphens"
        )


def _remove_created_space(directory: Path) -> None:
    for child in sorted(
        directory.rglob("*"), key=lambda item: len(item.parts), reverse=True
    ):
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    directory.rmdir()


def create_space(
    core: CoreLayout, instance: InstanceLayout, space_id: str
) -> CreateSpaceResult:
    _validate_space_id(space_id)

    directory = instance.spaces / space_id
    if directory.exists() or directory.is_symlink():
        raise HarnessiaError(f"{directory}: Space create target already exists")

    try:
        directory.mkdir()
        (directory / "SPACE.md").write_text(
            f"---\nversion: 2\nskills: []\n---\n\n# {space_id}\n"
        )
        (directory / "SOUL.md").write_text("")
        (directory / "INSTRUCTIONS.md").write_text("# Space Instructions\n")
        preparation = prepare_instance(core, instance, space_id)
    except Exception:
        if directory.is_dir() and not directory.is_symlink():
            _remove_created_space(directory)
        raise

    return CreateSpaceResult(directory, preparation)


def attach_space(
    core: CoreLayout, instance: InstanceLayout, space_id: str
) -> AttachSpaceResult:
    _validate_space_id(space_id)

    directory = instance.spaces / space_id
    if not directory.is_dir() or directory.is_symlink():
        raise HarnessiaError(
            f"{directory}: Space attach target must be an existing regular directory"
        )

    definition = directory / "SPACE.md"
    if definition.exists() or definition.is_symlink():
        raise HarnessiaError(
            f"{definition}: Space attach requires an absent Definition"
        )

    maintained = (
        (directory / "SOUL.md", ""),
        (directory / "INSTRUCTIONS.md", "# Space Instructions\n"),
    )
    for path, _ in maintained:
        if (path.exists() or path.is_symlink()) and (
            not path.is_file() or path.is_symlink()
        ):
            raise HarnessiaError(f"{path}: maintained Space file must be regular")

    initialized: list[Path] = []
    files = (
        (
            definition,
            f"---\nversion: 2\nskills: []\n---\n\n# {space_id}\n",
        ),
        *maintained,
    )
    try:
        for path, content in files:
            if path.exists():
                continue
            with path.open("x") as stream:
                initialized.append(path)
                stream.write(content)
        preparation = prepare_instance(core, instance, space_id)
    except Exception as error:
        for path in reversed(initialized):
            if path.is_file() and not path.is_symlink():
                path.unlink()
        if isinstance(error, OSError):
            raise HarnessiaError(
                f"{directory}: cannot attach Space directory: {error}"
            ) from error
        raise

    return AttachSpaceResult(directory, tuple(initialized), preparation)
