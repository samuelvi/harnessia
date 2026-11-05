from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.capabilities.commands import HarnessiaError, resolve_commands
from app.layout import CoreLayout, InstanceLayout
from app.space import load_instance_space


class CommandResolutionTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.core = CoreLayout.at(self.root)
        self.instance = InstanceLayout.at("work", self.root / "instance")
        self.space = self.instance.spaces / "example-space"
        self.space.mkdir(parents=True)
        self.source = self.instance.sources / "example"

    def tearDown(self):
        self.temp.cleanup()

    def write_command(self, path: Path, text: str = "Review $ARGUMENTS.\n") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def write_definition(self, paths: list[str]) -> None:
        commands = "\n".join(
            "  - source: instance/example\n"
            f"    path: {path}"
            for path in paths
        )
        (self.space / "SPACE.md").write_text(
            "---\nversion: 2\nskills: []\n"
            f"commands:\n{commands}\n---\n\n# Example\n"
        )

    def inventory(self):
        return resolve_commands(
            load_instance_space(self.core, self.instance, "example-space")
        )

    def test_resolves_command_without_frontmatter(self):
        command = self.source / "commands/review.md"
        self.write_command(command)
        self.write_definition(["commands/review.md"])

        inventory = self.inventory()

        self.assertEqual(inventory.ids, ("review",))
        self.assertEqual(inventory.commands[0].path, command)

    def test_custom_command_replaces_imported_command(self):
        self.write_command(self.source / "commands/review.md", "Imported")
        custom = self.space / "capabilities/custom/commands/review.md"
        self.write_command(custom, "Custom")
        self.write_definition(["commands/review.md"])

        self.assertEqual(self.inventory().commands[0].path, custom)

    def test_rejects_template_in_markdown_frontmatter(self):
        self.write_command(
            self.source / "commands/review.md",
            "---\ntemplate: forbidden\n---\n\nReview.\n",
        )
        self.write_definition(["commands/review.md"])

        with self.assertRaisesRegex(HarnessiaError, "template must come from the body"):
            self.inventory()

    def test_reports_shell_substitution(self):
        self.write_command(self.source / "commands/review.md", "Review !`git diff`.\n")
        self.write_definition(["commands/review.md"])

        self.assertEqual(len(self.inventory().warnings), 1)


if __name__ == "__main__":
    unittest.main()
