from pathlib import Path
import json
import subprocess
import unittest
from unittest.mock import patch

from app.mcp_inventory import read_mcp_inventory


class McpInventoryTest(unittest.TestCase):
    def test_keeps_only_valid_names_and_known_statuses(self):
        response = {"location": {"secret": "private"}, "data": [
            {"name": "playwright", "status": {"status": "connected"},
             "headers": {"Authorization": "secret"}},
            {"name": "context7", "status": {"status": "needs_auth", "error": "secret"}},
            {"name": "private token: secret", "status": {"status": "failed"}},
            {"name": "custom", "status": {"status": "unknown-secret"}},
        ]}
        with patch("app.mcp_inventory.subprocess.run", return_value=
                   subprocess.CompletedProcess([], 0, json.dumps(response), "secret")) as run:
            inventory = read_mcp_inventory("opencode", Path("/workspace"))

        self.assertEqual(run.call_args.args[0],
                         ("opencode", "api", "get", "/api/mcp?location%5Bdirectory%5D=%2Fworkspace"))
        self.assertEqual(run.call_args.kwargs["timeout"], 15)

        self.assertEqual(inventory, {"available": True, "servers": [
            {"id": "context7", "status": "needs_auth"},
            {"id": "custom", "status": "unknown"},
            {"id": "playwright", "status": "connected"},
        ]})
        self.assertNotIn("secret", json.dumps(inventory))

    def test_unavailable_inventory_never_claims_servers_are_absent(self):
        for failure in (OSError("secret"), subprocess.TimeoutExpired("opencode", 15)):
            with self.subTest(failure=type(failure).__name__), patch(
                "app.mcp_inventory.subprocess.run", side_effect=failure
            ):
                self.assertEqual(read_mcp_inventory("opencode", Path("/workspace")),
                                 {"available": False, "servers": []})

    def test_rejects_failed_malformed_and_unexpected_api_output(self):
        for code, output in ((1, "secret"), (0, "not json"), (0, "[]"),
                             (0, '{"data": {}}'), (0, '{"data": [null]}')):
            with self.subTest(output=output), patch(
                "app.mcp_inventory.subprocess.run", return_value=
                subprocess.CompletedProcess([], code, output, "secret")
            ):
                self.assertEqual(read_mcp_inventory("opencode", Path("/workspace")),
                                 {"available": False, "servers": []})
