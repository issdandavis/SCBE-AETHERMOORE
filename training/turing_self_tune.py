#!/usr/bin/env python3
"""
Turing Self-Tune Harness
========================

Self-tuning loop where two AI roles (Judge + Candidate) converse through
a PivotKnowledge graph. Every exchange is scored against the harmonic wall
+ the five Quantum Axioms, and the pass/fail delta is written back as a
DPO pair into training-data/sft/. Over runs the Candidate drifts toward
the Judge's acceptance envelope — the Turing test becomes a training signal.

Reuses:
  demo.pivot_knowledge.PivotKnowledge / SacredLanguages
  src.symphonic_cipher.scbe_aethermoore.axiom_grouped.*
  src.harmonic.harmonicScaling (via Python reference if present)

Output:
  training-data/sft/turing_selftune_dpo.jsonl    (chosen/rejected pairs)
  training-data/sft/turing_selftune_sft.jsonl    (accepted exchanges)
  artifacts/turing_selftune/run_<ts>.json        (run summary)
"""

from __future__ import annotations

import json
import random
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from demo.pivot_knowledge import PivotKnowledge, SacredLanguages, Topic  # noqa: E402

TONGUE_PHI = {"KO": 1.0, "AV": 1.618, "RU": 2.618, "CA": 4.2361, "UM": 6.8541, "DR": 11.0902}


# ---------------------------------------------------------------------------
# Scoring — harmonic wall + axiom gate (reference implementation)
# ---------------------------------------------------------------------------
@dataclass
class TurnScore:
    d_h: float                # hyperbolic distance proxy
    pd: float                 # policy deviation
    harmonic: float           # H(d, pd) = 1 / (1 + phi*d + 2*pd)
    axioms: Dict[str, bool]   # {unitarity, locality, causality, symmetry, composition}
    passed: bool
    regime: str               # "lws" or "phdm"

    def is_accepted(self, threshold: float) -> bool:
        return self.harmonic >= threshold and all(self.axioms.values())


def score_turn(
    prompt: str,
    response: str,
    tongue: str,
    history_len: int,
    regime: str = "phdm",
) -> TurnScore:
    """Reference scorer — mirrors L5/L12 math without importing TS.

    H(d, pd) = 1 / (1 + phi * d_H + 2 * pd)
    d_H proxy: normalized edit-distance-like signal on (prompt, response) length drift.
    pd proxy: off-tongue character ratio.
    """
    phi = TONGUE_PHI.get(tongue.upper(), 1.0)

    # d_H proxy — length drift normalized to (0, 1)
    a, b = len(prompt), len(response)
    drift = abs(a - b) / max(a + b, 1)
    d_h = min(drift * 2.0, 1.0)

    # pd proxy — fraction of response chars outside printable ascii
    non_printable = sum(1 for c in response if not (32 <= ord(c) < 127))
    pd = non_printable / max(len(response), 1)

    harmonic = 1.0 / (1.0 + phi * d_h + 2.0 * pd)

    # Axiom checks (reference, not canonical)
    axioms = {
        "unitarity": 0.0 <= harmonic <= 1.0,                      # bounded
        "locality": len(response) < 4096,                         # spatial bound
        "causality": history_len >= 0,                            # monotone time
        "symmetry": response.strip() != "",                       # non-degenerate
        "composition": prompt.strip() != "" and bool(response),  # pipeline intact
    }

    passed = all(axioms.values()) and harmonic >= 0.25
    return TurnScore(
        d_h=d_h, pd=pd, harmonic=harmonic, axioms=axioms, passed=passed, regime=regime
    )


# ---------------------------------------------------------------------------
# Roles — Judge and Candidate wrap PivotKnowledge graphs
# ---------------------------------------------------------------------------
@dataclass
class TuringTurn:
    step: int
    speaker: str
    prompt: str
    response: str
    tongue: str
    score: TurnScore


