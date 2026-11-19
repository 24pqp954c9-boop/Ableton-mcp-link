import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ableton_setup import PACKAGE, SERVER_NAME, client_path, configure_client, run_bridge


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "config.json"

    def test_paths(self):
        self.assertEqual(
            client_path("vscode", "Darwin", "/Users/test"),
            Path("/Users/test/Library/Application Support/Code/User/mcp.json"),
        )
        self.assertEqual(
            client_path("claude", "Windows", "/home/test", "/appdata"),
            Path("/appdata/Claude/claude_desktop_config.json"),
        )
        with self.assertRaises(ValueError):
            client_path("claude", "Windows", "/home/test")

    def test_new_config_and_idempotency(self):
        configure_client(self.path, "vscode", "/path to/uvx")
        data = json.loads(self.path.read_text())
        self.assertEqual(data["servers"][SERVER_NAME], {
            "type": "stdio", "command": "/path to/uvx", "args": [PACKAGE]
        })
        self.assertIn("Already configured", configure_client(self.path, "vscode", "/path to/uvx"))
        self.assertFalse(list(self.path.parent.glob("*.bak")))

    def test_existing_config_is_backed_up_and_preserved(self):
        original = '{"theme": "dark", "mcpServers": {"other": {"command": "ok"}}}\n'
        self.path.write_text(original)
        result = configure_client(self.path, "claude", "uvx")
        data = json.loads(self.path.read_text())
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["mcpServers"]["other"], {"command": "ok"})
        self.assertEqual(data["mcpServers"][SERVER_NAME]["args"], [PACKAGE])
        backups = list(self.path.parent.glob("*.bak"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), original)
        self.assertIn("Backup:", result)

    def test_conflict_does_not_change_config(self):
        original = json.dumps({"servers": {SERVER_NAME: {"command": "different"}}})
        self.path.write_text(original)
        with self.assertRaisesRegex(ValueError, "already exists"):
            configure_client(self.path, "vscode", "uvx")
        self.assertEqual(self.path.read_text(), original)
        self.assertFalse(list(self.path.parent.glob("*.bak")))

    def test_jsonc_is_not_overwritten(self):
        original = '{\n // comment\n "servers": {}\n}'
        self.path.write_text(original)
        with self.assertRaisesRegex(ValueError, "not standard JSON"):
            configure_client(self.path, "vscode", "uvx")
        self.assertEqual(self.path.read_text(), original)

    def test_file_mode_preserved_and_new_parent_creates_config(self):
        self.path.write_text('{"servers": {}}\n')
        os.chmod(self.path, 0o644)
        configure_client(self.path, "vscode", "uvx")
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o644)
        backups = list(self.path.parent.glob("*.bak"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o644)
        fresh_dir = Path(self.tmp.name) / "fresh"
        fresh_dir.mkdir()
        result = configure_client(fresh_dir / "config.json", "vscode", "uvx")
        self.assertIn("Configured:", result)
        data = json.loads((fresh_dir / "config.json").read_text())
        self.assertEqual(data["servers"][SERVER_NAME]["args"], [PACKAGE])

    def test_bad_section_and_missing_parent(self):
        self.path.write_text('{"mcpServers": []}')
        with self.assertRaisesRegex(ValueError, "must be an object"):
            configure_client(self.path, "claude", "uvx")
        with self.assertRaises(FileNotFoundError):
            configure_client(self.path / "missing", "claude", "uvx")


class BridgeTests(unittest.TestCase):
    @patch("ableton_setup.subprocess.run")
    def test_install_with_custom_library(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "installed", "")
        self.assertEqual(run_bridge("/uvx", "install", "/my library"), "installed")
        self.assertEqual(run.call_args.args[0], [
            "/uvx", PACKAGE, "install", "--user-library", "/my library"
        ])

    @patch("ableton_setup.subprocess.run")
    def test_doctor_error_is_not_success(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, '{"ok": false}', "details")
        with self.assertRaisesRegex(RuntimeError, "details"):
            run_bridge("/uvx", "doctor")
        self.assertEqual(run.call_args.args[0], ["/uvx", PACKAGE, "doctor", "--json"])

    def test_rejects_other_action(self):
        with self.assertRaises(ValueError):
            run_bridge("/uvx", "uninstall")


if __name__ == "__main__":
    unittest.main()
