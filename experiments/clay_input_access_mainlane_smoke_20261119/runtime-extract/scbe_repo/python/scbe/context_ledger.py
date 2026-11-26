"""context_ledger: a command-driven self-context ledger + packer for AIs without their own memory.

A weak / free / stateless model has no place to keep its working context between steps. This is that
place: a tiny store the AI writes to and reads from by RUNNING COMMANDS -- models are better at
running commands than composing prose. It holds small facts (set / get), a todo checklist
(todo / done), and a short running note log, all reachable as one-line commands, and can be RECALLed
to rehydrate context. Every command is appended to a sealed (SHA-256) event log, so the ledger is
tamper-evident and another agent can audit exactly what was written.

PACK is the compaction step: a DETERMINISTIC script (not the model "summarizing", which it is bad
at) that forwards the attention-heavy, context-reliant items (open todos + anchor facts + the most
recent notes), drops the rest (done todos, stale notes), and rewrites the survivors in a fixed
SHORTHAND codec -- more meaning per character, "like Chinese but not Chinese" -- which `expand()`
reverses. (The production shorthand is the Sacred-Tongue tokenizer; this codec is a small stand-in.)

    led = Ledger("agent-7")
    led.run("set goal sum-1..5"); led.run("todo write-loop"); led.run("todo verify")
    led.run("done write-loop"); led.run("note loop emits 15")
    led.run("pack")     # -> forward the heavy context in shorthand; drop the cleared/stale
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

COMMANDS = ("set", "get", "del", "keys", "todo", "done", "todos", "note", "recall", "pack", "help")

# fixed shorthand codec: common task words -> short codes (reversible via expand). Unique codes.
_SHORT = {
    "goal": "g",
    "task": "tk",
    "target": "tg",
    "todo": "+",
    "done": "x",
    "verify": "vf",
    "test": "ts",
    "loop": "lp",
    "write": "wr",
    "build": "bd",
    "run": "rn",
    "fix": "fx",
    "open": "op",
    "close": "cl",
    "function": "fn",
    "value": "vl",
    "check": "ck",
    "read": "rd",
    "save": "sv",
    "file": "fi",
    "error": "er",
    "pass": "ps",
    "fail": "fa",
    "next": "nx",
    "step": "sp",
    "model": "md",
    "context": "cx",
}
_LONG = {v: k for k, v in _SHORT.items()}


def shorten(text: str) -> str:
    """Rewrite text in the shorthand codec -- known words become short codes (more per character)."""
    return " ".join(_SHORT.get(tok.lower(), tok) for tok in text.split())


def expand(text: str) -> str:
    """Reverse the shorthand back to words."""
    return " ".join(_LONG.get(tok, tok) for tok in text.split())


def _seal(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


@dataclass
class Ledger:
    """One agent's command-driven working memory."""

    agent: str = "agent"
    kv: Dict[str, str] = field(default_factory=dict)
    open_todos: List[str] = field(default_factory=list)
    done_todos: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    events: List[dict] = field(default_factory=list)

    def run(self, command: str) -> dict:
        """Execute one command string. The whole interface is commands -- the AI's strength."""
        parts = command.strip().split()
        op = parts[0].lower() if parts else "help"
        arg = " ".join(parts[1:]).strip()
        ok, result = True, ""
        if op not in COMMANDS:
            ok, result = False, "unknown command %r; commands: %s" % (op, " ".join(COMMANDS))
        elif op == "set":
            k, _, v = arg.partition(" ")
            if not k:
                ok, result = False, "usage: set <key> <value>"
            else:
                self.kv[k] = v
                result = "%s=%s" % (k, v)
        elif op == "get":
            ok = arg in self.kv
            result = self.kv.get(arg, "(unset %r)" % arg)
        elif op == "del":
            ok = self.kv.pop(arg, None) is not None
            result = ("deleted %s" % arg) if ok else "(no key %r)" % arg
        elif op == "keys":
            result = " ".join(sorted(self.kv)) or "(empty)"
        elif op == "todo":
            if arg and arg not in self.open_todos and arg not in self.done_todos:
                self.open_todos.append(arg)
            result = "open: " + (", ".join(self.open_todos) or "(none)")
        elif op == "done":
            if arg in self.open_todos:
                self.open_todos.remove(arg)
                self.done_todos.append(arg)
                result = "done: %s" % arg
            else:
                ok, result = False, "(no open todo %r)" % arg
        elif op == "todos":
            result = "open=[%s] done=[%s]" % (", ".join(self.open_todos), ", ".join(self.done_todos))
        elif op == "note":
            if arg:
                self.notes.append(arg)
            result = "noted (%d total)" % len(self.notes)
        elif op == "recall":
            result = self.recall()
        elif op == "pack":
            result = self.pack(compact=True)["shorthand"]
        elif op == "help":
            result = "commands: " + " ".join(COMMANDS)
        rec = {"n": len(self.events) + 1, "cmd": op, "arg": arg, "ok": ok, "result": result}
        rec["seal"] = _seal({k: v for k, v in rec.items() if k != "seal"})
        self.events.append(rec)
        return {"ok": ok, "result": result}

    def recall(self) -> str:
        """The AI's whole working context as compact text, to re-read and continue."""
        lines = ["agent: %s" % self.agent]
        for k in sorted(self.kv):
            lines.append("%s=%s" % (k, self.kv[k]))
        lines.append("todos open=[%s] done=[%s]" % (", ".join(self.open_todos), ", ".join(self.done_todos)))
        if self.notes:
            lines.append("notes: " + " | ".join(self.notes[-3:]))
        return "\n".join(lines)

    def pack(self, keep_notes: int = 3, compact: bool = False) -> dict:
        """Forward the attention-heavy context, drop the rest, rewrite in shorthand.

        Kept (context-reliant): all anchor facts + still-open todos + the most recent notes.
        Dropped: cleared (done) todos and stale notes. Deterministic -- the script decides, not a
        model. If compact=True the dropped items are removed from the ledger in place.
        """
        kept_notes = self.notes[-keep_notes:] if keep_notes else []
        dropped = list(self.done_todos) + self.notes[: -keep_notes if keep_notes else None]
        long_parts = ["%s=%s" % (k, v) for k, v in self.kv.items()] + ["+%s" % t for t in self.open_todos] + kept_notes
        long_form = " ".join(long_parts)
        short = shorten(long_form)
        if compact:
            self.done_todos = []
            self.notes = kept_notes
        return {
            "kept": {"kv": dict(self.kv), "open_todos": list(self.open_todos), "notes": kept_notes},
            "dropped": dropped,
            "long": long_form,
            "shorthand": short,
            "chars_before": len(long_form),
            "chars_after": len(short),
            "ratio": round(len(short) / max(1, len(long_form)), 2),
        }

    def verify(self) -> bool:
        """The event log is tamper-evident: every command's seal still matches."""
        return all(e.get("seal") == _seal({k: v for k, v in e.items() if k != "seal"}) for e in self.events)

    # --- persistence: the durable scratch the AI re-reads next session ---------
    def to_json(self) -> str:
        return json.dumps(
            {
                "agent": self.agent,
                "kv": self.kv,
                "open_todos": self.open_todos,
                "done_todos": self.done_todos,
                "notes": self.notes,
                "events": self.events,
            },
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, text: str) -> "Ledger":
        d = json.loads(text)
        return cls(
            agent=d.get("agent", "agent"),
            kv=d.get("kv", {}),
            open_todos=d.get("open_todos", []),
            done_todos=d.get("done_todos", []),
            notes=d.get("notes", []),
            events=d.get("events", []),
        )

    def save(self, path: str) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "Ledger":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


def main(argv: Optional[list] = None) -> int:
    led = Ledger("demo-agent")
    print("CONTEXT LEDGER  the AI keeps + packs its own context by running commands\n")
    for cmd in ["set goal sum-loop", "todo write loop", "todo verify", "done write loop", "note loop emits 15"]:
        r = led.run(cmd)
        print("  $ %-22s -> %s" % (cmd, r["result"].replace("\n", " | ")))
    p = led.pack()
    print("\n  pack: drop %d cleared/stale; rewrite in shorthand" % len(p["dropped"]))
    print("    long (%d ch): %s" % (p["chars_before"], p["long"]))
    print("    short (%d ch): %s   ratio=%s" % (p["chars_after"], p["shorthand"], p["ratio"]))
    print("    expand back: %s" % expand(p["shorthand"]))
    print("\n  event log sealed + tamper-evident:", led.verify())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
