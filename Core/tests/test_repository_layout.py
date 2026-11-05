from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import unittest


CORE = Path(__file__).resolve().parents[1]
REPOSITORY = CORE.parent


class RepositoryLayoutTest(unittest.TestCase):
    def test_project_readmes_and_license_live_only_inside_core(self):
        for name in ("README.md", "README-ES.md"):
            self.assertFalse((REPOSITORY / name).exists())
            core_readme = (CORE / name).read_text()
            self.assertIn("cd Core", core_readme)
            self.assertIn("GPL-3.0-only", core_readme)
            self.assertIn("(LICENSE)", core_readme)
        license_text = (CORE / "LICENSE").read_text()
        self.assertIn("Version 3, 29 June 2007", license_text)
        self.assertIn("END OF TERMS AND CONDITIONS", license_text)
        self.assertFalse((REPOSITORY / "LICENSE").exists())
        self.assertTrue((CORE / ".gitignore").is_file())
        self.assertTrue((CORE / "Makefile").is_file())
        self.assertFalse((REPOSITORY / "Makefile").exists())

    def test_ignore_policy_excludes_siblings_and_generated_core_content(self):
        ignored = {
            "LocalInstance/spaces/example/SPACE.md",
            "AnotherInstance/sources/private/README.md",
            ".idea/workspace.xml",
            "Core/.idea/workspace.xml",
            ".harnessia/instances.yaml",
            "docs/sources/input.txt",
            "docs/deliverables/report.md",
            "docs/wip/backups/README.md",
            "Core/docs/sources/input.txt",
            "Core/docs/deliverables/report.md",
            "Core/docs/wip/backups/README.md",
            "Core/docs/wip/.env.example",
            "Core/docs/sources/.env.dist",
            "scratch.txt",
            "README.md",
            "README-ES.md",
            "LICENSE",
            ".env",
            ".env.example",
            "Core/.env",
            "Core/app/.env.production",
            "Core/.harnessia/instances.yaml",
            "Core/.work/notes.md",
            "Core/logs/run.json",
            "Core/sources/example/README.md",
            "Core/.opencode/skills/example/SKILL.md",
            "Core/.claude/skills/example/SKILL.md",
            "Core/app/__pycache__/core.pyc",
            "Core/.venv/bin/python",
            "Core/.pytest_cache/state",
            "Core/.mypy_cache/state",
            "Core/.ruff_cache/state",
            "Core/.coverage",
            "Core/htmlcov/index.html",
            "Core/.DS_Store",
        }
        maintained = {
            ".gitignore",
            "Core/.gitignore",
            "Core/.env.example",
            "Core/.env.dist",
            "Core/app/.env.example",
            "Core/app/.env.dist",
            "Core/README.md",
            "Core/README-ES.md",
            "Core/LICENSE",
            "Core/docs/DESIGN.md",
            "Core/app/__init__.py",
            "Core/.opencode/agents/space-curator.md",
        }
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            shutil.copyfile(REPOSITORY / ".gitignore", root / ".gitignore")
            (root / "Core").mkdir()
            shutil.copyfile(CORE / ".gitignore", root / "Core/.gitignore")
            result = subprocess.run(
                [
                    "git",
                    "-c",
                    "core.excludesFile=",
                    "check-ignore",
                    "--no-index",
                    "--stdin",
                ],
                cwd=root,
                input="\n".join(sorted(ignored | maintained)) + "\n",
                text=True,
                capture_output=True,
                check=True,
            )
        self.assertEqual(set(result.stdout.splitlines()), ignored)


if __name__ == "__main__":
    unittest.main()
