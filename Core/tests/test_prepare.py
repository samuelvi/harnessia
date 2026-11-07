from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from app.prepare import prepare_instance
from app.layout import CoreLayout, InstanceLayout
from app.projections.opencode import GENERATED_MARKER
from app.space import HarnessiaError


def write_skill(directory: Path, name: str) -> None:
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test {name}\n---\n\nBody\n"
    )


class PrepareTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve() / "Core"
        self.root.mkdir()
        (self.root / "SOUL.md").write_text("# Soul\n")
        (self.root / "INSTRUCTIONS.md").write_text("# Shared instructions\n")
        self.core = CoreLayout.at(self.root)
        self.instance = InstanceLayout.at("work", self.root / "instance")
        self.space = self.instance.spaces / "example-space"
        self.space.mkdir(parents=True)
        (self.space / "SOUL.md").write_text("")
        (self.space / "INSTRUCTIONS.md").write_text("# Instructions\n")
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
        write_skill(
            self.root / "sources/example/skills/example-skill",
            "example-skill",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_prepares_projection_and_logs_process(self):
        terminal = StringIO()

        with redirect_stdout(terminal):
            result = prepare_instance(self.core, self.instance, "example-space")

        self.assertEqual(result.skill_ids, ("example-skill",))
        self.assertEqual(result.log.parent, self.root / "logs")
        self.assertFalse((self.root.parent / "docs").exists())
        self.assertTrue((self.space / "opencode.jsonc").is_file())
        self.assertEqual(
            (self.space / "CLAUDE.md").read_text().splitlines()[1:],
            [
                "@../../../SOUL.md",
                "@SOUL.md",
                "@../../../INSTRUCTIONS.md",
                "@INSTRUCTIONS.md",
            ],
        )
        skill = self.space / ".claude/skills/example-skill"
        self.assertTrue(skill.is_symlink())
        self.assertFalse(skill.readlink().is_absolute())
        self.assertEqual(
            skill.resolve(),
            self.root
            / "sources/example/skills/example-skill",
        )
        settings = json.loads((self.space / ".claude/settings.json").read_text())
        self.assertEqual(settings["permissions"]["deny"], ["mcp__*"])
        self.assertEqual(
            json.loads((self.space / ".claude/harnessia-mcp.json").read_text()),
            {"mcpServers": {}},
        )
        self.assertIn("INFO Starting preparation", terminal.getvalue())
        self.assertIn("INFO Generated claude projection", terminal.getvalue())
        logs = list(
            (self.root / "logs").glob("*-prepare-example-space.log")
        )
        self.assertEqual(len(logs), 1)
        log_text = logs[0].read_text()
        self.assertIn("INFO Validated 1 effective skills", log_text)
        self.assertIn("INFO Preparation completed", log_text)

    def test_validation_failure_is_logged_and_does_not_write_projection(self):
        (self.space / "INSTRUCTIONS.md").unlink()

        with self.assertRaises(HarnessiaError):
            prepare_instance(self.core, self.instance, "example-space")

        self.assertFalse((self.space / "opencode.jsonc").exists())
        logs = list(
            (self.root / "logs").glob("*-prepare-example-space.log")
        )
        self.assertEqual(len(logs), 1)
        self.assertIn("WARNING Preparation stopped", logs[0].read_text())

    def test_selected_mcp_only_enables_opencode_and_keeps_claude_empty(self):
        definition = self.space / "SPACE.md"
        definition.write_text(definition.read_text().replace(
            "---\n\n# Example", "mcp: [playwright, context7]\n---\n\n# Example"
        ))

        prepare_instance(self.core, self.instance, "example-space")

        config = json.loads((self.space / "opencode.jsonc").read_text().split("\n", 1)[1])
        self.assertEqual(config["policies"], [
            {"action": "integration.use", "resource": "mcp:*", "effect": "deny"},
            {"action": "integration.use", "resource": "mcp:playwright", "effect": "allow"},
            {"action": "integration.use", "resource": "mcp:context7", "effect": "allow"},
        ])
        self.assertEqual(json.loads(
            (self.space / ".claude/harnessia-mcp.json").read_text()
        ), {"mcpServers": {}})
        settings = json.loads((self.space / ".claude/settings.json").read_text())
        self.assertEqual(settings["permissions"]["deny"], ["mcp__*"])

    def test_prepares_selected_agents_as_native_links(self):
        agent = self.instance.sources / "example/agents/reviewer.md"
        agent.parent.mkdir(parents=True)
        agent.write_text(
            "---\ndescription: Reviews changes\nmode: subagent\n---\n\nReview.\n"
        )
        definition = self.space / "SPACE.md"
        definition.write_text(
            definition.read_text().replace(
                "---\n\n# Example",
                "agents:\n"
                "  - source: instance/example\n"
                "    path: agents/reviewer.md\n"
                "---\n\n# Example",
            )
        )

        result = prepare_instance(self.core, self.instance, "example-space")

        self.assertEqual(result.agent_ids, ("reviewer",))
        link = self.space / ".opencode/agents/reviewer.md"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), agent)

    def test_prepares_selected_commands_as_native_links(self):
        command = self.instance.sources / "example/commands/review.md"
        command.parent.mkdir(parents=True)
        command.write_text("Review $ARGUMENTS.\n")
        definition = self.space / "SPACE.md"
        definition.write_text(
            definition.read_text().replace(
                "---\n\n# Example",
                "commands:\n"
                "  - source: instance/example\n"
                "    path: commands/review.md\n"
                "---\n\n# Example",
            )
        )

        result = prepare_instance(self.core, self.instance, "example-space")

        self.assertEqual(result.command_ids, ("review",))
        link = self.space / ".opencode/commands/review.md"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), command)

    def test_manual_agent_directory_blocks_all_projection_changes(self):
        projection = self.space / "opencode.jsonc"
        previous = GENERATED_MARKER + '\n{"previous": true}\n'
        projection.write_text(previous)
        agents = self.space / ".opencode/agents"
        agents.mkdir(parents=True)
        (agents / "manual.md").write_text("manual")

        with self.assertRaisesRegex(HarnessiaError, "not managed by Harnessia"):
            prepare_instance(self.core, self.instance, "example-space")

        self.assertEqual(projection.read_text(), previous)

    def test_manual_claude_file_blocks_all_projection_changes(self):
        projection = self.space / "opencode.jsonc"
        previous = GENERATED_MARKER + '\n{"previous": true}\n'
        projection.write_text(previous)
        (self.space / "CLAUDE.md").write_text("manual\n")

        with self.assertRaisesRegex(HarnessiaError, "not managed by Harnessia"):
            prepare_instance(self.core, self.instance, "example-space")

        self.assertEqual(projection.read_text(), previous)
        self.assertEqual((self.space / "CLAUDE.md").read_text(), "manual\n")

    def test_agent_write_failure_restores_previous_config(self):
        projection = self.space / "opencode.jsonc"
        previous = GENERATED_MARKER + '\n{"previous": true}\n'
        projection.write_text(previous)

        with patch(
            "app.projections.opencode.write_agents", side_effect=OSError("disk full")
        ):
            with self.assertRaisesRegex(HarnessiaError, "disk full"):
                prepare_instance(self.core, self.instance, "example-space")

        self.assertEqual(projection.read_text(), previous)

    def test_command_write_failure_restores_all_previous_projections(self):
        agent_source = self.instance.sources / "example/agents"
        command_source = self.instance.sources / "example/commands"
        agent_source.mkdir(parents=True)
        command_source.mkdir(parents=True)
        (agent_source / "old-agent.md").write_text(
            "---\ndescription: Old agent\nmode: subagent\n---\n\nOld.\n"
        )
        (command_source / "old-command.md").write_text("Old command.\n")
        definition = self.space / "SPACE.md"
        definition.write_text(
            definition.read_text().replace(
                "---\n\n# Example",
                "agents:\n"
                "  - source: instance/example\n"
                "    path: agents/old-agent.md\n"
                "commands:\n"
                "  - source: instance/example\n"
                "    path: commands/old-command.md\n"
                "---\n\n# Example",
            )
        )
        prepare_instance(self.core, self.instance, "example-space")
        projection = self.space / "opencode.jsonc"
        previous_projection = projection.read_bytes()
        claude = self.space / "CLAUDE.md"
        previous_claude = claude.read_bytes()

        (agent_source / "new-agent.md").write_text(
            "---\ndescription: New agent\nmode: subagent\n---\n\nNew.\n"
        )
        (command_source / "new-command.md").write_text("New command.\n")
        definition.write_text(
            definition.read_text()
            .replace("agents/old-agent.md", "agents/new-agent.md")
            .replace("commands/old-command.md", "commands/new-command.md")
        )

        with patch(
            "app.projections.opencode.write_commands", side_effect=OSError("disk full")
        ):
            with self.assertRaisesRegex(HarnessiaError, "disk full"):
                prepare_instance(self.core, self.instance, "example-space")

        self.assertEqual(projection.read_bytes(), previous_projection)
        self.assertEqual(claude.read_bytes(), previous_claude)
        agents = self.space / ".opencode/agents"
        commands = self.space / ".opencode/commands"
        self.assertTrue((agents / "old-agent.md").is_symlink())
        self.assertFalse((agents / "new-agent.md").exists())
        self.assertTrue((commands / "old-command.md").is_symlink())
        self.assertFalse((commands / "new-command.md").exists())

if __name__ == "__main__":
    unittest.main()
