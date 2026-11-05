from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import unittest

from app.instances import register_instance
from app.layout import CoreLayout
from app.source_status import inspect_sources, render_source_status


SPACE = """---
version: 2
skills:
  - source: core/example
    path: skills/example-skill
---

# Example
"""


def git(directory: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def write_skill(source: Path, body: str = "Body\n") -> None:
    skill = source / "skills/example-skill"
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Example\n---\n\n" + body
    )


class SourceStatusTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "sources/example"
        self.source.mkdir(parents=True)
        write_skill(self.source)
        plugin = self.source / ".claude-plugin/plugin.json"
        plugin.parent.mkdir(parents=True)
        plugin.write_text(
            json.dumps(
                {
                    "name": "example",
                    "version": "1.0.0",
                    "skills": ["./skills/example-skill"],
                }
            )
        )
        (self.root / "HARNESSIA.md").write_text(
            "---\nversion: 1\nskills:\n"
            "  - source: core/example\n"
            "    path: skills/example-skill\n"
            "---\n\n# Core\n"
        )
        instance = self.root / "instances/work"
        space = instance / "spaces/example-space"
        space.mkdir(parents=True)
        (space / "SPACE.md").write_text(SPACE)
        register_instance(CoreLayout.at(self.root), "work", instance)

    def tearDown(self):
        self.temp.cleanup()

    def initialize_repository(self) -> None:
        git(self.source, "init", "-b", "main")
        git(self.source, "config", "user.name", "Harnessia Test")
        git(self.source, "config", "user.email", "harnessia@example.invalid")
        git(self.source, "add", ".")
        git(self.source, "commit", "-m", "Initial")

    def test_reports_unversioned_source_and_affected_space(self):
        status = inspect_sources(self.root)

        self.assertEqual(len(status), 1)
        self.assertIsNone(status[0].revision)
        self.assertIsNone(status[0].git_error)
        self.assertEqual(
            status[0].consumers, ("core", "work/example-space")
        )
        self.assertIn("unversioned", render_source_status(status))

    def test_maps_source_usage_from_registered_instance(self):
        instance = self.root / "instances/sandbox"
        space = instance / "spaces/sandbox-space"
        space.mkdir(parents=True)
        (space / "SPACE.md").write_text(SPACE)
        register_instance(CoreLayout.at(self.root), "sandbox", instance)

        status = inspect_sources(self.root)

        self.assertEqual(
            status[0].consumers,
            ("core", "sandbox/sandbox-space", "work/example-space"),
        )

    def test_reports_missing_instance_source_at_its_owner_catalog(self):
        space = self.root / "instances/work/spaces/example-space/SPACE.md"
        space.write_text(SPACE.replace("core/example", "instance/missing"))

        statuses = inspect_sources(self.root)

        missing = next(
            status
            for status in statuses
            if status.source == Path("instance/work/missing")
        )
        self.assertTrue(missing.missing)
        self.assertIn(
            "instance/work/missing | missing",
            render_source_status(statuses),
        )

    def test_distinguishes_broken_git_metadata_from_unversioned_source(self):
        (self.source / ".git").write_text("gitdir: ../../../missing/repository\n")

        status = inspect_sources(self.root)[0]

        self.assertIsNone(status.revision)
        self.assertIsNotNone(status.git_error)
        self.assertIn("git-unavailable", render_source_status((status,)))

    def test_reports_dirty_selected_capability_and_dependency(self):
        self.initialize_repository()
        write_skill(self.source, "Changed\n")
        (self.source / "package.json").write_text("{}\n")

        status = inspect_sources(self.root)[0]

        self.assertTrue(status.dirty)
        self.assertEqual(
            [(change.kind, change.path, change.consumers)
             for change in status.working_capabilities],
            [
                (
                    "skill",
                    Path("skills/example-skill"),
                    ("core", "work/example-space"),
                )
            ],
        )
        self.assertEqual(status.working_dependencies, (Path("package.json"),))

    def test_source_plugin_manifest_is_not_selected_core_context(self):
        self.initialize_repository()
        manifest = self.source / ".claude-plugin/plugin.json"
        data = json.loads(manifest.read_text())
        data["version"] = "2.0.0"
        manifest.write_text(json.dumps(data))

        status = inspect_sources(self.root)[0]

        self.assertEqual(status.working_capabilities, ())

    def test_source_default_plugin_component_is_not_selected_core_context(self):
        self.initialize_repository()
        commands = self.source / "commands"
        commands.mkdir()
        (commands / "review.md").write_text("Review.\n")

        status = inspect_sources(self.root)[0]

        self.assertEqual(status.working_capabilities, ())

    def test_reports_known_upstream_update_without_fetching(self):
        self.initialize_repository()
        base = git(self.source, "rev-parse", "HEAD")
        write_skill(self.source, "Upstream\n")
        git(self.source, "add", ".")
        git(self.source, "commit", "-m", "Upstream change")
        upstream = git(self.source, "rev-parse", "HEAD")
        git(self.source, "checkout", "-q", "--detach", base)
        git(self.source, "branch", "-f", "main", base)
        git(self.source, "checkout", "-q", "main")
        git(self.source, "remote", "add", "origin", "https://example.invalid/example.git")
        git(self.source, "update-ref", "refs/remotes/origin/main", upstream)
        git(self.source, "branch", "--set-upstream-to=origin/main", "main")

        status = inspect_sources(self.root)[0]

        self.assertEqual(status.ahead, 0)
        self.assertEqual(status.behind, 1)
        self.assertEqual(status.upstream, "origin/main")
        self.assertEqual(
            status.upstream_capabilities[0].path,
            Path("skills/example-skill"),
        )
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), base)


if __name__ == "__main__":
    unittest.main()
