from __future__ import annotations

from .models import AgentState


LESSON_DELTAS = {
    "navigation-basics": {"learning": 0.06, "stability": 0.03, "drift": -0.01},
    "resource-discipline": {"learning": 0.04, "safety": 0.03, "drift": -0.02},
    "geoseal-boundary-test": {"safety": 0.05, "stability": 0.02, "drift": -0.03},
    "swarm-handoff": {"learning": 0.05, "stability": 0.04},
}


def apply_lesson(state: AgentState, lesson: str) -> AgentState:
    delta = LESSON_DELTAS.get(lesson, {})
    for key, val in delta.items():
        setattr(state, key, getattr(state, key) + val)
    state.clamp()
    return state
