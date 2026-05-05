"""List local training runs under training/runs/."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TrainingRun:
    name: str
    path: Path
    has_eval: bool
    verdict_count: int
    log_count: int
    size_bytes: int
    last_modified_ts: float

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": str(self.path),
            "has_eval": self.has_eval,
            "verdict_count": self.verdict_count,
            "log_count": self.log_count,
            "size_bytes": self.size_bytes,
            "last_modified_ts": self.last_modified_ts,
        }


def _dir_size_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                continue
    return total


def list_runs(runs_root: Path) -> list[TrainingRun]:
    """Return all training runs sorted by mtime descending."""

    if not runs_root.exists():
        return []

    out: list[TrainingRun] = []
    for child in runs_root.iterdir():
        if not child.is_dir():
            continue
        eval_dir = child / "eval"
        verdict_count = 0
        log_count = 0
        if eval_dir.is_dir():
            verdict_count = sum(1 for _ in eval_dir.glob("*_verdict.json"))
            log_count = sum(1 for _ in eval_dir.glob("*.log"))
        try:
            mtime = child.stat().st_mtime
        except OSError:
            mtime = 0.0
        out.append(
            TrainingRun(
                name=child.name,
                path=child,
                has_eval=eval_dir.is_dir(),
                verdict_count=verdict_count,
                log_count=log_count,
                size_bytes=_dir_size_bytes(child),
                last_modified_ts=mtime,
            )
        )
    out.sort(key=lambda r: r.last_modified_ts, reverse=True)
    return out
