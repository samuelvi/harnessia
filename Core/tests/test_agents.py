from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.capabilities.agents import HarnessiaError, resolve_agents
from app.layout import CoreLayout, InstanceLayout
from app.space import load_instance_space


def write_agent(path: Path, description: str = "Test agent") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ndescription: {description}\nmode: subagent\n---\n\nAgent prompt.\n"
    )


class AgentResolutionTest(unittest.TestCase):
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

    def write_definition(self, paths: list[str]) -> None:
        agents = "\n".join(
            "  - source: instance/example\n"
            f"    path: {path}"
            for path in paths
        )
        (self.space / "SPACE.md").write_text(
            "---\nversion: 2\nskills: []\n"
            f"agents:\n{agents}\n---\n\n# Example\n"
        )

    def inventory(self):
        return resolve_agents(
            load_instance_space(self.core, self.instance, "example-space")
        )

    def test_resolves_imported_agent(self):
        agent = self.source / "agents/reviewer.md"
        write_agent(agent)
        self.write_definition(["agents/reviewer.md"])

        inventory = self.inventory()

        self.assertEqual(inventory.ids, ("reviewer",))
        self.assertEqual(inventory.agents[0].path, agent)

    def test_custom_agent_replaces_imported_agent(self):
        write_agent(self.source / "agents/reviewer.md", "Imported")
        custom = self.space / "capabilities/custom/agents/reviewer.md"
        write_agent(custom, "Custom")
        self.write_definition(["agents/reviewer.md"])

        inventory = self.inventory()

        self.assertEqual(inventory.ids, ("reviewer",))
        self.assertEqual(inventory.agents[0].path, custom)

    def test_rejects_duplicate_imported_ids(self):
        write_agent(self.source / "one/reviewer.md")
        write_agent(self.source / "two/reviewer.md")
        self.write_definition(["one/reviewer.md", "two/reviewer.md"])

        with self.assertRaisesRegex(HarnessiaError, "duplicate imported agent ID"):
            self.inventory()

    def test_rejects_agent_without_description(self):
        path = self.source / "agents/reviewer.md"
        path.parent.mkdir(parents=True)
        path.write_text("---\nmode: subagent\n---\n\nPrompt\n")
        self.write_definition(["agents/reviewer.md"])

        with self.assertRaisesRegex(HarnessiaError, "description is required"):
            self.inventory()


if __name__ == "__main__":
    unittest.main()