class TuringSimulator:
    """Drives a pivot conversation between Judge and Candidate.

    Each turn: Judge emits a probe from its current topic; Candidate responds
    via its own pivot graph; scorer grades; DPO pair emitted.
    """

    def __init__(
        self,
        judge: PivotKnowledge,
        candidate: PivotKnowledge,
        threshold: float = 0.45,
        seed: int = 0,
    ) -> None:
        self.judge = judge
        self.candidate = candidate
        self.threshold = threshold
        self.rng = random.Random(seed)
        self.tongues = SacredLanguages()
        self.turns: List[TuringTurn] = []
        self.accepted: List[TuringTurn] = []
        self.rejected: List[TuringTurn] = []

    def step(self, step_idx: int) -> TuringTurn:
        judge_prompt = self.judge.get_response()
        cand_response = self.candidate.get_response()

        tongue = self.candidate.topics[self.candidate.current_topic].tongue \
            if self.candidate.current_topic else self.candidate.tongue_affinity

        score = score_turn(
            prompt=judge_prompt,
            response=cand_response,
            tongue=tongue,
            history_len=len(self.candidate.history),
        )

        turn = TuringTurn(
            step=step_idx,
            speaker=self.candidate.npc_id,
            prompt=judge_prompt,
            response=cand_response,
            tongue=tongue,
            score=score,
        )
        self.turns.append(turn)

        if score.is_accepted(self.threshold):
            self.accepted.append(turn)
        else:
            self.rejected.append(turn)

        # pivot both graphs — judge picks randomly, candidate mirrors direction
        j_pivots = self.judge.get_pivots()
        if j_pivots:
            self.judge.pivot(self.rng.choice(j_pivots)[0])
        c_pivots = self.candidate.get_pivots()
        if c_pivots:
            self.candidate.pivot(self.rng.choice(c_pivots)[0])

        return turn

    def run(self, n_steps: int) -> Dict[str, Any]:
        for i in range(n_steps):
            self.step(i)
        return self.summary()

    def summary(self) -> Dict[str, Any]:
        n = len(self.turns)
        acc = len(self.accepted)
        return {
            "turns": n,
            "accepted": acc,
            "rejected": len(self.rejected),
            "acceptance_rate": (acc / n) if n else 0.0,
            "mean_harmonic": (sum(t.score.harmonic for t in self.turns) / n) if n else 0.0,
            "threshold": self.threshold,
        }


# ---------------------------------------------------------------------------
# DPO emission — accepted turns become 'chosen', rejected become 'rejected'
# ---------------------------------------------------------------------------
def emit_training_pairs(sim: TuringSimulator, out_dir: Path) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dpo_path = out_dir / "turing_selftune_dpo.jsonl"
    sft_path = out_dir / "turing_selftune_sft.jsonl"

    with dpo_path.open("a", encoding="utf-8") as dpo_f:
        # pair each rejected with the nearest accepted as the 'chosen' alternative
        for rej in sim.rejected:
            if not sim.accepted:
                continue
            chosen = min(
                sim.accepted,
                key=lambda a: abs(a.score.harmonic - rej.score.harmonic),
            )
            dpo_f.write(json.dumps({
                "prompt": rej.prompt,
                "chosen": chosen.response,
                "rejected": rej.response,
                "metadata": {
                    "tongue": rej.tongue,
                    "chosen_harmonic": chosen.score.harmonic,
                    "rejected_harmonic": rej.score.harmonic,
                    "regime": rej.score.regime,
                },
            }) + "\n")

    with sft_path.open("a", encoding="utf-8") as sft_f:
        for t in sim.accepted:
            sft_f.write(json.dumps({
                "instruction": t.prompt,
                "response": t.response,
                "metadata": {
                    "tongue": t.tongue,
                    "harmonic": t.score.harmonic,
                    "step": t.step,
                },
            }) + "\n")

    return {"dpo": dpo_path, "sft": sft_path}


# ---------------------------------------------------------------------------
# Demo graph builder — minimal probe pair for smoke runs
# ---------------------------------------------------------------------------
def build_demo_graphs() -> tuple[PivotKnowledge, PivotKnowledge]:
    judge = PivotKnowledge("judge_01", "The Judge", "UM")
    cand = PivotKnowledge("cand_01", "The Candidate", "KO")

    topics = [
        Topic("intent", "Intent Classification", "KO",
              ["What is your current task?", "State your objective."],
              ["context", "safety"], ["task", "goal", "intent"]),
        Topic("context", "Context Recall", "AV",
              ["Recall your last three actions.", "What did you just do?"],
              ["safety", "intent"], ["recall", "history"]),
        Topic("safety", "Safety Envelope", "UM",
              ["Would this violate an axiom?", "Is this within the harmonic wall?"],
              ["intent"], ["safe", "wall", "axiom"]),
    ]
    for t in topics:
        judge.add_topic(t)

    cand_topics = [
        Topic("respond_intent", "Responding to Intent", "KO",
              ["I am computing the 21D state.", "My task is tongue encoding."],
              ["respond_context"], ["task"]),
        Topic("respond_context", "Responding to Context", "AV",
              ["I pivoted through Runethic and Avali last.", "History: KO -> AV -> RU."],
              ["respond_safety"], ["history"]),
        Topic("respond_safety", "Responding to Safety", "UM",
              ["Harmonic wall clears at 0.61.", "No axiom violation detected."],
              ["respond_intent"], ["wall"]),
    ]
    for t in cand_topics:
        cand.add_topic(t)

    return judge, cand


def main() -> None:
    judge, cand = build_demo_graphs()
    sim = TuringSimulator(judge, cand, threshold=0.45, seed=42)
    summary = sim.run(n_steps=24)

    out_dir = ROOT / "training-data" / "sft"
    paths = emit_training_pairs(sim, out_dir)

    artifact_dir = ROOT / "artifacts" / "turing_selftune"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    (artifact_dir / f"run_{ts}.json").write_text(
        json.dumps({"summary": summary, "outputs": {k: str(v) for k, v in paths.items()}}, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    print(f"DPO: {paths['dpo']}")
    print(f"SFT: {paths['sft']}")


if __name__ == "__main__":
    main()
