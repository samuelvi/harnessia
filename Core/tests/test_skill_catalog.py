from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from app.layout import CoreLayout, InstanceLayout
from app.skill_catalog import build_skill_catalog, render_skill_catalog
from app.space import load_instance_space


def write_skill(directory: Path, name: str, description: str) -> None:
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\nBody\n"
    )


class SkillCatalogTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.core = CoreLayout.at(self.root / "Core")
        self.instance = InstanceLayout.at("Work", self.root / "Work")
        self.space = self.instance.spaces / "atlas"
        self.core.directory.mkdir()
        self.space.mkdir(parents=True)
        self.instance.sources.mkdir()
        (self.core.directory / "SOURCES.yaml").write_text(
            "version: 2\nsources:\n"
            "  - id: shared\n"
            "    url: https://example.com/shared.git\n"
            "    branch: main\n"
            f"    revision: \"{'0' * 40}\"\n"
        )
        (self.instance.directory / "SOURCES.yaml").write_text(
            "version: 2\nsources: []\n"
        )
        (self.space / "SPACE.md").write_text(
            "---\nversion: 2\nskills:\n"
            "  - source: core/shared\n"
            "    path: skills/design\n"
            "---\n\n# Atlas\n"
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_indexes_only_core_and_owning_instance_skills(self):
        write_skill(
            self.core.sources / "shared/skills/design",
            "design",
            "Design systems",
        )
        write_skill(
            self.instance.sources / "private/skills/delivery",
            "delivery",
            "Deliver changes",
        )
        invalid = self.core.sources / "shared/skills/invalid"
        invalid.mkdir(parents=True)
        (invalid / "SKILL.md").write_text("not frontmatter\n")
        other = self.root / "Sandbox/sources/other/skills/private"
        write_skill(other, "private", "Must not be visible")

        catalog = build_skill_catalog(
            load_instance_space(self.core, self.instance, "atlas")
        )

        self.assertEqual(
            tuple(
                (item.source.as_posix(), item.path.as_posix(), item.id)
                for item in catalog.skills
            ),
            (
                ("core/shared", "skills/design", "design"),
                ("instance/private", "skills/delivery", "delivery"),
            ),
        )
        self.assertTrue(catalog.skills[0].selected)
        self.assertTrue(catalog.skills[0].pinned)
        self.assertFalse(catalog.skills[1].selected)
        self.assertFalse(catalog.skills[1].pinned)
        self.assertEqual(len(catalog.skipped), 1)

        rendered = [
            json.loads(line) for line in render_skill_catalog(catalog).splitlines()
        ]
        self.assertEqual(rendered[0]["description"], "Design systems")
        self.assertEqual(rendered[0]["source_state"], "pinned")
        self.assertEqual(rendered[1]["source"], "instance/private")
        self.assertEqual(rendered[1]["source_state"], "local")


if __name__ == "__main__":
    unittest.main()
