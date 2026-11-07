#!/usr/bin/env python3
"""Verify strict empty-catalog Claude startup without a prompt or model call.

Run from Core: uv run --no-project --with 'PyYAML>=6,<7' python -m tests.smoke_claude_mcp
Requires the installed Claude CLI. Uses only synthetic content and leaves no fixture.
"""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from app.layout import CoreLayout, InstanceLayout
from app.orchestration import SpaceLocation, build_space_consumer
from app.projections.base import apply_projection_plans


def main() -> int:
    executable = shutil.which("claude")
    if executable is None:
        print("FAIL: Claude CLI is required")
        return 1
    with tempfile.TemporaryDirectory(prefix="harnessia-claude-mcp-") as temporary:
        root = Path(temporary).resolve()
        instance = InstanceLayout.at("fixture", root / "instance")
        space = instance.spaces / "mcp-fixture"
        space.mkdir(parents=True)
        (root / "SOUL.md").write_text("")
        (root / "INSTRUCTIONS.md").write_text("# Synthetic fixture\n")
        (space / "SOUL.md").write_text("")
        (space / "INSTRUCTIONS.md").write_text("# Synthetic fixture\n")
        (space / "SPACE.md").write_text(
            "---\nversion: 2\nskills: []\nmcp: [playwright]\n---\n\n# Fixture\n"
        )
        plan = build_space_consumer(CoreLayout.at(root), SpaceLocation(instance, "mcp-fixture"))
        apply_projection_plans(plan.projections)
        # A project server must not survive the strict empty catalog. Its command
        # would exit immediately if loaded; the smoke must report no server at all.
        (space / ".mcp.json").write_text(json.dumps({"mcpServers": {
            "must-not-load": {"command": sys.executable, "args": ["-c", "pass"]}
        }}))
        requests = [
            {"type": "control_request", "request_id": "initialize",
             "request": {"subtype": "initialize", "hooks": None}},
            {"type": "control_request", "request_id": "mcp-status",
             "request": {"subtype": "mcp_status"}},
        ]
        try:
            result = subprocess.run(
                [executable, "--print", "--input-format", "stream-json",
                 "--output-format", "stream-json", "--verbose", "--no-session-persistence",
                 "--setting-sources", "project", "--strict-mcp-config",
                 "--mcp-config", ".claude/harnessia-mcp.json"],
                input="".join(json.dumps(request) + "\n" for request in requests),
                cwd=space, capture_output=True, text=True, timeout=45,
            )
            messages = [json.loads(line) for line in result.stdout.splitlines()
                        if line.startswith("{")]
        except (OSError, subprocess.TimeoutExpired, ValueError):
            print("FAIL: Claude control handshake unavailable")
            return 1
        status = next((message.get("response", {}) for message in messages
                       if message.get("type") == "control_response"
                       and message.get("response", {}).get("request_id") == "mcp-status"), {})
        if (result.returncode != 0 or status.get("subtype") != "success"
                or status.get("response", {}).get("mcpServers") != []):
            print("FAIL: strict empty-catalog startup did not confirm zero MCP servers")
            return 1
    print("PASS: Claude strict startup has zero MCP servers, no dummy and no model request")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
