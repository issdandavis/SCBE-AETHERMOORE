"""Governed MCP Room engine: GOVERN -> ROUTE -> RECEIPT -> shared transcript.

A Room is a topic-scoped surface. Each inbound message is screened by the SCBE governance
gate, routed to the best-matching NICHE tool, and turned into a sealed RECEIPT appended to
a shared transcript. Attacks are refused at the gate before any tool runs. This is the pure
engine; scripts/mcp_rooms/server.py exposes a Room as a real MCP server.

    from scbe_aethermoore.rooms import build_security_room
    room = build_security_room()
    receipt = room.ask("Please redact the PII in: reach me at jo@acme.io or 10.0.0.5")
    receipt["routed_tool"]  # -> "pii_redact"
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

from scbe_aethermoore import scan  # governance gate


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _seal(receipt: dict) -> str:
    body = {k: v for k, v in receipt.items() if k != "seal"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


@dataclass
class NicheTool:
    """A specialist sub-tool the room routes to for one aspect of the topic."""

    name: str
    description: str
    keywords: Tuple[str, ...]
    handler: Callable[[str], str]

    def score(self, message: str) -> int:
        low = message.lower()
        return sum(1 for k in self.keywords if k in low)


@dataclass
class Room:
    """A topic-scoped, governed MCP room. ask() governs, routes, and receipts every hop."""

    topic: str
    tools: List[NicheTool] = field(default_factory=list)
    transcript: List[dict] = field(default_factory=list)
    block_tiers: Tuple[str, ...] = ("ESCALATE", "DENY")  # refuse routing on these decisions

    def register(self, tool: NicheTool) -> None:
        self.tools.append(tool)

    def route(self, message: str) -> Optional[NicheTool]:
        ranked = sorted(self.tools, key=lambda t: t.score(message), reverse=True)
        best = ranked[0] if ranked else None
        return best if best and best.score(message) > 0 else None

    def ask(self, message: str, actor: str = "agent") -> dict:
        turn = len(self.transcript) + 1
        g = scan(message)
        gov = {"decision": g["decision"], "score": g["score"], "intent_flags": g["intent_flags"]}
        receipt = {
            "turn": turn,
            "topic": self.topic,
            "actor": actor,
            "message_sha256": _sha(message),
            "governance": gov,
            "routed_tool": None,
            "status": "",
            "result": "",
            "result_sha256": None,
        }
        if g["decision"] in self.block_tiers:
            receipt["status"] = "REFUSED"
            receipt["result"] = f"Refused by governance gate (decision={g['decision']}, flags={gov['intent_flags']})."
        else:
            tool = self.route(message)
            if tool is None:
                receipt["status"] = "NO_SPECIALIST"
                receipt["result"] = f"No niche tool in room '{self.topic}' matched this request."
            else:
                result = tool.handler(message)
                receipt["routed_tool"] = tool.name
                receipt["status"] = "ANSWERED"
                receipt["result"] = result
                receipt["result_sha256"] = _sha(result)
        receipt["seal"] = _seal(receipt)
        self.transcript.append(receipt)
        return receipt

    def verify(self) -> bool:
        """True iff every receipt in the transcript still matches its seal (tamper check)."""
        return all(r.get("seal") == _seal(r) for r in self.transcript)


# ── A concrete demo room: "security-ops" with three distinct niche tools ──────
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_SECRET = re.compile(r"\b(?:sk-|AKIA|ghp_|xoxb-)[A-Za-z0-9_-]{8,}\b")
_TIERS = {
    "ALLOW": "safe -- proceed",
    "QUARANTINE": "suspicious -- flag for review",
    "ESCALATE": "high risk -- requires governance action",
    "DENY": "adversarial -- blocked",
}


def _pii_redact(message: str) -> str:
    red, n = message, 0
    for rx, tag in ((_EMAIL, "[EMAIL]"), (_IPV4, "[IP]"), (_SECRET, "[SECRET]")):
        red, k = rx.subn(tag, red)
        n += k
    return f"redacted {n} item(s): {red}"


def _digest(message: str) -> str:
    return f"sha256={_sha(message)} length={len(message)}"


def _policy_explain(message: str) -> str:
    low = message.lower()
    hits = [f"{t} = {d}" for t, d in _TIERS.items() if t.lower() in low]
    if hits:
        return "; ".join(hits)
    return "SCBE decision tiers: ALLOW>=0.75 | QUARANTINE>=0.45 | ESCALATE>=0.20 | DENY<0.20."


# ── MCP-to-MCP forwarding: route a governed sub-aspect to an EXTERNAL MCP sub-server ──────────
# The room's gate runs in Room.ask BEFORE any handler, so an ESCALATE/DENY message is refused and
# never reaches the sub-server. This closes the one gap between the in-process room and a real
# multi-tool MCP control plane: now a niche tool can be another MCP server, still gated + receipted.


def forward_to_mcp(
    command: str,
    args: Sequence[str],
    remote_tool: str,
    message: str,
    arg_name: str = "message",
    timeout: float = 15.0,
) -> str:
    """Open a stdio MCP client to an external sub-server, call ONE remote tool, return its text. A sync
    wrapper over the async SDK (lazy import, so the engine has no hard MCP dependency). Raises on any
    failure -- the caller's handler turns that into a receipted error so a broken sub-server never crashes
    the room."""
    import asyncio

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def _call() -> str:
        params = StdioServerParameters(command=command, args=list(args))
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                res = await session.call_tool(remote_tool, {arg_name: message})
                parts = [getattr(c, "text", "") for c in getattr(res, "content", [])]
                return "".join(p for p in parts if p)

    return asyncio.run(asyncio.wait_for(_call(), timeout))


def mcp_niche_tool(
    name: str,
    description: str,
    keywords: Sequence[str],
    command: str,
    args: Sequence[str] = (),
    remote_tool: str = "echo",
    arg_name: str = "message",
    timeout: float = 15.0,
) -> NicheTool:
    """A NicheTool that FORWARDS a routed sub-aspect to an external MCP sub-server. Because Room.ask gates
    before calling any handler, an ESCALATE/DENY message is refused and this forward never fires -- the
    sub-server is unreachable to an attacker. A forwarding error is returned as receipted text, not raised."""

    def handler(message: str) -> str:
        try:
            out = forward_to_mcp(command, args, remote_tool, message, arg_name=arg_name, timeout=timeout)
            return out or "(empty result from %s)" % remote_tool
        except Exception as exc:  # a broken/absent sub-server is a receipted error, never a room crash
            return "MCP forward to %r failed: %s: %s" % (remote_tool, type(exc).__name__, exc)

    return NicheTool(name, description, tuple(keywords), handler)


def build_security_room() -> Room:
    room = Room(topic="security-ops")
    room.register(
        NicheTool(
            "pii_redact",
            "Mask emails, IPs, and secret tokens in text.",
            ("redact", "pii", "mask", "anonymize", "scrub", "sensitive", "personal data"),
            _pii_redact,
        )
    )
    room.register(
        NicheTool(
            "digest",
            "Compute a SHA-256 fingerprint + length of text.",
            ("hash", "digest", "fingerprint", "sha", "sha256", "checksum"),
            _digest,
        )
    )
    room.register(
        NicheTool(
            "policy_explain",
            "Explain SCBE governance decision tiers.",
            ("policy", "tier", "decision", "allow", "quarantine", "escalate", "deny", "explain", "what does"),
            _policy_explain,
        )
    )
    return room
