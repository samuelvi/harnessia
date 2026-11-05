from dataclasses import dataclass
from pathlib import Path

from .effective import resolve_effective_core, resolve_effective_space
from .instances import consumer_instance_layouts
from .layout import CoreLayout, InstanceLayout
from .projections.base import ProjectionPlan, validate_projection_plans
from .projections.claude import build_claude_plan, build_core_claude_plan
from .projections.opencode import build_opencode_plan, build_core_opencode_plan
from .space import discover_instance_space_ids, load_instance_space


@dataclass(frozen=True)
class SpaceLocation:
    instance: InstanceLayout
    space_id: str

    @property
    def consumer(self) -> str:
        return f"{self.instance.id}/{self.space_id}"


@dataclass(frozen=True)
class ConsumerPlan:
    consumer: str
    definition: Path
    projections: tuple[ProjectionPlan, ...]
    skill_ids: tuple[str, ...]
    agent_ids: tuple[str, ...] = ()
    command_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def discover_instance_spaces(instance: InstanceLayout) -> tuple[SpaceLocation, ...]:
    return tuple(
        SpaceLocation(instance, space_id)
        for space_id in discover_instance_space_ids(instance)
    )


def discover_spaces(core: CoreLayout) -> tuple[SpaceLocation, ...]:
    return tuple(
        location
        for instance in consumer_instance_layouts(core)
        for location in discover_instance_spaces(instance)
    )


def build_core_consumer(core: CoreLayout) -> ConsumerPlan:
    effective = resolve_effective_core(core.directory)
    return ConsumerPlan(
        consumer="core",
        definition=core.directory / "HARNESSIA.md",
        projections=(
            build_core_opencode_plan(effective),
            build_core_claude_plan(effective),
        ),
        skill_ids=effective.skills.ids,
    )


def build_space_consumer(core: CoreLayout, location: SpaceLocation) -> ConsumerPlan:
    effective = resolve_effective_space(
        load_instance_space(core, location.instance, location.space_id)
    )
    return ConsumerPlan(
        consumer=location.consumer,
        definition=effective.definition.directory / "SPACE.md",
        projections=(build_opencode_plan(effective), build_claude_plan(effective)),
        skill_ids=effective.skills.ids,
        agent_ids=effective.agents.ids,
        command_ids=effective.commands.ids,
        warnings=effective.commands.warnings,
    )


def validate_consumers(consumers: tuple[ConsumerPlan, ...]) -> None:
    validate_projection_plans(
        tuple(
            projection
            for consumer in consumers
            for projection in consumer.projections
        )
    )
