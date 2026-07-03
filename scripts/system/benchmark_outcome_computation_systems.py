"""Outcome-computation benchmark for SCBE vs external systems.

This is a research scorecard, not a formal performance benchmark. It compares
systems by what outcome guarantee they can produce:

* proof
* executable receipt
* counterexample/failure case
* broad domain expression
* human-accessible authoring
* reproducible artifacts
* visual/geometric composition
* usefulness as AI training feedback

Scores are 0..5 and deliberately conservative. The artifact is useful because
the criteria and weights are explicit and can be revised as SCBE gets stronger.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


CRITERIA: dict[str, dict[str, Any]] = {
    "proof_strength": {
        "weight": 0.18,
        "meaning": "Machine-checkable proof or hard formal guarantee.",
    },
    "executable_outcome": {
        "weight": 0.18,
        "meaning": "Can run the thing and verify the produced result.",
    },
    "counterexample_power": {
        "weight": 0.14,
        "meaning": "Finds minimal failures, bad states, or rejected fakes.",
    },
    "domain_breadth": {
        "weight": 0.12,
        "meaning": "Range of domains expressible without rebuilding the whole tool.",
    },
    "human_accessibility": {
        "weight": 0.10,
        "meaning": "Usable by normal builders, students, or operators.",
    },
    "artifact_reproducibility": {
        "weight": 0.12,
        "meaning": "Receipts, logs, proof objects, or deterministic reruns.",
    },
    "visual_geometric_composition": {
        "weight": 0.08,
        "meaning": "Can compose programs as shapes, graphs, blocks, flows, or geometry.",
    },
    "ai_training_feedback": {
        "weight": 0.08,
        "meaning": "Can produce training/eval feedback useful to AI agents.",
    },
}


SYSTEMS: list[dict[str, Any]] = [
    {
        "system": "SCBE Machine Crystal lane",
        "class": "homegrown geometric outcome system",
        "scores": {
            "proof_strength": 2,
            "executable_outcome": 4,
            "counterexample_power": 3,
            "domain_breadth": 4,
            "human_accessibility": 3,
            "artifact_reproducibility": 4,
            "visual_geometric_composition": 5,
            "ai_training_feedback": 3,
        },
        "best_at": "geometry-routed execution receipts across shape programs, p/n/e conservation, Bhargava overlays, and PHDM gates",
        "weak_at": "not yet a formal proof assistant; limited chemistry/nuclear tables; small benchmark corpus",
        "evidence": [
            "python/scbe/machine_crystal.py",
            "python/scbe/machine_crystal_higher.py",
            "python/scbe/machine_crystal_pne_cube.py",
            "python/scbe/machine_crystal_particle_chem.py",
            "scripts/system/review_machine_crystal_area.py",
        ],
    },
    {
        "system": "Rocq/Coq",
        "class": "interactive proof assistant",
        "scores": {
            "proof_strength": 5,
            "executable_outcome": 3,
            "counterexample_power": 2,
            "domain_breadth": 3,
            "human_accessibility": 2,
            "artifact_reproducibility": 5,
            "visual_geometric_composition": 1,
            "ai_training_feedback": 3,
        },
        "best_at": "machine-checked specifications and proofs, including program extraction",
        "weak_at": "high proof-engineering cost; not a friendly visual composition surface",
        "evidence": ["https://rocq-prover.org/"],
    },
    {
        "system": "Lean + Mathlib",
        "class": "proof assistant and formal math library",
        "scores": {
            "proof_strength": 5,
            "executable_outcome": 3,
            "counterexample_power": 2,
            "domain_breadth": 4,
            "human_accessibility": 3,
            "artifact_reproducibility": 5,
            "visual_geometric_composition": 1,
            "ai_training_feedback": 4,
        },
        "best_at": "large community formal mathematics and proof-as-code workflows",
        "weak_at": "requires formalization skill; not an execution-receipt system by default",
        "evidence": ["https://lean-lang.org/", "https://lean-lang.org/use-cases/mathlib/"],
    },
    {
        "system": "seL4 proof stack",
        "class": "formally verified operating-system kernel",
        "scores": {
            "proof_strength": 5,
            "executable_outcome": 4,
            "counterexample_power": 2,
            "domain_breadth": 1,
            "human_accessibility": 1,
            "artifact_reproducibility": 5,
            "visual_geometric_composition": 0,
            "ai_training_feedback": 2,
        },
        "best_at": "end-to-end machine-checked kernel correctness for a specific system",
        "weak_at": "not general-purpose authoring; very high engineering cost",
        "evidence": ["https://sel4.systems/Verification/proofs.html"],
    },
    {
        "system": "CompCert",
        "class": "formally verified C compiler",
        "scores": {
            "proof_strength": 5,
            "executable_outcome": 4,
            "counterexample_power": 1,
            "domain_breadth": 2,
            "human_accessibility": 2,
            "artifact_reproducibility": 5,
            "visual_geometric_composition": 0,
            "ai_training_feedback": 2,
        },
        "best_at": "compiler correctness: generated assembly matches source semantics",
        "weak_at": "focused on C compilation, not broad outcome composition",
        "evidence": ["https://compcert.org/"],
    },
    {
        "system": "Dafny",
        "class": "verification-aware programming language",
        "scores": {
            "proof_strength": 4,
            "executable_outcome": 4,
            "counterexample_power": 4,
            "domain_breadth": 3,
            "human_accessibility": 3,
            "artifact_reproducibility": 4,
            "visual_geometric_composition": 0,
            "ai_training_feedback": 4,
        },
        "best_at": "developer-facing specs, automated verification, counterexamples, and compilation to normal languages",
        "weak_at": "requires explicit specs; less visual/geometric than SCBE",
        "evidence": ["https://dafny.org/"],
    },
    {
        "system": "Frama-C",
        "class": "formal C analysis platform",
        "scores": {
            "proof_strength": 4,
            "executable_outcome": 3,
            "counterexample_power": 4,
            "domain_breadth": 2,
            "human_accessibility": 2,
            "artifact_reproducibility": 4,
            "visual_geometric_composition": 0,
            "ai_training_feedback": 3,
        },
        "best_at": "industrial C source-code analysis with formal-method plugins",
        "weak_at": "C-focused and specialist-heavy",
        "evidence": ["https://frama-c.com/"],
    },
    {
        "system": "TLA+ / TLC / TLAPS",
        "class": "formal specification and model checking",
        "scores": {
            "proof_strength": 4,
            "executable_outcome": 2,
            "counterexample_power": 5,
            "domain_breadth": 3,
            "human_accessibility": 2,
            "artifact_reproducibility": 4,
            "visual_geometric_composition": 1,
            "ai_training_feedback": 3,
        },
        "best_at": "state-machine and distributed-systems design failures before implementation",
        "weak_at": "spec-level, not direct program execution",
        "evidence": ["https://proofs.tlapl.us/doc/web/content/Home.html"],
    },
    {
        "system": "Z3",
        "class": "SMT solver",
        "scores": {
            "proof_strength": 4,
            "executable_outcome": 2,
            "counterexample_power": 5,
            "domain_breadth": 3,
            "human_accessibility": 1,
            "artifact_reproducibility": 4,
            "visual_geometric_composition": 0,
            "ai_training_feedback": 4,
        },
        "best_at": "symbolic satisfiability and counterexample generation inside other tools",
        "weak_at": "not a user-facing computation environment by itself",
        "evidence": ["https://www.microsoft.com/en-us/research/project/z3-3/", "https://microsoft.github.io/z3guide/docs/logic/intro/"],
    },
    {
        "system": "Hypothesis / QuickCheck",
        "class": "property-based testing",
        "scores": {
            "proof_strength": 2,
            "executable_outcome": 4,
            "counterexample_power": 5,
            "domain_breadth": 4,
            "human_accessibility": 4,
            "artifact_reproducibility": 3,
            "visual_geometric_composition": 0,
            "ai_training_feedback": 5,
        },
        "best_at": "turning properties into many generated tests and minimized counterexamples",
        "weak_at": "testing, not proof; strength depends on chosen properties",
        "evidence": ["https://hypothesis.readthedocs.io/"],
    },
    {
        "system": "AFL++ / coverage-guided fuzzing",
        "class": "fuzz testing",
        "scores": {
            "proof_strength": 1,
            "executable_outcome": 4,
            "counterexample_power": 5,
            "domain_breadth": 3,
            "human_accessibility": 2,
            "artifact_reproducibility": 3,
            "visual_geometric_composition": 0,
            "ai_training_feedback": 4,
        },
        "best_at": "finding concrete crashing or security-relevant inputs by coverage feedback",
        "weak_at": "bug finding rather than correctness proof",
        "evidence": ["https://google.github.io/clusterfuzz/reference/coverage-guided-vs-blackbox/"],
    },
    {
        "system": "SWE-bench Verified",
        "class": "real-world AI software engineering benchmark",
        "scores": {
            "proof_strength": 1,
            "executable_outcome": 4,
            "counterexample_power": 3,
            "domain_breadth": 4,
            "human_accessibility": 3,
            "artifact_reproducibility": 4,
            "visual_geometric_composition": 0,
            "ai_training_feedback": 5,
        },
        "best_at": "evaluating whether AI patches real GitHub issues under a shared harness",
        "weak_at": "benchmark only; does not give internal proof or geometry",
        "evidence": ["https://www.swebench.com/"],
    },
    {
        "system": "Wolfram Language / Mathematica",
        "class": "symbolic computational language",
        "scores": {
            "proof_strength": 2,
            "executable_outcome": 5,
            "counterexample_power": 2,
            "domain_breadth": 5,
            "human_accessibility": 3,
            "artifact_reproducibility": 4,
            "visual_geometric_composition": 3,
            "ai_training_feedback": 3,
        },
        "best_at": "broad symbolic/numeric/data computation with high-level domain objects",
        "weak_at": "not primarily a formal verification system",
        "evidence": ["https://www.wolfram.com/language/"],
    },
    {
        "system": "Scratch / Blockly / Node-RED",
        "class": "homegrown-friendly block and flow systems",
        "scores": {
            "proof_strength": 0,
            "executable_outcome": 4,
            "counterexample_power": 1,
            "domain_breadth": 4,
            "human_accessibility": 5,
            "artifact_reproducibility": 2,
            "visual_geometric_composition": 5,
            "ai_training_feedback": 2,
        },
        "best_at": "accessible composition through blocks and flows",
        "weak_at": "weak formal guarantees and weak receipts unless paired with tests",
        "evidence": ["https://scratch.mit.edu/starter-projects", "https://docs.blockly.com/", "https://github.com/node-red/node-red"],
    },
]


def weighted_score(scores: dict[str, int]) -> float:
    total = 0.0
    for criterion, meta in CRITERIA.items():
        total += (float(scores[criterion]) / 5.0) * float(meta["weight"]) * 100.0
    return round(total, 2)


def benchmark() -> dict[str, Any]:
    rows = []
    for system in SYSTEMS:
        row = dict(system)
        row["weighted_score_0_100"] = weighted_score(system["scores"])
        rows.append(row)
    rows.sort(key=lambda r: r["weighted_score_0_100"], reverse=True)
    return {
        "schema": "scbe_outcome_computation_benchmark_v1",
        "benchmark_name": "Outcome-based computation systems comparison",
        "claim_boundary": "Subjective capability scorecard with explicit criteria; not a runtime speed benchmark or proof of superiority.",
        "criteria": CRITERIA,
        "systems": rows,
        "top_by_score": rows[0]["system"],
        "scbe_position": next(i + 1 for i, row in enumerate(rows) if row["system"] == "SCBE Machine Crystal lane"),
    }


def main() -> int:
    receipt = benchmark()
    out_dir = ROOT / "artifacts/outcome_computation"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "systems_benchmark.json"
    out_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
