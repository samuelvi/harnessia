from dataclasses import dataclass
from pathlib import Path

from .capabilities.agents import AgentInventory, resolve_agents
from .capabilities.commands import CommandInventory, resolve_commands
from .capabilities.skills import (
    SkillInventory,
    resolve_imported_skills,
    resolve_skills,
)
from .context import resolve_context_paths
from .layout import CoreLayout
from .core import CoreDefinition, load_core_definition
from .space import SpaceDefinition
from .source_resolver import SourceResolver


@dataclass(frozen=True)
class EffectiveSpace:
    definition: SpaceDefinition
    context_paths: tuple[Path, ...]
    skills: SkillInventory
    agents: AgentInventory
    commands: CommandInventory


@dataclass(frozen=True)
class EffectiveCoreContext:
    definition: CoreDefinition
    skills: SkillInventory


def resolve_effective_space(definition: SpaceDefinition) -> EffectiveSpace:
    context_paths = resolve_context_paths(definition)
    return EffectiveSpace(
        definition=definition,
        context_paths=context_paths,
        skills=resolve_skills(definition),
        agents=resolve_agents(definition),
        commands=resolve_commands(definition),
    )


def resolve_effective_core(directory: Path) -> EffectiveCoreContext:
    definition = load_core_definition(directory)
    return EffectiveCoreContext(
        definition=definition,
        skills=resolve_imported_skills(
            SourceResolver(CoreLayout.at(definition.directory)), definition.skills
        ),
    )
