from dataclasses import dataclass
from pathlib import Path

from .space import (
    CapabilityReference,
    HarnessiaError,
    load_core_skill_references,
    parse_frontmatter,
)


CORE_FIELDS = {"version", "skills"}
CORE_DEFINITION_NAME = "HARNESSIA.md"
CORE_CONSUMER = "core"


@dataclass(frozen=True)
class CoreDefinition:
    directory: Path
    skills: tuple[CapabilityReference, ...]


def load_core_definition(directory: Path) -> CoreDefinition:
    directory = directory.resolve()
    definition_path = directory / CORE_DEFINITION_NAME
    if not definition_path.is_file() or definition_path.is_symlink():
        raise HarnessiaError(
            f"{definition_path}: Core Definition must be a maintained regular file"
        )
    data, _ = parse_frontmatter(definition_path.read_text(), definition_path)
    unknown = set(data) - CORE_FIELDS
    if unknown:
        field = sorted(unknown)[0]
        raise HarnessiaError(f"{definition_path}: unsupported field '{field}'")
    missing = CORE_FIELDS - set(data)
    if missing:
        field = sorted(missing)[0]
        raise HarnessiaError(f"{definition_path}: missing required field '{field}'")
    if data["version"] != 1:
        raise HarnessiaError(f"{definition_path}: version must be 1")

    return CoreDefinition(
        directory=directory,
        skills=load_core_skill_references(data["skills"], definition_path),
    )
