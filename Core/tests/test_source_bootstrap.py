from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import unittest

import yaml

from app.instances import register_instance
from app.layout import CoreLayout
from app.source_bootstrap import (
    check_sources,
    clone_sources,
    load_source_manifest,
    reconcile_sources,
)
from app.space import HarnessiaError


def git(directory: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class SourceBootstrapTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.outside_temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.seed = self.root / "seed"
        self.remote = self.root / "remote.git"
        self.source_path = Path("core/example")
        self.source = self.root / "sources/example"
        self.seed.mkdir(parents=True)
        git(self.seed, "init", "-b", "main")
        git(self.seed, "config", "user.name", "Harnessia Test")
        git(self.seed, "config", "user.email", "harnessia@example.invalid")
        self.write_seed_skill("One\n")
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-m", "Initial")
        self.initial_revision = git(self.seed, "rev-parse", "HEAD")
        subprocess.run(
            ["git", "init", "--bare", str(self.remote)],
            check=True,
            capture_output=True,
        )
        git(self.seed, "remote", "add", "origin", str(self.remote))
        git(self.seed, "push", "-u", "origin", "main")
        self.write_seed_skill("Two\n")
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-m", "Update")
        self.updated_revision = git(self.seed, "rev-parse", "HEAD")
        git(self.seed, "push", "origin", "main")
        self.write_manifest(self.initial_revision)

    def tearDown(self):
        self.temp.cleanup()
        self.outside_temp.cleanup()

    def write_seed_skill(self, body: str) -> None:
        skill = self.seed / "skills/example-skill"
        skill.mkdir(parents=True, exist_ok=True)
        (skill / "SKILL.md").write_text(
            "---\nname: example-skill\ndescription: Example\n---\n\n" + body
        )
        plugin = self.seed / ".claude-plugin/plugin.json"
        plugin.parent.mkdir(parents=True, exist_ok=True)
        plugin.write_text(
            json.dumps(
                {
                    "name": "example",
                    "version": "1.0.0",
                    "skills": ["./skills/example-skill"],
                }
            )
        )

    def write_manifest(self, revision: str) -> None:
        manifest = {
            "version": 2,
            "sources": [
                {
                    "id": "example",
                    "url": str(self.remote),
                    "branch": "main",
                    "revision": revision,
                }
            ],
        }
        (self.root / "SOURCES.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False)
        )

    def write_space(self) -> Path:
        (self.root / "SOUL.md").write_text("# Soul\n")
        (self.root / "INSTRUCTIONS.md").write_text("# Shared instructions\n")
        (self.root / "HARNESSIA.md").write_text(
            "---\nversion: 1\nskills:\n"
            "  - source: core/example\n"
            "    path: skills/example-skill\n"
            "---\n\n# Core\n"
        )
        instance = self.root / "work-instance"
        space = instance / "spaces/example-space"
        space.mkdir(parents=True)
        (instance / "SOURCES.yaml").write_text("version: 2\nsources: []\n")
        (space / "SOUL.md").write_text("")
        (space / "INSTRUCTIONS.md").write_text("# Instructions\n")
        (space / "SPACE.md").write_text(
            """---
version: 2
skills:
  - source: core/example
    path: skills/example-skill
---

# Example
"""
        )
        register_instance(CoreLayout.at(self.root), "work", instance)
        return space

    def test_clone_installs_exact_revision_and_skips_valid_existing_source(self):
        result = clone_sources(self.root)

        self.assertEqual(result.cloned, (self.source_path,))
        self.assertEqual(result.current, ())
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), self.initial_revision)
        self.assertEqual(git(self.source, "branch", "--show-current"), "main")
        self.assertEqual(
            git(self.source, "rev-parse", "--abbrev-ref", "@{upstream}"),
            "origin/main",
        )
        self.assertIn("One", (self.source / "skills/example-skill/SKILL.md").read_text())

        second = clone_sources(self.root)

        self.assertEqual(second.cloned, ())
        self.assertEqual(second.current, (self.source_path,))
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), self.initial_revision)

    def test_rejects_legacy_manifest_version(self):
        (self.root / "SOURCES.yaml").write_text("version: 1\nsources: []\n")

        with self.assertRaisesRegex(HarnessiaError, "version must be 2"):
            clone_sources(self.root)

    def test_version_two_instance_manifest_owns_instance_source(self):
        (self.root / "SOURCES.yaml").write_text("version: 2\nsources: []\n")
        instance = Path(self.outside_temp.name) / "sandbox"
        (instance / "spaces").mkdir(parents=True)
        (instance / "SOURCES.yaml").write_text(
            yaml.safe_dump(
                {
                    "version": 2,
                    "sources": [
                        {
                            "id": "example",
                            "url": str(self.remote),
                            "branch": "main",
                            "revision": self.initial_revision,
                        }
                    ],
                },
                sort_keys=False,
            )
        )
        register_instance(CoreLayout.at(self.root), "sandbox", instance)

        result = clone_sources(self.root)

        self.assertEqual(result.cloned, (Path("instance/sandbox/example"),))
        self.assertEqual(
            git(instance / "sources/example", "rev-parse", "HEAD"),
            self.initial_revision,
        )

    def test_clone_rejects_existing_drift_without_overwriting_it(self):
        clone_sources(self.root)
        skill = self.source / "skills/example-skill/SKILL.md"
        skill.write_text("local work\n")

        with self.assertRaisesRegex(HarnessiaError, "worktree is not clean"):
            clone_sources(self.root)

        self.assertEqual(skill.read_text(), "local work\n")
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), self.initial_revision)

    def test_manifest_rejects_storage_paths(self):
        data = yaml.safe_load((self.root / "SOURCES.yaml").read_text())
        data["sources"][0]["path"] = "sources/example"
        (self.root / "SOURCES.yaml").write_text(yaml.safe_dump(data))

        with self.assertRaisesRegex(HarnessiaError, "unsupported field 'path'"):
            load_source_manifest(self.root)

    def test_clone_rejects_source_catalog_that_resolves_outside_root(self):
        (self.root / "sources").symlink_to(self.outside_temp.name)

        with self.assertRaisesRegex(HarnessiaError, "resolves outside Core"):
            clone_sources(self.root)

        self.assertFalse(Path(self.outside_temp.name, "example").exists())

    def test_check_and_reconcile_keep_pins_spaces_and_projections_coherent(self):
        clone_sources(self.root)
        space = self.write_space()

        checked = check_sources(self.root)

        self.assertEqual(checked.sources, (self.source_path,))
        self.assertEqual(
            checked.consumers, ("core", "work/example-space")
        )
        git(self.source, "merge", "--ff-only", "origin/main")

        with self.assertRaisesRegex(HarnessiaError, "expected revision"):
            check_sources(self.root)

        reconciled = reconcile_sources(self.root)

        self.assertEqual(len(reconciled.changes), 1)
        self.assertEqual(reconciled.changes[0].old_revision, self.initial_revision)
        self.assertEqual(reconciled.changes[0].new_revision, self.updated_revision)
        specs = load_source_manifest(self.root)
        self.assertEqual(specs[0].revision, self.updated_revision)
        self.assertTrue((space / "opencode.jsonc").is_file())
        self.assertTrue((space / "CLAUDE.md").is_file())
        self.assertTrue((self.root / ".opencode/skills/example-skill").is_symlink())
        self.assertTrue(
            (
                self.root
                / ".claude/skills/harnessia-core/skills/example-skill"
            ).is_symlink()
        )

    def test_check_validates_registered_instance_consumers(self):
        clone_sources(self.root)
        self.write_space()
        instance = Path(self.outside_temp.name) / "sandbox"
        space = instance / "spaces/sandbox-space"
        space.mkdir(parents=True)
        (instance / "SOURCES.yaml").write_text("version: 2\nsources: []\n")
        (space / "SOUL.md").write_text("")
        (space / "INSTRUCTIONS.md").write_text("# Sandbox instructions\n")
        (space / "SPACE.md").write_text(
            """---
version: 2
skills:
  - source: core/example
    path: skills/example-skill
---

# Sandbox
"""
        )
        register_instance(CoreLayout.at(self.root), "sandbox", instance)

        checked = check_sources(self.root)

        self.assertEqual(
            checked.consumers,
            ("core", "sandbox/sandbox-space", "work/example-space"),
        )

    def test_missing_registered_instance_blocks_source_check(self):
        clone_sources(self.root)
        self.write_space()
        register_instance(
            CoreLayout.at(self.root), "sandbox", Path(self.outside_temp.name) / "missing"
        )

        with self.assertRaisesRegex(HarnessiaError, "sandbox: missing"):
            check_sources(self.root)

        with self.assertRaisesRegex(HarnessiaError, "sandbox: missing"):
            reconcile_sources(self.root)

    def test_failed_reconciliation_keeps_pins_and_projections_unchanged(self):
        clone_sources(self.root)
        space = self.write_space()
        git(self.source, "merge", "--ff-only", "origin/main")
        reconcile_sources(self.root)
        projection = space / "opencode.jsonc"
        previous_projection = projection.read_bytes()
        (self.seed / "skills/example-skill/SKILL.md").unlink()
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-m", "Remove selected skill")
        removed_revision = git(self.seed, "rev-parse", "HEAD")
        git(self.seed, "push", "origin", "main")
        git(self.source, "fetch", "origin")
        git(self.source, "merge", "--ff-only", "origin/main")

        with self.assertRaisesRegex(HarnessiaError, "example-skill.*does not exist"):
            reconcile_sources(self.root)

        self.assertEqual(load_source_manifest(self.root)[0].revision, self.updated_revision)
        self.assertEqual(projection.read_bytes(), previous_projection)
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), removed_revision)

    def test_check_treats_source_plugin_manifest_as_ordinary_pinned_content(self):
        clone_sources(self.root)
        self.write_space()
        manifest = self.source / ".claude-plugin/plugin.json"
        data = json.loads(manifest.read_text())
        data["agents"] = []
        manifest.write_text(json.dumps(data))
        git(self.source, "config", "user.name", "Harnessia Test")
        git(self.source, "config", "user.email", "harnessia@example.invalid")
        git(self.source, "add", ".")
        git(self.source, "commit", "-m", "Incompatible plugin")
        self.write_manifest(git(self.source, "rev-parse", "HEAD"))

        checked = check_sources(self.root)

        self.assertEqual(checked.consumers, ("core", "work/example-space"))


if __name__ == "__main__":
    unittest.main()
