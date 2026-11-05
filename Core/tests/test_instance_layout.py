from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import unittest

from app.__main__ import main
from app.effective import resolve_effective_space
from app.instances import register_instance
from app.layout import CoreLayout, InstanceLayout
from app.prepare import prepare_all, prepare_instance, prepare_instance_all
from app.space import HarnessiaError, load_instance_space


class InstanceLayoutTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        root = Path(self.temp.name).resolve()
        self.core = CoreLayout.at(root / "core")
        self.instance = InstanceLayout.at("work", root / "instances/company")
        self.core.directory.mkdir()
        self.instance.spaces.mkdir(parents=True)
        self.space = self.instance.spaces / "example-space"
        self.space.mkdir()

        (self.core.directory / "SOUL.md").write_text("# Core soul\n")
        (self.core.directory / "INSTRUCTIONS.md").write_text("# Core instructions\n")
        (self.instance.directory / "SOUL.md").write_text("# Instance soul\n")
        (self.instance.directory / "INSTRUCTIONS.md").write_text(
            "# Instance instructions\n"
        )
        (self.space / "SOUL.md").write_text("# Space soul\n")
        (self.space / "INSTRUCTIONS.md").write_text("# Space instructions\n")
        (self.space / "SPACE.md").write_text(
            """---
version: 2
skills:
  - source: core/example
    path: skills/example-skill
---

# Example
"""
        )
        skill = (
            self.core.directory
            / "sources/example/skills/example-skill"
        )
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: example-skill\ndescription: Example\n---\n\nBody\n"
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_loads_space_from_instance_outside_core(self):
        definition = load_instance_space(
            self.core, self.instance, "example-space"
        )

        self.assertEqual(definition.core, self.core)
        self.assertEqual(definition.instance, self.instance)
        self.assertEqual(definition.directory, self.space)

    def test_prepares_external_instance_with_ordered_context(self):
        (self.space / "MEMORY.md").write_text("# Space memory\n")

        result = prepare_instance(self.core, self.instance, "example-space")

        self.assertEqual(result.skill_ids, ("example-skill",))
        self.assertTrue((self.space / "opencode.jsonc").is_file())
        expected_context = [
            Path(
                os.path.relpath(self.core.directory / "SOUL.md", self.space)
            ).as_posix(),
            "../../SOUL.md",
            "SOUL.md",
            Path(
                os.path.relpath(
                    self.core.directory / "INSTRUCTIONS.md", self.space
                )
            ).as_posix(),
            "../../INSTRUCTIONS.md",
            "INSTRUCTIONS.md",
            "MEMORY.md",
        ]
        self.assertEqual(
            (self.space / "CLAUDE.md").read_text().splitlines()[1:],
            [f"@{path}" for path in expected_context],
        )
        config = json.loads(
            "\n".join((self.space / "opencode.jsonc").read_text().splitlines()[1:])
        )
        self.assertEqual(config["instructions"], expected_context)
        self.assertEqual(len(config["skills"]), 1)
        self.assertEqual(
            (self.space / config["skills"][0]).resolve(),
            self.core.directory
            / "sources/example/skills",
        )
        self.assertEqual(result.log.parent, self.core.logs)

    def test_resolves_context_from_core_through_instance_to_space(self):
        (self.space / "MEMORY.md").write_text("# Space memory\n")

        effective = resolve_effective_space(
            load_instance_space(self.core, self.instance, "example-space")
        )

        self.assertEqual(
            effective.context_paths,
            (
                Path(
                    os.path.relpath(
                        self.core.directory / "SOUL.md", self.space
                    )
                ),
                Path("../../SOUL.md"),
                Path("SOUL.md"),
                Path(
                    os.path.relpath(
                        self.core.directory / "INSTRUCTIONS.md", self.space
                    )
                ),
                Path("../../INSTRUCTIONS.md"),
                Path("INSTRUCTIONS.md"),
                Path("MEMORY.md"),
            ),
        )

    def test_cli_prepares_registered_instance(self):
        register_instance(self.core, "work", self.instance.directory)

        result = main(
            ["prepare", "--instance", "work", "--space", "example-space"],
            directory=self.core.directory,
        )

        self.assertEqual(result, 0)
        self.assertTrue((self.space / "opencode.jsonc").is_file())

    def test_cli_creates_and_prepares_minimal_space(self):
        register_instance(self.core, "Work", self.instance.directory)

        result = main(
            ["space", "create", "Work", "atlas"],
            directory=self.core.directory,
        )

        space = self.instance.spaces / "atlas"
        self.assertEqual(result, 0)
        self.assertEqual(
            (space / "SPACE.md").read_text(),
            "---\nversion: 2\nskills: []\n---\n\n# atlas\n",
        )
        self.assertEqual((space / "SOUL.md").read_text(), "")
        self.assertFalse((space / "SOUL.md").is_symlink())
        self.assertEqual(
            (space / "INSTRUCTIONS.md").read_text(), "# Space Instructions\n"
        )
        self.assertTrue((space / "opencode.jsonc").is_file())
        self.assertTrue((space / "CLAUDE.md").is_file())

    def test_cli_refuses_to_overwrite_existing_space_path(self):
        register_instance(self.core, "Work", self.instance.directory)
        space = self.instance.spaces / "atlas"
        space.mkdir()
        marker = space / "maintained.txt"
        marker.write_text("keep\n")

        result = main(
            ["space", "create", "Work", "atlas"],
            directory=self.core.directory,
        )

        self.assertEqual(result, 1)
        self.assertEqual(marker.read_text(), "keep\n")
        self.assertEqual(tuple(space.iterdir()), (marker,))

    def test_cli_attaches_and_prepares_existing_space_directory(self):
        register_instance(self.core, "Work", self.instance.directory)
        space = self.instance.spaces / "attached-space"
        space.mkdir()
        marker = space / "maintained.txt"
        marker.write_text("keep\n")
        soul = space / "SOUL.md"
        soul.write_text("# Existing Space soul\n")

        result = main(
            ["space", "attach", "Work", "attached-space"],
            directory=self.core.directory,
        )

        self.assertEqual(result, 0)
        self.assertEqual(marker.read_text(), "keep\n")
        self.assertEqual(soul.read_text(), "# Existing Space soul\n")
        self.assertEqual(
            (space / "SPACE.md").read_text(),
            "---\nversion: 2\nskills: []\n---\n\n# attached-space\n",
        )
        self.assertEqual(
            (space / "INSTRUCTIONS.md").read_text(), "# Space Instructions\n"
        )
        self.assertTrue((space / "opencode.jsonc").is_file())
        self.assertTrue((space / "CLAUDE.md").is_file())

    def test_cli_attach_rolls_back_only_new_space_files_on_failure(self):
        register_instance(self.core, "Work", self.instance.directory)
        space = self.instance.spaces / "attached-space"
        space.mkdir()
        marker = space / "maintained.txt"
        marker.write_text("keep\n")
        soul = space / "SOUL.md"
        soul.write_text("# Existing Space soul\n")
        (self.core.directory / "INSTRUCTIONS.md").unlink()

        result = main(
            ["space", "attach", "Work", "attached-space"],
            directory=self.core.directory,
        )

        self.assertEqual(result, 1)
        self.assertEqual(marker.read_text(), "keep\n")
        self.assertEqual(soul.read_text(), "# Existing Space soul\n")
        self.assertFalse((space / "SPACE.md").exists())
        self.assertFalse((space / "INSTRUCTIONS.md").exists())

    def test_cli_attach_rejects_maintained_file_collision_before_writing(self):
        register_instance(self.core, "Work", self.instance.directory)
        space = self.instance.spaces / "attached-space"
        space.mkdir()
        marker = space / "maintained.txt"
        marker.write_text("keep\n")
        soul = space / "SOUL.md"
        soul.symlink_to(marker)

        result = main(
            ["space", "attach", "Work", "attached-space"],
            directory=self.core.directory,
        )

        self.assertEqual(result, 1)
        self.assertTrue(soul.is_symlink())
        self.assertEqual(soul.resolve(), marker)
        self.assertFalse((space / "SPACE.md").exists())
        self.assertFalse((space / "INSTRUCTIONS.md").exists())

    def test_cli_removes_new_space_when_preparation_fails(self):
        register_instance(self.core, "Work", self.instance.directory)
        (self.core.directory / "INSTRUCTIONS.md").unlink()

        result = main(
            ["space", "create", "Work", "atlas"],
            directory=self.core.directory,
        )

        self.assertEqual(result, 1)
        self.assertFalse((self.instance.spaces / "atlas").exists())

    def test_cli_prepares_every_space_in_registered_instance(self):
        register_instance(self.core, "work", self.instance.directory)

        result = main(
            ["prepare-instance", "work"],
            directory=self.core.directory,
        )

        self.assertEqual(result, 0)
        self.assertTrue((self.space / "opencode.jsonc").is_file())

    def test_prepare_all_includes_registered_instances(self):
        (self.core.directory / "HARNESSIA.md").write_text(
            "---\nversion: 1\nskills: []\n---\n\n# Core\n"
        )
        register_instance(self.core, "work", self.instance.directory)

        result = prepare_all(self.core.directory)

        self.assertEqual(len(result.spaces), 1)
        self.assertEqual(result.spaces[0].skill_ids, ("example-skill",))
        self.assertTrue((self.space / "opencode.jsonc").is_file())

    def test_prepare_all_validates_every_consumer_before_writing(self):
        (self.core.directory / "HARNESSIA.md").write_text(
            "---\nversion: 1\nskills: []\n---\n\n# Core\n"
        )
        invalid = self.instance.spaces / "invalid-space"
        invalid.mkdir()
        (invalid / "SPACE.md").write_text(
            "---\nversion: 2\nskills: []\n---\n\n# Invalid\n"
        )
        register_instance(self.core, "work", self.instance.directory)

        with self.assertRaises(HarnessiaError):
            prepare_all(self.core.directory)

        self.assertFalse((self.core.directory / ".opencode/skills").exists())
        self.assertFalse((self.space / "opencode.jsonc").exists())

    def test_prepare_instance_all_validates_every_space_before_writing(self):
        invalid = self.instance.spaces / "invalid-space"
        invalid.mkdir()
        (invalid / "SPACE.md").write_text(
            "---\nversion: 2\nskills: []\n---\n\n# Invalid\n"
        )

        with self.assertRaises(HarnessiaError):
            prepare_instance_all(self.core, self.instance)

        self.assertFalse((self.space / "opencode.jsonc").exists())


if __name__ == "__main__":
    unittest.main()
