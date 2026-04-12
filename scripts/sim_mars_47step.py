"""47-step Mars blackout-resumption sim — history reducer + Fibonacci trust ladder."""
from dataclasses import dataclass, field
from typing import List, Dict, Set
import time, random, statistics

phi = (1 + 5 ** 0.5) / 2

@dataclass
class WorldState:
    year: int = 0
    population: float = 1.0
    power: float = 1.0
    knowledge: float = 1.0
    economy: float = 1.0
    culture: float = 1.0
    technology: float = 1.0
    negative_flags: Set[str] = field(default_factory=set)
    dual_states: Set[str] = field(default_factory=set)
    memory: List[Dict] = field(default_factory=list)
    trust_ladder: List[float] = field(default_factory=lambda: [1.0, 1.0])
    betrayal_count: int = 0


def apply_step(state: WorldState, delta: Dict) -> WorldState:
    prev2, prev1 = state.trust_ladder[-2], state.trust_ladder[-1]
    betrayal_delta = float(delta.get("betrayal", 0.0))
    import math
    depth = max(1, len(state.trust_ladder) - 1)
    soft_phi = phi ** (1.0 / depth)
    if betrayal_delta > 0:
        new_trust = prev1 - soft_phi * abs(betrayal_delta)
        state.betrayal_count += 1
    else:
        new_trust = math.log1p(soft_phi * prev1) + prev2 / phi
    state.trust_ladder.append(new_trust)
    state.trust_ladder = state.trust_ladder[-12:]

    trust_factor = max(0.3, min(1.8, new_trust / 8.0))
    damping = 1.0 / trust_factor

    for k, v in delta.get("scalars", {}).items():
        setattr(state, k, getattr(state, k) + v * damping)
    state.negative_flags |= set(delta.get("neg", []))
    state.dual_states |= set(delta.get("dual", []))
    state.memory.append({**delta, "trust": new_trust, "factor": trust_factor})
    state.year += 1
    return state


def run(seed_state: WorldState, deltas: List[Dict], max_steps: int = 47):
    timings = []
    for d in deltas[:max_steps]:
        t0 = time.perf_counter()
        apply_step(seed_state, d)
        timings.append(time.perf_counter() - t0)
    return seed_state, timings


def synth_deltas(n=47, seed=7):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        d = {"scalars": {"power": rng.uniform(-0.05, 0.1),
                         "knowledge": rng.uniform(0.0, 0.08),
                         "culture": rng.uniform(-0.02, 0.05)}}
        if i in (15, 32):
            d["betrayal"] = 1.0
            d["neg"] = [f"breach_{i}"]
        out.append(d)
    return out


if __name__ == "__main__":
    state = WorldState()
    deltas = synth_deltas()
    final, timings = run(state, deltas, max_steps=47)
    drift = max(abs(t - statistics.mean(timings)) for t in timings)
    print({
        "year": final.year,
        "trust_level": round(final.trust_ladder[-1], 3),
        "betrayal_count": final.betrayal_count,
        "mean_step_us": round(statistics.mean(timings) * 1e6, 2),
        "max_step_us": round(max(timings) * 1e6, 2),
        "timing_drift_us": round(drift * 1e6, 2),
        "memory_len": len(final.memory),
        "negative_flags": sorted(final.negative_flags),
    })
