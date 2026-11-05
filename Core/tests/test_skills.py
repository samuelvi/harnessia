from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.capabilities.skills import HarnessiaError, resolve_skills
from app.layout import CoreLayout, InstanceLayout
from app.space import load_instance_space


def write_skill(directory: Path, name: str, body: str = "BODY") -> None:
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test skill {name}\n---\n\n{body}\n"
    )


class SkillResolutionTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.core = CoreLayout.at(self.root)
        self.instance = InstanceLayout.at("work", self.root / "instance")
        self.space = self.instance.spaces / "example-space"
        self.space.mkdir(parents=True)
        self.source = self.core.sources / "example"
        self.definition = self.space / "SPACE.md"

    def tearDown(self):
        self.temp.cleanup()

    def write_definition(self, paths: list[str]) -> None:
        skills = "\n".join(
            "  - source: core/example\n"
            f"    path: {path}"
            for path in paths
        )
        self.definition.write_text(
            "---\nversion: 2\nskills:\n"
            f"{skills}\n---\n\n# Example\n"
        )

    def inventory(self):
        return resolve_skills(
            load_instance_space(self.core, self.instance, "example-space")
        )

    def test_resolves_imported_skill_and_catalog_root(self):
        write_skill(self.source / "skills/example-skill", "example-skill")
        self.write_definition(["skills/example-skill"])

        inventory = self.inventory()

        self.assertEqual(inventory.ids, ("example-skill",))
        self.assertEqual(inventory.catalog_roots, ((self.source / "skills").resolve(),))

    def test_custom_skill_replaces_imported_skill(self):
        write_skill(
            self.source / "skills/example-skill", "example-skill", "IMPORTED"
        )
        custom = self.space / "capabilities/custom/skills/example-skill"
        write_skill(custom, "example-skill", "CUSTOM")
        self.write_definition(["skills/example-skill"])

        inventory = self.inventory()

        self.assertEqual(inventory.ids, ("example-skill",))
        self.assertEqual(inventory.skills[0].directory, custom.resolve())
        self.assertEqual(
            inventory.catalog_roots,
            (
                (self.source / "skills").resolve(),
                (self.space / "capabilities/custom/skills").resolve(),
            ),
        )

    def test_rejects_duplicate_imported_ids(self):
        write_skill(self.source / "one/duplicate", "duplicate")
        write_skill(self.source / "two/duplicate", "duplicate")
        self.write_definition(["one/duplicate", "two/duplicate"])

        with self.assertRaisesRegex(HarnessiaError, "duplicate imported skill ID"):
            self.inventory()

    def test_imported_skill_id_comes_from_frontmatter(self):
        write_skill(self.source / "skills/example-skill", "different-name")
        self.write_definition(["skills/example-skill"])

        inventory = self.inventory()

        self.assertEqual(inventory.ids, ("different-name",))

    def test_rejects_custom_name_that_differs_from_directory(self):
        write_skill(self.source / "skills/example-skill", "example-skill")
        custom = self.space / "capabilities/custom/skills/custom-skill"
        write_skill(custom, "different-name")
        self.write_definition(["skills/example-skill"])

        with self.assertRaisesRegex(HarnessiaError, "must match directory"):
            self.inventory()

    def test_rejects_target_that_escapes_source_through_symlink(self):
        outside = self.root / "outside/escaped"
        write_skill(outside, "escaped")
        self.source.mkdir(parents=True)
        (self.source / "escaped").symlink_to(outside, target_is_directory=True)
        self.write_definition(["escaped"])

        with self.assertRaisesRegex(HarnessiaError, "resolves outside its source"):
            self.inventory()

    def test_rejects_source_symlink_outside_owner_catalog(self):
        outside_source = self.root / "outside/sandbox-example"
        write_skill(outside_source / "skills/example-skill", "example-skill")
        self.source.parent.mkdir(parents=True)
        self.source.symlink_to(outside_source, target_is_directory=True)
        self.write_definition(["skills/example-skill"])

        with self.assertRaisesRegex(
            HarnessiaError, "resolves outside its owning catalog"
        ):
            self.inventory()

    def test_rejects_nested_custom_categories(self):
        write_skill(
            self.source / "skills/example-skill", "example-skill", "IMPORTED"
        )
        write_skill(
            self.space / "capabilities/custom/skills/category/custom-skill",
            "custom-skill",
        )
        self.write_definition(["skills/example-skill"])

        with self.assertRaisesRegex(HarnessiaError, "must contain SKILL.md directly"):
            self.inventory()

    def test_rejects_custom_skill_symlink_that_escapes_space(self):
        write_skill(self.source / "skills/example-skill", "example-skill")
        outside = self.root / "outside/custom-skill"
        write_skill(outside, "custom-skill")
        custom_root = self.space / "capabilities/custom/skills"
        custom_root.mkdir(parents=True)
        (custom_root / "custom-skill").symlink_to(outside, target_is_directory=True)
        self.write_definition(["skills/example-skill"])

        with self.assertRaisesRegex(HarnessiaError, "resolves outside custom skills"):
            self.inventory()

    def test_rejects_custom_skills_directory_symlink_outside_space(self):
        write_skill(self.source / "skills/example-skill", "example-skill")
        outside = self.root / "outside/custom-skills"
        write_skill(outside / "custom-skill", "custom-skill")
        custom_parent = self.space / "capabilities/custom"
        custom_parent.mkdir(parents=True)
        (custom_parent / "skills").symlink_to(outside, target_is_directory=True)
        self.write_definition(["skills/example-skill"])

        with self.assertRaisesRegex(
            HarnessiaError, "custom skills must be maintained inside the Space"
        ):
            self.inventory()


if __name__ == "__main__":
    unittest.main()
