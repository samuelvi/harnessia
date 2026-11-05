from dataclasses import dataclass
from pathlib import Path

from .instances import consumer_instance_layouts, registered_instance
from .layout import CoreLayout, InstanceLayout


@dataclass(frozen=True)
class SourceIdentity:
    owner: str | None
    source_id: str

    @classmethod
    def from_selection(
        cls, reference: Path, instance: InstanceLayout | None = None
    ) -> "SourceIdentity":
        scope, source_id = reference.parts
        if scope == "core":
            return cls(None, source_id)
        if instance is None:
            raise ValueError(f"{reference}: Instance Source has no owning Instance")
        return cls(instance.id, source_id)

    @classmethod
    def from_reference(cls, reference: Path) -> "SourceIdentity":
        parts = reference.parts
        if len(parts) == 2 and parts[0] == "core":
            return cls(None, parts[1])
        if len(parts) == 3 and parts[0] == "instance":
            return cls(parts[1], parts[2])
        raise ValueError(f"{reference}: invalid global Source reference")

    @property
    def reference(self) -> Path:
        if self.owner is None:
            return Path("core", self.source_id)
        return Path("instance", self.owner, self.source_id)

    def directory(self, core: CoreLayout) -> Path:
        if self.owner is None:
            return core.sources / self.source_id
        return registered_instance(core, self.owner).layout.sources / self.source_id


@dataclass(frozen=True)
class SourceLocation:
    identity: SourceIdentity
    directory: Path

    @property
    def reference(self) -> Path:
        return self.identity.reference


def source_locations(core: CoreLayout) -> tuple[SourceLocation, ...]:
    locations: dict[SourceIdentity, Path] = {}

    if core.sources.is_dir():
        for source in core.sources.iterdir():
            if source.is_dir():
                locations[SourceIdentity(None, source.name)] = source

    for instance in consumer_instance_layouts(core):
        if not instance.sources.is_dir():
            continue
        for source in instance.sources.iterdir():
            if source.is_dir():
                locations[SourceIdentity(instance.id, source.name)] = source

    return tuple(
        SourceLocation(identity, locations[identity])
        for identity in sorted(
            locations, key=lambda item: item.reference.as_posix()
        )
    )


def source_location_map(core: CoreLayout) -> dict[Path, Path]:
    return {location.reference: location.directory for location in source_locations(core)}


def source_directory(core: CoreLayout, reference: Path) -> Path:
    return SourceIdentity.from_reference(reference).directory(core)
