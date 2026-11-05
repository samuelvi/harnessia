from dataclasses import dataclass
from pathlib import Path

from ..space import (
    CapabilityReference,
    HarnessiaError,
    PORTABLE_ID,
    SpaceDefinition,
    parse_frontmatter,
)
from ..source_resolver import SourceResolver


@dataclass(frozen=True)
class Skill:
    id: str
    directory: Path
    description: str


@dataclass(frozen=True)
class SkillInventory:
    skills: tuple[Skill, ...]
    catalog_roots: tuple[Path, ...]

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(skill.id for skill in self.skills)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def load_skill(directory: Path, *, custom: bool = False) -> Skill:
    definition = directory / "SKILL.md"
    if not definition.is_file():
        raise HarnessiaError(f"{directory}: skill must contain SKILL.md directly")
    data, _ = parse_frontmatter(definition.read_text(), definition)
    for field in ("name", "description"):
        if field not in data:
            raise HarnessiaError(f"{definition}: missing required field '{field}'")
    name = data["name"]
    if (
        not isinstance(name, str)
        or len(name) > 64
        or not PORTABLE_ID.fullmatch(name)
    ):
        raise HarnessiaError(
            f"{definition}: name must be 1-64 lowercase letters, digits and hyphens"
        )
    if custom and name != directory.name:
        raise HarnessiaError(
            f"{definition}: name '{name}' must match directory '{directory.name}'"
        )
    description = data["description"]
    if (
        not isinstance(description, str)
        or not description.strip()
        or len(description) > 1024
    ):
        raise HarnessiaError(
            f"{definition}: description must be non-empty and at most 1024 characters"
        )
    return Skill(id=name, directory=directory, description=description)


def resolve_imported_skills(
    resolver: SourceResolver, references: tuple[CapabilityReference, ...]
) -> SkillInventory:
    imported: dict[str, Skill] = {}
    catalogs: list[Path] = []

    for index, reference in enumerate(references):
        _, resolved_target = resolver.target(
            reference.source, reference.path, f"skills[{index}]"
        )
        skill = load_skill(resolved_target)
        if skill.id in imported:
            previous = imported[skill.id].directory
            raise HarnessiaError(
                f"duplicate imported skill ID '{skill.id}': {previous} and "
                f"{skill.directory}"
            )
        imported[skill.id] = skill
        catalog = resolved_target.parent
        if catalog not in catalogs:
            catalogs.append(catalog)

    return SkillInventory(
        skills=tuple(imported.values()), catalog_roots=tuple(catalogs)
    )


def resolve_skills(definition: SpaceDefinition) -> SkillInventory:
    imported_inventory = resolve_imported_skills(
        SourceResolver(definition.core, definition.instance), definition.skills
    )
    imported = {skill.id: skill for skill in imported_inventory.skills}
    catalogs = list(imported_inventory.catalog_roots)

    effective = dict(imported)
    custom_root = definition.directory / "capabilities/custom/skills"
    custom_found = False
    if custom_root.exists():
        if not custom_root.is_dir():
            raise HarnessiaError(f"{custom_root}: custom skills path must be a directory")
        resolved_custom_root = custom_root.resolve(strict=True)
        if not _is_within(resolved_custom_root, definition.directory.resolve(strict=True)):
            raise HarnessiaError(
                f"{custom_root}: custom skills must be maintained inside the Space"
            )
        for entry in sorted(custom_root.iterdir(), key=lambda item: item.name):
            if entry.name.startswith("."):
                continue
            if not entry.is_dir() or not (entry / "SKILL.md").is_file():
                raise HarnessiaError(
                    f"{entry}: custom skill directory must contain SKILL.md directly"
                )
            resolved_entry = entry.resolve(strict=True)
            if not _is_within(resolved_entry, resolved_custom_root):
                raise HarnessiaError(
                    f"{entry}: custom skill resolves outside custom skills"
                )
            skill = load_skill(resolved_entry, custom=True)
            effective[skill.id] = skill
            custom_found = True
    if custom_found:
        catalogs.append(custom_root)

    return SkillInventory(skills=tuple(effective.values()), catalog_roots=tuple(catalogs))
