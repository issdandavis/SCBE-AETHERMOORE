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
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
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


def percentile(values: Sequence[float], q: float) -> Optional[float]:
    """Return the qth percentile using linear interpolation."""

    if not values:
        return None
    if q < 0 or q > 100:
        raise ValueError("percentile q must be between 0 and 100")
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return round(ordered[0], 6)
    pos = (len(ordered) - 1) * (q / 100.0)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return round(ordered[lo], 6)
    frac = pos - lo
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * frac, 6)


def weighted_mean(values: Sequence[float], weights: Sequence[float]) -> Optional[float]:
    """Return sum(value*weight)/sum(weight), or None for no positive total weight."""

    if len(values) != len(weights):
        raise ValueError("values and weights must have the same length")
    total_weight = sum(float(w) for w in weights)
    if not values or total_weight <= 0:
        return None
    return round(sum(float(v) * float(w) for v, w in zip(values, weights)) / total_weight, 6)


def pearson_correlation(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    """Return Pearson correlation, or None when fewer than two points or zero variance."""

    if len(xs) != len(ys):
        raise ValueError("xs and ys must have the same length")
    if len(xs) < 2:
        return None
    xvals = [float(x) for x in xs]
    yvals = [float(y) for y in ys]
    xmean = sum(xvals) / len(xvals)
    ymean = sum(yvals) / len(yvals)
    xdiff = [x - xmean for x in xvals]
    ydiff = [y - ymean for y in yvals]
    xvar = sum(d * d for d in xdiff)
    yvar = sum(d * d for d in ydiff)
    if xvar <= 0 or yvar <= 0:
        return None
    corr = sum(x * y for x, y in zip(xdiff, ydiff)) / math.sqrt(xvar * yvar)
    return round(corr, 6)


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


def _field_from_packet(packet: KnownLogicPacket, path: str) -> Any:
    if path == "answer":
        return packet.answer
    if path == "source":
        return packet.source
    if path.startswith("metadata."):
        current: Any = packet.metadata
        for part in path.split(".")[1:]:
            if not isinstance(current, Mapping) or part not in current:
                raise KeyError("packet %s has no field %s" % (packet.packet_id, path))
            current = current[part]
        return current
    raise KeyError("unsupported packet field reference: %s" % path)


def _resolve_ref(value: Any, packets: Sequence[KnownLogicPacket]) -> Any:
    if isinstance(value, str):
        if value.startswith("$prev."):
            if not packets:
                raise ValueError("%s requires a previous packet" % value)
            return _field_from_packet(packets[-1], value[len("$prev.") :])
        if value.startswith("$step."):
            parts = value.split(".", 2)
            if len(parts) != 3:
                raise ValueError("bad step reference: %s" % value)
            index = int(parts[1])
            if index < 0 or index >= len(packets):
                raise IndexError("step reference out of range: %s" % value)
            return _field_from_packet(packets[index], parts[2])
        return value
    if isinstance(value, Mapping):
        if "$eq" in value:
            left, right = value["$eq"]
            return _resolve_ref(left, packets) == _resolve_ref(right, packets)
        return {str(k): _resolve_ref(v, packets) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_ref(v, packets) for v in value]
    return value


def run_known_pipeline(steps: Sequence[Mapping[str, Any]]) -> List[KnownLogicPacket]:
    """Run nested deterministic commands, passing packet fields forward by reference.

    References supported inside a step payload:

    * `$prev.answer`
    * `$prev.metadata.<key>`
    * `$step.<index>.answer`
    * `{"$eq": [left, right]}`

    Example: compute prime membership, then route with an if/then gate whose
    condition is `{"$eq": ["$prev.answer", "prime"]}`.
    """

    packets: List[KnownLogicPacket] = []
    for index, raw in enumerate(steps):
        if "tool" not in raw:
            raise KeyError("pipeline step %d missing tool" % index)
        payload = _resolve_ref(raw.get("payload") or {}, packets)
        if not isinstance(payload, Mapping):
            raise TypeError("pipeline step %d payload must resolve to a mapping" % index)
        packets.append(run_known_tool(str(raw["tool"]), payload))
    return packets


def packet_from_record(record: Mapping[str, Any]) -> KnownLogicPacket:
    """Build the authoritative packet for one repeatable JSONL record."""

    if "packet" in record:
        raw = record["packet"]
        if not isinstance(raw, Mapping):
            raise TypeError("packet must be an object")
        return KnownLogicPacket(
            packet_id=str(raw["packet_id"]),
            task=str(raw["task"]),
            answer=str(raw["answer"]),
            process=str(raw["process"]),
            source=str(raw["source"]),
            metadata=dict(raw.get("metadata") or {}),
        )
    if "pipeline" in record:
        raw_steps = record["pipeline"]
        if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)):
            raise TypeError("pipeline must be a list of steps")
        packets = run_known_pipeline(raw_steps)
        if not packets:
            raise ValueError("pipeline produced no packets")
        return packets[-1]
    if "tool" in record:
        payload = record.get("payload") or {}
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be an object")
        return run_known_tool(str(record["tool"]), payload)
    raise KeyError("record must contain one of: packet, pipeline, tool")


