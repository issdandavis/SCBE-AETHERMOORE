#!/usr/bin/env python3
"""Aether TUI -- the SCBE console with a real Claude-Code-style layout.

A live-scrolling field on top (AI replies, scene text, command output stream in
here) and an anchored input box at the bottom. You type a NUMBER you can see, or
plain English to talk to the AI. Scenes branch, nest, and loop -- interactive
fiction over the real SCBE tools.

    python scripts/aether_tui.py              # run it
    python scripts/aether_tui.py --selftest   # headless verify (no terminal needed)

Falls back to scripts/aether_console.py if Textual isn't installed.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CATALOG = Path(__file__).resolve().parent / "powershell" / "AetherMenu.catalog.json"

try:
    from rich.text import Text
    from textual import work
    from textual.app import App, ComposeResult
    from textual.widgets import Footer, Header, Input, RichLog
except Exception:  # textual missing -> defer to the print-loop console
    if __name__ == "__main__" and "--selftest" not in sys.argv:
        os.execv(sys.executable, [sys.executable, str(Path(__file__).with_name("aether_console.py"))])
    raise


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))["categories"]


def _git(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, cwd=str(REPO), timeout=5).stdout.strip()
    except Exception:
        return ""


NARRATION = {
    "__hub__": "You stand at the heart of the system. Doors hum around you -- pick one, or just speak.",
    "GitHub": "The forge -- where your work becomes real and ships.",
    "Tokens & Cube": "The lexicon -- turn plain words into the six sacred tongues.",
    "Chemistry": "The crucible -- words become atoms, bonds, and orbitals.",
    "Safety & Governance": "The gate -- decide what is allowed to pass.",
    "Code & AI": "The familiar -- ask, and it answers; command, and it acts.",
    "Notes & Vault": "The archive -- everything you have written, within reach.",
    "System & Health": "The engine room -- check the pulse of the machine.",
    "See & Feel (Synesthesia)": "The prism -- see, hear, and feel any thought.",
}


class AetherApp(App):
    CSS = """
    Screen { layout: vertical; }
    RichLog { height: 1fr; padding: 0 1; background: $surface; }
    Input { dock: bottom; border: round $accent; }
    """
    TITLE = "AETHER CONSOLE"
    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self.cats = load_catalog()
        self.mode = "hub"  # hub | scene | await_input | await_confirm
        self.scene = None
        self.pending = None  # action awaiting an input value
        self.pending_cmd = None  # command awaiting y/n confirm

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RichLog(id="log", wrap=True, highlight=False)
        yield Input(placeholder="Type a number you see, or talk to the AI...   (q to quit)", id="cmd")
        yield Footer()

    def on_mount(self):
        repo = _git(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]) or REPO.name
        branch = _git(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "-"
        self.sub_title = f"{repo} - {branch}"
        self.show_hub()
        self.query_one("#cmd", Input).focus()

    # ---- output helpers ----
    def w(self, markup: str):
        self.query_one("#log", RichLog).write(Text.from_markup(markup))

    def show_hub(self):
        self.w("")
        self.w("[bold cyan]== AETHER CONSOLE -- what do you want to do? ==[/]")
        self.w(f"[magenta]{NARRATION['__hub__']}[/]")
        self.w("")
        for i, cat in enumerate(self.cats, 1):
            self.w(f"  [cyan]{i:>2})[/]  {cat.get('icon', '')}  {cat['category']}")
        self.w("  [green]a)[/] ask the AI anything      [dim]q) quit[/]")
        self.mode = "hub"
        self.scene = None

    def show_scene(self, cat):
        self.w("")
        self.w(f"[bold cyan]== {cat.get('icon', '')} {cat['category']} ==[/]")
        self.w(f"[magenta]{NARRATION.get(cat['category'], '')}[/]")
        self.w("")
        for i, a in enumerate(cat["actions"], 1):
            self.w(f"  [cyan]{i:>2})[/]  {a['label']}")
            if a.get("desc"):
                self.w(f"       [dim]{a['desc']}[/]")
        self.w("  [dim]b) back to the hub      q) quit[/]")
        self.scene = cat
        self.mode = "scene"

    # ---- run commands, streaming output into the log ----
    def _catalog_argv(self, cmd: str) -> list[list[str]]:
        parts = shlex.split(cmd)
        commands: list[list[str]] = [[]]
        for part in parts:
            if part == "&&":
                commands.append([])
                continue
            commands[-1].append(sys.executable if part == "python" else part)
        return [argv for argv in commands if argv]

    @work(thread=True, exclusive=False)
    def run_command(self, cmd: str):
        self.call_from_thread(self.w, f"[green]> {cmd}[/]")
        env = dict(os.environ, PYTHONPATH=".")
        try:
            for argv in self._catalog_argv(cmd):
                proc = subprocess.Popen(
                    argv,
                    cwd=str(REPO),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                )
                assert proc.stdout is not None
                for line in proc.stdout:
                    self.call_from_thread(self.w, line.rstrip("\n"))
                proc.wait()
                if proc.returncode:
                    break
            self.call_from_thread(self.w, "[dim](done)[/]")
        except Exception as e:  # pragma: no cover
            self.call_from_thread(self.w, f"[red](error: {e})[/]")

    def ask_ai(self, q: str):
        self.run_command(f"python scbe.py ask {shlex.quote(q)}")

    def choose(self, action):
        if action.get("needs_input"):
            self.pending = action
            self.mode = "await_input"
            self.w(f"[yellow]{action.get('input_prompt', 'Value')}[/]")
        elif action.get("run_mode") == "confirm":
            self.pending_cmd = action["command"]
            self.mode = "await_confirm"
            self.w(f"[yellow]Run this?  {action['command']}   (y / n)[/]")
        else:
            self.run_command(action["command"])

    # ---- the one input handler: a number, or English ----
    def on_input_submitted(self, event: Input.Submitted):
        val = event.value.strip()
        self.query_one("#cmd", Input).value = ""
        if not val:
            return
        low = val.lower()
        if low in ("q", "quit", "exit"):
            self.exit()
            return

        if self.mode == "await_input":
            if low in ("b", "back", "cancel"):
                self.pending, self.mode = None, "scene"
                self.w("[dim](cancelled)[/]")
                return
            action, self.pending = self.pending, None
            cmd = action["command"].replace("{input}", val)
            if action.get("run_mode") == "confirm":
                self.pending_cmd, self.mode = cmd, "await_confirm"
                self.w(f"[yellow]Run this?  {cmd}   (y / n)[/]")
            else:
                self.mode = "scene"
                self.run_command(cmd)
            return

        if self.mode == "await_confirm":
            if low in ("y", "yes"):
                self.run_command(self.pending_cmd)
            else:
                self.w("[dim](cancelled)[/]")
            self.pending_cmd, self.mode = None, "scene"
            return

        if self.mode == "hub":
            if val.isdigit() and 1 <= int(val) <= len(self.cats):
                self.show_scene(self.cats[int(val) - 1])
            elif low in ("a", "ask"):
                self.w("[green]Ask away -- type your question and press Enter.[/]")
            else:
                self.ask_ai(val)
            return

        # scene
        if low in ("b", "back"):
            self.show_hub()
            return
        actions = self.scene["actions"]
        if val.isdigit() and 1 <= int(val) <= len(actions):
            self.choose(actions[int(val) - 1])
        else:
            self.ask_ai(val)


async def _selftest():
    """Headless verification via Textual's test pilot -- no terminal needed."""
    app = AetherApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.mode == "hub", f"start: expected hub, got {app.mode}"
        inp = app.query_one("#cmd", Input)
        inp.value = "1"
        await pilot.press("enter")
        await pilot.pause()
        assert app.mode == "scene", f"after '1': expected scene, got {app.mode}"
        assert app.scene is app.cats[0], "entered the wrong scene"
        # a needs-input choice should pause for the value
        idx = next((i for i, a in enumerate(app.scene["actions"], 1) if a.get("needs_input")), None)
        if idx:
            inp.value = str(idx)
            await pilot.press("enter")
            await pilot.pause()
            assert app.mode == "await_input", f"needs-input: expected await_input, got {app.mode}"
            inp.value = "back"  # bail out of the pending input
            await pilot.press("enter")
            await pilot.pause()
        inp.value = "b"
        await pilot.press("enter")
        await pilot.pause()
        assert app.mode == "hub", f"after 'b': expected hub, got {app.mode}"
    print("SELFTEST PASS: hub -> scene -> needs-input prompt -> back to hub all work")


def main():
    if "--selftest" in sys.argv:
        import asyncio

        asyncio.run(_selftest())
        return
    AetherApp().run()


if __name__ == "__main__":
    main()
