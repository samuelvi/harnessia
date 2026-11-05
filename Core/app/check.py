from dataclasses import dataclass

from .instances import consumer_instance_layouts
from .layout import CoreLayout, InstanceLayout
from .orchestration import (
    build_core_consumer,
    build_space_consumer,
    discover_instance_spaces,
    validate_consumers,
)
from .space import HarnessiaError


@dataclass(frozen=True)
class CheckedSpace:
    consumer: str
    skills: int
    agents: int
    commands: int


@dataclass(frozen=True)
class CheckInstanceResult:
    instance_id: str
    spaces: tuple[CheckedSpace, ...]


@dataclass(frozen=True)
class CheckAllResult:
    core_skills: int
    instances: tuple[CheckInstanceResult, ...]

    @property
    def spaces(self) -> tuple[CheckedSpace, ...]:
        return tuple(space for instance in self.instances for space in instance.spaces)


def check_instance(
    core: CoreLayout, instance: InstanceLayout
) -> CheckInstanceResult:
    checked: list[CheckedSpace] = []
    errors: list[str] = []
    for location in discover_instance_spaces(instance):
        try:
            plan = build_space_consumer(core, location)
            validate_consumers((plan,))
            checked.append(
                CheckedSpace(
                    consumer=plan.consumer,
                    skills=len(plan.skill_ids),
                    agents=len(plan.agent_ids),
                    commands=len(plan.command_ids),
                )
            )
        except (HarnessiaError, OSError) as error:
            errors.append(f"{location.consumer}: {error}")
    if errors:
        raise HarnessiaError(
            f"Instance '{instance.id}' check failed:\n" + "\n".join(errors)
        )
    return CheckInstanceResult(instance.id, tuple(checked))


def check_all(core: CoreLayout) -> CheckAllResult:
    core_consumer = build_core_consumer(core)
    validate_consumers((core_consumer,))
    return CheckAllResult(
        core_skills=len(core_consumer.skill_ids),
        instances=tuple(
            check_instance(core, instance)
            for instance in consumer_instance_layouts(core)
        ),
    )


def render_instance_check(result: CheckInstanceResult) -> str:
    lines = [
        f"Validated Instance {result.instance_id}: {len(result.spaces)} Spaces without writing."
    ]
    lines.extend(
        f"  {space.consumer}: {space.skills} skills, {space.agents} agents, "
        f"{space.commands} commands"
        for space in result.spaces
    )
    return "\n".join(lines)


def render_all_check(result: CheckAllResult) -> str:
    lines = [
        f"Validated Core ({result.core_skills} skills), "
        f"{len(result.instances)} Instances "
        f"and {len(result.spaces)} Spaces without writing."
    ]
    for instance in result.instances:
        lines.append(render_instance_check(instance))
    return "\n".join(lines)
