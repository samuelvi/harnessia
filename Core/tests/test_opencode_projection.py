import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from app.projections.opencode import (
    GENERATED_MARKER,
    HarnessiaError,
    render_opencode,
    write_projection,
)
from app.context import resolve_context_paths
from app.effective import resolve_effective_space
from app.layout import CoreLayout, InstanceLayout
from app.space import load_instance_space


def write_skill(directory: Path, name: str) -> None:
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test {name}\n---\n\nBody\n"
    )


class ProjectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.core = CoreLayout.at(self.root)
        self.instance = InstanceLayout.at("work", self.root / "instance")
        self.space = self.instance.spaces / "example-space"
        self.space.mkdir(parents=True)
        self.source = self.core.sources / "example"
        write_skill(self.source / "skills/example-skill", "example-skill")
        (self.root / "SOUL.md").write_text("# Shared soul\n")
        (self.root / "INSTRUCTIONS.md").write_text("# Shared instructions\n")
        (self.space / "SOUL.md").write_text("")
        (self.space / "INSTRUCTIONS.md").write_text("# Instructions\n")
        (self.space / "SPACE.md").write_text(
            """---
version: 2
skills:
  - source: core/example
    path: skills/example-skill
---

# Example
"""
        )
        self.external = self.root.parent / f"{self.root.name}-external"
        self.external.mkdir()
        (self.space / "project").symlink_to(self.external, target_is_directory=True)

    def tearDown(self):
        if self.external.exists():
            shutil.rmtree(self.external)
        self.temp.cleanup()

    def effective_space(self):
        definition = load_instance_space(self.core, self.instance, "example-space")
        return resolve_effective_space(definition)

    def test_renders_isolated_opencode_configuration(self):
        (self.space / "SOUL.md").write_text("# Space soul\n")
        effective = self.effective_space()

        config = render_opencode(effective)

        self.assertEqual(config["instructions"], [
            "../../../SOUL.md",
            "SOUL.md",
            "../../../INSTRUCTIONS.md",
            "INSTRUCTIONS.md",
        ])
        self.assertEqual(config["skills"], ["../../../sources/example/skills"])
        self.assertEqual(config["permissions"], [
            {"action": "skill", "resource": "*", "effect": "deny"},
            {"action": "skill", "resource": "example-skill", "effect": "allow"},
        ])
        self.assertEqual(config["policies"], [
            {"action": "integration.use", "resource": "mcp:*", "effect": "deny"},
        ])

    def test_loads_space_memory_after_operating_instructions(self):
        (self.space / "MEMORY.md").write_text("# Memory\n")
        effective = self.effective_space()

        config = render_opencode(effective)

        self.assertEqual(
            config["instructions"],
            [
                "../../../SOUL.md",
                "SOUL.md",
                "../../../INSTRUCTIONS.md",
                "INSTRUCTIONS.md",
                "MEMORY.md",
            ],
        )

    def test_requires_shared_instructions(self):
        (self.root / "INSTRUCTIONS.md").unlink()
        definition = load_instance_space(self.core, self.instance, "example-space")

        with self.assertRaisesRegex(
            HarnessiaError,
            "shared INSTRUCTIONS.md must be a maintained regular file",
        ):
            resolve_context_paths(definition)

    def test_rejects_symlinked_space_memory(self):
        outside = self.external / "memory.md"
        outside.write_text("external")
        (self.space / "MEMORY.md").symlink_to(outside)
        definition = load_instance_space(self.core, self.instance, "example-space")

        with self.assertRaisesRegex(HarnessiaError, "MEMORY.md must be a maintained regular file"):
            resolve_context_paths(definition)

    def test_rejects_space_memory_larger_than_32_kib(self):
        (self.space / "MEMORY.md").write_bytes(b"x" * (32 * 1024 + 1))
        definition = load_instance_space(self.core, self.instance, "example-space")

        with self.assertRaisesRegex(HarnessiaError, "MEMORY.md must not exceed 32 KiB"):
            resolve_context_paths(definition)

    def test_requires_space_instructions(self):
        (self.space / "INSTRUCTIONS.md").unlink()
        definition = load_instance_space(self.core, self.instance, "example-space")

        with self.assertRaisesRegex(HarnessiaError, "INSTRUCTIONS.md is required"):
            resolve_context_paths(definition)

    def test_allows_only_selected_mcp_servers(self):
        definition_path = self.space / "SPACE.md"
        definition_path.write_text(
            definition_path.read_text().replace(
                "---\n\n# Example", "mcp:\n  - figma\n---\n\n# Example"
            )
        )
        effective = self.effective_space()

        config = render_opencode(effective)

        self.assertEqual(config["policies"], [
            {"action": "integration.use", "resource": "mcp:*", "effect": "deny"},
            {"action": "integration.use", "resource": "mcp:figma", "effect": "allow"},
        ])

    def test_rejects_symlinked_space_instructions(self):
        outside = self.external / "instructions.md"
        outside.write_text("external")
        (self.space / "INSTRUCTIONS.md").unlink()
        (self.space / "INSTRUCTIONS.md").symlink_to(outside)
        definition = load_instance_space(self.core, self.instance, "example-space")

        with self.assertRaisesRegex(HarnessiaError, "must be a maintained regular file"):
            resolve_context_paths(definition)

    def test_rejects_symlinked_space_soul(self):
        (self.space / "SOUL.md").unlink()
        (self.space / "SOUL.md").symlink_to("../../../SOUL.md")
        definition = load_instance_space(self.core, self.instance, "example-space")

        with self.assertRaisesRegex(
            HarnessiaError, "Space SOUL.md must be a maintained regular file"
        ):
            resolve_context_paths(definition)

    def test_requires_space_soul(self):
        (self.space / "SOUL.md").unlink()
        definition = load_instance_space(self.core, self.instance, "example-space")

        with self.assertRaisesRegex(
            HarnessiaError, "Space SOUL.md must be a maintained regular file"
        ):
            resolve_context_paths(definition)

    def test_rejects_reserved_content_directory_instead_of_symlink(self):
        (self.space / "project").unlink()
        (self.space / "project").mkdir()
        definition = load_instance_space(self.core, self.instance, "example-space")

        with self.assertRaisesRegex(HarnessiaError, "project must be a symbolic link"):
            resolve_context_paths(definition)

    def test_protects_manual_opencode_configuration(self):
        target = self.space / "opencode.jsonc"
        target.write_text('{"model":"manual"}\n')

        with self.assertRaisesRegex(HarnessiaError, "not managed by Harnessia"):
            write_projection(target, {"skills": []})

        self.assertEqual(target.read_text(), '{"model":"manual"}\n')

    def test_replaces_owned_projection(self):
        target = self.space / "opencode.jsonc"
        target.write_text(GENERATED_MARKER + "\n{}\n")

        write_projection(target, {"skills": ["relative/path"]})

        text = target.read_text()
        self.assertTrue(text.startswith(GENERATED_MARKER))
        self.assertEqual(json.loads("\n".join(text.splitlines()[1:])), {
            "skills": ["relative/path"]
        })

if __name__ == "__main__":
    unittest.main()
