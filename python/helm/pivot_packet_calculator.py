"""pivot_packet_calculator -- structured pivot-conversation packets for small agents.

This module turns a conversational pivot into a compact, trainable packet:

* if the user asks a calculable question, route it through deterministic tools;
* otherwise, preserve the topic shift as a polite, bounded pivot packet;
* train visible rationale summaries, not hidden chain-of-thought;
* keep the same SCBE invariant as the coding contract: false_success_count == 0.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

try:
    from . import query_dispatch
    from .known_logic_injection import KnownLogicPacket, inject_or_fallback
except ImportError:  # pragma: no cover - script/notebook fallback
    import query_dispatch
    from known_logic_injection import KnownLogicPacket, inject_or_fallback

MODEL_SYSTEM_PROMPT = (
    "You are an SCBE pivot conversation calculator. "
    "Do not expose hidden chain-of-thought. "
    "Use compact visible reasoning summaries, deterministic packets, and polite safety phrasing."
)

POSITIVE_CONVERSATION_POINTS = (
    "Please be careful with the user's current context.",
    "If you would kindly keep the pivot explicit, preserve the useful thread before changing direction.",
    "Use deterministic tools or known packets for arithmetic, lookup, conversion, and gate decisions.",
    "If a step cannot be verified, escalate instead of pretending it is solved.",
)


@dataclass(frozen=True)
class PivotConversationPacket:
    """A visible, trainable packet for one pivot-conversation step."""

    packet_id: str
    task: str
    user_text: str
    pivot_from: str
    pivot_to: str
    domain: str
    status: str
    answer: str
    visible_reasoning_summary: List[str]
    positive_points: List[str] = field(default_factory=lambda: list(POSITIVE_CONVERSATION_POINTS))
    safety_phrase: str = "Please be careful and verify the packet before treating it as complete."
    calculator: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    false_success_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def render(self) -> str:
        """Return the assistant target text used for SFT."""

        lines = [
            "<SCBE_PIVOT_PACKET v=\"1\">",
            f"packet_id: {self.packet_id}",
            f"task: {self.task}",
            f"pivot: {self.pivot_from} -> {self.pivot_to}",
            f"domain: {self.domain}",
            f"status: {self.status}",
            f"care: {self.safety_phrase}",
            "visible_reasoning_summary:",
        ]
        for item in self.visible_reasoning_summary:
            lines.append(f"- {item}")
        if self.calculator:
            lines.append("calculator:")
            lines.append(f"- tool: {self.calculator.get('tool')}")
            lines.append(f"- source: {self.calculator.get('source')}")
            lines.append(f"- verified: {str(self.calculator.get('verified')).lower()}")
        lines.extend(
            [
                "positive_conversation_points:",
                *[f"- {point}" for point in self.positive_points],
                "answer:",
                self.answer,
                f"false_success_count: {self.false_success_count}",
                "</SCBE_PIVOT_PACKET>",
            ]
        )
        return "\n".join(lines)


def _stable_id(prefix: str, *parts: Any) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    return "%s:%s" % (prefix, hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16])


def _jsonish(value: Any) -> str:
    if isinstance(value, (dict, list, tuple, bool, int, float)) or value is None:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def _domain_from_dispatch(tool: Optional[str], fallback: str = "conversation") -> str:
    if not tool:
        return fallback
    for domain, tools in query_dispatch.T.BY_DOMAIN.items():
        if tool in tools:
            return domain
    return "deterministic_tool"


def calculator_packet_from_text(text: str, *, model_output: Optional[str] = None) -> Optional[PivotConversationPacket]:
    """Route a calculable conversation turn through deterministic tools when possible."""

    routed = query_dispatch.dispatch(text)
    if not routed:
        return None
    answer = _jsonish(routed["answer"])
    tool = str(routed["tool"])
    args = list(routed.get("args") or [])
    domain = _domain_from_dispatch(tool)
    known = KnownLogicPacket(
        packet_id=_stable_id("pivot_calc", text, tool, args, answer),
        task=text,
        answer=answer,
        process="query_dispatch matched %s with args=%s; run deterministic tool and serialize the answer." % (tool, args),
        source="tool:%s" % tool,
        metadata={"tool": tool, "args": args, "domain": domain},
    )
    decision = inject_or_fallback(known, model_output)
    return PivotConversationPacket(
        packet_id=known.packet_id,
        task="agentic_calculator",
        user_text=text,
        pivot_from="conversation",
        pivot_to="deterministic_tool",
        domain=domain,
        status=decision["status"],
        answer=str(decision["answer"]),
        visible_reasoning_summary=[
            "Detected a calculable request before asking the model to guess.",
            "Used the deterministic tool as the authority.",
            "Accepted model output only if it matched the known packet; otherwise used the packet answer.",
        ],
        calculator={"tool": tool, "source": known.source, "verified": True, "args": args},
        metadata={"deterministic_answer": decision["deterministic_answer"], "closed": decision["closed"]},
        false_success_count=int(decision["false_success_count"]),
    )


def build_pivot_packet(
    *,
    user_text: str,
    answer: str,
    task: str = "pivot_conversation",
    pivot_from: str = "current_context",
    pivot_to: str = "next_useful_context",
    domain: str = "conversation",
    metadata: Optional[Mapping[str, Any]] = None,
) -> PivotConversationPacket:
    """Build a non-calculator pivot packet with a visible rationale summary."""

    calc = calculator_packet_from_text(user_text)
    if calc is not None:
        return calc
    meta = dict(metadata or {})
    return PivotConversationPacket(
        packet_id=_stable_id("pivot", task, user_text, answer, pivot_from, pivot_to),
        task=task,
        user_text=user_text,
        pivot_from=pivot_from,
        pivot_to=pivot_to,
        domain=domain,
        status="pivot_packet",
        answer=answer,
        visible_reasoning_summary=[
            "Preserved the user's current thread before pivoting.",
            "Named the destination context so the next action is explicit.",
            "Kept the response bounded, polite, and verifiable.",
        ],
        metadata=meta,
        false_success_count=0,
    )


def topic_row_to_packet(row: Mapping[str, Any]) -> PivotConversationPacket:
    """Convert an existing pivot notebook SFT row into a packetized training row."""

    instruction = str(row.get("instruction") or row.get("prompt") or "")
    response = str(row.get("response") or row.get("chosen") or "")
    topic = str(row.get("topic") or "unknown_topic")
    tongue = str(row.get("tongue") or "NA")
    trajectory = str(row.get("trajectory") or "linear")
    return build_pivot_packet(
        user_text=instruction,
        answer=response,
        task="topic_pivot",
        pivot_from=topic,
        pivot_to="%s:%s" % (trajectory, tongue),
        domain="topic_graph",
        metadata=dict(row),
    )


def to_sft_record(packet: PivotConversationPacket) -> Dict[str, Any]:
    """Emit a chat SFT record in the same shape as the tool-trajectory corpus."""

    return {
        "messages": [
            {"role": "system", "content": MODEL_SYSTEM_PROMPT},
            {"role": "user", "content": packet.user_text},
            {"role": "assistant", "content": packet.render()},
        ],
        "meta": {
            "source": "pivot_packet_calculator",
            "packet_id": packet.packet_id,
            "task": packet.task,
            "domain": packet.domain,
            "status": packet.status,
            "false_success_count": packet.false_success_count,
        },
    }


def to_dpo_record(packet: PivotConversationPacket, rejected: str) -> Dict[str, Any]:
    return {
        "prompt": packet.user_text,
        "chosen": packet.render(),
        "rejected": rejected,
        "meta": {
            "source": "pivot_packet_calculator",
            "packet_id": packet.packet_id,
            "false_success_count": packet.false_success_count,
        },
    }


def build_packet_records(rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [to_sft_record(topic_row_to_packet(row)) for row in rows]


def summarize_packets(packets: Sequence[PivotConversationPacket]) -> Dict[str, Any]:
    total = len(packets)
    calculator = sum(1 for p in packets if p.calculator)
    false_success = sum(int(p.false_success_count or 0) for p in packets)
    statuses: Dict[str, int] = {}
    for packet in packets:
        statuses[packet.status] = statuses.get(packet.status, 0) + 1
    return {
        "total": total,
        "calculator_packets": calculator,
        "conversation_packets": total - calculator,
        "statuses": statuses,
        "false_success_count": false_success,
        "contract_passed": false_success == 0,
    }


if __name__ == "__main__":
    demo = calculator_packet_from_text("what is the 10th prime?")
    assert demo is not None
    assert demo.answer == "29"
    assert demo.false_success_count == 0
    print(json.dumps(demo.to_dict(), indent=2, sort_keys=True))
