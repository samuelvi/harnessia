from dataclasses import dataclass
from pathlib import Path
import re


INSTANCE_ID = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")


@dataclass(frozen=True)
class CoreLayout:
    directory: Path

    @classmethod
    def at(cls, directory: Path) -> "CoreLayout":
        return cls(directory.resolve())

    @property
    def local_state(self) -> Path:
        return self.directory / ".harnessia"

    @property
    def logs(self) -> Path:
        return self.directory / "logs"

    @property
    def sources(self) -> Path:
        return self.directory / "sources"

    @property
    def source_manifest(self) -> Path:
        return self.directory / "SOURCES.yaml"


@dataclass(frozen=True)
class InstanceLayout:
    id: str
    directory: Path
    spaces: Path

    @classmethod
    def at(cls, instance_id: str, directory: Path) -> "InstanceLayout":
        resolved = directory.resolve()
        return cls(id=instance_id, directory=resolved, spaces=resolved / "spaces")

    @property
    def sources(self) -> Path:
        return self.directory / "sources"

    @property
    def source_manifest(self) -> Path:
        return self.directory / "SOURCES.yaml"

    @property
    def local_state(self) -> Path:
        return self.directory / ".harnessia"
