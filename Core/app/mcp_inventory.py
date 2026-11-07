"""Best-effort MCP metadata for curation, never configuration or credentials."""

import json
from pathlib import Path
import subprocess
from urllib.parse import urlencode

from .space import MCP_ID


MCP_STATUSES = {"connected", "disabled", "failed", "needs_auth", "pending"}


def read_mcp_inventory(executable: str, directory: Path) -> dict[str, object]:
    unavailable: dict[str, object] = {"available": False, "servers": []}
    try:
        result = subprocess.run(
            (
                executable,
                "api",
                "get",
                "/api/mcp?" + urlencode({"location[directory]": str(directory)}),
            ),
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return unavailable
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            return unavailable
        servers: dict[str, str] = {}
        for entry in payload["data"]:
            if not isinstance(entry, dict):
                return unavailable
            name = entry.get("name")
            if not isinstance(name, str) or len(name) > 64 or not MCP_ID.fullmatch(name):
                continue
            status = entry.get("status")
            state = status.get("status") if isinstance(status, dict) else None
            servers[name] = (
                state if isinstance(state, str) and state in MCP_STATUSES else "unknown"
            )
        return {
            "available": True,
            "servers": [
                {"id": name, "status": servers[name]} for name in sorted(servers)
            ],
        }
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return unavailable
