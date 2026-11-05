from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.projections.native import AGENT_MARKER, HarnessiaError, write_agents
from app.capabilities.agents import Agent, AgentInventory


class AgentProjectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.space = self.root / "spaces/work/example-space"
        self.space.mkdir(parents=True)
        self.source = self.root / "sources/example/agents"
        self.source.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def inventory(self, *ids: str) -> AgentInventory:
        agents = []
        for agent_id in ids:
            path = self.source / f"{agent_id}.md"
            path.write_text("agent")
            agents.append(Agent(id=agent_id, path=path))
        return AgentInventory(tuple(agents))

    def test_writes_relative_native_agent_links(self):
        target = self.space / ".opencode/agents"

        write_agents(target, self.inventory("reviewer", "tester"))

        self.assertEqual((target / ".harnessia-generated").read_text(), AGENT_MARKER)
        for agent_id in ("reviewer", "tester"):
            link = target / f"{agent_id}.md"
            self.assertTrue(link.is_symlink())
            self.assertFalse(Path(link.readlink()).is_absolute())
            self.assertEqual(link.resolve(), self.source / f"{agent_id}.md")

    def test_refuses_manual_agent_directory(self):
        target = self.space / ".opencode/agents"
        target.mkdir(parents=True)
        (target / "manual.md").write_text("manual")

        with self.assertRaisesRegex(HarnessiaError, "not managed by Harnessia"):
            write_agents(target, self.inventory("reviewer"))

        self.assertTrue((target / "manual.md").is_file())

    def test_replaces_owned_directory_without_stale_agents(self):
        target = self.space / ".opencode/agents"
        write_agents(target, self.inventory("old-agent"))

        write_agents(target, self.inventory("new-agent"))

        self.assertFalse((target / "old-agent.md").exists())
        self.assertTrue((target / "new-agent.md").is_symlink())

    def test_empty_inventory_removes_owned_directory(self):
        target = self.space / ".opencode/agents"
        write_agents(target, self.inventory("old-agent"))

        write_agents(target, AgentInventory(()))

        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
