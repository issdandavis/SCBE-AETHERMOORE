from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Set

import numpy as np

from .model_synthesis import ModelNode, SynthesisResult, synthesize


@dataclass
class FrankenCandidate:
    name: str
    provider: str
    model: str
    capabilities: Set[str]
    trust: float
    pos: np.ndarray


def select_team(required: Set[str], candidates: Iterable[FrankenCandidate], max_team: int = 3) -> List[FrankenCandidate]:
    pool = list(candidates)
    team: List[FrankenCandidate] = []
    covered: Set[str] = set()

    while len(team) < max_team and covered != required:
        best = None
        best_gain = -1
        for c in pool:
            if c in team:
                continue
            gain = len((c.capabilities & required) - covered)
            if gain > best_gain:
                best = c
                best_gain = gain
        if best is None or best_gain <= 0:
            break
        team.append(best)
        covered |= (best.capabilities & required)

    return team


def build_frankenmodel(task: Dict, candidates: List[FrankenCandidate], perp_space: np.ndarray) -> Dict:
    required = set(task.get("requires", []))
    team = select_team(required, candidates, max_team=3)

    covered = set()
    for t in team:
        covered |= (t.capabilities & required)

    missing = sorted(required - covered)
    if len(team) < 2:
        return {
            "decision": "DENY",
            "reason": "insufficient team size for synthesis",
            "selected": [c.name for c in team],
            "missing_capabilities": missing,
        }

    model_nodes = [ModelNode(name=t.name, pos=t.pos, trust=t.trust) for t in team]
    synthesis: SynthesisResult = synthesize(model_nodes, perp_space, threshold=float(task.get("threshold", 1000.0)))

    return {
        "decision": synthesis.decision,
        "reason": synthesis.reason,
        "selected": [
            {
                "name": t.name,
                "provider": t.provider,
                "model": t.model,
                "capabilities": sorted(t.capabilities),
                "trust": t.trust,
            }
            for t in team
        ],
        "missing_capabilities": missing,
        "composite_pos": [float(x) for x in synthesis.composite_pos],
        "inherited_trust": synthesis.inherited_trust,
        "harmonic_energy": synthesis.harmonic_energy,
    }


def candidate_from_dict(d: Dict) -> FrankenCandidate:
    return FrankenCandidate(
        name=str(d["name"]),
        provider=str(d.get("provider", "unknown")),
        model=str(d.get("model", "unknown")),
        capabilities=set(d.get("capabilities", [])),
        trust=float(d.get("trust", 0.5)),
        pos=np.array(d.get("pos", [0.0, 0.0, 0.0]), dtype=np.float64),
    )
