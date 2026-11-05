from dataclasses import dataclass
from pathlib import Path

from .layout import CoreLayout, InstanceLayout
from .space import HarnessiaError


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class SourceResolver:
    core: CoreLayout
    instance: InstanceLayout | None = None

    def directory(self, reference: Path, label: str) -> Path:
        parts = reference.parts
        if len(parts) != 2 or parts[0] not in {"core", "instance"}:
            raise HarnessiaError(
                f"{label}.source must match core/<source-id> or instance/<source-id>"
            )
        if parts[0] == "core":
            catalog = self.core.sources
        else:
            if self.instance is None:
                raise HarnessiaError(
                    f"{label}.source '{reference}' requires an owning Instance"
                )
            catalog = self.instance.sources
        source = catalog / parts[1]

        if not source.is_dir():
            raise HarnessiaError(f"{label}.source '{reference}' does not exist")
        resolved_catalog = catalog.resolve(strict=True)
        resolved_source = source.resolve(strict=True)
        if not _is_within(resolved_source, resolved_catalog):
            raise HarnessiaError(
                f"{label}.source '{reference}' resolves outside its owning catalog"
            )
        return resolved_source

    def target(self, reference: Path, path: Path, label: str) -> tuple[Path, Path]:
        source = self.directory(reference, label)
        target = source / path
        if not target.exists():
            raise HarnessiaError(f"{label} '{reference}/{path}' does not exist")
        resolved_target = target.resolve(strict=True)
        if not _is_within(resolved_target, source):
            raise HarnessiaError(f"{label} '{path}' resolves outside its source")
        return source, resolved_target
