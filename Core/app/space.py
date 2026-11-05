from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re

import yaml

from .layout import INSTANCE_ID, CoreLayout, InstanceLayout


PORTABLE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MCP_ID = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
SPACE_FIELDS = {"version", "skills", "agents", "commands", "mcp"}
REQUIRED_SPACE_FIELDS = {"version", "skills"}
REFERENCE_FIELDS = {"source", "path"}


class HarnessiaError(ValueError):
    """A user-correctable Harnessia validation failure."""


@dataclass(frozen=True)
class CapabilityReference:
    source: Path
    path: Path


@dataclass(frozen=True)
class SpaceDefinition:
    core: CoreLayout
    instance: InstanceLayout
    directory: Path
    id: str
    skills: tuple[CapabilityReference, ...]
    agents: tuple[CapabilityReference, ...]
    commands: tuple[CapabilityReference, ...]
    mcp_servers: tuple[str, ...]


def _portable_path(value: object, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise HarnessiaError(f"{field} must be a non-empty POSIX path")
    if value.startswith("~"):
        raise HarnessiaError(f"{field} must not start with '~'")
    pure = PurePosixPath(value)
    if pure.is_absolute():
        raise HarnessiaError(f"{field} must be relative to Core")
    if ".." in pure.parts:
        raise HarnessiaError(f"{field} must not contain '..'")
    if "." in pure.parts or "" in pure.parts:
        raise HarnessiaError(f"{field} must be normalized")
    return Path(*pure.parts)


def _portable_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not PORTABLE_ID.fullmatch(value):
        raise HarnessiaError(
            f"{field} must use lowercase letters, digits and single hyphens"
        )
    return value


def parse_frontmatter(text: str, path: Path) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise HarnessiaError(f"{path}: missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise HarnessiaError(f"{path}: unclosed YAML frontmatter")
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError as error:
        raise HarnessiaError(f"{path}: invalid YAML frontmatter: {error}") from error
    if not isinstance(data, dict):
        raise HarnessiaError(f"{path}: YAML frontmatter must be a mapping")
    return data, text[end + 5 :]


def _space_directory(instance: InstanceLayout, space_id: str) -> tuple[Path, str]:
    relative = _portable_path(space_id, "SPACE")
    if len(relative.parts) != 1:
        raise HarnessiaError("SPACE must be a single space ID within an Instance")
    path_id = _portable_id(relative.parts[0], "SPACE id")
    return instance.spaces / path_id, path_id


def discover_instance_space_ids(instance: InstanceLayout) -> tuple[str, ...]:
    return tuple(
        definition.parent.name
        for definition in sorted(instance.spaces.glob("*/SPACE.md"))
    )


def _load_references(
    raw_references: object,
    kind: str,
    definition_path: Path,
) -> tuple[CapabilityReference, ...]:
    if not isinstance(raw_references, list):
        raise HarnessiaError(f"{definition_path}: {kind} must be a list")
    references = []
    for index, raw in enumerate(raw_references):
        label = f"{kind}[{index}]"
        if not isinstance(raw, dict):
            raise HarnessiaError(f"{definition_path}: {label} must be a mapping")
        unknown_fields = set(raw) - REFERENCE_FIELDS
        if unknown_fields:
            field = sorted(unknown_fields)[0]
            raise HarnessiaError(
                f"{definition_path}: {label} has unsupported field '{field}'"
            )
        missing_fields = REFERENCE_FIELDS - set(raw)
        if missing_fields:
            field = sorted(missing_fields)[0]
            raise HarnessiaError(
                f"{definition_path}: {label} is missing required field '{field}'"
            )
        source = _portable_path(raw["source"], f"{label}.source")
        path = _portable_path(raw["path"], f"{label}.path")
        parts = source.parts
        if not (
            len(parts) == 2
            and parts[0] in {"core", "instance"}
            and PORTABLE_ID.fullmatch(parts[1])
        ):
            raise HarnessiaError(
                f"{definition_path}: {label}.source must match "
                "core/<source-id> or instance/<source-id>"
            )
        references.append(CapabilityReference(source=source, path=path))
    return tuple(references)


def load_core_skill_references(
    raw_references: object,
    definition_path: Path,
) -> tuple[CapabilityReference, ...]:
    references = _load_references(
        raw_references,
        "skills",
        definition_path,
    )
    for index, reference in enumerate(references):
        parts = reference.source.parts
        if len(parts) != 2 or parts[0] != "core":
            raise HarnessiaError(
                f"{definition_path}: skills[{index}].source must match "
                "core/<source-id>"
            )
    return references


def load_instance_space(
    core: CoreLayout, instance: InstanceLayout, space_id: str
) -> SpaceDefinition:
    if not INSTANCE_ID.fullmatch(instance.id):
        raise HarnessiaError(
            "Instance id must use letters, digits and single hyphens"
        )
    directory, path_id = _space_directory(instance, space_id)
    definition_path = directory / "SPACE.md"
    if not definition_path.is_file():
        raise HarnessiaError(f"{definition_path}: Space Definition does not exist")
    spaces_root = instance.spaces.resolve(strict=True)
    resolved_directory = directory.resolve(strict=True)
    try:
        resolved_directory.relative_to(spaces_root)
    except ValueError as error:
        raise HarnessiaError(
            f"{directory}: Space directory resolves outside spaces"
        ) from error
    data, _ = parse_frontmatter(definition_path.read_text(), definition_path)
    unknown = set(data) - SPACE_FIELDS
    if unknown:
        field = sorted(unknown)[0]
        raise HarnessiaError(f"{definition_path}: unsupported field '{field}'")
    missing = REQUIRED_SPACE_FIELDS - set(data)
    if missing:
        field = sorted(missing)[0]
        raise HarnessiaError(f"{definition_path}: missing required field '{field}'")
    if data["version"] != 2:
        raise HarnessiaError(f"{definition_path}: version must be 2")

    skills = _load_references(data["skills"], "skills", definition_path)
    agents = _load_references(data.get("agents", []), "agents", definition_path)
    commands = _load_references(
        data.get("commands", []),
        "commands",
        definition_path,
    )
    raw_mcp = data.get("mcp", [])
    if not isinstance(raw_mcp, list):
        raise HarnessiaError(f"{definition_path}: mcp must be a list")
    mcp_servers: list[str] = []
    for index, server_id in enumerate(raw_mcp):
        if (
            not isinstance(server_id, str)
            or len(server_id) > 64
            or not MCP_ID.fullmatch(server_id)
        ):
            raise HarnessiaError(
                f"{definition_path}: mcp[{index}] must be a lowercase MCP server ID"
            )
        if server_id in mcp_servers:
            raise HarnessiaError(
                f"{definition_path}: duplicate MCP server ID '{server_id}'"
            )
        mcp_servers.append(server_id)

    return SpaceDefinition(
        core=core,
        instance=instance,
        directory=directory,
        id=path_id,
        skills=skills,
        agents=agents,
        commands=commands,
        mcp_servers=tuple(mcp_servers),
    )
