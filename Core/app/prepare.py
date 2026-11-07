from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .layout import CoreLayout, InstanceLayout
from .orchestration import (
    ConsumerPlan,
    SpaceLocation,
    build_core_consumer,
    build_space_consumer,
    discover_instance_spaces,
    discover_spaces,
    validate_consumers,
)
from .projections.base import apply_projection_plans
from .space import HarnessiaError


@dataclass(frozen=True)
class PrepareResult:
    projections: tuple[Path, ...]
    log: Path
    skill_ids: tuple[str, ...]
    agent_ids: tuple[str, ...]
    command_ids: tuple[str, ...]


@dataclass(frozen=True)
class PrepareAllResult:
    core: PrepareResult
    spaces: tuple[PrepareResult, ...]

    @property
    def projections(self) -> tuple[Path, ...]:
        return self.core.projections + tuple(
            projection for result in self.spaces for projection in result.projections
        )


class RunLog:
    def __init__(self, core: CoreLayout, space_id: str):
        now = datetime.now(timezone.utc)
        filename = f"{now.strftime('%Y-%m-%dT%H%M%S.%fZ')}-prepare-{space_id}.log"
        self.path = core.logs / filename
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, level: str, message: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        line = f"{timestamp} {level} {message}"
        print(line)
        with self.path.open("a") as handle:
            handle.write(line + "\n")

    def info(self, message: str) -> None:
        self.write("INFO", message)

    def warning(self, message: str) -> None:
        self.write("WARNING", message)


def _space_id_from_reference(reference: str) -> str:
    candidate = Path(reference).name
    return candidate if candidate and candidate not in {".", ".."} else "unknown"


def _apply_space_consumer(core: CoreLayout, consumer: ConsumerPlan) -> PrepareResult:
    log = RunLog(core, _space_id_from_reference(consumer.consumer))
    log.info(f"Starting preparation for {consumer.consumer}")

    def complete() -> None:
        for plan in consumer.projections:
            log.info(f"Generated {plan.client} projection")
        log.info("Preparation completed")

    try:
        log.info(f"Validated Space Definition {consumer.definition}")
        log.info(f"Validated {len(consumer.skill_ids)} effective skills")
        log.info(f"Validated {len(consumer.agent_ids)} effective agents")
        log.info(f"Validated {len(consumer.command_ids)} effective commands")
        for warning in consumer.warnings:
            log.warning(warning)
        apply_projection_plans(consumer.projections, after_write=complete)
        return PrepareResult(
            projections=tuple(
                target
                for plan in consumer.projections
                for target in plan.targets
                if target.exists() or target.is_symlink()
            ),
            log=log.path,
            skill_ids=consumer.skill_ids,
            agent_ids=consumer.agent_ids,
            command_ids=consumer.command_ids,
        )
    except (HarnessiaError, OSError) as error:
        log.warning(str(error))
        log.warning("Preparation stopped; no partial projection was written")
        if isinstance(error, HarnessiaError):
            raise
        raise HarnessiaError(str(error)) from error


def prepare_instance(
    core: CoreLayout, instance: InstanceLayout, space_id: str
) -> PrepareResult:
    reference = f"{instance.id}/{space_id}"
    try:
        consumer = build_space_consumer(core, SpaceLocation(instance, space_id))
    except (HarnessiaError, OSError) as error:
        log = RunLog(core, _space_id_from_reference(reference))
        log.info(f"Starting preparation for {reference}")
        log.warning(str(error))
        log.warning("Preparation stopped; no partial projection was written")
        if isinstance(error, HarnessiaError):
            raise
        raise HarnessiaError(str(error)) from error
    return _apply_space_consumer(core, consumer)


def prepare_instance_all(
    core: CoreLayout, instance: InstanceLayout
) -> tuple[PrepareResult, ...]:
    consumers = tuple(
        build_space_consumer(core, location)
        for location in discover_instance_spaces(instance)
    )
    validate_consumers(consumers)
    return tuple(_apply_space_consumer(core, consumer) for consumer in consumers)


def _apply_core_consumer(
    core: CoreLayout, consumer: ConsumerPlan
) -> PrepareResult:
    log = RunLog(core, "core")
    log.info("Starting preparation for Core")

    def complete() -> None:
        for plan in consumer.projections:
            log.info(f"Generated {plan.client} projection")
        log.info("Core preparation completed")

    try:
        log.info(f"Validated Core Definition {consumer.definition}")
        log.info(f"Validated {len(consumer.skill_ids)} effective Core skills")
        apply_projection_plans(consumer.projections, after_write=complete)
        return PrepareResult(
            projections=tuple(
                target
                for plan in consumer.projections
                for target in plan.targets
                if target.exists() or target.is_symlink()
            ),
            log=log.path,
            skill_ids=consumer.skill_ids,
            agent_ids=(),
            command_ids=(),
        )
    except (HarnessiaError, OSError) as error:
        log.warning(str(error))
        log.warning("Core preparation stopped; no partial projection was written")
        if isinstance(error, HarnessiaError):
            raise
        raise HarnessiaError(str(error)) from error


def prepare_core(directory: Path) -> PrepareResult:
    core = CoreLayout.at(directory)
    try:
        consumer = build_core_consumer(core)
    except (HarnessiaError, OSError) as error:
        log = RunLog(core, "core")
        log.info("Starting preparation for Core")
        log.warning(str(error))
        log.warning("Core preparation stopped; no partial projection was written")
        if isinstance(error, HarnessiaError):
            raise
        raise HarnessiaError(str(error)) from error
    return _apply_core_consumer(core, consumer)


def prepare_all(directory: Path) -> PrepareAllResult:
    core = CoreLayout.at(directory)
    core_consumer = build_core_consumer(core)
    space_consumers = tuple(
        build_space_consumer(core, location) for location in discover_spaces(core)
    )
    validate_consumers((core_consumer, *space_consumers))
    return PrepareAllResult(
        core=_apply_core_consumer(core, core_consumer),
        spaces=tuple(
            _apply_space_consumer(core, consumer) for consumer in space_consumers
        ),
    )
