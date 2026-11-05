from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from app.prepare import prepare_core
from app.projections.claude import CORE_PLUGIN_MARKER
from app.projections.native import CORE_SKILL_MARKER
from app.space import HarnessiaError


def write_skill(directory: Path, name: str) -> None:
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test {name}\n---\n\nBody\n"
    )


class CorePrepareTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "sources/example"
        write_skill(self.source / "skills/one", "one")
        write_skill(self.source / "skills/two", "two")
        self.write_definition(("skills/one",))
        self.write_plugin(("skills/one",))

    def tearDown(self):
        self.temp.cleanup()

    def write_definition(self, paths: tuple[str, ...]) -> None:
        references = "".join(
            "  - source: core/example\n"
            f"    path: {path}\n"
            for path in paths
        )
        (self.root / "HARNESSIA.md").write_text(
            f"---\nversion: 1\nskills:\n{references}---\n\n# Core\n"
        )

    def write_plugin(
        self, paths: tuple[str, ...], **components: object
    ) -> None:
        manifest = self.source / ".claude-plugin/plugin.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, object] = {
            "name": "example-plugin",
            "version": "1.0.0",
            "skills": [f"./{path}" for path in paths],
        }
        data.update(components)
        manifest.write_text(json.dumps(data))

    def test_prepares_relative_opencode_links_and_namespaced_claude_plugin(self):
        result = prepare_core(self.root)

        self.assertEqual(result.skill_ids, ("one",))
        opencode = self.root / ".opencode/skills"
        claude = self.root / ".claude/skills"
        self.assertEqual(
            (opencode / ".harnessia-generated").read_text(), CORE_SKILL_MARKER
        )
        self.assertEqual(
            (claude / ".harnessia-generated").read_text(), CORE_PLUGIN_MARKER
        )
        self.assertEqual((opencode / "one").resolve(), self.source / "skills/one")
        claude_skill = claude / "harnessia-core/skills/one"
        self.assertEqual(claude_skill.resolve(), self.source / "skills/one")
        self.assertEqual(
            json.loads(
                (claude / "harnessia-core/.claude-plugin/plugin.json").read_text()
            )["name"],
            "harnessia-core",
        )
        self.assertFalse((opencode / "one").readlink().is_absolute())
        self.assertFalse(claude_skill.readlink().is_absolute())

    def test_source_plugin_cannot_broaden_core_selection(self):
        self.write_plugin(("skills/one", "skills/two"))

        prepare_core(self.root)

        plugin = self.root / ".claude/skills/harnessia-core"
        manifest = json.loads(
            (plugin / ".claude-plugin/plugin.json").read_text()
        )
        self.assertEqual(manifest["skills"], ["./skills/one"])
        self.assertTrue((plugin / "skills/one").is_symlink())
        self.assertFalse((plugin / "skills/two").exists())

    def test_does_not_require_source_plugin_manifest(self):
        (self.source / ".claude-plugin/plugin.json").unlink()

        result = prepare_core(self.root)

        self.assertEqual(result.skill_ids, ("one",))
        self.assertEqual(
            (self.root / ".claude/skills/harnessia-core/skills/one").resolve(),
            self.source / "skills/one",
        )

    def test_ignores_source_plugin_manifest_that_escapes_source(self):
        plugin_directory = self.source / ".claude-plugin"
        manifest_content = (plugin_directory / "plugin.json").read_text()
        (plugin_directory / "plugin.json").unlink()
        plugin_directory.rmdir()
        outside = self.root / "outside-plugin"
        outside.mkdir()
        (outside / "plugin.json").write_text(manifest_content)
        plugin_directory.symlink_to(outside, target_is_directory=True)

        prepare_core(self.root)

        self.assertTrue(
            (self.root / ".claude/skills/harnessia-core/skills/one").is_symlink()
        )

    def test_source_plugin_fields_cannot_add_components(self):
        self.write_plugin(("skills/one",), agents=["./agents/reviewer.md"])

        prepare_core(self.root)

        manifest = json.loads(
            (
                self.root
                / ".claude/skills/harnessia-core/.claude-plugin/plugin.json"
            ).read_text()
        )
        self.assertNotIn("agents", manifest)

    def test_source_default_components_are_not_projected(self):
        commands = self.source / "commands"
        commands.mkdir()
        (commands / "review.md").write_text("Review.\n")

        prepare_core(self.root)

        self.assertFalse(
            (self.root / ".claude/skills/harnessia-core/commands").exists()
        )

    def test_manual_core_skill_directory_blocks_both_clients(self):
        target = self.root / ".opencode/skills"
        target.mkdir(parents=True)
        (target / "manual").write_text("manual")

        with self.assertRaisesRegex(HarnessiaError, "not managed by Harnessia"):
            prepare_core(self.root)

        self.assertFalse((self.root / ".claude/skills").exists())

    def test_second_adapter_failure_restores_both_previous_projections(self):
        prepare_core(self.root)
        old_opencode = (self.root / ".opencode/skills/one").resolve()
        old_claude = (
            self.root / ".claude/skills/harnessia-core/skills/one"
        ).resolve()
        self.write_definition(("skills/two",))
        self.write_plugin(("skills/two",))

        with patch(
            "app.projections.claude._write_core_plugin",
            side_effect=OSError("disk full"),
        ):
            with self.assertRaisesRegex(HarnessiaError, "disk full"):
                prepare_core(self.root)

        self.assertEqual((self.root / ".opencode/skills/one").resolve(), old_opencode)
        self.assertFalse((self.root / ".opencode/skills/two").exists())
        self.assertEqual(
            (self.root / ".claude/skills/harnessia-core/skills/one").resolve(),
            old_claude,
        )


if __name__ == "__main__":
    unittest.main()
