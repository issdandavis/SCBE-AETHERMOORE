"""Synapses -- a governed MCP routing library over the Crystal Cranium connectome.

Grounded in "PHDM as AI Brain Architecture (Crystal Cranium)": the connectome's neural
bridges are SYNAPSES, the Six Sacred Tongues are the synapse WEIGHTS (an escalation
signal -- KO 1.0 -> DR 11.09), and a valid THOUGHT is a path along existing synapses (a
jump with no edge is an "orthogonal excursion" and is blocked). Each synapse firing is
GOVERNED by the gate and emits a sealed RECEIPT, so a multi-hop route across regions is a
fully governed, tamper-evident "thought".

The flagship motif is the MCP TRIANGLE for support model calls -- three regions
(guard / worker / support) wired by three synapses -- so a primary model call is governed,
worked, and (when it needs help) supported, with a receipt per hop. Synapses route BETWEEN
regions; the Governed MCP Room (rooms.py) routes WITHIN a region to niche tools.

    from scbe_aethermoore.synapses import build_support_triangle, support_call
    tri = build_support_triangle()
    out = support_call(tri, "Plan and redact the PII before sending this customer email ...")
    [h["target"] for h in out["path"]]   # -> ['guard', 'worker', 'support']
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from scbe_aethermoore import scan  # governance gate

# Sacred Tongue weights = synapse weights (escalation signal; higher = more scrutiny).
TONGUES: Dict[str, float] = {"KO": 1.00, "AV": 1.62, "RU": 2.62, "CA": 4.24, "UM": 6.85, "DR": 11.09}
TONGUE_ROLE: Dict[str, str] = {
    "KO": "intent/proceed",
    "AV": "attention/context",
    "RU": "memory",
    "CA": "execution",
    "UM": "suppression/redact",
    "DR": "lock/seal/authority",
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _seal(rec: dict) -> str:
    body = {k: v for k, v in rec.items() if k != "seal"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


@dataclass
class Region:
    """A cognitive node -- a tool or model-call surface the connectome can route to.

    r is the radial position in the Poincare skull (0 = stable core, ->1 = the Wall);
    ring names the anatomical layer (core / cortex / bridge / cerebellum / risk).
    """

    name: str
    role: str
    handler: Callable[[str], str]
    r: float = 0.0
    ring: str = ""


@dataclass
class Synapse:
    """A typed, tongue-weighted route between two regions."""

    source: str
    target: str
    tongue: str

    @property
    def weight(self) -> float:
        return TONGUES[self.tongue]


@dataclass
class Connectome:
    """A graph of regions + synapses. fire() governs, runs the target, and receipts the hop."""

    regions: Dict[str, Region] = field(default_factory=dict)
    synapses: List[Synapse] = field(default_factory=list)
    transcript: List[dict] = field(default_factory=list)
    block_tiers: tuple = ("ESCALATE", "DENY")

    def add_region(self, region: Region) -> None:
        self.regions[region.name] = region

    def add_synapse(self, synapse: Synapse) -> None:
        self.synapses.append(synapse)

    def edge(self, source: str, target: str) -> Optional[Synapse]:
        return next((s for s in self.synapses if s.source == source and s.target == target), None)

    def fire(self, source: str, target: str, message: str, actor: str = "agent") -> dict:
        hop = len(self.transcript) + 1
        syn = self.edge(source, target)
        g = scan(message)
        gov = {"decision": g["decision"], "score": g["score"], "intent_flags": g["intent_flags"]}
        rec = {
            "hop": hop,
            "source": source,
            "target": target,
            "synapse": (
                None if syn is None else {"tongue": syn.tongue, "weight": syn.weight, "role": TONGUE_ROLE[syn.tongue]}
            ),
            "message_sha256": _sha(message),
            "governance": gov,
            "status": "",
            "result": "",
            "result_sha256": None,
        }
        if syn is None:
            rec["status"] = "NO_SYNAPSE"  # orthogonal excursion: no edge connects these regions
            rec["result"] = f"No synapse {source}->{target}; orthogonal excursion blocked."
        elif g["decision"] in self.block_tiers:
            rec["status"] = "REFUSED"
            rec["result"] = f"Refused at synapse {source}->{target} by gate ({g['decision']}, {gov['intent_flags']})."
        elif target not in self.regions:
            rec["status"] = "NO_REGION"
            rec["result"] = f"No region '{target}'."
        else:
            out = self.regions[target].handler(message)
            rec["status"] = "FIRED"
            rec["result"] = out
            rec["result_sha256"] = _sha(out)
        rec["seal"] = _seal(rec)
        self.transcript.append(rec)
        return rec

    def verify(self) -> bool:
        return all(r.get("seal") == _seal(r) for r in self.transcript)


# ── The MCP triangle for governed support model calls ─────────────────────────
def _guard_handler(message: str) -> str:
    return f"governance cleared: {scan(message)['decision']}"


def _default_worker(message: str) -> str:
    # Worker delegates the niche aspect to a Governed MCP Room (within-region routing).
    from scbe_aethermoore.rooms import build_security_room

    r = build_security_room().ask(message)
    return f"worker via room[{r['routed_tool'] or '-'}]: {r['result']}"


def _default_support(message: str) -> str:
    return f"support attached (context + second-opinion governance={scan(message)['decision']})"


def build_support_triangle(
    worker: Optional[Callable[[str], str]] = None,
    support: Optional[Callable[[str], str]] = None,
) -> Connectome:
    """guard / worker / support wired into a triangle for governed support model calls."""
    c = Connectome()
    c.add_region(Region("guard", "governance check + final seal", _guard_handler))
    c.add_region(Region("worker", "primary model call (routes to niche tools)", worker or _default_worker))
    c.add_region(Region("support", "supporting context / second opinion", support or _default_support))
    # triangle: enter at guard, work, support, close back at guard
    c.add_synapse(Synapse("entry", "guard", "DR"))  # govern first (lock/seal authority)
    c.add_synapse(Synapse("guard", "worker", "KO"))  # proceed to the primary call (intent)
    c.add_synapse(Synapse("worker", "support", "AV"))  # pull supporting context (attention)
    c.add_synapse(Synapse("support", "guard", "DR"))  # close the loop: re-seal at guard
    return c


def support_call(c: Connectome, message: str, need_support: Optional[Callable[[str], bool]] = None) -> dict:
    """Run a governed support model call through the triangle: govern -> work -> (support) -> seal."""
    guard = c.fire("entry", "guard", message)
    if guard["status"] != "FIRED":
        return {"status": guard["status"], "result": guard["result"], "path": [guard]}
    work = c.fire("guard", "worker", message)
    path = [guard, work]
    wants = need_support(message) if need_support else len(message) > 60
    if wants:
        path.append(c.fire("worker", "support", message))
        path.append(c.fire("support", "guard", message))  # close the triangle, re-seal
    return {
        "status": "COMPLETED",
        "result": path[-1]["result"],
        "path": path,
        "route": " -> ".join(h["target"] for h in path),
        "sealed": c.verify(),
    }
