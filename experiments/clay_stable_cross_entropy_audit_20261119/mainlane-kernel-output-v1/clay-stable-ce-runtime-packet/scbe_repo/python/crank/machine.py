"""Crank — turn long AI work into a visible workflow machine.

Intent in -> controlled, checkpointed steps -> a cataloged result with receipts.

The discipline is borrowed from a mechanical calculator: a result is only real
when every step has settled into a constrained, receipted state — no half-turned
gears, no in-between. Each phase produces an output that is gated, hashed into a
**tamper-evident receipt chain**, and checked for the three failure modes a real
workflow actually has:

    drift     : a phase produced nothing (missing output, or it raised)
    blocked   : the gate refused a phase's (non-empty) output
    collision : a phase produced output identical to an earlier phase (no progress)

The catalog — the ordered receipts plus the final chain digest — is the proof the
work happened and in what state: the AI-workflow analog of the accumulator reading.

Executors are injected, so the machine itself is deterministic and testable; the
actual research/build/review work plugs in as phase functions (an AI call, a loom
build+verify, a real policy gate, ...).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

# A phase does the work: (intent, context) -> output. context["outputs"] holds
# the accepted outputs of earlier phases, keyed by phase name.
PhaseFn = Callable[[str, Dict[str, Any]], Any]
# A gate judges an output: (phase_name, output) -> GateVerdict.
GateFn = Callable[[str, Any], "GateVerdict"]


def _digest(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


@dataclass
class GateVerdict:
    allow: bool
    reason: str = ""


def default_gate(phase: str, output: Any) -> GateVerdict:
    """Minimal gate — accepts any non-empty output. Swap in a real policy (e.g. scbe score)."""
    return GateVerdict(True) if not _is_empty(output) else GateVerdict(False, "empty output")


@dataclass
class Phase:
    name: str
    run: PhaseFn


@dataclass
class Receipt:
    phase: str
    status: str  # ok | drift | blocked | collision
    input_digest: str
    output_digest: Optional[str]
    chain_digest: str
    output: Any = None
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "status": self.status,
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
            "chain_digest": self.chain_digest,
            "note": self.note,
        }


@dataclass
class Catalog:
    intent: str
    receipts: List[Receipt]
    result: Any
    chain_digest: str
    ok: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "ok": self.ok,
            "chain_digest": self.chain_digest,
            "result": self.result,
            "receipts": [r.to_dict() for r in self.receipts],
        }


def turn(intent: str, phases: List[Phase], gate: GateFn = default_gate, stop_on_fail: bool = True) -> Catalog:
    """Turn the crank: run phases in order, settling each into a receipt in a chain.

    A phase's output is accepted only if it is non-empty (else *drift*), passes the
    gate (else *blocked*), and differs from every earlier accepted output (else
    *collision*). Each receipt folds the previous chain digest, so any change to any
    phase's output or status changes the final ``chain_digest`` — the catalog is
    tamper-evident proof of exactly what happened.
    """
    context: Dict[str, Any] = {"intent": intent, "outputs": {}}
    receipts: List[Receipt] = []
    chain = _digest(["crank.v1", intent])
    first_seen: Dict[str, str] = {}  # output_digest -> phase that first produced it
    result: Any = None
    ok = True

    for phase in phases:
        in_digest = _digest({"intent": intent, "prior": context["outputs"]})
        status, note, out, out_digest = "ok", "", None, None

        try:
            out = phase.run(intent, context)
        except Exception as exc:  # a phase that raises is drift — the machine does not crash
            status, note = "drift", f"phase raised {exc.__class__.__name__}: {exc}"

        if status == "ok" and _is_empty(out):
            status, note = "drift", "no output"
        if status == "ok":
            verdict = gate(phase.name, out)
            if not verdict.allow:
                status, note = "blocked", verdict.reason or "gate refused"
        if status == "ok":
            out_digest = _digest(out)
            if out_digest in first_seen:
                status, note = "collision", f"identical output to phase '{first_seen[out_digest]}'"
            else:
                first_seen[out_digest] = phase.name
                context["outputs"][phase.name] = out
                result = out

        chain = _digest([chain, phase.name, status, out_digest])
        receipts.append(
            Receipt(
                phase=phase.name,
                status=status,
                input_digest=in_digest,
                output_digest=out_digest,
                chain_digest=chain,
                output=out if status == "ok" else None,
                note=note,
            )
        )
        if status != "ok":
            ok = False
            if stop_on_fail:
                break

    return Catalog(intent=intent, receipts=receipts, result=result, chain_digest=chain, ok=ok)


def render(catalog: Catalog) -> str:
    """A compact, human/agent-readable view of the run state (the 'visible' part)."""
    glyph = {"ok": "✓", "drift": "∅", "blocked": "⛔", "collision": "⟳"}
    lines = [f"crank · intent: {catalog.intent!r} · {'OK' if catalog.ok else 'FAILED'} · chain {catalog.chain_digest}"]
    for r in catalog.receipts:
        mark = glyph.get(r.status, "?")
        detail = f"  [{r.note}]" if r.note else ""
        lines.append(f"  {mark} {r.phase}: {r.status} (out {r.output_digest or '—'}){detail}")
    return "\n".join(lines)
