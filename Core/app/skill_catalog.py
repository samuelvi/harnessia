from dataclasses import dataclass
import json
from pathlib import Path

from .capabilities.skills import load_skill
from .source_bootstrap import load_instance_source_manifest, load_source_manifest
from .space import HarnessiaError, PORTABLE_ID, SpaceDefinition


@dataclass(frozen=True)
class SkillCandidate:
    source: Path
    path: Path
    id: str
    description: str
    definition: Path
    selected: bool
    pinned: bool


@dataclass(frozen=True)
class SkillCatalog:
    skills: tuple[SkillCandidate, ...]
    skipped: tuple[str, ...]


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _source_roots(definition: SpaceDefinition) -> tuple[tuple[Path, Path], ...]:
    roots: list[tuple[Path, Path]] = []
    for scope, directory in (
        ("core", definition.core.sources),
        ("instance", definition.instance.sources),
    ):
        if not directory.is_dir() or directory.is_symlink():
            continue
        for source in sorted(directory.iterdir(), key=lambda item: item.name):
            if (
                source.is_dir()
                and not source.is_symlink()
                and PORTABLE_ID.fullmatch(source.name)
            ):
                roots.append((Path(scope, source.name), source))
    return tuple(roots)


def build_skill_catalog(definition: SpaceDefinition) -> SkillCatalog:
    selected = {
        (reference.source.as_posix(), reference.path.as_posix())
        for reference in definition.skills
    }
    candidates: list[SkillCandidate] = []
    skipped: list[str] = []
    pinned = {
        ("core", spec.source_id)
        for spec in load_source_manifest(definition.core.directory)
    }
    pinned.update(
        ("instance", spec.source_id)
        for spec in load_instance_source_manifest(definition.instance)
    )

    for source_reference, source_directory in _source_roots(definition):
        resolved_source = source_directory.resolve(strict=True)
        for skill_file in sorted(source_directory.rglob("SKILL.md")):
            relative_file = skill_file.relative_to(source_directory)
            if ".git" in relative_file.parts or skill_file.is_symlink():
                continue
            skill_directory = skill_file.parent
            try:
                resolved_skill = skill_directory.resolve(strict=True)
                if not _is_within(resolved_skill, resolved_source):
                    continue
                skill = load_skill(resolved_skill)
            except (HarnessiaError, OSError) as error:
                skipped.append(f"{skill_file}: {error}")
                continue
            relative_skill = skill_directory.relative_to(source_directory)
            candidates.append(
                SkillCandidate(
                    source=source_reference,
                    path=relative_skill,
                    id=skill.id,
                    description=skill.description,
                    definition=skill_file.resolve(),
                    selected=(
                        source_reference.as_posix(), relative_skill.as_posix()
                    )
                    in selected,
                    pinned=(source_reference.parts[0], source_reference.parts[1])
                    in pinned,
                )
            )

    return SkillCatalog(
        skills=tuple(
            sorted(
                candidates,
                key=lambda item: (
                    item.source.as_posix(),
                    item.path.as_posix(),
                    item.id,
                ),
            )
        ),
        skipped=tuple(skipped),
    )


def render_skill_catalog(catalog: SkillCatalog) -> str:
    return "".join(
        json.dumps(
            {
                "source": candidate.source.as_posix(),
                "path": candidate.path.as_posix(),
                "id": candidate.id,
                "description": candidate.description,
                "definition": candidate.definition.as_posix(),
                "selected": candidate.selected,
                "pinned": candidate.pinned,
                "source_state": "pinned" if candidate.pinned else "local",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
        for candidate in catalog.skills
    )
