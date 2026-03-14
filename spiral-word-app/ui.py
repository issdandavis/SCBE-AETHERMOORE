#!/usr/bin/env python3
"""
@file ui.py
@module spiral-word-app/ui
@layer Layer 14
@component Textual TUI for SpiralWord

Terminal-based interactive editor with real-time WebSocket sync.
Provides a split view: editor pane + status/audit sidebar.

Run: python ui.py [doc_id] [--server ws://localhost:8000]
"""

import argparse
import asyncio
import json
import sys
import time

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Header, Footer, TextArea, Static, Input, Log
    from textual.binding import Binding
except ImportError:
    print("textual required: pip install textual", file=sys.stderr)
    sys.exit(1)

try:
    import httpx
except ImportError:
    httpx = None

try:
    import websockets
except ImportError:
    websockets = None


class StatusBar(Static):
    """Bottom status bar showing connection and governance info."""

    def __init__(self):
        super().__init__("Disconnected")
        self._doc_id = ""
        self._version = 0
        self._connected = False
        self._tongue = "KO"

    def update_status(
        self, doc_id: str = "", version: int = 0,
        connected: bool = False, tongue: str = "KO"
    ):
        self._doc_id = doc_id
        self._version = version
        self._connected = connected
        self._tongue = tongue
        conn = "Connected" if connected else "Disconnected"
        self.update(
            f" [{conn}] doc={self._doc_id}  v{self._version}  tongue={self._tongue}"
        )


