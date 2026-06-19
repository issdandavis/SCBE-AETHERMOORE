"""desktop_access: one governed action registry, exposed through all three AI access points.

An AI can operate a desktop three ways (cheapest + most reliable first):
  1. ACTION API / MCP  -- the AI calls a named verb (open_app, run_allowed_command) directly.
  2. DOM / accessibility -- the AI clicks the real element by selector + ARIA role/label.
  3. PIXELS / set-of-marks -- the AI picks a numbered mark overlaid on a screenshot.

This is the SCBE control plane: ONE registry of typed, allowlist-classed actions, surfaced all
three ways off the same definitions, so the same action is reachable as a verb, a selector, or a
mark. EVERY invocation goes through the allowlist (safe / guarded / denied) + a destructive-command
screen (the never-delete rule, in-system) and emits a SHA-256 sealed receipt. The reliable channel
(the action API) is what should actually drive your own apps; DOM and pixels are for surfaces you
did not instrument (un-wired apps, then canvas/emulator regions).

Governance honesty: the deterministic gate here is the allowlist + destructive screen. If the SCBE
L13 intent gate is importable it is layered on top of any free-text command; otherwise the allowlist
+ destructive screen stand alone. This is exactly the allowlist model the AetherDesk shell already
uses, made governable and multi-channel.

    from python.scbe.desktop_access import default_registry
    reg = default_registry()
    reg.invoke("open_app", {"app": "terminal"})       # the verb channel (governed + sealed)
    reg.access_points("open_app")                      # the same action, all three ways
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

# destructive / broad-scope commands refused outright, no confirm overrides (never-delete rule)
_DESTRUCTIVE = re.compile(
    r"\b(rm\s+-rf|rm\s+-fr|rmdir\s+/s|del\s+/|format\b|mkfs|dd\s+if=|shutdown|reboot|"
    r":\(\)\{|>\s*/dev/sd|chmod\s+-r\s+000)\b|wipe|fdisk",
    re.IGNORECASE,
)


def _seal(rec: dict) -> str:
    body = {k: v for k, v in rec.items() if k != "seal"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _gate(text: str) -> Optional[str]:
    """Best-effort SCBE L13 intent gate over free-text; None if the gate is not importable."""
    for mod in ("scbe_aethermoore", "src.scbe_aethermoore"):
        try:
            scan = __import__(mod, fromlist=["scan"]).scan
            return scan(text)["decision"]
        except Exception:
            continue
    return None


@dataclass(frozen=True)
class Action:
    """One desktop action, defined once and surfaced through all three access points."""

    name: str
    summary: str
    params: Dict[str, str]  # param name -> type ("string"/"int")
    safety: str  # "safe" | "guarded" | "denied"
    selector: str  # DOM selector for the structure channel
    role: str  # ARIA role
    label: str  # ARIA / accessible name
    handler: Callable[[Dict[str, Any]], Any]
    text_param: Optional[str] = None  # which param carries free text to gate (e.g. a command)


@dataclass
class ActionRegistry:
    actions: Dict[str, Action] = field(default_factory=dict)
    transcript: List[dict] = field(default_factory=list)

    def register(self, action: Action) -> None:
        self.actions[action.name] = action

    # --- access point 1: the verb / action API (governed + sealed) ---------------
    def invoke(self, name: str, params: Optional[Dict[str, Any]] = None, confirm: Optional[str] = None) -> dict:
        params = params or {}
        action = self.actions.get(name)
        rec: dict = {"hop": len(self.transcript) + 1, "action": name, "params": params, "decision": "", "result": ""}
        if action is None:
            rec.update(decision="NO_ACTION", result="no action %r" % name)
        elif action.safety == "denied":
            rec.update(decision="DENIED", result="action %r is denied" % name)
        else:
            text = str(params.get(action.text_param, "")) if action.text_param else ""
            gate = _gate(text) if text else None
            if text and _DESTRUCTIVE.search(text):
                rec.update(decision="REFUSED", result="destructive/broad-scope command blocked: %r" % text)
            elif gate in ("DENY", "ESCALATE"):
                rec.update(decision="REFUSED", result="L13 gate %s on %r" % (gate, text), gate=gate)
            elif action.safety == "guarded" and not confirm:
                rec.update(decision="NEEDS_CONFIRM", result="guarded action; pass confirm='<reason>'")
            else:
                rec.update(decision="ALLOWED", result=action.handler(params), gate=gate)
        rec["seal"] = _seal(rec)
        self.transcript.append(rec)
        return rec

    def verify(self) -> bool:
        return all(r.get("seal") == _seal(r) for r in self.transcript)

    # --- access point 1 (schema): MCP tools ---------------------------------------
    def mcp_tools(self) -> List[dict]:
        return [
            {
                "name": a.name,
                "description": a.summary,
                "safety": a.safety,
                "inputSchema": {
                    "type": "object",
                    "properties": {p: {"type": t} for p, t in a.params.items()},
                    "required": list(a.params),
                },
            }
            for a in self.actions.values()
            if a.safety != "denied"
        ]

    # --- access point 2: DOM / accessibility manifest -----------------------------
    def dom_manifest(self) -> Dict[str, dict]:
        return {a.name: {"selector": a.selector, "role": a.role, "label": a.label} for a in self.actions.values()}

    # --- access point 3: pixels / set-of-marks ------------------------------------
    def set_of_marks(self) -> List[dict]:
        return [
            {"mark": i, "action": a.name, "label": a.label, "selector": a.selector}
            for i, a in enumerate(self.actions.values(), start=1)
        ]

    # --- the unifying view: one action, all three access points -------------------
    def access_points(self, name: str) -> dict:
        a = self.actions[name]
        marks = {m["action"]: m["mark"] for m in self.set_of_marks()}
        return {
            "action": name,
            "verb": {"call": name, "params": list(a.params), "safety": a.safety},  # channel 1
            "dom": {"selector": a.selector, "role": a.role, "label": a.label},  # channel 2
            "pixels": {"mark": marks[name], "label": a.label},  # channel 3
        }


# --- a representative AetherDesk-style action set -------------------------------
_APPS = ["terminal", "files", "editor", "browser", "settings"]
_ALLOWED_CMDS = {"help", "apps", "ls", "pwd", "echo", "date", "whoami"}


def default_registry() -> ActionRegistry:
    reg = ActionRegistry()

    def list_apps(_p):
        return {"apps": _APPS}

    def open_app(p):
        app = p.get("app", "")
        return ("opened %s" % app) if app in _APPS else "no app %r" % app

    def list_windows(_p):
        return {"windows": []}

    def focus_window(p):
        return "focused window %s" % p.get("id", "")

    def run_allowed_command(p):
        cmd = str(p.get("command", "")).strip()
        head = cmd.split()[0] if cmd else ""
        return ("ran: %s" % cmd) if head in _ALLOWED_CMDS else "command %r not on the allowlist" % head

    def save_file(p):
        return "saved %s (%d bytes)" % (p.get("path", ""), len(str(p.get("content", ""))))

    def shutdown(_p):
        return "should never run"

    reg.register(Action("list_apps", "List installed apps", {}, "safe", "#start-menu", "list", "Start menu", list_apps))
    reg.register(
        Action(
            "open_app", "Open an app by name", {"app": "string"}, "safe", "[data-app]", "button", "App icon", open_app
        )
    )
    reg.register(Action("list_windows", "List open windows", {}, "safe", "#taskbar", "list", "Taskbar", list_windows))
    reg.register(
        Action(
            "focus_window",
            "Focus a window",
            {"id": "string"},
            "safe",
            "[data-win]",
            "button",
            "Window tab",
            focus_window,
        )
    )
    reg.register(
        Action(
            "run_allowed_command",
            "Run an allowlisted terminal command",
            {"command": "string"},
            "guarded",
            "#terminal-input",
            "textbox",
            "Terminal",
            run_allowed_command,
            text_param="command",
        )
    )
    reg.register(
        Action(
            "save_file",
            "Save content to a path",
            {"path": "string", "content": "string"},
            "guarded",
            "#save",
            "button",
            "Save",
            save_file,
            text_param="content",
        )
    )
    reg.register(Action("shutdown", "Power off (denied)", {}, "denied", "#power", "button", "Power", shutdown))
    return reg


# --- access point 4: the Rubik's cube as the controller ------------------------
# Each face-turn SELECTS a desktop action; a twist sequence plays a sequence of governed,
# sealed actions. The cube steering wheel now steers the DESKTOP, not arithmetic -- so a human
# (or a speedcuber, or the AI) can "play" the cube to operate the desktop, every turn governed.
_MOVE_ACTION: Dict[str, tuple] = {
    "U": ("list_apps", {}),
    "R": ("open_app", {"app": "terminal"}),
    "F": ("list_windows", {}),
    "D": ("focus_window", {"id": "1"}),
    "L": ("save_file", {"path": "/note", "content": "hi"}),
    "B": ("run_allowed_command", {"command": "help"}),
}


def cube_moves() -> Dict[str, str]:
    """The cube controller map: face-turn -> desktop action."""
    return {m: name for m, (name, _) in _MOVE_ACTION.items()}


def play_cube(reg: ActionRegistry, twists: str, confirm: Optional[str] = None) -> dict:
    """Play a Singmaster twist sequence as DESKTOP actions through the governed registry."""
    hops: List[dict] = []
    for raw in twists.replace(",", " ").split():
        m = raw.strip().upper().rstrip("'")  # face letter; primes ignored for now
        if m not in _MOVE_ACTION:
            hops.append({"move": raw, "decision": "UNKNOWN_MOVE", "result": "no action on %r" % raw})
            continue
        name, params = _MOVE_ACTION[m]
        r = reg.invoke(name, params, confirm=confirm)
        hops.append({"move": raw, "action": name, "decision": r["decision"], "result": r["result"]})
    return {
        "twists": twists,
        "hops": hops,
        "sealed": reg.verify(),
        "route": " -> ".join("%s:%s" % (h["move"], h.get("action", "?")) for h in hops),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    reg = default_registry()
    print("DESKTOP ACCESS  one registry, three access points  (%d actions)\n" % len(reg.actions))
    print("== access point 1: VERB / MCP (governed + sealed) ==")
    for name, params in [
        ("open_app", {"app": "terminal"}),
        ("run_allowed_command", {"command": "rm -rf /"}),
        (
            "run_allowed_command",
            {"command": "ls"},
        ),
        ("shutdown", {}),
    ]:
        r = reg.invoke(name, params if isinstance(params, dict) else {}, confirm="demo")
        print(
            "  %-20s -> %-13s %s"
            % (name + str(params if name == "run_allowed_command" else ""), r["decision"], r["result"])
        )
    print("  transcript sealed:", reg.verify())
    print("\n== access point 2: DOM manifest (sample) ==")
    print("  open_app ->", reg.dom_manifest()["open_app"])
    print("\n== access point 3: set-of-marks (sample) ==")
    print(" ", reg.set_of_marks()[:3])
    print("\n== the same action, all three ways ==")
    print("  open_app ->", json.dumps(reg.access_points("open_app")))
    print("\n== access point 4: the RUBIK'S CUBE as the controller ==")
    print("  cube map:", cube_moves())
    cr = play_cube(reg, "U R F B", confirm="cube turn")
    print("  play 'U R F B' ->", cr["route"])
    for h in cr["hops"]:
        print("    %-3s %-20s %-13s %s" % (h["move"], h.get("action", "-"), h["decision"], h["result"]))
    print("  transcript still sealed:", cr["sealed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
