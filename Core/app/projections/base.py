from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import os
import shutil
from uuid import uuid4

from ..space import HarnessiaError


@dataclass(frozen=True)
class ProjectionPlan:
    client: str
    targets: tuple[Path, ...]
    validate: Callable[[], None]
    write: Callable[[], None]


def _present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _remove(path: Path) -> None:
    if not _present(path):
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def validate_projection_plans(plans: tuple[ProjectionPlan, ...]) -> None:
    targets = tuple(target for plan in plans for target in plan.targets)
    if len(set(targets)) != len(targets):
        raise HarnessiaError("projection plans contain duplicate targets")
    for target in targets:
        for other in targets:
            if target == other:
                continue
            try:
                target.relative_to(other)
            except ValueError:
                continue
            raise HarnessiaError(
                f"projection target {target} is nested under managed target {other}"
            )

    for plan in plans:
        plan.validate()


def apply_projection_plans(plans: tuple[ProjectionPlan, ...]) -> None:
    validate_projection_plans(plans)
    targets = tuple(target for plan in plans for target in plan.targets)

    backups: list[tuple[Path, Path | None]] = []
    try:
        for target in targets:
            backup = None
            if _present(target):
                backup = target.parent / f".{target.name}-prepare-backup-{uuid4().hex}"
                os.replace(target, backup)
            backups.append((target, backup))
        for plan in plans:
            plan.write()
    except (HarnessiaError, OSError):
        for target, backup in reversed(backups):
            _remove(target)
            if backup is not None and _present(backup):
                os.replace(backup, target)
        raise
    else:
        for _, backup in backups:
            if backup is not None:
                _remove(backup)
