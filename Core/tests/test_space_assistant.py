from pathlib import Path
from tempfile import TemporaryDirectory
import os
import json
import subprocess
import unittest
from unittest.mock import patch

from app.__main__ import main
from app.instances import register_instance
from app.layout import CoreLayout, InstanceLayout
from app.prepare import prepare_instance
from app.space_assistant import configure_space
from app.space import HarnessiaError, parse_frontmatter


ROOT = Path(__file__).resolve().parents[1]


def write_skill(directory: Path, name: str, description: str) -> None:
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\nBody\n"
    )


class SpaceAssistantTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.core = CoreLayout.at(self.root / "Core")
        self.instance = InstanceLayout.at("Work", self.root / "Work")
        self.space = self.instance.spaces / "atlas"
        self.core.directory.mkdir()
        self.space.mkdir(parents=True)
        self.instance.sources.mkdir()
        (self.core.directory / "SOUL.md").write_text("# Core soul\n")
        (self.core.directory / "INSTRUCTIONS.md").write_text(
            "# Core instructions\n"
        )
        (self.core.directory / "SOURCES.yaml").write_text(
            "version: 2\nsources: []\n"
        )
        (self.instance.directory / "SOURCES.yaml").write_text(
            "version: 2\nsources: []\n"
        )
        (self.space / "SPACE.md").write_text(
            "---\nversion: 2\nskills: []\n---\n\n# Atlas\n"
        )
        (self.space / "SOUL.md").write_text("")
        (self.space / "INSTRUCTIONS.md").write_text("# Instructions\n")
        agent = self.core.directory / ".opencode/agents/space-curator.md"
        agent.parent.mkdir(parents=True)
        agent.write_text("fixture\n")
        write_skill(
            self.core.sources / "shared/skills/design",
            "design",
            "Design systems",
        )

    def tearDown(self):
        self.temp.cleanup()

    def fake_opencode(self, body: str = "exit 0\n") -> Path:
        executable = self.root / "fake-opencode"
        executable.write_text("#!/bin/sh\n"
            'if [ "$1" = "api" ]; then\n'
            '  printf \'%s\\n\' \'{"data":[{"name":"playwright","status":{"status":"connected"}}]}\'\n'
            '  exit 0\nfi\n' + body)
        executable.chmod(0o755)
        return executable

    def test_launches_curator_with_local_skill_index(self):
        capture = self.root / "arguments.txt"
        executable = self.fake_opencode(
            'printf "%s\\n" "$@" > "$FAKE_CAPTURE"\nexit 0\n'
        )
        previous = os.environ.get("FAKE_CAPTURE")
        os.environ["FAKE_CAPTURE"] = str(capture)
        try:
            result = configure_space(
                self.core,
                self.instance,
                "atlas",
                executable=executable,
                require_tty=False,
            )
        finally:
            if previous is None:
                os.environ.pop("FAKE_CAPTURE", None)
            else:
                os.environ["FAKE_CAPTURE"] = previous

        arguments = capture.read_text().splitlines()
        self.assertEqual(arguments[:3], ["mini", "--agent", "space-curator"])
        self.assertEqual(arguments[3], "--prompt")
        prompt = "\n".join(arguments[4:])
        self.assertIn("Work/atlas", prompt)
        self.assertIn("Core and Instance Work", prompt)
        self.assertFalse(result.changed)
        self.assertTrue(result.catalog.is_file())
        self.assertEqual(
            result.catalog.parent.parent,
            self.core.directory / ".harnessia/space-configure/Work/atlas",
        )
        self.assertFalse((self.core.directory / ".work").exists())
        catalog = result.catalog.read_text()
        self.assertIn('"source": "core/shared"', catalog)
        self.assertNotIn("Sandbox", catalog)
        self.assertIn("MCP", prompt)
        self.assertIn("mcp-inventory.json", prompt)
        self.assertIn("mcp-guide.md", prompt)
        inventory = json.loads((result.catalog.parent / "mcp-inventory.json").read_text())
        self.assertEqual(inventory["servers"], [{"id": "playwright", "status": "connected"}])

    def test_prepares_approved_mcp_selection_without_installing_servers(self):
        executable = self.fake_opencode(
            "cat > \"$FAKE_SPACE\" <<'EOF'\n"
            "---\nversion: 2\nskills: []\nmcp: [playwright, not-installed]\n---\n\n# Atlas\n"
            "EOF\n"
        )
        with patch.dict(os.environ, {"FAKE_SPACE": str(self.space / "SPACE.md")}):
            result = configure_space(self.core, self.instance, "atlas",
                                     executable=executable, require_tty=False)
        self.assertTrue(result.changed)
        config = (self.space / "opencode.jsonc").read_text()
        self.assertIn("mcp:not-installed", config)
        self.assertNotIn('"servers"', config)
        self.assertEqual(json.loads((self.space / ".claude/harnessia-mcp.json").read_text()),
                         {"mcpServers": {}})

    def test_unavailable_inventory_does_not_block_curation(self):
        executable = self.fake_opencode()
        with patch("app.space_assistant.read_mcp_inventory", return_value={
            "available": False, "servers": []
        }):
            result = configure_space(self.core, self.instance, "atlas",
                                     executable=executable, require_tty=False)
        inventory = json.loads((result.catalog.parent / "mcp-inventory.json").read_text())
        self.assertFalse(inventory["available"])
        self.assertFalse(result.changed)

    def test_invalid_mcp_or_unrelated_fields_restore_definition_and_projections(self):
        prepare_instance(self.core, self.instance, "atlas")
        definition = self.space / "SPACE.md"
        before = definition.read_text()
        targets = (self.space / "opencode.jsonc", self.space / ".claude/settings.json",
                   self.space / ".claude/harnessia-mcp.json")
        output_before = [path.read_bytes() for path in targets]
        for field in ("mcp: [playwright, playwright]", "mcp: [INVALID]",
                      "agents: []", "commands: []", "version: 1"):
            with self.subTest(field=field):
                proposal = before.replace("skills: []", "skills: []\n" + field)
                executable = self.fake_opencode(
                    "cat > \"$FAKE_SPACE\" <<'EOF'\n" + proposal + "EOF\n"
                )
                with patch.dict(os.environ, {"FAKE_SPACE": str(definition)}):
                    with self.assertRaises(HarnessiaError):
                        configure_space(self.core, self.instance, "atlas",
                                        executable=executable, require_tty=False)
                self.assertEqual(definition.read_text(), before)
                self.assertEqual([path.read_bytes() for path in targets], output_before)

    def test_mcp_edit_rolls_back_when_claude_projection_cannot_be_written(self):
        prepare_instance(self.core, self.instance, "atlas")
        definition = self.space / "SPACE.md"
        before = definition.read_text()
        opencode_before = (self.space / "opencode.jsonc").read_bytes()
        executable = self.fake_opencode(
            "cat > \"$FAKE_SPACE\" <<'EOF'\n" +
            before.replace("skills: []", "skills: []\nmcp: [playwright]") + "EOF\n"
        )
        with patch.dict(os.environ, {"FAKE_SPACE": str(definition)}), patch(
            "app.projections.claude._write_text", side_effect=OSError("disk full")
        ):
            with self.assertRaisesRegex(HarnessiaError, "disk full"):
                configure_space(self.core, self.instance, "atlas",
                                executable=executable, require_tty=False)
        self.assertEqual(definition.read_text(), before)
        self.assertEqual((self.space / "opencode.jsonc").read_bytes(), opencode_before)

    def test_prepares_approved_space_definition_after_assistant_exits(self):
        executable = self.fake_opencode(
            "cat > \"$FAKE_SPACE\" <<'EOF'\n"
            "---\nversion: 2\nskills:\n"
            "  - source: core/shared\n"
            "    path: skills/design\n"
            "---\n\n# Atlas\n"
            "EOF\n"
            "exit 0\n"
        )
        previous = os.environ.get("FAKE_SPACE")
        os.environ["FAKE_SPACE"] = str(self.space / "SPACE.md")
        try:
            result = configure_space(
                self.core,
                self.instance,
                "atlas",
                executable=executable,
                require_tty=False,
            )
        finally:
            if previous is None:
                os.environ.pop("FAKE_SPACE", None)
            else:
                os.environ["FAKE_SPACE"] = previous

        self.assertTrue(result.changed)
        self.assertIsNotNone(result.preparation)
        self.assertEqual(result.preparation.skill_ids, ("design",))
        self.assertTrue((self.space / "opencode.jsonc").is_file())
        self.assertTrue((self.space / "CLAUDE.md").is_file())
        self.assertEqual(
            (result.catalog.parent / "SPACE.proposed.md").read_text(),
            (self.space / "SPACE.md").read_text(),
        )

    def test_restores_definition_when_approved_selection_is_invalid(self):
        prepare_instance(self.core, self.instance, "atlas")
        opencode_before = (self.space / "opencode.jsonc").read_text()
        claude_before = (self.space / "CLAUDE.md").read_text()
        original = (self.space / "SPACE.md").read_text()
        executable = self.fake_opencode(
            "cat > \"$FAKE_SPACE\" <<'EOF'\n"
            "---\nversion: 2\n---\n\n# Atlas\n"
            "EOF\n"
            "exit 0\n"
        )
        previous = os.environ.get("FAKE_SPACE")
        os.environ["FAKE_SPACE"] = str(self.space / "SPACE.md")
        try:
            with self.assertRaisesRegex(
                HarnessiaError, "missing required field 'skills'"
            ):
                configure_space(
                    self.core,
                    self.instance,
                    "atlas",
                    executable=executable,
                    require_tty=False,
                )
        finally:
            if previous is None:
                os.environ.pop("FAKE_SPACE", None)
            else:
                os.environ["FAKE_SPACE"] = previous

        self.assertEqual((self.space / "SPACE.md").read_text(), original)
        attempts = tuple(
            (self.core.directory / ".harnessia/space-configure/Work/atlas").glob(
                "*/SPACE.proposed.md"
            )
        )
        self.assertEqual(len(attempts), 1)
        self.assertNotIn("skills", attempts[0].read_text())
        self.assertEqual((self.space / "opencode.jsonc").read_text(), opencode_before)
        self.assertEqual((self.space / "CLAUDE.md").read_text(), claude_before)

    def test_restores_definition_when_assistant_exits_unsuccessfully(self):
        original = (self.space / "SPACE.md").read_text()
        executable = self.fake_opencode(
            "printf '%s' '# interrupted proposal' > \"$FAKE_SPACE\"\n"
            "exit 23\n"
        )
        with patch.dict(os.environ, {"FAKE_SPACE": str(self.space / "SPACE.md")}):
            with self.assertRaisesRegex(HarnessiaError, "exited with status 23"):
                configure_space(
                    self.core,
                    self.instance,
                    "atlas",
                    executable=executable,
                    require_tty=False,
                )

        self.assertEqual((self.space / "SPACE.md").read_text(), original)
        attempts = tuple(
            (self.core.directory / ".harnessia/space-configure/Work/atlas").glob(
                "*/SPACE.proposed.md"
            )
        )
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].read_text(), "# interrupted proposal")

    def test_restores_definition_when_interactive_session_is_interrupted(self):
        original = (self.space / "SPACE.md").read_text()

        def interrupt(*args, **kwargs):
            if args[0][1] == "api":
                return subprocess.CompletedProcess(args[0], 0, '{"data": []}', "")
            (self.space / "SPACE.md").write_text("# interrupted proposal")
            raise KeyboardInterrupt

        with patch("app.space_assistant.subprocess.run", side_effect=interrupt):
            with self.assertRaisesRegex(HarnessiaError, "was interrupted"):
                configure_space(
                    self.core,
                    self.instance,
                    "atlas",
                    executable=self.fake_opencode(),
                    require_tty=False,
                )

        self.assertEqual((self.space / "SPACE.md").read_text(), original)

    def test_restores_definition_when_proposal_changes_body(self):
        original = (self.space / "SPACE.md").read_text()
        executable = self.fake_opencode(
            "cat > \"$FAKE_SPACE\" <<'EOF'\n"
            "---\nversion: 2\nskills:\n"
            "  - source: core/shared\n"
            "    path: skills/design\n"
            "---\n\n# Changed body\n"
            "EOF\n"
        )
        with patch.dict(os.environ, {"FAKE_SPACE": str(self.space / "SPACE.md")}):
            with self.assertRaisesRegex(
                HarnessiaError, "may change only the skills and mcp fields"
            ):
                configure_space(
                    self.core,
                    self.instance,
                    "atlas",
                    executable=executable,
                    require_tty=False,
                )

        self.assertEqual((self.space / "SPACE.md").read_text(), original)
        self.assertFalse((self.space / "opencode.jsonc").exists())

    def test_restores_definition_when_assistant_removes_it(self):
        original = (self.space / "SPACE.md").read_text()
        executable = self.fake_opencode('rm "$FAKE_SPACE"\n')
        with patch.dict(os.environ, {"FAKE_SPACE": str(self.space / "SPACE.md")}):
            with self.assertRaisesRegex(HarnessiaError, "removed Space Definition"):
                configure_space(
                    self.core,
                    self.instance,
                    "atlas",
                    executable=executable,
                    require_tty=False,
                )

        self.assertEqual((self.space / "SPACE.md").read_text(), original)
        markers = tuple(
            (self.core.directory / ".harnessia/space-configure/Work/atlas").glob(
                "*/SPACE.proposed-missing.txt"
            )
        )
        self.assertEqual(len(markers), 1)

    def test_requires_interactive_terminal(self):
        with (
            patch("app.space_assistant.sys.stdin.isatty", return_value=True),
            patch("app.space_assistant.sys.stdout.isatty", return_value=False),
        ):
            with self.assertRaisesRegex(HarnessiaError, "must be run directly"):
                configure_space(
                    self.core,
                    self.instance,
                    "atlas",
                    executable=self.fake_opencode(),
                )

        self.assertFalse((self.core.directory / ".harnessia").exists())

    def test_reports_missing_opencode_executable(self):
        with patch("app.space_assistant.shutil.which", return_value=None):
            with self.assertRaisesRegex(HarnessiaError, "OpenCode is required"):
                configure_space(
                    self.core,
                    self.instance,
                    "atlas",
                    require_tty=False,
                )

    def test_rejects_missing_space_before_starting_assistant(self):
        with self.assertRaisesRegex(HarnessiaError, "Space Definition does not exist"):
            configure_space(
                self.core,
                self.instance,
                "missing",
                executable=self.fake_opencode(),
                require_tty=False,
            )

    def test_cli_configures_registered_space(self):
        register_instance(self.core, "Work", self.instance.directory)
        executable = self.fake_opencode()

        with (
            patch.dict(os.environ, {"HARNESSIA_OPENCODE": str(executable)}),
            patch("app.space_assistant.sys.stdin.isatty", return_value=True),
            patch("app.space_assistant.sys.stdout.isatty", return_value=True),
        ):
            result = main(
                ["space", "configure", "Work", "atlas"],
                directory=self.core.directory,
            )

        self.assertEqual(result, 0)


class SpaceCuratorAgentTest(unittest.TestCase):
    def test_agent_requires_approval_and_denies_external_tools(self):
        path = ROOT / ".opencode/agents/space-curator.md"
        data, body = parse_frontmatter(path.read_text(), path)
        permissions = {
            permission["action"]: permission["effect"]
            for permission in data["permissions"]
        }

        self.assertEqual(data["mode"], "primary")
        self.assertEqual(permissions["edit"], "ask")
        for action in ("shell", "subagent", "webfetch", "websearch"):
            self.assertEqual(permissions[action], "deny")
        self.assertEqual(permissions["skill"], "deny")
        self.assertEqual(permissions["*"], "deny")
        self.assertEqual(permissions["question"], "allow")
        self.assertIn("explicitly approves the exact selection", body)
        self.assertIn("modify only the `skills` and `mcp` fields", body)
        self.assertIn("not configured", body)
        self.assertIn("Never install", body)


if __name__ == "__main__":
    unittest.main()
