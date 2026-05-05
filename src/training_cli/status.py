"""Unified training status: aggregate runs + verdicts + heartbeat into one snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.training_cli.heartbeat import HeartbeatStatus, read_heartbeat
from src.training_cli.runs import TrainingRun, list_runs
from src.training_cli.verdicts import Verdict, load_verdicts


@dataclass(frozen=True)
class TrainingStatus:
    runs: tuple[TrainingRun, ...]
    recent_verdicts: tuple[Verdict, ...]
    heartbeat: HeartbeatStatus

    @property
    def latest_pass_rate(self) -> float | None:
        for v in self.recent_verdicts:
            if v.pass_rate is not None:
                return v.pass_rate
        return None

    @property
    def latest_status(self) -> str:
        if not self.recent_verdicts:
            return "no_verdicts"
        return self.recent_verdicts[0].status

    def to_dict(self) -> dict[str, Any]:
        return {
            "runs": [r.to_summary_dict() for r in self.runs],
            "recent_verdicts": [v.to_summary_dict() for v in self.recent_verdicts],
            "heartbeat": self.heartbeat.to_summary_dict(),
            "latest_pass_rate": self.latest_pass_rate,
            "latest_status": self.latest_status,
        }


def collect_status(repo_root: Path, *, verdict_limit: int = 10) -> TrainingStatus:
    runs_root = repo_root / "training" / "runs"
    runs = list_runs(runs_root)
    verdicts = load_verdicts(runs_root, limit=verdict_limit)
    heartbeat = read_heartbeat(repo_root)
    return TrainingStatus(
        runs=tuple(runs),
        recent_verdicts=tuple(verdicts),
        heartbeat=heartbeat,
    )
