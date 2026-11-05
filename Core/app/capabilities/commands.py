from dataclasses import dataclass
from pathlib import Path

from ..space import HarnessiaError, PORTABLE_ID, SpaceDefinition, parse_frontmatter
from ..source_resolver import SourceResolver


@dataclass(frozen=True)
class Command:
    id: str
    path: Path


@dataclass(frozen=True)
class CommandInventory:
    commands: tuple[Command, ...]
    warnings: tuple[str, ...]

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(command.id for command in self.commands)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _validate_command(path: Path) -> tuple[Command, str | None]:
    if path.suffix != ".md" or not path.is_file():
        raise HarnessiaError(f"{path}: command must be a Markdown file")
    command_id = path.stem
    if len(command_id) > 64 or not PORTABLE_ID.fullmatch(command_id):
        raise HarnessiaError(
            f"{path}: command filename must use 1-64 lowercase letters, digits and hyphens"
        )
    text = path.read_text()
    body = text
    if text.startswith("---\n"):
        data, body = parse_frontmatter(text, path)
        if "template" in data:
            raise HarnessiaError(
                f"{path}: template must come from the body of a Markdown command"
            )
        for field in ("description", "agent", "model"):
            if field in data and not isinstance(data[field], str):
                raise HarnessiaError(f"{path}: {field} must be a string")
        for field in ("subagent", "subtask"):
            if field in data and not isinstance(data[field], bool):
                raise HarnessiaError(f"{path}: {field} must be true or false")
    if not body.strip():
        raise HarnessiaError(f"{path}: command prompt body must not be empty")
    warning = None
    if "!`" in body:
        warning = f"{path}: command contains native shell substitution; review before use"
    return Command(id=command_id, path=path), warning


def resolve_commands(definition: SpaceDefinition) -> CommandInventory:
    imported: dict[str, Command] = {}
    warnings: list[str] = []
    resolver = SourceResolver(definition.core, definition.instance)
    for index, reference in enumerate(definition.commands):
        _, resolved_target = resolver.target(
            reference.source, reference.path, f"commands[{index}]"
        )
        command, warning = _validate_command(resolved_target)
        if command.id in imported:
            raise HarnessiaError(
                f"duplicate imported command ID '{command.id}': "
                f"{imported[command.id].path} and {command.path}"
            )
        imported[command.id] = command
        if warning:
            warnings.append(warning)

    effective = dict(imported)
    custom_root = definition.directory / "capabilities/custom/commands"
    if custom_root.exists():
        if not custom_root.is_dir():
            raise HarnessiaError(f"{custom_root}: custom commands path must be a directory")
        resolved_root = custom_root.resolve(strict=True)
        if not _is_within(resolved_root, definition.directory.resolve(strict=True)):
            raise HarnessiaError(
                f"{custom_root}: custom commands must be maintained inside the Space"
            )
        for entry in sorted(custom_root.iterdir(), key=lambda item: item.name):
            if entry.name.startswith("."):
                continue
            resolved_entry = entry.resolve(strict=True)
            if not _is_within(resolved_entry, resolved_root):
                raise HarnessiaError(
                    f"{entry}: custom command resolves outside custom commands"
                )
            command, warning = _validate_command(resolved_entry)
            effective[command.id] = command
            if warning:
                warnings.append(warning)

    return CommandInventory(tuple(effective.values()), tuple(warnings))
