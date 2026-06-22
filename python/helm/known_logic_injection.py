"""known_logic_injection -- deterministic answer/process injection for code agents.

This is the "parrot" lane: when the system already knows the answer or the
process, do not ask the model to rediscover it. Put the known logic in context,
ask the model to echo/apply it, verify the echo, and fall back to the
deterministic source if the model fumbles.

The model is allowed to be useful formatting glue. It is not the authority.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

MODEL_ECHO_VERIFIED = "model_echo_verified"
DETERMINISTIC_FALLBACK = "deterministic_fallback"


@dataclass(frozen=True)
class KnownLogicPacket:
    """A compact, auditable packet of answer-bearing logic.

    `answer` is the known output. `process` is the deterministic route used to get
    it. A model can repeat or apply this packet, but the packet remains the
    authority if verification fails.
    """

    packet_id: str
    task: str
    answer: str
    process: str
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_prompt(self) -> str:
        return render_injection_prompt(self)


def _normalize(value: str) -> str:
    return " ".join(str(value).strip().split())


def exact_echo(candidate: str, packet: KnownLogicPacket) -> bool:
    """Default verifier: model must return the known answer exactly after whitespace normalization."""

    return _normalize(candidate) == _normalize(packet.answer)


def inject_or_fallback(
    packet: KnownLogicPacket,
    model_output: Optional[str],
    verifier: Optional[Callable[[str, KnownLogicPacket], bool]] = None,
) -> Dict[str, Any]:
    """Accept a model echo only if verified; otherwise use the deterministic packet answer.

    This gives a hard floor for known-answer tasks:

    * model repeats/applies the packet correctly -> use the verified model output
    * model misses, drifts, or refuses -> use the deterministic answer directly

    The function always closes the task without false success because an
    unverified model output is never shipped as the answer.
    """

    check = verifier or exact_echo
    output = "" if model_output is None else str(model_output)
    accepted = bool(output and check(output, packet))
    status = MODEL_ECHO_VERIFIED if accepted else DETERMINISTIC_FALLBACK
    return {
        "status": status,
        "packet_id": packet.packet_id,
        "source": packet.source,
        "model_output_accepted": accepted,
        "model_output": output,
        "answer": output if accepted else packet.answer,
        "deterministic_answer": packet.answer,
        "process": packet.process,
        "closed": True,
        "false_success_count": 0,
    }


def render_injection_prompt(packet: KnownLogicPacket) -> str:
    """Render a minimal prompt where known logic, not model reasoning, is the payload."""

    return (
        "You are not solving this from scratch.\n"
        "Use the KNOWN LOGIC PACKET exactly.\n\n"
        "TASK:\n%s\n\n"
        "KNOWN PROCESS:\n%s\n\n"
        "KNOWN ANSWER:\n%s\n\n"
        "Return only the known answer. Do not re-derive it." % (packet.task, packet.process, packet.answer)
    )


def sieve_primes(limit: int) -> List[int]:
    """Return all primes <= limit using a deterministic sieve."""

    if limit < 2:
        return []
    flags = [True] * (limit + 1)
    flags[0] = False
    flags[1] = False
    p = 2
    while p * p <= limit:
        if flags[p]:
            for multiple in range(p * p, limit + 1, p):
                flags[multiple] = False
        p += 1
    return [i for i, ok in enumerate(flags) if ok]


def prime_membership_packet(n: int) -> KnownLogicPacket:
    """Build a packet that answers whether n is prime by running the sieve."""

    primes = sieve_primes(n)
    is_prime = n in set(primes)
    return KnownLogicPacket(
        packet_id="prime_membership:%d" % n,
        task="Decide whether %d is prime." % n,
        answer="prime" if is_prime else "composite",
        process="Run sieve_primes(%d); answer prime iff %d appears in the returned list." % (n, n),
        source="tool:sieve_primes",
        metadata={"n": n, "prime_count_to_n": len(primes)},
    )


def sieve_packet(limit: int) -> KnownLogicPacket:
    primes = sieve_primes(limit)
    return KnownLogicPacket(
        packet_id="sieve_primes:%d" % limit,
        task="List all primes up to %d." % limit,
        answer=json.dumps(primes, separators=(",", ":")),
        process="Run the deterministic Sieve of Eratosthenes up to %d." % limit,
        source="tool:sieve_primes",
        metadata={"limit": limit, "count": len(primes)},
    )


def chart_lookup_packet(chart: Mapping[str, Any], key: str, *, packet_id: Optional[str] = None) -> KnownLogicPacket:
    if key not in chart:
        raise KeyError("chart has no key %r" % key)
    answer = chart[key]
    return KnownLogicPacket(
        packet_id=packet_id or "chart_lookup:%s" % key,
        task="Look up %r in the provided chart." % key,
        answer=json.dumps(answer, sort_keys=True) if isinstance(answer, (dict, list)) else str(answer),
        process="Read chart[%r] exactly; do not infer from surrounding keys." % key,
        source="tool:chart_lookup",
        metadata={"key": key},
    )


def if_then_packet(condition: bool, when_true: str, when_false: str, *, label: str = "condition") -> KnownLogicPacket:
    answer = when_true if condition else when_false
    return KnownLogicPacket(
        packet_id="if_then:%s:%s" % (label, int(condition)),
        task="Apply the if/then rule for %s." % label,
        answer=answer,
        process="If %s is true return %r; otherwise return %r. The observed condition is %s."
        % (label, when_true, when_false, condition),
        source="tool:if_then",
        metadata={"condition": condition, "label": label},
    )


def run_known_tool(name: str, payload: Mapping[str, Any]) -> KnownLogicPacket:
    """Small deterministic tool registry for nested command pipelines."""

    if name == "prime_membership":
        return prime_membership_packet(int(payload["n"]))
    if name == "sieve_primes":
        return sieve_packet(int(payload["limit"]))
    if name == "chart_lookup":
        return chart_lookup_packet(payload["chart"], str(payload["key"]))
    if name == "if_then":
        return if_then_packet(
            bool(payload["condition"]),
            str(payload["when_true"]),
            str(payload["when_false"]),
            label=str(payload.get("label") or "condition"),
        )
    raise ValueError("unknown known-logic tool: %s" % name)


def _demo() -> Dict[str, Any]:
    packet = run_known_tool("prime_membership", {"n": 97})
    good = inject_or_fallback(packet, "prime")
    bad = inject_or_fallback(packet, "composite")
    return {
        "packet": asdict(packet),
        "prompt": packet.to_prompt(),
        "model_repeats": good,
        "model_fumbles": bad,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="known-logic-injection",
        description="inject deterministic answer/process packets and fall back when the model fails to echo them",
    )
    ap.add_argument("--demo", action="store_true", help="print the built-in prime-membership demo")
    args = ap.parse_args(list(argv) if argv is not None else None)
    if not args.demo:
        print("Use --demo, or import run_known_tool() and inject_or_fallback().")
        return 0
    print(json.dumps(_demo(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
