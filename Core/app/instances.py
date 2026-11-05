from dataclasses import dataclass
from pathlib import Path
import os
import tempfile

import yaml

from .layout import INSTANCE_ID, CoreLayout, InstanceLayout
from .space import HarnessiaError


REGISTRY_VERSION = 1
REGISTRY_FIELDS = {"version", "instances"}
INSTANCE_FIELDS = {"id", "path"}


@dataclass(frozen=True)
class RegisteredInstance:
    id: str
    path: Path

    @property
    def layout(self) -> InstanceLayout:
        return InstanceLayout.at(self.id, self.path)

    @property
    def state(self) -> str:
        if not self.path.exists():
            return "missing"
        if not self.path.is_dir() or self.path.is_symlink():
            return "invalid"
        spaces = self.path / "spaces"
        if not spaces.is_dir() or spaces.is_symlink():
            return "invalid"
        return "available"


def registry_path(core: CoreLayout) -> Path:
    return core.local_state / "instances.yaml"


def _exact_fields(data: dict, fields: set[str], label: str) -> None:
    unknown = set(data) - fields
    if unknown:
        raise HarnessiaError(f"{label}: unsupported field '{sorted(unknown)[0]}'")
    missing = fields - set(data)
    if missing:
        raise HarnessiaError(f"{label}: missing required field '{sorted(missing)[0]}'")


def _instance_id(value: object, label: str) -> str:
    if not isinstance(value, str) or not INSTANCE_ID.fullmatch(value):
        raise HarnessiaError(
            f"{label}: Instance ID must use letters, digits and single hyphens"
        )
    return value


def _absolute_path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value or "\0" in value or "\n" in value:
        raise HarnessiaError(f"{label}: path must be a non-empty single-line string")
    path = Path(value)
    if not path.is_absolute():
        raise HarnessiaError(f"{label}: path must be absolute")
    return path.resolve()


def load_instance_registry(core: CoreLayout) -> tuple[RegisteredInstance, ...]:
    path = registry_path(core)
    if not path.exists() and not path.is_symlink():
        return ()
    if not path.is_file() or path.is_symlink():
        raise HarnessiaError(f"{path}: Instance registry must be a regular file")
    try:
        data = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as error:
        raise HarnessiaError(f"{path}: cannot read Instance registry: {error}") from error
    if not isinstance(data, dict):
        raise HarnessiaError(f"{path}: Instance registry must be a mapping")
    _exact_fields(data, REGISTRY_FIELDS, str(path))
    if data["version"] != REGISTRY_VERSION:
        raise HarnessiaError(f"{path}: version must be {REGISTRY_VERSION}")
    if not isinstance(data["instances"], list):
        raise HarnessiaError(f"{path}: instances must be a list")

    instances: list[RegisteredInstance] = []
    ids: set[str] = set()
    paths: set[Path] = set()
    for index, raw in enumerate(data["instances"]):
        label = f"{path}: instances[{index}]"
        if not isinstance(raw, dict):
            raise HarnessiaError(f"{label}: entry must be a mapping")
        _exact_fields(raw, INSTANCE_FIELDS, label)
        instance_id = _instance_id(raw["id"], f"{label}.id")
        instance_path = _absolute_path(raw["path"], f"{label}.path")
        if instance_id in ids:
            raise HarnessiaError(f"{label}.id: duplicate Instance ID '{instance_id}'")
        if instance_path in paths:
            raise HarnessiaError(f"{label}.path: duplicate Instance path '{instance_path}'")
        ids.add(instance_id)
        paths.add(instance_path)
        instances.append(RegisteredInstance(instance_id, instance_path))
    return tuple(instances)


def _write_instance_registry(
    core: CoreLayout, instances: tuple[RegisteredInstance, ...]
) -> None:
    path = registry_path(core)
    directory = path.parent
    _validate_registry_directory(directory)
    directory.mkdir(parents=True, exist_ok=True)
    content = yaml.safe_dump(
        {
            "version": REGISTRY_VERSION,
            "instances": [
                {"id": instance.id, "path": instance.path.as_posix()}
                for instance in instances
            ],
        },
        sort_keys=False,
    )
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory, delete=False
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def register_instance(
    core: CoreLayout, instance_id: str, path: Path
) -> RegisteredInstance:
    registered, updated = _registration_update(core, instance_id, path)
    _write_instance_registry(core, updated)
    return registered


def preflight_instance_registration(
    core: CoreLayout, instance_id: str, path: Path
) -> RegisteredInstance:
    registered, _ = _registration_update(core, instance_id, path)
    return registered


def _registration_update(
    core: CoreLayout, instance_id: str, path: Path
) -> tuple[RegisteredInstance, tuple[RegisteredInstance, ...]]:
    instance_id = _instance_id(instance_id, "Instance ID")
    if not path.is_absolute():
        raise HarnessiaError("Instance path must be absolute")
    registered = RegisteredInstance(instance_id, path.resolve())
    _validate_registry_directory(registry_path(core).parent)
    current = load_instance_registry(core)
    for instance in current:
        if instance.id != instance_id and instance.path == registered.path:
            if instance.id.casefold() == instance_id.casefold():
                continue
            raise HarnessiaError(
                f"Instance path '{registered.path}' is already registered as "
                f"'{instance.id}'"
            )
    updated = tuple(
        instance
        for instance in current
        if instance.id != instance_id and instance.path != registered.path
    )
    updated += (registered,)
    return registered, tuple(sorted(updated, key=lambda instance: instance.id))


def _validate_registry_directory(directory: Path) -> None:
    if directory.exists() or directory.is_symlink():
        if not directory.is_dir() or directory.is_symlink():
            raise HarnessiaError(
                f"{directory}: local state path must be a regular directory"
            )


def registered_instance(core: CoreLayout, instance_id: str) -> RegisteredInstance:
    instance_id = _instance_id(instance_id, "Instance ID")
    for instance in load_instance_registry(core):
        if instance.id == instance_id:
            return instance
    raise HarnessiaError(f"Instance '{instance_id}' is not registered")


def consumer_instance_layouts(core: CoreLayout) -> tuple[InstanceLayout, ...]:
    registered = load_instance_registry(core)
    unavailable = tuple(
        instance for instance in registered if instance.state != "available"
    )
    if unavailable:
        details = "\n".join(
            f"{instance.id}: {instance.state} ({instance.path})"
            for instance in unavailable
        )
        raise HarnessiaError(f"Registered Instances are unavailable:\n{details}")

    return tuple(instance.layout for instance in registered)


def render_instance_registry(instances: tuple[RegisteredInstance, ...]) -> str:
    if not instances:
        return "No Instances registered."
    return "\n".join(
        f"{instance.id} | {instance.state} | {instance.path}"
        for instance in instances
    )
