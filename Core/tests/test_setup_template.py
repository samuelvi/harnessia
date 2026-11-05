from pathlib import Path
from tempfile import TemporaryDirectory
import os
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/space-setup.sh"


class SetupTemplateTest(unittest.TestCase):
    def test_rejects_documentation_example_path_before_invoking_make(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            marker = directory / "make-invoked"
            executable = directory / "make"
            executable.write_text('#!/bin/sh\n: > "$FAKE_MARKER"\n')
            executable.chmod(0o755)
            environment = os.environ.copy()
            environment.update(
                {
                    "PATH": f"{directory}:{environment['PATH']}",
                    "FAKE_MARKER": str(marker),
                    "INSTANCE": "Work",
                    "INSTANCE_PATH": "/Users/me/Harnessia/Work",
                    "SPACE": "atlas",
                }
            )

            result = subprocess.run(
                ["bash", str(TEMPLATE)],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("set INSTANCE_PATH", result.stderr)
            self.assertFalse(marker.exists())

    def test_attaches_existing_directory_that_is_not_an_initialized_space(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            instance = directory / "Work"
            space = instance / "spaces/example-space"
            space.mkdir(parents=True)
            log = directory / "make-calls"
            executable = directory / "make"
            executable.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$FAKE_LOG"\n')
            executable.chmod(0o755)
            environment = os.environ.copy()
            environment.update(
                {
                    "PATH": f"{directory}:{environment['PATH']}",
                    "FAKE_LOG": str(log),
                    "INSTANCE": "Work",
                    "INSTANCE_PATH": str(instance),
                    "SPACE": "example-space",
                }
            )

            result = subprocess.run(
                ["bash", str(TEMPLATE)],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
            )
            calls = log.read_text().splitlines()

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            calls,
            [
                f"instance-attach INSTANCE=Work INSTANCE_PATH={instance}",
                "sources-clone",
                "space-attach INSTANCE=Work SPACE=example-space",
                "space-configure INSTANCE=Work SPACE=example-space",
                "check INSTANCE=Work",
            ],
        )

    def test_uses_atlas_as_the_demo_space_name(self):
        template = TEMPLATE.read_text()

        self.assertIn('SPACE="${SPACE:-atlas}"', template)

    def test_copy_in_core_docs_wip_runs_make_from_core(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve()
            core = directory / "Core"
            core.mkdir()
            (core / "Makefile").write_text("# Fixture\n")
            (core / "HARNESSIA.md").write_text("# Fixture\n")
            copied = core / "docs/wip/space-setup.sh"
            copied.parent.mkdir(parents=True)
            copied.write_text(TEMPLATE.read_text())
            instance = directory / "Example"
            space = instance / "spaces/atlas"
            space.mkdir(parents=True)
            (space / "SPACE.md").write_text("# Existing Space\n")
            log = directory / "make-calls"
            executable = directory / "make"
            executable.write_text(
                '#!/bin/sh\nprintf "%s %s\\n" "$PWD" "$*" >> "$FAKE_LOG"\n'
            )
            executable.chmod(0o755)
            environment = dict(
                os.environ,
                PATH=f"{directory}:{os.environ['PATH']}",
                FAKE_LOG=str(log),
                INSTANCE="Example",
                INSTANCE_PATH=str(instance),
                SPACE="atlas",
            )

            result = subprocess.run(
                ["bash", str(copied)],
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                log.read_text().splitlines(),
                [
                    f"{core} instance-attach INSTANCE=Example INSTANCE_PATH={instance}",
                    f"{core} sources-clone",
                    f"{core} space-configure INSTANCE=Example SPACE=atlas",
                    f"{core} check INSTANCE=Example",
                ],
            )


if __name__ == "__main__":
    unittest.main()
