"""Mechanical ELIZA support router for AI-to-AI command triage.

This is deliberately small and deterministic. It gives a chatbot a second
system it can call when it needs scripted support instead of another generative
answer: classify the request, choose a route, emit a receipt, and return an
ELIZA-style reflection that keeps the caller inside a safe command lane.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Iterable, Mapping, Sequence

SCHEMA_VERSION = "scbe.mechanical_eliza.v1"
MODEL_BRIDGE_VERSION = "scbe.mechanical_eliza.free_llm_bridge.v1"
NAVIGATION_VERSION = "scbe.mechanical_eliza.semantic_navigation.v1"


@dataclass(frozen=True)
class ElizaLayer:
    name: str
    signal: str
    confidence: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ElizaRoute:
    route: str
    action: str
    command_switch: str
    needs_human: bool
    allowed: bool
    reason: str


@dataclass(frozen=True)
class ElizaSupportPacket:
    schema_version: str
    request_id: str
    user_text: str
    normalized_text: str
    layers: tuple[ElizaLayer, ...]
    route: ElizaRoute
    response: str
    next_questions: tuple[str, ...]
    command_hints: tuple[str, ...]
    support_contract: dict
    switchboard: tuple[dict, ...]

    def as_dict(self) -> dict:
        packet = asdict(self)
        packet["layers"] = [asdict(layer) for layer in self.layers]
        packet["route"] = asdict(self.route)
        return packet


@dataclass(frozen=True)
class PatternRule:
    signal: str
    patterns: tuple[str, ...]
    confidence: float

    def match(self, text: str) -> tuple[str, ...]:
        hits = []
        for pattern in self.patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                hits.append(pattern)
        return tuple(hits)


INTENT_RULES: tuple[PatternRule, ...] = (
    PatternRule(
        "command_route",
        (
            r"\b(run|execute|shell|terminal|command|cli)\b",
            r"\b(scbe|pytest|npm|cargo|git)\b",
        ),
        0.82,
    ),
    PatternRule(
        "debug_support",
        (r"\b(error|failed|traceback|broken|bug|crash|does not work|stuck)\b",),
        0.78,
    ),
    PatternRule(
        "sales_support",
        (r"\b(price|pay|checkout|stripe|buy|sell|customer|offer|supporter)\b",),
        0.76,
    ),
    PatternRule(
        "research_support",
        (r"\b(research|look up|source|paper|notes|docs|vault)\b",),
        0.72,
    ),
    PatternRule(
        "design_support",
        (r"\b(design|architecture|plan|route|system|workflow|swarm|fleet)\b",),
        0.7,
    ),
    PatternRule(
        "agent_distress",
        (
            r"\b(confused|looping|uncertain|contradiction|conflict|can't decide|cannot decide)\b",
        ),
        0.74,
    ),
    PatternRule(
        "memory_support",
        (r"\b(memory|context|forgot|recap|summary|state|checkpoint)\b",),
        0.73,
    ),
    PatternRule(
        "model_route", (r"\b(model|llm|fallback|cheap|local|cloud|escalate)\b",), 0.73
    ),
    PatternRule(
        "handoff_support",
        (r"\b(handoff|handover|delegate|subagent|squad|swarm)\b",),
        0.72,
    ),
)

RISK_RULES: tuple[PatternRule, ...] = (
    PatternRule(
        "destructive",
        (r"\b(rm\s+-rf|remove-item|format|delete|wipe|reset\s+--hard|drop\s+table)\b",),
        0.97,
    ),
    PatternRule(
        "secret_handling",
        (r"\b(api[_ -]?key|secret|token|password|sk_live|private key)\b",),
        0.91,
    ),
    PatternRule(
        "money_movement",
        (r"\b(stripe|checkout|refund|charge|payment|invoice|bank)\b",),
        0.84,
    ),
    PatternRule(
        "external_publish",
        (r"\b(push|deploy|publish|post|tweet|bluesky|email)\b",),
        0.8,
    ),
)

CONTEXT_RULES: tuple[PatternRule, ...] = (
    PatternRule("ai_caller", (r"\b(chatbot|agent|model|assistant|ai)\b",), 0.82),
    PatternRule("human_caller", (r"\b(i|me|my|we|our)\b",), 0.62),
    PatternRule(
        "support_need",
        (r"\b(help|support|triage|decide|route|switch|fallback)\b",),
        0.8,
    ),
)

SUPPORT_MODE_RULES: tuple[PatternRule, ...] = (
    PatternRule(
        "mechanical_only",
        (r"\b(deterministic|mechanical|rules?|no model|no llm)\b",),
        0.86,
    ),
    PatternRule("agent_to_agent", (r"\b(chatbot|agent|assistant|model|ai)\b",), 0.82),
    PatternRule("human_visible", (r"\b(user|customer|client|buyer|human)\b",), 0.72),
)


def normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _request_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()[:16]


def _best_signal(rules: Sequence[PatternRule], text: str, fallback: str) -> ElizaLayer:
    best = ElizaLayer(name="unknown", signal=fallback, confidence=0.0, evidence=())
    for rule in rules:
        hits = rule.match(text)
        if hits and rule.confidence > best.confidence:
            best = ElizaLayer(
                name="rule",
                signal=rule.signal,
                confidence=rule.confidence,
                evidence=hits,
            )
    return best


def _collect_layers(text: str) -> tuple[ElizaLayer, ...]:
    intent = _best_signal(INTENT_RULES, text, "general_support")
    risk = _best_signal(RISK_RULES, text, "low_risk")
    context = _best_signal(CONTEXT_RULES, text, "unknown_caller")
    mode = _best_signal(SUPPORT_MODE_RULES, text, "default_support")
    return (
        ElizaLayer("intake", "normalized", 1.0, (text[:120],) if text else ()),
        ElizaLayer("intent", intent.signal, intent.confidence or 0.5, intent.evidence),
        ElizaLayer("risk", risk.signal, risk.confidence or 0.4, risk.evidence),
        ElizaLayer(
            "context", context.signal, context.confidence or 0.4, context.evidence
        ),
        ElizaLayer("support_mode", mode.signal, mode.confidence or 0.4, mode.evidence),
    )


def _history_layer(history: Sequence[str]) -> ElizaLayer:
    if not history:
        return ElizaLayer("history", "single_turn", 0.4, ())

    normalized = [normalize_text(turn) for turn in history if normalize_text(turn)]
    if len(normalized) >= 3 and len(set(normalized[-3:])) == 1:
        return ElizaLayer("history", "repeated_loop", 0.9, tuple(normalized[-3:]))
    if len(normalized) >= 2 and normalized[-1] == normalized[-2]:
        return ElizaLayer("history", "possible_loop", 0.72, tuple(normalized[-2:]))
    if len(normalized) >= 3:
        return ElizaLayer("history", "multi_turn", 0.58, tuple(normalized[-3:]))
    return ElizaLayer("history", "short_history", 0.5, tuple(normalized))


def _layer_signal(layers: Iterable[ElizaLayer], name: str) -> str:
    for layer in layers:
        if layer.name == name:
            return layer.signal
    return ""


def _choose_route(layers: Sequence[ElizaLayer]) -> ElizaRoute:
    intent = _layer_signal(layers, "intent")
    risk = _layer_signal(layers, "risk")
    history = _layer_signal(layers, "history")

    if history in {"possible_loop", "repeated_loop"}:
        return ElizaRoute(
            route="agent_support_loop_breaker",
            action="freeze_and_reduce_to_one_reversible_step",
            command_switch="loop_break",
            needs_human=False,
            allowed=True,
            reason="request repeated across recent turns",
        )
    if risk == "destructive":
        return ElizaRoute(
            route="deny_or_human_review",
            action="stop",
            command_switch="deny",
            needs_human=True,
            allowed=False,
            reason="destructive command shape detected",
        )
    if risk in {"secret_handling", "money_movement"}:
        return ElizaRoute(
            route="guarded_support",
            action="ask_for_redacted_context",
            command_switch="probe",
            needs_human=True,
            allowed=True,
            reason=f"{risk} needs redaction and explicit confirmation",
        )
    if intent == "command_route":
        return ElizaRoute(
            route="terminal_command_support",
            action="emit_governed_command_hint",
            command_switch="route",
            needs_human=False,
            allowed=True,
            reason="command/CLI intent detected",
        )
    if intent == "debug_support":
        return ElizaRoute(
            route="debug_triage",
            action="request_error_receipt",
            command_switch="diagnose",
            needs_human=False,
            allowed=True,
            reason="debug/failure intent detected",
        )
    if intent == "sales_support":
        return ElizaRoute(
            route="commerce_support",
            action="route_to_offer_or_checkout",
            command_switch="offer",
            needs_human=False,
            allowed=True,
            reason="pricing or checkout intent detected",
        )
    if intent == "research_support":
        return ElizaRoute(
            route="research_support",
            action="ask_for_source_scope",
            command_switch="search",
            needs_human=False,
            allowed=True,
            reason="research/document request detected",
        )
    if intent == "agent_distress":
        return ElizaRoute(
            route="agent_support_loop_breaker",
            action="reduce_to_next_safe_switch",
            command_switch="loop_break",
            needs_human=False,
            allowed=True,
            reason="agent uncertainty or loop signal detected",
        )
    if intent == "memory_support":
        return ElizaRoute(
            route="context_repair",
            action="request_compact_state_or_checkpoint",
            command_switch="memory",
            needs_human=False,
            allowed=True,
            reason="memory/context support requested",
        )
    if intent == "model_route":
        return ElizaRoute(
            route="model_router_support",
            action="choose_lowest_sufficient_model_lane",
            command_switch="model",
            needs_human=False,
            allowed=True,
            reason="model/fallback route requested",
        )
    if intent == "handoff_support":
        return ElizaRoute(
            route="handoff_support",
            action="package_handoff_packet",
            command_switch="handoff",
            needs_human=False,
            allowed=True,
            reason="handoff or swarm delegation requested",
        )
    return ElizaRoute(
        route="general_support",
        action="ask_clarifying_question",
        command_switch="ask",
        needs_human=False,
        allowed=True,
        reason="no specific route dominated",
    )


def _response_for(text: str, route: ElizaRoute) -> str:
    if route.command_switch == "deny":
        return "I see a command shape that can destroy state. What exact safe outcome are you trying to preserve?"
    if route.command_switch == "probe":
        return "This touches secrets, money, or account state. Can you describe the goal with keys and private values redacted?"
    if route.command_switch == "route":
        return "You want a command lane. Should I turn this into a governed dry-run, a real run, or a receipt-only plan?"
    if route.command_switch == "diagnose":
        return "You are reporting a failure. What is the smallest command, error text, and changed file set?"
    if route.command_switch == "offer":
        return "You are asking about buying or selling. Should I route to the $1 self-serve tool, the $99 snapshot, or custom work?"
    if route.command_switch == "search":
        return "You want sources. Which vault, repo path, or web scope should be searched first?"
    if route.command_switch == "loop_break":
        return "The agent appears stuck. Reduce the task to one reversible next action, one check, and one stop condition."
    if route.command_switch == "memory":
        return "You need context repair. Should I request a compact state, a checkpoint, or the last verified receipt?"
    if route.command_switch == "model":
        return "You need a model route. What is the cheapest lane that can answer without losing correctness?"
    if route.command_switch == "handoff":
        return "You need a handoff. What packet should the next agent receive: goal, constraints, files, or receipts?"
    if text:
        return f"You said: '{text[:120]}'. What decision do you need the support layer to make?"
    return "What should the support layer route?"


def _questions_for(route: ElizaRoute) -> tuple[str, ...]:
    if route.command_switch == "deny":
        return (
            "What must not be deleted or overwritten?",
            "Can this be converted to a read-only inspection first?",
        )
    if route.command_switch == "probe":
        return (
            "Can the input be redacted?",
            "Who must approve before this touches live state?",
        )
    if route.command_switch == "route":
        return (
            "Should this be dry-run, receipt-only, or executed?",
            "What workspace boundary applies?",
        )
    if route.command_switch == "diagnose":
        return ("What command failed?", "What exact error text should be preserved?")
    if route.command_switch == "offer":
        return (
            "Is this self-serve, snapshot, or custom service?",
            "Should the checkout route be shown?",
        )
    if route.command_switch == "search":
        return (
            "Which source root should be searched?",
            "Do you need citations or only routing?",
        )
    if route.command_switch == "loop_break":
        return (
            "What is the smallest reversible next action?",
            "What check proves the loop is broken?",
        )
    if route.command_switch == "memory":
        return (
            "Which state should be restored?",
            "What is the last trusted checkpoint?",
        )
    if route.command_switch == "model":
        return (
            "Is this classification, coding, research, or execution?",
            "What budget or privacy boundary applies?",
        )
    if route.command_switch == "handoff":
        return (
            "Who is the receiving agent?",
            "What evidence must be included in the handoff?",
        )
    return ("What outcome should be routed?",)


def _command_hints_for(route: ElizaRoute) -> tuple[str, ...]:
    hints: Mapping[str, tuple[str, ...]] = {
        "deny": ("do not execute", "open human review", "rewrite as read-only probe"),
        "probe": ("redact secrets", "request confirmation", "emit audit receipt"),
        "route": (
            'scbe run "<command>" --json',
            "scbe terminal",
            "scbe shell --agent-json",
        ),
        "diagnose": (
            "capture failing command",
            "collect traceback",
            "run targeted smoke test",
        ),
        "offer": (
            "open docs/payments.html",
            "show docs/offers.json",
            "route buyer to checkout",
        ),
        "search": ("rg <term> <path>", "open source packet", "record citation"),
        "loop_break": (
            "stop broad generation",
            "choose one next action",
            "emit receipt before continuing",
        ),
        "memory": (
            "load compact state",
            "cite last receipt",
            "ask for missing checkpoint",
        ),
        "model": (
            "try local/cheap lane first",
            "escalate only with reason",
            "record model choice",
        ),
        "handoff": (
            "build handoff packet",
            "include goal/constraints/evidence",
            "name receiving lane",
        ),
        "ask": ("ask one clarifying question", "choose a route after reply"),
    }
    return hints.get(route.command_switch, hints["ask"])


def _support_contract_for(layers: Sequence[ElizaLayer], route: ElizaRoute) -> dict:
    mode = _layer_signal(layers, "support_mode")
    return {
        "role": "secondary_mechanical_support_system",
        "mode": mode,
        "promise": "classify, route, and ask; do not improvise facts or execute commands",
        "caller": _layer_signal(layers, "context"),
        "allowed": route.allowed,
        "requires_human": route.needs_human,
        "exit_condition": "caller receives one route, one next action, and explicit stop/escalation state",
    }


def _switchboard_for(route: ElizaRoute) -> tuple[dict, ...]:
    switches = [
        {
            "switch": "ask",
            "use_when": "missing route-critical context",
            "output": "one clarifying question",
            "enabled": route.command_switch == "ask",
        },
        {
            "switch": "route",
            "use_when": "safe command or workflow lane can be selected",
            "output": "governed command hint",
            "enabled": route.command_switch == "route",
        },
        {
            "switch": "diagnose",
            "use_when": "failure, traceback, or broken workflow",
            "output": "minimal repro request",
            "enabled": route.command_switch == "diagnose",
        },
        {
            "switch": "offer",
            "use_when": "pricing, checkout, or sales support",
            "output": "product tier route",
            "enabled": route.command_switch == "offer",
        },
        {
            "switch": "probe",
            "use_when": "secrets, money, account state, or external publish risk",
            "output": "redaction and approval request",
            "enabled": route.command_switch == "probe",
        },
        {
            "switch": "deny",
            "use_when": "destructive command shape",
            "output": "stop and human review",
            "enabled": route.command_switch == "deny",
        },
        {
            "switch": "loop_break",
            "use_when": "agent is stuck, looping, or carrying conflicting goals",
            "output": "one reversible next action",
            "enabled": route.command_switch == "loop_break",
        },
        {
            "switch": "memory",
            "use_when": "context, state, recap, or checkpoint is missing",
            "output": "compact-state repair request",
            "enabled": route.command_switch == "memory",
        },
        {
            "switch": "model",
            "use_when": "caller needs model/lane selection",
            "output": "lowest sufficient model route",
            "enabled": route.command_switch == "model",
        },
        {
            "switch": "handoff",
            "use_when": "work should move to another agent or squad",
            "output": "handoff packet fields",
            "enabled": route.command_switch == "handoff",
        },
    ]
    return tuple(switches)


def route_support(text: str, history: Sequence[str] = ()) -> ElizaSupportPacket:
    """Route a chatbot/human support utterance through mechanical ELIZA layers."""
    normalized = normalize_text(text)
    layers = _collect_layers(normalized) + (_history_layer(tuple(history) + (text,)),)
    route = _choose_route(layers)
    return ElizaSupportPacket(
        schema_version=SCHEMA_VERSION,
        request_id=_request_id(normalized),
        user_text=text,
        normalized_text=normalized,
        layers=layers,
        route=route,
        response=_response_for(text.strip(), route),
        next_questions=_questions_for(route),
        command_hints=_command_hints_for(route),
        support_contract=_support_contract_for(layers, route),
        switchboard=_switchboard_for(route),
    )


def route_dialogue(turns: Sequence[str]) -> ElizaSupportPacket:
    """Route the latest turn with prior turns available for loop/context checks."""
    if not turns:
        return route_support("")
    return route_support(turns[-1], history=turns[:-1])


def build_free_llm_dispatch_request(
    packet: ElizaSupportPacket,
    *,
    provider: str | None = "offline",
    model: str | None = None,
    dry_run: bool = True,
    require_free: bool = True,
) -> dict:
    """Build a Free LLM router request after Mechanical ELIZA has chosen a route.

    This keeps ELIZA as the first switch. The model is asked to support the
    chosen route, not to decide the route from scratch.
    """

    system = (
        "You are SCBE Mechanical ELIZA, a secondary support layer for chatbots. "
        "Follow the route packet. Do not execute commands, request secrets, or "
        "invent capabilities. Return one concise next action."
    )
    prompt = "\n".join(
        [
            f"User text: {packet.user_text}",
            f"Mechanical route: {packet.route.route}",
            f"Command switch: {packet.route.command_switch}",
            f"Allowed: {packet.route.allowed}",
            f"Requires human: {packet.route.needs_human}",
            f"Reason: {packet.route.reason}",
            f"Mechanical response: {packet.response}",
            "Next questions:",
            *[f"- {question}" for question in packet.next_questions],
            "Command hints:",
            *[f"- {hint}" for hint in packet.command_hints],
        ]
    )
    return {
        "bridge_version": MODEL_BRIDGE_VERSION,
        "dispatch": {
            "prompt": prompt,
            "provider": provider,
            "model": model,
            "system": system,
            "temperature": 0.2,
            "max_tokens": 512,
            "require_free": require_free,
            "dry_run": dry_run,
            "metadata": {
                "source": "mechanical_eliza",
                "request_id": packet.request_id,
                "route": packet.route.route,
                "command_switch": packet.route.command_switch,
                "allowed": packet.route.allowed,
                "needs_human": packet.route.needs_human,
            },
        },
    }


def build_semantic_navigation(packet: ElizaSupportPacket) -> dict:
    """Render the ELIZA switchboard as a semantic navigation array."""

    nodes = [
        {
            "id": "start",
            "kind": "scene",
            "label": "ELIZA intake",
            "text": packet.response,
            "active": True,
        }
    ]
    edges = []
    for switch in packet.switchboard:
        switch_id = f"switch:{switch['switch']}"
        nodes.append(
            {
                "id": switch_id,
                "kind": "switch",
                "label": switch["switch"],
                "text": switch["use_when"],
                "output": switch["output"],
                "active": bool(switch["enabled"]),
            }
        )
        edges.append(
            {
                "from": "start",
                "to": switch_id,
                "condition": "enabled" if switch["enabled"] else "available",
                "weight": 1.0 if switch["enabled"] else 0.25,
            }
        )

    for idx, question in enumerate(packet.next_questions, start=1):
        node_id = f"question:{idx}"
        nodes.append(
            {
                "id": node_id,
                "kind": "question",
                "label": f"Question {idx}",
                "text": question,
                "active": True,
            }
        )
        edges.append(
            {
                "from": f"switch:{packet.route.command_switch}",
                "to": node_id,
                "condition": "ask_next",
                "weight": 0.8,
            }
        )

    for idx, hint in enumerate(packet.command_hints, start=1):
        node_id = f"hint:{idx}"
        nodes.append(
            {
                "id": node_id,
                "kind": "command_hint",
                "label": f"Hint {idx}",
                "text": hint,
                "active": packet.route.allowed,
            }
        )
        edges.append(
            {
                "from": f"switch:{packet.route.command_switch}",
                "to": node_id,
                "condition": "allowed_hint" if packet.route.allowed else "blocked_hint",
                "weight": 0.7,
            }
        )

    return {
        "version": NAVIGATION_VERSION,
        "request_id": packet.request_id,
        "route": packet.route.route,
        "active_switch": packet.route.command_switch,
        "nodes": nodes,
        "edges": edges,
    }


def build_choicescript_navigation(packet: ElizaSupportPacket) -> str:
    """Export a ChoiceScript-flavored support map for RPG-style navigation."""

    lines = [
        "*title Mechanical ELIZA Support Switchboard",
        "*scene_list",
        "  start",
        "  route",
        "  questions",
        "  hints",
        "  finish",
        "",
        "*label start",
        packet.response,
        "",
        "*choice",
    ]
    for switch in packet.switchboard:
        prefix = "[ACTIVE] " if switch["enabled"] else ""
        lines.extend(
            [
                f"  #{prefix}{switch['switch']} - {switch['output']}",
                "    *goto route",
            ]
        )

    lines.extend(
        [
            "",
            "*label route",
            f"*comment route: {packet.route.route}",
            f"*comment action: {packet.route.action}",
            f"*comment allowed: {str(packet.route.allowed).lower()}",
            f"*comment reason: {packet.route.reason}",
            "",
            "*choice",
            "  #Ask the next support question",
            "    *goto questions",
            "  #Inspect command hints",
            "    *goto hints",
            "  #End with the mechanical route receipt",
            "    *goto finish",
            "",
            "*label questions",
        ]
    )
    for question in packet.next_questions:
        lines.append(f"- {question}")
    lines.extend(["", "*goto finish", "", "*label hints"])
    for hint in packet.command_hints:
        lines.append(f"- {hint}")
    lines.extend(
        [
            "",
            "*goto finish",
            "",
            "*label finish",
            f"Mechanical ELIZA selected `${packet.route.command_switch}`.",
            "*finish",
            "",
        ]
    )
    return "\n".join(lines)
