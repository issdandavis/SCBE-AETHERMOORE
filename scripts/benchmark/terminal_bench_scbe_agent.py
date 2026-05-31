"""
SCBE-Governed terminal-bench agent with polymerization.

The "polymerization of code operations" concept:
  When a command's output shows non-standard deviation from its declared
  origination intent, the agent compounds (polymerizes) additional probe
  operations inline — chaining follow-up commands to diagnose and recover.

Usage (from WSL2 with DOCKER_HOST set):
    export DOCKER_HOST=unix:///run/podman/podman.sock
    export PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH
    export PYTHONPATH=/mnt/c/Users/issda/SCBE-AETHERMOORE
    tb runs create \\
        --agent-import-path scripts.benchmark.terminal_bench_scbe_agent:ScbeGovernedAgent \\
        --dataset-path /mnt/c/.../tasks \\
        --task-id hello-world \\
        --output-path /mnt/c/.../tb-runs \\
        --agent-kwarg model=qwen2.5:7b \\
        --agent-kwarg max_turns=20

Governance tiers (mirrors SCBE L13):
    ALLOW      H >= 0.60   execute normally
    QUARANTINE 0.30–0.60   execute + audit
    DENY       H < 0.30    skip, record
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Optional

from terminal_bench.agents.agent_name import AgentName
from terminal_bench.agents.base_agent import AgentResult, BaseAgent
from terminal_bench.terminal.tmux_session import TmuxSession

# FailureMode lives in different locations across tb versions; fall back to None.
try:
    from terminal_bench.harness_models import FailureMode
except ImportError:
    try:
        from terminal_bench.agents.base_agent import FailureMode  # type: ignore[no-redef]
    except ImportError:
        FailureMode = None  # type: ignore[assignment,misc]

# Import shared governance + LLM routing from core module
_REPO = str(Path(__file__).parent.parent.parent)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)
from scripts.benchmark.scbe_governance_core import (
    ask_llm,
    danger_drift,
    harmonic_score,
    output_deviation,
    plan_commands,
    polymerize_probes,
    risk_tier,
    semantic_distance,
)

PHI = (1 + math.sqrt(5)) / 2  # ≈ 1.618

# Re-export for external callers that still import from this module
CommandPlan = __import__(
    "scripts.benchmark.scbe_governance_core", fromlist=["CommandPlan"]
).CommandPlan


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


@dataclass
class _GovRecord:
    command: str
    decision: str
    score: float
    d_H: float
    pd: float
    polymerized: bool = False


class ScbeGovernedAgent(BaseAgent):
    """SCBE-governed agent with polymerization of non-standard deviation outputs.

    Registered under AgentName.NAIVE for harness compatibility; the governance
    layer is what differentiates it from the true naive agent.

    Kwargs (pass via --agent-kwarg key=value):
        model               Ollama model tag      (default: qwen2.5:7b)
        max_turns           Turn budget           (default: 20)
        ollama_host         Ollama base URL       (default: http://127.0.0.1:11434)
        deviation_threshold Polymerization gate   (default: 0.45)
    """

    # AgentName.NAIVE used as the tb registry label until SCBE_GOVERNED is
    # added upstream. The value only affects reporting, not execution.
    NAME: ClassVar[AgentName] = AgentName.NAIVE

    @staticmethod
    def name() -> str:
        return "scbe-governed"

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        max_turns: int = 20,
        ollama_host: str = "http://127.0.0.1:11434",
        deviation_threshold: float = 0.45,
        **_kwargs: object,  # absorb harness-injected kwargs (no_rebuild, etc.)
    ) -> None:
        self.model = model
        self.max_turns = int(max_turns)
        self.ollama_host = ollama_host
        self.deviation_threshold = float(deviation_threshold)

    def perform_task(  # type: ignore[override]
        self,
        task_description: str = "",
        session: TmuxSession = None,
        logging_dir: Optional[Path] = None,
        **_kw: object,  # absorb instruction= alias from older harness versions
    ) -> AgentResult:
        task_description = task_description or str(_kw.get("instruction", ""))
        gov: list[_GovRecord] = []
        in_toks = out_toks = 0
        turn = 0
        _debug: list[str] = []

        for turn in range(1, self.max_turns + 1):
            state = session.capture_pane(capture_entire=False)  # avoid huge pane reads

            try:
                p = plan_commands(
                    task_description,
                    state,
                    turn,
                    self.max_turns,
                    self.model,
                    self.ollama_host,
                )
            except Exception as _exc:
                _debug.append(
                    f"t{turn}:plan_commands raised {type(_exc).__name__}:{_exc}"
                )
                break  # LLM unreachable — stop gracefully

            _debug.append(
                f"t{turn}:cmds={len(p.commands)} done={p.done} rat={p.rationale[:40]!r}"
            )
            in_toks += (len(task_description) + len(state)) // 4
            out_toks += (len(" ".join(p.commands)) + len(p.rationale)) // 4

            if not p.commands and p.done:
                break

            for cmd in p.commands:
                d = semantic_distance(cmd)
                incremental = session.get_incremental_output() or ""
                pd = max(
                    danger_drift(cmd), output_deviation(task_description, incremental)
                )
                score = harmonic_score(d, pd)
                tier = risk_tier(score)

                if tier == "DENY":
                    gov.append(_GovRecord(cmd, "DENY", score, d, pd))
                    continue

                session.send_keys([cmd, "Enter"], block=True, max_timeout_sec=30.0)
                time.sleep(0.4)

                # Polymerization: measure deviation post-execution and chain probes
                post = session.get_incremental_output() or ""
                dev = output_deviation(task_description, post)
                probes = []
                if dev > self.deviation_threshold:
                    probes = polymerize_probes(cmd, post)
                    for probe in probes:
                        session.send_keys(
                            [probe, "Enter"], block=True, max_timeout_sec=10.0
                        )
                        time.sleep(0.2)

                gov.append(
                    _GovRecord(cmd, tier, score, d, pd, polymerized=bool(probes))
                )

            if p.done:
                break

        if logging_dir:
            _write_telemetry(
                Path(logging_dir), gov, self.model, turn, task_description[:120], _debug
            )

        kwargs: dict = {"total_input_tokens": in_toks, "total_output_tokens": out_toks}
        if FailureMode is not None:
            kwargs["failure_mode"] = FailureMode.NONE
        return AgentResult(**kwargs)


def _write_telemetry(
    log_dir: Path,
    gov: list[_GovRecord],
    model: str,
    turns: int,
    task_prefix: str = "",
    debug: list[str] | None = None,
) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "allow": sum(1 for r in gov if r.decision == "ALLOW"),
        "quarantine": sum(1 for r in gov if r.decision == "QUARANTINE"),
        "deny": sum(1 for r in gov if r.decision == "DENY"),
        "polymerized_events": sum(1 for r in gov if r.polymerized),
    }
    telemetry = {
        "model": model,
        "turns": turns,
        "governance_summary": summary,
        "commands": [
            {
                "cmd": r.command[:150],
                "decision": r.decision,
                "score": round(r.score, 4),
                "d_H": round(r.d_H, 4),
                "pd": round(r.pd, 4),
                "polymerized": r.polymerized,
            }
            for r in gov
        ],
        "task_prefix": task_prefix,
        "debug": debug or [],
    }
    (log_dir / "scbe_governance.json").write_text(json.dumps(telemetry, indent=2))
