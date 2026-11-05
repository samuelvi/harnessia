from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.layout import CoreLayout, InstanceLayout
from app.space import HarnessiaError, load_instance_space


VALID_SPACE = """---
version: 2
skills:
  - source: core/example
    path: skills/example-skill
---

# CTO Management Studio
"""


class SpaceDefinitionTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        root = Path(self.temp.name).resolve()
        self.core = CoreLayout.at(root / "core")
        self.instance = InstanceLayout.at("work", root / "instance")
        self.space = self.instance.spaces / "cto-management-studio"
        self.space.mkdir(parents=True)
        (self.space / "SPACE.md").write_text(VALID_SPACE)

    def tearDown(self):
        self.temp.cleanup()

    def load(self):
        return load_instance_space(
            self.core, self.instance, "cto-management-studio"
        )

    def test_derives_identity_from_instance_and_directory(self):
        definition = self.load()

        self.assertEqual(definition.id, "cto-management-studio")
        self.assertEqual(definition.instance.id, "work")
        self.assertEqual(definition.skills[0].source, Path("core/example"))
        self.assertEqual(definition.agents, ())
        self.assertEqual(definition.commands, ())
        self.assertEqual(definition.mcp_servers, ())

    def test_loads_agent_and_command_references(self):
        (self.space / "SPACE.md").write_text(
            VALID_SPACE.replace(
                "---\n\n# CTO",
                "agents:\n"
                "  - source: instance/example\n"
                "    path: agents/reviewer.md\n"
                "commands:\n"
                "  - source: instance/example\n"
                "    path: commands/review.md\n"
                "---\n\n# CTO",
            )
        )

        definition = self.load()

        self.assertEqual(definition.agents[0].path, Path("agents/reviewer.md"))
        self.assertEqual(definition.commands[0].path, Path("commands/review.md"))

    def test_loads_mcp_allowlist(self):
        (self.space / "SPACE.md").write_text(
            VALID_SPACE.replace(
                "---\n\n# CTO", "mcp:\n  - figma\n  - context7\n---\n\n# CTO"
            )
        )

        self.assertEqual(self.load().mcp_servers, ("figma", "context7"))

    def test_rejects_duplicate_mcp_ids(self):
        (self.space / "SPACE.md").write_text(
            VALID_SPACE.replace(
                "---\n\n# CTO", "mcp:\n  - figma\n  - figma\n---\n\n# CTO"
            )
        )

        with self.assertRaisesRegex(HarnessiaError, "duplicate MCP server ID"):
            self.load()

    def test_rejects_invalid_mcp_id(self):
        (self.space / "SPACE.md").write_text(
            VALID_SPACE.replace(
                "---\n\n# CTO", "mcp:\n  - Context7\n---\n\n# CTO"
            )
        )

        with self.assertRaisesRegex(HarnessiaError, "lowercase MCP server ID"):
            self.load()

    def test_rejects_declarative_identity_fields(self):
        for field in ("id: another-space", "profile: work", "instance: work"):
            with self.subTest(field=field):
                (self.space / "SPACE.md").write_text(
                    VALID_SPACE.replace("version: 2", f"version: 2\n{field}")
                )
                with self.assertRaisesRegex(HarnessiaError, "unsupported field"):
                    self.load()

    def test_rejects_version_one(self):
        (self.space / "SPACE.md").write_text(
            VALID_SPACE.replace("version: 2", "version: 1")
        )

        with self.assertRaisesRegex(HarnessiaError, "version must be 2"):
            self.load()

    def test_rejects_parent_segments_in_capability_paths(self):
        (self.space / "SPACE.md").write_text(
            VALID_SPACE.replace(
                "path: skills/example-skill", "path: ../example-skill"
            )
        )

        with self.assertRaisesRegex(HarnessiaError, "must not contain '..'"):
            self.load()

    def test_rejects_legacy_source_reference(self):
        (self.space / "SPACE.md").write_text(
            VALID_SPACE.replace(
                "core/example", "profiles/common/sources/external/example"
            )
        )

        with self.assertRaisesRegex(HarnessiaError, "core/<source-id>"):
            self.load()

    def test_reports_missing_space_definition(self):
        with self.assertRaisesRegex(HarnessiaError, "Space Definition does not exist"):
            load_instance_space(self.core, self.instance, "missing-space")

    def test_rejects_space_directory_that_escapes_instance(self):
        outside = self.instance.directory.parent / "outside-space"
        outside.mkdir()
        (outside / "SPACE.md").write_text(VALID_SPACE)
        (self.space / "SPACE.md").unlink()
        self.space.rmdir()
        self.space.symlink_to(outside, target_is_directory=True)

        with self.assertRaisesRegex(HarnessiaError, "resolves outside spaces"):
            self.load()


if __name__ == "__main__":
    unittest.main()
