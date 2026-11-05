from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.instance_lifecycle import attach_instance, create_instance
from app.instances import registered_instance, register_instance
from app.layout import CoreLayout
from app.space import HarnessiaError


class InstanceLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.core = CoreLayout.at(self.root / "core")
        self.core.directory.mkdir()
        (self.core.directory / "SOUL.md").write_text("# Core soul\n")

    def tearDown(self):
        self.temp.cleanup()

    def test_create_builds_minimal_instance_and_attaches_it(self):
        target = self.root / "instances/client"

        result = create_instance(self.core, "client", target)

        self.assertEqual(result.instance.state, "available")
        self.assertTrue((target / "spaces").is_dir())
        self.assertTrue((target / "sources").is_dir())
        self.assertEqual(
            (target / "SOURCES.yaml").read_text(), "version: 2\nsources: []\n"
        )
        self.assertIn("sources/", (target / ".gitignore").read_text())
        self.assertNotIn("spaces/*/SOUL.md", (target / ".gitignore").read_text())
        self.assertEqual(registered_instance(self.core, "client").path, target)
        self.assertFalse((target / ".harnessia").exists())

    def test_create_reports_directory_creation_failure_as_harnessia_error(self):
        target = self.root / "instances/client"

        with patch(
            "app.instance_lifecycle.Path.mkdir",
            side_effect=PermissionError(13, "Permission denied", str(target)),
        ):
            with self.assertRaisesRegex(
                HarnessiaError, "cannot create Instance directory"
            ):
                create_instance(self.core, "client", target)

        self.assertFalse(target.exists())

    def test_attach_replaces_generated_space_soul_link_with_empty_file(self):
        first = self.root / "instances/first"
        create_instance(self.core, "client", first)
        second = self.root / "instances/second"
        (second / "spaces/example").mkdir(parents=True)
        (second / "sources").mkdir()
        (second / "SOURCES.yaml").write_text("version: 2\nsources: []\n")
        (second / "spaces/example/SPACE.md").write_text("fixture\n")
        (second / "spaces/example/SOUL.md").symlink_to("missing")

        attach_instance(self.core, "client", second)

        soul = second / "spaces/example/SOUL.md"
        self.assertTrue(soul.is_file())
        self.assertFalse(soul.is_symlink())
        self.assertEqual(soul.read_text(), "")
        self.assertEqual(registered_instance(self.core, "client").path, second)

    def test_attach_preserves_maintained_space_soul(self):
        target = self.root / "instances/client"
        (target / "spaces/example").mkdir(parents=True)
        (target / "sources").mkdir()
        (target / "SOURCES.yaml").write_text("version: 2\nsources: []\n")
        (target / "spaces/example/SPACE.md").write_text("fixture\n")
        (target / "spaces/example/SOUL.md").write_text("maintained\n")

        attach_instance(self.core, "client", target)

        soul = target / "spaces/example/SOUL.md"
        self.assertFalse(soul.is_symlink())
        self.assertEqual(soul.read_text(), "maintained\n")

    def test_attach_migrates_legacy_lowercase_instance_name(self):
        target = self.root / "instances/Work"
        create_instance(self.core, "work", target)

        result = attach_instance(self.core, "Work", target)

        self.assertEqual(result.instance.id, "Work")
        self.assertEqual(registered_instance(self.core, "Work").path, target)
        with self.assertRaisesRegex(HarnessiaError, "is not registered"):
            registered_instance(self.core, "work")

    def test_attach_creates_missing_space_soul(self):
        target = self.root / "instances/client"
        (target / "spaces/example").mkdir(parents=True)
        (target / "sources").mkdir()
        (target / "SOURCES.yaml").write_text("version: 2\nsources: []\n")
        (target / "spaces/example/SPACE.md").write_text("fixture\n")

        result = attach_instance(self.core, "client", target)

        soul = target / "spaces/example/SOUL.md"
        self.assertEqual(result.initialized_souls, (soul,))
        self.assertTrue(soul.is_file())
        self.assertFalse(soul.is_symlink())
        self.assertEqual(soul.read_text(), "")

    def test_attach_removes_legacy_generated_core_soul_link(self):
        target = self.root / "instances/client"
        (target / "spaces").mkdir(parents=True)
        (target / "sources").mkdir()
        (target / "SOURCES.yaml").write_text("version: 2\nsources: []\n")
        legacy = target / ".harnessia/core/SOUL.md"
        legacy.parent.mkdir(parents=True)
        legacy.symlink_to(self.core.directory / "SOUL.md")

        attach_instance(self.core, "client", target)

        self.assertFalse(legacy.exists())
        self.assertFalse(legacy.is_symlink())
        self.assertFalse((target / ".harnessia").exists())

    def test_attach_preserves_existing_ignore_policy_and_is_idempotent(self):
        target = self.root / "instances/client"
        (target / "spaces").mkdir(parents=True)
        (target / "sources").mkdir()
        (target / "SOURCES.yaml").write_text("version: 2\nsources: []\n")
        custom = "# Local policy\nprivate-notes/\n\n"
        legacy = (
            "# BEGIN Harnessia managed ignore rules\n"
            "spaces/*/SOUL.md\n"
            "# END Harnessia managed ignore rules\n"
        )
        (target / ".gitignore").write_text(custom + legacy)

        attach_instance(self.core, "client", target)
        first = (target / ".gitignore").read_text()
        attach_instance(self.core, "client", target)

        self.assertTrue(first.startswith(custom))
        self.assertIn("sources/", first)
        self.assertNotIn("spaces/*/SOUL.md", first)
        self.assertEqual(first.count("BEGIN Harnessia managed"), 1)
        self.assertEqual((target / ".gitignore").read_text(), first)

    def test_registry_preflight_prevents_instance_mutation(self):
        target = self.root / "instances/client"
        (target / "spaces/example").mkdir(parents=True)
        (target / "sources").mkdir()
        (target / "SOURCES.yaml").write_text("version: 2\nsources: []\n")
        (target / "spaces/example/SPACE.md").write_text("fixture\n")
        soul = target / "spaces/example/SOUL.md"
        soul.symlink_to("old-target")
        ignore = target / ".gitignore"
        ignore.write_text("custom/\n")
        register_instance(self.core, "other", target)

        with self.assertRaisesRegex(HarnessiaError, "already registered"):
            attach_instance(self.core, "client", target)

        self.assertEqual(soul.readlink(), Path("old-target"))
        self.assertEqual(ignore.read_text(), "custom/\n")
        self.assertFalse((target / ".harnessia").exists())

    def test_registry_directory_preflight_prevents_instance_mutation(self):
        target = self.root / "instances/client"
        (target / "spaces").mkdir(parents=True)
        (target / "sources").mkdir()
        (target / "SOURCES.yaml").write_text("version: 2\nsources: []\n")
        ignore = target / ".gitignore"
        ignore.write_text("custom/\n")
        (self.core.directory / ".harnessia").write_text("blocked\n")

        with self.assertRaisesRegex(HarnessiaError, "local state path"):
            attach_instance(self.core, "client", target)

        self.assertEqual(ignore.read_text(), "custom/\n")
        self.assertFalse((target / ".harnessia").exists())


if __name__ == "__main__":
    unittest.main()
