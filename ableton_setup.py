"""Backend for the Ableton MCP setup assistant."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


PACKAGE = "mcp-server-ableton-live@1.8.1"
SERVER_NAME = "ableton-live-mcp-setup"


def find_uvx():
    executable = "uvx.exe" if os.name == "nt" else "uvx"
    found = shutil.which(executable)
    if found:
        return str(Path(found).resolve())
    for folder in (Path.home() / ".local" / "bin", Path.home() / ".cargo" / "bin"):
        candidate = folder / executable
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(
        "uvx was not found. Install uv using the Install uv button, "
        "then reopen this app."
    )


def client_path(client, system, home, appdata=None):
    home = Path(home)
    if system == "Darwin":
        root = home / "Library" / "Application Support"
    elif system == "Windows":
        if not appdata:
            raise ValueError("APPDATA is not set; cannot find client configuration.")
        root = Path(appdata)
    else:
        raise ValueError("This app supports macOS and Windows.")
    if client == "vscode":
        return root / "Code" / "User" / "mcp.json"
    if client == "claude":
        return root / "Claude" / "claude_desktop_config.json"
    raise ValueError(f"Unknown client: {client}")


def configure_client(path, client, uvx):
    """Add an entry without replacing one or discarding a non-JSON configuration."""
    path = Path(path)
    if client not in ("vscode", "claude"):
        raise ValueError(f"Unknown client: {client}")
    if path.is_symlink():
        raise ValueError(f"Refusing to replace the linked configuration file {path}.")
    if not path.parent.is_dir():
        raise FileNotFoundError(
            f"Client settings folder not found: {path.parent}. "
            "Install and open the client once, then try again."
        )
    existing = path.exists()
    if existing:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(
                f"Cannot safely edit {path}: it is not standard JSON. "
                "The original was not changed; add the server manually instead."
            ) from exc
    else:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object; no changes made.")
    key = "servers" if client == "vscode" else "mcpServers"
    servers = data.setdefault(key, {})
    if not isinstance(servers, dict):
        raise ValueError(f"{key} in {path} must be an object; no changes made.")
    entry = {"command": str(uvx), "args": [PACKAGE]}
    if client == "vscode":
        entry["type"] = "stdio"
    if SERVER_NAME in servers:
        if servers[SERVER_NAME] == entry:
            return f"Already configured: {path}"
        raise ValueError(
            f"{SERVER_NAME} already exists in {path} with different settings. "
            "Review it manually; no changes made."
        )
    servers[SERVER_NAME] = entry
    if existing:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=path.name + ".", suffix=".bak", dir=path.parent, delete=False
        ) as backup:
            backup.write(path.read_bytes())
            backup_path = backup.name
    else:
        backup_path = None
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as out:
            temporary = Path(out.name)
            json.dump(data, out, indent=2, ensure_ascii=False)
            out.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return f"Configured: {path}" + (f"\nBackup: {backup_path}" if backup_path else "")


def run_bridge(uvx, action, library=""):
    if action not in ("install", "doctor"):
        raise ValueError("Unsupported bridge action.")
    command = [uvx, PACKAGE, action]
    if library:
        command.extend(["--user-library", library])
    if action == "doctor":
        command.append("--json")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=300, creationflags=flags,
    )
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    if result.returncode:
        raise RuntimeError(f"{action} failed (exit {result.returncode}):\n{output}")
    return output or f"{action} completed."
