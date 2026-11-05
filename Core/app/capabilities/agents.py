from dataclasses import dataclass
from pathlib import Path

from ..space import HarnessiaError, PORTABLE_ID, SpaceDefinition, parse_frontmatter
from ..source_resolver import SourceResolver


@dataclass(frozen=True)
class Agent:
    id: str
    path: Path


@dataclass(frozen=True)
class AgentInventory:
    agents: tuple[Agent, ...]

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(agent.id for agent in self.agents)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _validate_agent(path: Path) -> Agent:
    if path.suffix != ".md" or not path.is_file():
        raise HarnessiaError(f"{path}: agent must be a Markdown file")
    agent_id = path.stem
    if len(agent_id) > 64 or not PORTABLE_ID.fullmatch(agent_id):
        raise HarnessiaError(
            f"{path}: agent filename must use 1-64 lowercase letters, digits and hyphens"
        )
    data, _ = parse_frontmatter(path.read_text(), path)
    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        raise HarnessiaError(f"{path}: agent description is required")
    mode = data.get("mode")
    if mode not in {"primary", "subagent", "all"}:
        raise HarnessiaError(
            f"{path}: agent mode must be 'primary', 'subagent', or 'all'"
        )
    return Agent(id=agent_id, path=path)


def resolve_agents(definition: SpaceDefinition) -> AgentInventory:
    imported: dict[str, Agent] = {}
    resolver = SourceResolver(definition.core, definition.instance)
    for index, reference in enumerate(definition.agents):
        _, resolved_target = resolver.target(
            reference.source, reference.path, f"agents[{index}]"
        )
        agent = _validate_agent(resolved_target)
        if agent.id in imported:
            raise HarnessiaError(
                f"duplicate imported agent ID '{agent.id}': "
                f"{imported[agent.id].path} and {agent.path}"
            )
        imported[agent.id] = agent

    effective = dict(imported)
    custom_root = definition.directory / "capabilities/custom/agents"
    if custom_root.exists():
        if not custom_root.is_dir():
            raise HarnessiaError(f"{custom_root}: custom agents path must be a directory")
        resolved_root = custom_root.resolve(strict=True)
        if not _is_within(resolved_root, definition.directory.resolve(strict=True)):
            raise HarnessiaError(
                f"{custom_root}: custom agents must be maintained inside the Space"
            )
        for entry in sorted(custom_root.iterdir(), key=lambda item: item.name):
            if entry.name.startswith("."):
                continue
            resolved_entry = entry.resolve(strict=True)
            if not _is_within(resolved_entry, resolved_root):
                raise HarnessiaError(
                    f"{entry}: custom agent resolves outside custom agents"
                )
            agent = _validate_agent(resolved_entry)
            effective[agent.id] = agent

    return AgentInventory(agents=tuple(effective.values()))
