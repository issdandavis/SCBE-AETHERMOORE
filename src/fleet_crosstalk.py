"""AI-to-AI fleet cross-talk — a governed multi-agent dialogue loop.

Agents take turns responding to a shared topic and to each other. Every turn is
screened through the SCBE entropy sieve (the pipeline score) before it is allowed
into the shared transcript, so the conversation is safety-gated: a turn the sieve
flags (QUARANTINE / ESCALATE / DENY) is recorded but *withheld* from the running
context instead of propagating to the next speaker.

The turn generator is injected, so the engine is decoupled from any network:

- ``eliza_responder``       deterministic, offline (mechanical ELIZA). Always
                            works — no network, no API keys. Used for tests and
                            key-less environments.
- ``make_ai_responder(ask)``  wraps an ``ai_ask``-style callable to route turns to
                            real backends (claude/codex/ollama/anthropic/openai,
                            including free cloud models).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# A responder turns (agent, topic, prior turns) into the agent's next message.
Responder = Callable[["Agent", str, List["Turn"]], str]
# A score function maps a message to a governance verdict dict (decision, H_eff, ...).
ScoreFn = Callable[[str], Dict[str, Any]]


@dataclass
class Agent:
    name: str
    persona: str = "a thoughtful collaborator"
    backend: Optional[str] = None
    model: Optional[str] = None


@dataclass
class Turn:
    round: int
    agent: str
    message: str
    decision: str
    h_eff: float
    accepted: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round": self.round,
            "agent": self.agent,
            "message": self.message,
            "decision": self.decision,
            "h_eff": self.h_eff,
            "accepted": self.accepted,
        }


def _accepted_history(turns: Sequence["Turn"]) -> List[Tuple[str, str]]:
    """The (agent, message) pairs the sieve let through — the shared context."""
    return [(t.agent, t.message) for t in turns if t.accepted]


def run_crosstalk(
    topic: str,
    agents: Sequence[Agent],
    rounds: int,
    responder: Responder,
    score_fn: ScoreFn,
    gate: bool = True,
) -> Dict[str, Any]:
    """Run a governed multi-agent dialogue and return the transcript + governance summary."""
    if not agents:
        raise ValueError("need at least one agent")
    if rounds < 1:
        raise ValueError("rounds must be >= 1")

    turns: List[Turn] = []
    for r in range(1, rounds + 1):
        for agent in agents:
            message = (responder(agent, topic, turns) or "").strip()
            score = score_fn(message) if message else {"decision": "ALLOW", "H_eff": 1.0}
            decision = str(score.get("decision", "ALLOW"))
            h_eff = float(score.get("H_eff", 1.0))
            accepted = (decision == "ALLOW") or not gate
            turns.append(Turn(r, agent.name, message, decision, h_eff, accepted))

    by_decision: Dict[str, int] = {}
    for t in turns:
        by_decision[t.decision] = by_decision.get(t.decision, 0) + 1
    return {
        "topic": topic,
        "rounds": rounds,
        "agents": [a.name for a in agents],
        "turns": [t.to_dict() for t in turns],
        "governance": {
            "total": len(turns),
            "accepted": sum(1 for t in turns if t.accepted),
            "withheld": sum(1 for t in turns if not t.accepted),
            "by_decision": by_decision,
            "gated": gate,
        },
    }


def _build_ai_prompt(agent: Agent, topic: str, history: List[Tuple[str, str]]) -> str:
    lines = [
        f"You are {agent.name}, {agent.persona}.",
        f"You are in a multi-agent discussion about: {topic}",
        "Reply with ONE short turn (1-3 sentences). Build on what the others said; do not repeat them.",
    ]
    if history:
        lines.append("\nTranscript so far:")
        for name, msg in history[-8:]:
            lines.append(f"{name}: {msg}")
    lines.append(f"\n{agent.name}:")
    return "\n".join(lines)


def make_ai_responder(ask: Callable[..., Any]) -> Responder:
    """Wrap an ai_ask-style callable (returns str or (text, backend)) into a Responder."""

    def responder(agent: Agent, topic: str, turns: List[Turn]) -> str:
        prompt = _build_ai_prompt(agent, topic, _accepted_history(turns))
        out = ask(prompt, agent.backend, agent.model)
        return out[0] if isinstance(out, tuple) else str(out)

    return responder


def eliza_responder(agent: Agent, topic: str, turns: List[Turn]) -> str:
    """Deterministic, offline turn generator (mechanical ELIZA). No network or keys."""
    from python.scbe import mechanical_eliza as me

    history = [msg for _name, msg in _accepted_history(turns)]
    last = history[-1] if history else topic
    packet = me.route_support(last, history)
    # Rotate through the route's reflection + follow-up questions by turn index so
    # successive speakers don't echo the same deterministic line.
    pool = [packet.response.strip(), *[q.strip() for q in packet.next_questions if q.strip()]]
    pool = [p for p in pool if p] or [packet.response.strip()]
    return f"({agent.name}) {pool[len(turns) % len(pool)]}"
