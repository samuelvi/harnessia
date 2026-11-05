from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import unittest

from app.source_update import fetch_sources, pull_sources
from app.space import HarnessiaError


def git(directory: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class SourceUpdateTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.seed = self.root / "seed"
        self.remote = self.root / "remote.git"
        self.source = self.root / "sources/example"
        self.seed.mkdir(parents=True)
        git(self.seed, "init", "-b", "main")
        git(self.seed, "config", "user.name", "Harnessia Test")
        git(self.seed, "config", "user.email", "harnessia@example.invalid")
        (self.seed / "README.md").write_text("one\n")
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-m", "Initial")
        subprocess.run(
            ["git", "init", "--bare", str(self.remote)],
            check=True,
            capture_output=True,
        )
        git(self.seed, "remote", "add", "origin", str(self.remote))
        git(self.seed, "push", "-u", "origin", "main")
        self.source.parent.mkdir(parents=True)
        subprocess.run(
            ["git", "clone", "-b", "main", str(self.remote), str(self.source)],
            check=True,
            capture_output=True,
        )
        (self.root / "sources/unversioned").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def push_update(self, text: str = "two\n") -> str:
        (self.seed / "README.md").write_text(text)
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-m", text.strip())
        git(self.seed, "push", "origin", "main")
        return git(self.seed, "rev-parse", "HEAD")

    def test_fetch_discovers_git_sources_without_changing_worktrees(self):
        original = git(self.source, "rev-parse", "HEAD")
        remote_revision = self.push_update()

        result = fetch_sources(self.root)

        self.assertEqual(
            result.sources,
            (Path("core/example"),),
        )
        self.assertEqual(
            result.skipped,
            (Path("core/unversioned"),),
        )
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), original)
        self.assertEqual(git(self.source, "rev-parse", "origin/main"), remote_revision)

    def test_pull_fast_forwards_from_already_fetched_revision(self):
        remote_revision = self.push_update()
        fetch_sources(self.root)

        result = pull_sources(self.root)

        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0].new_revision, remote_revision)
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), remote_revision)
        self.assertEqual((self.source / "README.md").read_text(), "two\n")

    def test_pull_preflights_every_source_before_updating_any(self):
        second = self.root / "sources/second"
        second.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "-b", "main", str(self.remote), str(second)],
            check=True,
            capture_output=True,
        )
        first_revision = git(self.source, "rev-parse", "HEAD")
        self.push_update()
        fetch_sources(self.root)
        (second / "local.txt").write_text("local\n")

        with self.assertRaisesRegex(HarnessiaError, "worktree is not clean"):
            pull_sources(self.root)

        self.assertEqual(git(self.source, "rev-parse", "HEAD"), first_revision)


if __name__ == "__main__":
    unittest.main()
