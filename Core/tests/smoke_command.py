#!/usr/bin/env python3
"""End-to-end smoke test: an external command resolves to `/echo verified` output.

Single attempt by design: this script never loops and never retries. Long-lived
or scheduled callers own their own retry policy; keep that policy bounded there.

Avoids `openai/*` models by default so a provider outage or account issue cannot
turn this verification into a retry loop of paid API calls. Override the model
with HARNESSIA_SMOKE_MODEL; allow OpenAI explicitly with HARNESSIA_SMOKE_ALLOW_OPENAI=1.
"""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

DEFAULT_MODEL = "google/gemini-flash-lite-latest"
ENGINE_ROOT = Path(__file__).resolve().parents[1]


def default_opencode() -> str:
    """The installed runtime must be V2: V1 binaries reject V2 config keys."""
    v2 = Path.home() / ".opencode/bin/opencode"
    if v2.is_file():
        return str(v2)
    raise SystemExit(
        "FAIL expected the V2 runtime at ~/.opencode/bin/opencode;"
        " set HARNESSIA_OPENCODE to a V2 opencode binary"
    )


def build_fixture(root: Path) -> Path:
    space = root / "instance/spaces/command-fixture"
    source = root / "sources/fixture"
    space.mkdir(parents=True)
    (source / "commands").mkdir(parents=True)
    (root / "SOUL.md").write_text("# Soul\n")
    (root / "INSTRUCTIONS.md").write_text("# Shared instructions\n")
    (space / "SOUL.md").write_text("")
    (space / "INSTRUCTIONS.md").write_text("# Instructions\n")
    (source / "commands/echo.md").write_text(
        "---\ndescription: Command fixture\n---\n\nOutput only COMMAND:$ARGUMENTS\n"
    )
    (space / "SPACE.md").write_text(
        """---
version: 2
skills: []
commands:
  - source: core/fixture
    path: commands/echo.md
---

# Fixture
"""
    )
    return space


def smoke(model: str) -> int:
    # user-site resolves from HOME; read it before swapping HOME so the
    # hermetic fake home still satisfies Python dependencies (yaml, ...).
    import site
    user_site = site.getusersitepackages()
    home = Path.home()
    env = dict(
        os.environ,
        PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        PYTHONPATH=os.pathsep.join(filter(None, [str(ENGINE_ROOT), user_site])),
        PYTHONDONTWRITEBYTECODE="1",
    )
    for name in ("OPENCODE", "OPENCODE_SESSION_ID", "OPENCODE_TERMINAL",
                 "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
        env.pop(name, None)

    with tempfile.TemporaryDirectory(prefix="harnessia-smoke-") as root:
        # Hermetic HOME: no user plugins, global skills, or MCP servers leak in.
        # Only auth.json survives, so the run stays one cheap model call.
        auth_src = home / ".local/share/opencode/auth.json"
        fake_home = Path(root) / "home"
        auth_dir = fake_home / ".local/share/opencode"
        auth_dir.mkdir(parents=True)
        if auth_src.is_file():
            shutil.copy(auth_src, auth_dir / "auth.json")
        env["HOME"] = str(fake_home)
        space = build_fixture(Path(root))
        prep = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os; from pathlib import Path"
                "; from app.layout import CoreLayout, InstanceLayout"
                "; from app.prepare import prepare_instance"
                "; root=Path(os.environ['FIXTURE_ROOT'])"
                "; core=CoreLayout.at(root)"
                "; instance=InstanceLayout.at('work', root/'instance')"
                "; prepare_instance(core, instance, 'command-fixture')",
            ],
            cwd=ENGINE_ROOT,
            env=dict(env, FIXTURE_ROOT=root),
            timeout=60,
        )
        if prep.returncode:
            print(f"FAIL prepare exit={prep.returncode}")
            return prep.returncode

        run = subprocess.run(
            [os.environ.get("HARNESSIA_OPENCODE") or default_opencode(),
             "run", "--standalone", "--auto", "--model", model, "/echo verified"],
            cwd=space,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        output = run.stdout + run.stderr
        if run.returncode:
            print(f"FAIL run exit={run.returncode}\n{output}")
            return run.returncode
        if "COMMAND:verified" not in output:
            print(f"FAIL missing marker\n{output}")
            return 1
    print("OpenCode command smoke test: COMMAND:verified")
    return 0


def main() -> int:
    model = os.environ.get("HARNESSIA_SMOKE_MODEL", DEFAULT_MODEL)
    if model.startswith("openai/") and os.environ.get("HARNESSIA_SMOKE_ALLOW_OPENAI") != "1":
        print(f"FAIL refused openai model {model}:"
              " set HARNESSIA_SMOKE_ALLOW_OPENAI=1 to override")
        return 2
    return smoke(model)


if __name__ == "__main__":
    raise SystemExit(main())
