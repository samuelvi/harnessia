from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.core import load_core_definition
from app.effective import resolve_effective_core
from app.space import HarnessiaError


def write_skill(directory: Path, name: str) -> None:
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test {name}\n---\n\nBody\n"
    )


class CoreDefinitionTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "sources/example"
        write_skill(self.source / "skills/example", "effective-name")
        self.write_definition("core/example")

    def tearDown(self):
        self.temp.cleanup()

    def write_definition(self, source: str, path: str = "skills/example") -> None:
        (self.root / "HARNESSIA.md").write_text(
            "---\nversion: 1\nskills:\n"
            f"  - source: {source}\n"
            f"    path: {path}\n"
            "---\n\n# Core\n"
        )

    def test_resolves_client_agnostic_core_context(self):
        definition = load_core_definition(self.root)
        effective = resolve_effective_core(self.root)

        self.assertEqual(len(definition.skills), 1)
        self.assertEqual(effective.skills.ids, ("effective-name",))
        self.assertEqual(
            effective.skills.skills[0].directory,
            (self.source / "skills/example").resolve(),
        )

    def test_allows_an_explicit_empty_selection(self):
        (self.root / "HARNESSIA.md").write_text(
            "---\nversion: 1\nskills: []\n---\n\n# Core\n"
        )

        self.assertEqual(resolve_effective_core(self.root).skills.ids, ())

    def test_rejects_instance_source(self):
        self.write_definition("instance/example")

        with self.assertRaisesRegex(HarnessiaError, "core/<source-id>"):
            load_core_definition(self.root)

    def test_rejects_legacy_source(self):
        self.write_definition("profiles/common/sources/external/example")

        with self.assertRaisesRegex(HarnessiaError, "core/<source-id>"):
            load_core_definition(self.root)

    def test_rejects_unknown_fields(self):
        path = self.root / "HARNESSIA.md"
        path.write_text(
            path.read_text().replace("version: 1", "version: 1\nagents: []")
        )

        with self.assertRaisesRegex(HarnessiaError, "unsupported field 'agents'"):
            load_core_definition(self.root)

    def test_rejects_skill_target_that_escapes_source(self):
        outside = self.root / "outside/escaped"
        write_skill(outside, "escaped")
        (self.source / "escaped").symlink_to(outside, target_is_directory=True)
        self.write_definition("core/example", "escaped")

        with self.assertRaisesRegex(HarnessiaError, "resolves outside its source"):
            resolve_effective_core(self.root)


if __name__ == "__main__":
    unittest.main()
