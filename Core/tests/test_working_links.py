import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.instance_lifecycle import attach_instance, create_instance
from app.layout import CoreLayout
from app.prepare import prepare_all, prepare_instance
from app.space import HarnessiaError
from app.space_lifecycle import create_space
from app.working_links import load_working_link_names


class WorkingLinksTest(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.core = CoreLayout.at(self.root / "core")
        self.core.directory.mkdir()
        (self.core.directory / "SOUL.md").write_text("# Core\n")
        (self.core.directory / "HARNESSIA.md").write_text(
            "---\nversion: 1\nskills: []\n---\n"
        )

    def instance(self, name):
        return create_instance(self.core, name, self.root / name).instance.layout

    def test_optional_manifest_has_no_requirement_for_a_default_instance(self):
        self.assertEqual(prepare_all(self.core.directory).spaces, ())

    def test_manifests_scope_validation_claude_and_git_ignore_to_the_owner(self):
        first = self.instance("Example-A")
        second = self.instance("Example-B")
        self.assertEqual(load_working_link_names(first), ("project", "documentation"))
        outside = self.root / "external"
        outside.mkdir()
        for instance, name in ((first, "repository"), (second, "manuals")):
            (instance.directory / "WORKING_LINKS.yaml").write_text(
                f"version: 1\nnames: [{name}]\n"
            )
            attach_instance(self.core, instance.id, instance.directory)
            create_space(self.core, instance, "atlas")
            (instance.spaces / "atlas" / name).symlink_to(outside)

        for instance, own, other in (
            (first, "repository", "manuals"),
            (second, "manuals", "repository"),
        ):
            space = instance.spaces / "atlas"
            (space / other).mkdir()
            prepare_instance(self.core, instance, "atlas")
            settings = json.loads((space / ".claude/settings.json").read_text())
            self.assertEqual(
                settings["claudeMdExcludes"], [f"{space / own}/**", f"{outside}/**"]
            )
            ignore = (instance.directory / ".gitignore").read_text()
            self.assertIn(f"spaces/*/{own}\n", ignore)
            self.assertNotIn(f"spaces/*/{other}\n", ignore)
            self.assertIn("spaces/*/project\n", ignore)
            self.assertTrue((space / other).is_dir())

    def test_bad_manifests_fail_before_attachment_modifies_ignore_policy(self):
        instance = self.instance("Example")
        manifest = instance.directory / "WORKING_LINKS.yaml"
        ignore = instance.directory / ".gitignore"
        before = ignore.read_bytes()
        for content in (
            "version: true\nnames: []\n",
            "version: 1\nnames: not-a-list\n",
            "version: 1\nnames: [a, a]\n",
            "version: 1\nnames: [project]\n",
            "version: 1\nnames: [docs]\n",
            "version: 1\nnames: [../outside]\n",
            "version: 1\nnames: ['a*']\n",
            "version: 1\nnames: []\nextra: true\n",
        ):
            with self.subTest(content=content):
                manifest.write_text(content)
                with self.assertRaisesRegex(HarnessiaError, "WORKING_LINKS.yaml"):
                    attach_instance(self.core, instance.id, instance.directory)
                self.assertEqual(ignore.read_bytes(), before)

        manifest.unlink()
        manifest.symlink_to("missing")
        with self.assertRaisesRegex(HarnessiaError, "must be a regular file"):
            load_working_link_names(instance)
