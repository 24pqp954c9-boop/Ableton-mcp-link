"""Desktop setup assistant for the community Ableton Live MCP server."""

import os
from pathlib import Path
import platform
from subprocess import TimeoutExpired
import sys
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import webbrowser

from ableton_setup import client_path, configure_client, find_uvx, run_bridge


class SetupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ableton MCP Setup")
        self.geometry("760x700")
        self.minsize(630, 600)
        self.library = tk.StringVar()
        self.buttons = []

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Ableton MCP Setup", font=("TkDefaultFont", 20, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="Connect Ableton Live 12 to VS Code Copilot or Claude Desktop.",
        ).pack(anchor="w", pady=(4, 12))

        self.button(frame, "1. Install uv (opens instructions)", lambda: webbrowser.open(
            "https://docs.astral.sh/uv/getting-started/installation/"
        )).pack(anchor="w")
        ttk.Label(
            frame, text="Install uv first. Internet access is needed to download the MCP server."
        ).pack(anchor="w", pady=(3, 10))

        ttk.Label(frame, text="Optional: custom Ableton User Library folder").pack(anchor="w")
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(3, 6))
        ttk.Entry(row, textvariable=self.library).pack(side="left", fill="x", expand=True)
        self.button(row, "Browse", self.browse).pack(side="left", padx=(6, 0))
        self.button(frame, "2. Install Ableton Remote Script", lambda: self.start("install")).pack(anchor="w")
        ttk.Label(
            frame,
            text=("Restart Live, then select AbletonMCP in Settings > Tempo & MIDI > "
                  "Control Surface. Set Input and Output to None."),
            wraplength=700, justify="left",
        ).pack(anchor="w", pady=(6, 10))

        clients = ttk.Frame(frame)
        clients.pack(anchor="w")
        self.button(clients, "3. Configure VS Code Copilot", lambda: self.start("vscode")).pack(side="left")
        self.button(clients, "Configure Claude Desktop", lambda: self.start("claude")).pack(side="left", padx=8)
        ttk.Label(
            frame, text="Restart the selected client after setup; start the server in its MCP settings.",
            wraplength=700,
        ).pack(anchor="w", pady=(6, 10))

        self.button(frame, "4. Check connection", lambda: self.start("doctor")).pack(anchor="w")
        ttk.Label(
            frame,
            text="Keep Live open and dismiss any dialogs before checking. Save your Live set before AI edits.",
            wraplength=700,
        ).pack(anchor="w", pady=(6, 8))
        self.output = scrolledtext.ScrolledText(frame, height=10, wrap="word", state="disabled")
        self.output.pack(fill="both", expand=True)
        self.log(
            "This is an independent setup assistant, not an Ableton product. "
            "The bridge listens on localhost without authentication: do not expose its port."
        )

    def button(self, parent, text, command):
        button = ttk.Button(parent, text=text, command=command)
        self.buttons.append(button)
        return button

    def browse(self):
        selected = filedialog.askdirectory(title="Choose Ableton User Library")
        if selected:
            self.library.set(selected)

    def log(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def start(self, action):
        for button in self.buttons:
            button.configure(state="disabled")
        library = self.library.get().strip()
        self.log(f"Running {action}...")
        threading.Thread(target=self.worker, args=(action, library), daemon=True).start()

    def worker(self, action, library):
        try:
            uvx = find_uvx()
            if action in ("install", "doctor"):
                message = run_bridge(uvx, action, library)
            else:
                path = client_path(action, platform.system(), Path.home(), os.environ.get("APPDATA"))
                message = configure_client(path, action, uvx)
        except (OSError, ValueError, RuntimeError, TimeoutExpired) as exc:
            message = f"Setup did not complete: {exc}"
        self.after(0, self.finished, message)

    def finished(self, message):
        self.log(message)
        for button in self.buttons:
            button.configure(state="normal")


if __name__ == "__main__":
    if "--self-test" not in sys.argv:
        SetupApp().mainloop()