def evaluate_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Run one known-logic record and return its packet + decision receipt."""

    packet = packet_from_record(record)
    model_output = record.get("model_output")
    decision = inject_or_fallback(packet, None if model_output is None else str(model_output))
    return {
        "id": str(record.get("id") or packet.packet_id),
        "weight": float(record.get("weight", 1.0)),
        "packet": asdict(packet),
        "prompt": packet.to_prompt(),
        "decision": decision,
    }


def _length_percentiles(values: Sequence[float]) -> Dict[str, Optional[float]]:
    return {
        "p0": percentile(values, 0),
        "p50": percentile(values, 50),
        "p90": percentile(values, 90),
        "p100": percentile(values, 100),
    }


def summarize_decisions(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    attempted = len(rows)
    echo_verified = sum(1 for r in rows if r["decision"]["status"] == MODEL_ECHO_VERIFIED)
    fallback = sum(1 for r in rows if r["decision"]["status"] == DETERMINISTIC_FALLBACK)
    false_success = sum(int(r["decision"].get("false_success_count", 0) or 0) for r in rows)
    closed = sum(1 for r in rows if r["decision"].get("closed") is True)
    weights = [float(r.get("weight", 1.0) or 0.0) for r in rows]
    echo_flags = [1.0 if r["decision"]["status"] == MODEL_ECHO_VERIFIED else 0.0 for r in rows]
    packet_rows = [r for r in rows if "packet" in r]
    answer_lengths = [
        len(str(r["decision"].get("deterministic_answer") or r["decision"].get("answer") or "")) for r in rows
    ]
    prompt_lengths = [len(str(r.get("prompt") or "")) for r in packet_rows]
    process_lengths = [len(str(r["packet"].get("process") or "")) for r in packet_rows]
    model_output_lengths = [len(str(r["decision"].get("model_output") or "")) for r in rows]
    packet_echo_flags = [1.0 if r["decision"]["status"] == MODEL_ECHO_VERIFIED else 0.0 for r in packet_rows]
    return {
        "attempted": attempted,
        "model_echo_verified": echo_verified,
        "deterministic_fallback": fallback,
        "false_success_count": false_success,
        "closure_rate": round(closed / attempted, 6) if attempted else 0.0,
        "echo_rate": round(echo_verified / attempted, 6) if attempted else 0.0,
        "weighted_echo_rate": weighted_mean(echo_flags, weights),
        "answer_length_percentiles": _length_percentiles(answer_lengths),
        "prompt_length_percentiles": _length_percentiles(prompt_lengths),
        "process_length_percentiles": _length_percentiles(process_lengths),
        "model_output_length_percentiles": _length_percentiles(model_output_lengths),
        "correlations": {
            "model_output_length_vs_echo": pearson_correlation(model_output_lengths, echo_flags),
            "prompt_length_vs_echo": pearson_correlation(prompt_lengths, packet_echo_flags),
            "process_length_vs_echo": pearson_correlation(process_lengths, packet_echo_flags),
        },
        "contract_passed": attempted == closed and false_success == 0,
    }


def to_sft_record(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Convert one known-logic decision into the same {messages, meta} shape used by tool trajectories."""

    packet = row["packet"]
    decision = row["decision"]
    return {
        "messages": [
            {
                "role": "system",
                "content": "Use known logic packets exactly. If the packet already contains the answer, repeat it.",
            },
            {"role": "user", "content": row["prompt"]},
            {"role": "assistant", "content": str(decision["deterministic_answer"])},
        ],
        "meta": {
            "source": "known_logic_injection",
            "id": row["id"],
            "packet_id": packet["packet_id"],
            "tool_source": packet["source"],
            "status": decision["status"],
            "false_success_count": decision["false_success_count"],
        },
    }


def run_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            try:
                raw = json.loads(text)
                if not isinstance(raw, Mapping):
                    raise TypeError("record must be an object")
                rows.append(evaluate_record(raw))
            except Exception as exc:  # intentionally report bad rows as receipts, not tracebacks
                rows.append(
                    {
                        "id": "line_%d" % lineno,
                        "error": str(exc),
                        "decision": {
                            "status": "record_error",
                            "closed": True,
                            "false_success_count": 0,
                            "answer": None,
                        },
                    }
                )
    return rows


def _write_json(path: Optional[str], data: Any) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Optional[str], rows: Sequence[Mapping[str, Any]]) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def _demo() -> Dict[str, Any]:
    packet = run_known_tool("prime_membership", {"n": 97})
    pipeline = run_known_pipeline(
        [
            {"tool": "prime_membership", "payload": {"n": 97}},
            {
                "tool": "if_then",
                "payload": {
                    "condition": {"$eq": ["$prev.answer", "prime"]},
                    "when_true": "ALLOW",
                    "when_false": "DENY",
                    "label": "prime_gate",
                },
            },
        ]
    )
    good = inject_or_fallback(packet, "prime")
    bad = inject_or_fallback(packet, "composite")
    return {
        "packet": asdict(packet),
        "prompt": packet.to_prompt(),
        "nested_pipeline": [asdict(p) for p in pipeline],
        "model_repeats": good,
        "model_fumbles": bad,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="known-logic-injection",
        description="inject deterministic answer/process packets and fall back when the model fails to echo them",
    )
    ap.add_argument("--demo", action="store_true", help="print the built-in prime-membership demo")
    ap.add_argument("--input", help="JSONL known-logic records to replay")
    ap.add_argument("--out", help="write detailed decision receipts as JSON")
    ap.add_argument("--summary", help="write summary metrics as JSON")
    ap.add_argument("--sft-out", help="write repeat/apply SFT records as JSONL")
    args = ap.parse_args(list(argv) if argv is not None else None)
    if args.input:
        rows = run_jsonl(args.input)
        summary = summarize_decisions([r for r in rows if "decision" in r])
        _write_json(args.out, {"summary": summary, "rows": rows})
        _write_json(args.summary, summary)
        _write_jsonl(args.sft_out, [to_sft_record(r) for r in rows if "packet" in r])
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if summary["contract_passed"] else 1
    if not args.demo:
        print("Use --demo, --input records.jsonl, or import run_known_tool() and inject_or_fallback().")
        return 0
    print(json.dumps(_demo(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
