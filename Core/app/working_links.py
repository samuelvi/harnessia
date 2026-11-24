from dataclasses import dataclass
from pathlib import Path

import yaml

from .layout import InstanceLayout
from .space import HarnessiaError, PORTABLE_ID, SpaceDefinition


DEFAULT_WORKING_LINKS = ("project", "documentation")
RESERVED_NAMES = {"capabilities", "docs", "work"}
MANIFEST_NAME = "WORKING_LINKS.yaml"


@dataclass(frozen=True)
class WorkingLink:
    path: Path
    target: Path


def load_working_link_names(instance: InstanceLayout) -> tuple[str, ...]:
    manifest = instance.directory / MANIFEST_NAME
    if not manifest.exists() and not manifest.is_symlink():
        return DEFAULT_WORKING_LINKS
    if manifest.is_symlink() or not manifest.is_file():
        raise HarnessiaError(f"{manifest}: working link manifest must be a regular file")
    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise HarnessiaError(f"{manifest}: cannot read working link manifest: {error}") from error
    if not isinstance(data, dict) or set(data) != {"version", "names"}:
        raise HarnessiaError(f"{manifest}: expected a mapping with version and names")
    if type(data["version"]) is not int or data["version"] != 1:
        raise HarnessiaError(f"{manifest}: version must be the integer 1")
    if not isinstance(data["names"], list):
        raise HarnessiaError(f"{manifest}: names must be a list")

    names = list(DEFAULT_WORKING_LINKS)
    for index, name in enumerate(data["names"]):
        if not isinstance(name, str) or not PORTABLE_ID.fullmatch(name):
            raise HarnessiaError(f"{manifest}: names[{index}] must be a lowercase portable ID")
        if name in RESERVED_NAMES or name in names:
            raise HarnessiaError(f"{manifest}: duplicate or reserved working link name '{name}'")
        names.append(name)
    return tuple(names)


def resolve_working_links(definition: SpaceDefinition) -> tuple[WorkingLink, ...]:
    links = []
    for name in load_working_link_names(definition.instance):
        link = definition.directory / name
        if not link.is_symlink():
            if link.exists():
                raise HarnessiaError(f"{link}: {name} must be a symbolic link")
            continue
        try:
            target = link.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise HarnessiaError(f"{link}: {name} link is broken or cannot be resolved") from error
        if not target.is_dir():
            raise HarnessiaError(f"{link}: {name} must resolve to a directory")
        if target.is_relative_to(definition.directory.resolve()):
            raise HarnessiaError(f"{link}: {name} must resolve outside the Space directory")
        links.append(WorkingLink(link, target))
    return tuple(links)
