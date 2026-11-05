from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MakefileContractTest(unittest.TestCase):
    def test_every_public_make_command_is_documented_in_readme(self):
        makefile = (ROOT / "Makefile").read_text()
        readme = (ROOT / "README.md").read_text()
        targets = tuple(re.findall(r"^([a-z][a-z0-9-]*):", makefile, re.MULTILINE))

        self.assertEqual(
            targets,
            (
                "prepare",
                "prepare-core",
                "prepare-instance",
                "prepare-all",
                "instance-create",
                "instance-attach",
                "instance-list",
                "space-create",
                "space-attach",
                "space-configure",
                "check",
                "sources-clone",
                "sources-check",
                "sources-status",
                "sources-fetch",
                "sources-pull",
                "sources-reconcile",
                "test",
                "verify",
            ),
        )
        for target in targets:
            self.assertIn(f"`make {target}", readme)

    def test_prepare_commands_have_unambiguous_scope(self):
        makefile = (ROOT / "Makefile").read_text()
        prepare_instance = makefile.split("prepare-instance:\n", 1)[1].split(
            "\n\n", 1
        )[0]
        prepare_all = makefile.split("prepare-all:\n", 1)[1].split("\n\n", 1)[0]

        self.assertIn("INSTANCE", prepare_instance)
        self.assertIn('prepare-instance "$(INSTANCE)"', prepare_instance)
        self.assertIn("does not accept INSTANCE", prepare_all)
        self.assertNotIn("prepare-all --instance", prepare_all)
        self.assertIn("prepare-all", prepare_all)

    def test_verify_is_read_only(self):
        makefile = (ROOT / "Makefile").read_text()
        recipe = makefile.split("verify:\n", 1)[1]

        self.assertIn("test", recipe)
        self.assertIn("sources-check", recipe)
        self.assertIn("check", recipe)
        self.assertNotIn("prepare", recipe)


if __name__ == "__main__":
    unittest.main()
