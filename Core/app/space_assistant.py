from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from uuid import uuid4

from .layout import CoreLayout, InstanceLayout
from .prepare import PrepareResult, prepare_instance
from .skill_catalog import build_skill_catalog, render_skill_catalog
from .space import HarnessiaError, load_instance_space, parse_frontmatter


@dataclass(frozen=True)
class ConfigureSpaceResult:
    directory: Path
    catalog: Path
    changed: bool
    preparation: PrepareResult | None


def _artifact_directory(core: CoreLayout, instance_id: str, space_id: str) -> Path:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S.%fZ")
    return (
        core.local_state
        / "space-configure"
        / instance_id
        / space_id
        / f"{now}-{uuid4().hex}"
    )


def _assistant_executable(executable: Path | str | None) -> str:
    if executable is not None:
        return str(executable)
    configured = os.environ.get("HARNESSIA_OPENCODE")
    if configured:
        return configured
    discovered = shutil.which("opencode")
    if discovered is None:
        raise HarnessiaError(
            "OpenCode is required for space-configure; install it or set "
            "HARNESSIA_OPENCODE"
        )
    return discovered


def _prompt(
    definition: Path, catalog: Path, instance_id: str, space_id: str
) -> str:
    return (
        f"Configure the skills for Harnessia Space {instance_id}/{space_id}.\n"
        f"The client-agnostic definition is {definition}.\n"
        f"The local candidate index is {catalog}.\n"
        f"Use skills only from Core and Instance {instance_id}; do not search "
        "external Sources or other Instances. Follow the space-curator agent "
        "workflow, ask only for missing information, and do not edit until the "
        "user explicitly approves the exact selection."
    )


def _replace_definition(path: Path, content: str, mode: int) -> None:
    temporary = path.parent / f".{path.name}-restore-{uuid4().hex}"
    try:
        temporary.write_text(content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except OSError as error:
        raise HarnessiaError(
            f"{path}: cannot restore original Space Definition: {error}"
        ) from error
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def _current_definition(path: Path) -> str | None:
    try:
        if path.is_symlink() or not path.is_file():
            return None
        return path.read_text()
    except OSError:
        return None


def _record_proposal(artifact_directory: Path, content: str | None) -> None:
    if content is None:
        (artifact_directory / "SPACE.proposed-missing.txt").write_text(
            "The assistant removed SPACE.md or made it unreadable.\n"
        )
        return
    (artifact_directory / "SPACE.proposed.md").write_text(content)


def _record_proposal_or_restore(
    artifact_directory: Path,
    definition_path: Path,
    content: str | None,
    before: str,
    before_mode: int,
) -> None:
    try:
        _record_proposal(artifact_directory, content)
    except OSError as error:
        _replace_definition(definition_path, before, before_mode)
        raise HarnessiaError(
            f"{artifact_directory}: cannot record proposed Space Definition; "
            f"the original was restored: {error}"
        ) from error


def _validate_skills_only(before: str, after: str, definition_path: Path) -> None:
    before_data, before_body = parse_frontmatter(before, definition_path)
    after_data, after_body = parse_frontmatter(after, definition_path)
    before_other = {key: value for key, value in before_data.items() if key != "skills"}
    after_other = {key: value for key, value in after_data.items() if key != "skills"}
    if before_body != after_body or before_other != after_other:
        raise HarnessiaError(
            f"{definition_path}: space-configure may change only the skills field"
        )


def configure_space(
    core: CoreLayout,
    instance: InstanceLayout,
    space_id: str,
    *,
    executable: Path | str | None = None,
    require_tty: bool = True,
) -> ConfigureSpaceResult:
    try:
        definition = load_instance_space(core, instance, space_id)
        definition_path = definition.directory / "SPACE.md"
        if definition_path.is_symlink():
            raise HarnessiaError(
                f"{definition_path}: space-configure requires a regular "
                "Space Definition"
            )
        before = definition_path.read_text()
        before_mode = stat.S_IMODE(definition_path.stat().st_mode)
    except OSError as error:
        raise HarnessiaError(f"cannot read Space Definition: {error}") from error

    if require_tty and not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise HarnessiaError(
            "space-configure is interactive and must be run directly in a terminal"
        )

    agent = core.directory / ".opencode/agents/space-curator.md"
    if not agent.is_file() or agent.is_symlink():
        raise HarnessiaError(f"{agent}: Space curator agent is not installed")

    assistant_executable = _assistant_executable(executable)

    artifact_directory = _artifact_directory(core, instance.id, space_id)
    try:
        artifact_directory.mkdir(parents=True)
        catalog_path = artifact_directory / "skills.jsonl"
        catalog_path.write_text(render_skill_catalog(build_skill_catalog(definition)))
        (artifact_directory / "SPACE.before.md").write_text(before)
    except OSError as error:
        raise HarnessiaError(
            f"{artifact_directory}: cannot create configuration artifacts: {error}"
        ) from error

    command = (
        assistant_executable,
        "mini",
        "--agent",
        "space-curator",
        "--prompt",
        _prompt(definition_path, catalog_path, instance.id, space_id),
    )
    try:
        completed = subprocess.run(command, cwd=core.directory)
    except OSError as error:
        after = _current_definition(definition_path)
        if after != before:
            _record_proposal_or_restore(
                artifact_directory,
                definition_path,
                after,
                before,
                before_mode,
            )
            _replace_definition(definition_path, before, before_mode)
        raise HarnessiaError(f"cannot start OpenCode Mini: {error}") from error
    except KeyboardInterrupt as error:
        after = _current_definition(definition_path)
        if after != before:
            _record_proposal_or_restore(
                artifact_directory,
                definition_path,
                after,
                before,
                before_mode,
            )
            _replace_definition(definition_path, before, before_mode)
        raise HarnessiaError("OpenCode Mini was interrupted") from error

    after = _current_definition(definition_path)
    changed = after != before
    if changed:
        _record_proposal_or_restore(
            artifact_directory,
            definition_path,
            after,
            before,
            before_mode,
        )

    if completed.returncode != 0:
        if changed:
            _replace_definition(definition_path, before, before_mode)
        raise HarnessiaError(
            f"OpenCode Mini exited with status {completed.returncode}"
        )

    preparation = None
    if changed:
        try:
            if after is None:
                raise HarnessiaError(
                    f"{definition_path}: assistant removed Space Definition"
                )
            _validate_skills_only(before, after, definition_path)
            preparation = prepare_instance(core, instance, space_id)
        except (Exception, KeyboardInterrupt):
            _replace_definition(definition_path, before, before_mode)
            raise

    return ConfigureSpaceResult(
        directory=definition.directory,
        catalog=catalog_path,
        changed=changed,
        preparation=preparation,
    )
