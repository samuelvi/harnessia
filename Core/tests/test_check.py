from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.check import check_all, check_instance
from app.instances import register_instance
from app.layout import CoreLayout, InstanceLayout
from app.space import HarnessiaError


class ReadOnlyCheckTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        root = Path(self.temp.name).resolve()
        self.core = CoreLayout.at(root / "core")
        self.instance = InstanceLayout.at("client", root / "instance")
        self.core.directory.mkdir()
        self.instance.spaces.mkdir(parents=True)
        (self.instance.directory / "sources/example/skills/example-skill").mkdir(
            parents=True
        )
        (self.core.directory / "SOUL.md").write_text("# Core soul\n")
        (self.core.directory / "INSTRUCTIONS.md").write_text("# Core instructions\n")
        (self.core.directory / "HARNESSIA.md").write_text(
            "---\nversion: 1\nskills: []\n---\n\n# Core\n"
        )
        (self.core.directory / "SOURCES.yaml").write_text("version: 2\nsources: []\n")
        (self.instance.directory / "SOURCES.yaml").write_text(
            "version: 2\nsources: []\n"
        )
        skill = (
            self.instance.directory
            / "sources/example/skills/example-skill/SKILL.md"
        )
        skill.write_text(
            "---\nname: example-skill\ndescription: Example\n---\n\nBody\n"
        )
        self.space = self.instance.spaces / "example-space"
        self.space.mkdir()
        (self.space / "SOUL.md").write_text("")
        (self.space / "INSTRUCTIONS.md").write_text("# Space\n")
        (self.space / "SPACE.md").write_text(
            """---
version: 2
skills:
  - source: instance/example
    path: skills/example-skill
---

# Example
"""
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_instance_check_builds_plans_without_writing(self):
        result = check_instance(self.core, self.instance)

        self.assertEqual(result.spaces[0].skills, 1)
        self.assertFalse((self.space / "opencode.jsonc").exists())
        self.assertFalse((self.space / "CLAUDE.md").exists())

    def test_all_check_includes_registered_instance_without_writing(self):
        register_instance(self.core, "client", self.instance.directory)

        result = check_all(self.core)

        self.assertEqual(result.core_skills, 0)
        self.assertEqual(len(result.instances), 1)
        self.assertEqual(result.spaces[0].consumer, "client/example-space")
        self.assertFalse((self.space / "opencode.jsonc").exists())

    def test_all_check_without_registry_ignores_external_instances(self):
        (self.space / "SPACE.md").write_text("invalid unregistered Definition\n")

        result = check_all(self.core)

        self.assertEqual(result.core_skills, 0)
        self.assertEqual(result.instances, ())
        self.assertEqual(result.spaces, ())
        self.assertFalse((self.core.directory / ".harnessia/instances.yaml").exists())
        self.assertFalse((self.space / "opencode.jsonc").exists())

    def test_instance_check_rejects_projection_ownership_conflict_without_writing(self):
        manual = self.space / "CLAUDE.md"
        manual.write_text("# Maintained manually\n")

        with self.assertRaisesRegex(HarnessiaError, "not managed by Harnessia"):
            check_instance(self.core, self.instance)

        self.assertEqual(manual.read_text(), "# Maintained manually\n")
        self.assertFalse((self.space / "opencode.jsonc").exists())

    def test_all_check_validates_core_projection_ownership_without_writing(self):
        skills = self.core.directory / ".opencode/skills"
        skills.mkdir(parents=True)
        (skills / "manual").write_text("manual\n")

        with self.assertRaisesRegex(HarnessiaError, "not managed by Harnessia"):
            check_all(self.core)

        self.assertEqual((skills / "manual").read_text(), "manual\n")


if __name__ == "__main__":
    unittest.main()