class SpiralWordApp(App):
    """SpiralWord TUI — collaborative editor with SCBE governance."""

    TITLE = "SpiralWord"
    SUB_TITLE = "SCBE-Governed Collaborative Editor"

    CSS = """
    #editor-area {
        height: 1fr;
    }
    #sidebar {
        width: 40;
        border-left: solid $accent;
    }
    #audit-log {
        height: 1fr;
    }
    #command-input {
        dock: bottom;
        height: 3;
    }
    #status-bar {
        dock: bottom;
        height: 1;
        background: $boost;
        color: $text;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+a", "ai_prompt", "AI Edit"),
        Binding("ctrl+r", "refresh", "Refresh"),
    ]

    def __init__(self, doc_id: str, server_url: str):
        super().__init__()
        self.doc_id = doc_id
        self.server_url = server_url
        self.ws_url = server_url.replace("http://", "ws://").replace("https://", "wss://")
        self._ws = None
        self._version = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="editor-area"):
                yield TextArea(id="editor")
                yield Input(
                    placeholder="Type command: /ai <prompt>, /save, /refresh",
                    id="command-input",
                )
            with Vertical(id="sidebar"):
                yield Static("Audit Log", classes="title")
                yield Log(id="audit-log", max_lines=200)
        yield StatusBar()
        yield Footer()

    async def on_mount(self):
        """Load initial document and start WebSocket listener."""
        self._status = self.query_one(StatusBar)
        self._editor = self.query_one("#editor", TextArea)
        self._audit = self.query_one("#audit-log", Log)

        # Load document via REST
        await self._load_document()

        # Start WebSocket sync in background
        self.run_worker(self._ws_loop(), exclusive=True)

    async def _load_document(self):
        """Fetch document content via REST API."""
        if not httpx:
            self._audit.write_line("[WARN] httpx not installed, cannot fetch doc")
            return

        try:
            async with httpx.AsyncClient(base_url=self.server_url) as c:
                r = await c.get(f"/doc/{self.doc_id}")
                r.raise_for_status()
                data = r.json()
                self._editor.load_text(data.get("text", ""))
                self._version = data.get("version", 0)
                self._status.update_status(
                    doc_id=self.doc_id, version=self._version, connected=False
                )
                self._audit.write_line(f"[INFO] Loaded doc '{self.doc_id}' v{self._version}")
        except Exception as e:
            self._audit.write_line(f"[ERROR] Failed to load doc: {e}")

    async def _ws_loop(self):
        """WebSocket listener for real-time sync."""
        if not websockets:
            self._audit.write_line("[WARN] websockets not installed, sync disabled")
            return

        ws_endpoint = f"{self.ws_url}/ws/{self.doc_id}"
        retry_delay = 1.0

        while True:
            try:
                async with websockets.connect(ws_endpoint) as ws:
                    self._ws = ws
                    self._status.update_status(
                        doc_id=self.doc_id, version=self._version, connected=True
                    )
                    self._audit.write_line("[INFO] WebSocket connected")
                    retry_delay = 1.0

                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg["type"] == "snapshot":
                            data = msg["data"]
                            self._editor.load_text(data.get("text", ""))
                            self._version = data.get("version", 0)
                            self._audit.write_line(
                                f"[SYNC] Snapshot v{self._version}"
                            )
                        elif msg["type"] == "op":
                            op = msg["data"]
                            self._audit.write_line(
                                f"[SYNC] {op['op_type']} by {op['site_id']}"
                            )
                            # Reload full doc to stay consistent
                            await self._load_document()
                        elif msg["type"] == "error":
                            self._audit.write_line(
                                f"[ERROR] {msg.get('message', 'unknown')}"
                            )

            except Exception as e:
                self._ws = None
                self._status.update_status(
                    doc_id=self.doc_id, version=self._version, connected=False
                )
                self._audit.write_line(
                    f"[WARN] WebSocket disconnected: {e}. Retrying in {retry_delay:.0f}s..."
                )
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30.0)

    async def on_input_submitted(self, event: Input.Submitted):
        """Handle command input."""
        cmd = event.value.strip()
        event.input.clear()

        if not cmd:
            return

        if cmd.startswith("/ai "):
            prompt = cmd[4:].strip()
            await self._ai_edit(prompt)
        elif cmd == "/save":
            await self.action_save()
        elif cmd == "/refresh":
            await self.action_refresh()
        elif cmd.startswith("/write "):
            text = cmd[7:]
            await self._replace_doc(text)
        else:
            self._audit.write_line(
                f"[CMD] Unknown: {cmd}. Try /ai, /save, /refresh, /write"
            )

    async def _ai_edit(self, prompt: str):
        """Send AI edit request."""
        if not httpx:
            self._audit.write_line("[ERROR] httpx not installed")
            return

        self._audit.write_line(f"[AI] Requesting: {prompt[:60]}...")
        try:
            async with httpx.AsyncClient(base_url=self.server_url, timeout=30.0) as c:
                r = await c.post(
                    f"/doc/{self.doc_id}/ai",
                    json={"prompt": prompt, "provider": "echo", "site_id": "tui"},
                )
                r.raise_for_status()
                d = r.json()

                if d["status"] == "blocked":
                    self._audit.write_line(f"[BLOCKED] {d['message']}")
                else:
                    self._audit.write_line(
                        f"[AI] OK: tongue={d['tongue']} conf={d['confidence']:.2f} "
                        f"len={d['generated_length']}"
                    )
                    await self._load_document()
        except Exception as e:
            self._audit.write_line(f"[ERROR] AI edit failed: {e}")

    async def _replace_doc(self, content: str):
        """Replace document via REST."""
        if not httpx:
            return

        try:
            async with httpx.AsyncClient(base_url=self.server_url) as c:
                r = await c.post(
                    f"/doc/{self.doc_id}/replace",
                    json={"content": content, "site_id": "tui"},
                )
                r.raise_for_status()
                self._audit.write_line(f"[WRITE] Replaced doc v{r.json()['version']}")
                await self._load_document()
        except Exception as e:
            self._audit.write_line(f"[ERROR] Write failed: {e}")

    async def action_save(self):
        """Save current editor content to server."""
        content = self._editor.text
        await self._replace_doc(content)

    async def action_refresh(self):
        """Reload document from server."""
        await self._load_document()

    async def action_ai_prompt(self):
        """Focus the command input for AI prompt."""
        self.query_one("#command-input", Input).focus()

    async def action_quit(self):
        """Quit the app."""
        self.exit()


def main():
    parser = argparse.ArgumentParser(
        prog="spiralword-ui",
        description="SpiralWord TUI — Terminal collaborative editor",
    )
    parser.add_argument("doc_id", nargs="?", default="untitled",
                        help="Document ID to open")
    parser.add_argument("--server", default="http://localhost:8000",
                        help="SpiralWord server URL")
    args = parser.parse_args()

    app = SpiralWordApp(doc_id=args.doc_id, server_url=args.server)
    app.run()


if __name__ == "__main__":
    main()
