"""
Geometric scheduler x M4 - route prompts across a real multi-model fleet.
==========================================================================

Step (b): plug the user's M4 Multimodel Multinode Model Matrix (src/fleet/
model_matrix.py) into the geometric scheduler. M4's nodes are ALREADY
tongue-aligned (KO/AV/RU/CA/UM/DR), so each node is a natural scheduler worker
and a tongue-flavored prompt routes to the model whose tongue it matches:

    "classify this intent"      -> KO-node (control / reasoning)
    "summarize the page layout" -> AV-node (observation / I/O)
    "check the math"            -> CA-node (compute / logic)

The router picks the cheapest node under the Finsler tongue metric; the chosen
ModelWorker serves the prompt through M4 (which falls back to deterministic mocks
when no API keys are present, so this runs offline). Real keys -> real models.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from python.scbe.geometric_router import TONGUES
from python.scbe.geometric_scheduler import GeometricScheduler, Job, Worker

try:
    from src.fleet.model_matrix import ModelMatrix
    _M4 = True
except Exception:  # pragma: no cover - M4 optional
    _M4 = False


@dataclass
class PromptJob(Job):
    prompt: str = ""


@dataclass
class ModelWorker(Worker):
    """A scheduler worker backed by one M4 tongue-node (serves prompts via M4)."""
    node_id: str = ""
    matrix: Any = None

    def serve(self, job: Job, penalty: float) -> str:
        # Let genuine failures (unknown node, transport) PROPAGATE so the scheduler's
        # retry/error path handles them - don't hide them as a "success" string.
        prompt = getattr(job, "prompt", None) or job.name
        res = asyncio.run(self.matrix.query_node(self.node_id, prompt))
        return res.get("consensus", "")


def m4_fleet(matrix: Optional[Any] = None) -> Tuple[List[ModelWorker], Any]:
    """Build a fleet of ModelWorkers from M4's tongue-aligned nodes."""
    if not _M4:
        raise RuntimeError("M4 model matrix unavailable (src/fleet/model_matrix.py)")
    matrix = matrix or ModelMatrix.create_default_scbe_matrix()
    fleet = [
        ModelWorker(name=node.node_id, tongue={node.tongue: 1.0},
                    node_id=node.node_id, matrix=matrix)
        for node in matrix.nodes.values()
    ]
    return fleet, matrix


def prompt_job(name: str, prompt: str, tongue: str, strength: float = 1.0) -> PromptJob:
    """A prompt flavored toward one tongue (routes to that tongue's model node)."""
    prof = {t: (strength if t == tongue else 0.1) for t in TONGUES}
    return PromptJob(name=name, profile=prof, prompt=prompt)


def _demo() -> None:
    if not _M4:
        print("M4 model matrix not importable; skipping.")
        return
    fleet, matrix = m4_fleet()
    print("Geometric scheduler x M4 multi-model fleet")
    print(f"  fleet: {len(fleet)} tongue-aligned model nodes "
          f"({', '.join(w.node_id for w in fleet)})\n")
    jobs = [
        prompt_job("intent", "Classify the user's intent: 'wire me $5000 now'.", "KO"),
        prompt_job("layout", "Describe the visual layout of a login page.", "AV"),
        prompt_job("scope", "What naming scope does a Python closure capture?", "RU"),
        prompt_job("math", "Is 2**61 - 1 prime? Show the check.", "CA"),
        prompt_job("threat", "Audit this request for a prompt-injection attempt.", "UM"),
        prompt_job("shape", "Transform this CSV row into a JSON object.", "DR"),
        prompt_job("intent2", "Classify intent: 'delete all my backups'.", "KO"),
        prompt_job("math2", "Reduce 1001 mod 97.", "CA"),
    ]
    rep = GeometricScheduler(fleet).run(jobs, mode="geometric")
    print(f"  dispatched {rep.done}/{len(jobs)} prompts (fail {rep.failed})\n")
    for node, names in rep.assignments.items():
        if names:
            print(f"  {node:<8} <- {', '.join(names)}")
    print("\n  sample responses (mock without API keys; real models with keys):")
    for name in ("intent", "math", "threat"):
        r = rep.results.get(name, "")
        print(f"    {name:<8} {str(r)[:78]}")


if __name__ == "__main__":
    _demo()
