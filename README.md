# Ableton MCP Link

Tools for Ableton Live 12.

## Ableton MCP Setup

A desktop setup assistant for the independent [Ableton Live MCP server](https://github.com/wstierhout/ableton-live-mcp).
It helps install the Remote Script, configure GitHub Copilot in VS Code and/or
Claude Desktop, and check the connection. The app does not itself generate music
or provide an AI service.

### Get the app

On GitHub, open **Actions > Build setup app**, select a successful run, and
download the artifact for your computer: Windows, macOS Apple Silicon, or macOS
Intel. Extract the downloaded archive; on macOS, extract the app archive inside
it as well. You can send the resulting app to a friend. Artifacts expire and
may require GitHub sign-in; download and share the app itself if needed.

The builds are **unsigned and not notarized**. macOS Gatekeeper or Windows
SmartScreen may block them. Only open a build you trust; macOS users can use
System Settings > Privacy & Security to allow a blocked app. Signing and
notarization require an Apple developer account and are not configured here.

### Set up

1. Install Ableton Live 12 and the AI client you want to use. Open each client
   once so its user settings folder exists.
2. Open the setup app. Use its link to install [uv](https://docs.astral.sh/uv/)
   if it is not installed; reopen the app afterwards. Internet access is needed
   for uv to fetch the pinned MCP package and its dependencies.
3. If your Ableton User Library is not at the default location, choose it with
   **Browse**. Click **Install Ableton Remote Script**. Existing, different
   scripts are not replaced.
4. Restart Live. In **Settings > Tempo & MIDI**, select **AbletonMCP** in an
   unused Control Surface row and set its input and output to **None**.
5. Configure the client(s) you use, then restart them. In VS Code, start the
   server from the MCP settings and enable its tools in Copilot Chat. In Claude
   Desktop, confirm the server is available.
6. With Live open, click **Check connection**. Ask your AI client to read the
   tempo and track names first; use a disposable set when trying edits.

The app only adds its own named server. It backs up existing JSON settings
before modifying them, refuses to overwrite a conflicting entry, and leaves
files it cannot safely parse untouched. In particular VS Code configuration
may contain JSON with comments; if so, use **MCP: Open User Configuration** in
VS Code and manually add the following inside its existing `servers` object.
Replace the example path with the result of `which uvx` on macOS or
`where uvx` in Windows Command Prompt (use forward slashes in Windows paths):

```json
"ableton-live-mcp-setup": {
  "type": "stdio",
  "command": "/full/path/to/uvx",
  "args": ["mcp-server-ableton-live@1.8.1"]
}
```

Existing custom VS Code profiles are not modified; the app targets the default
profile.

The server downloads code from PyPI, and AI clients can make destructive
changes in Live. Save your set before edits and review tool approvals. The
bridge listens on `127.0.0.1:9877` without authentication; do not forward its
port or expose it to a network.

### Run from source

Requires Python 3.10+ with Tkinter on macOS or Windows:

```sh
python app.py
python -m unittest discover -s tests -v
```

The [build workflow](.github/workflows/build-app.yml) produces standalone app
artifacts using PyInstaller; each recipient still needs Ableton, uv, and an AI
client on their own computer.
