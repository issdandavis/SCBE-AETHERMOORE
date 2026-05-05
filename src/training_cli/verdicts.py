"""Read run verdicts from training/runs/<run>/eval/*.json.

Verdict schema (canonical for stage6 regression evals):
  {
    "job_id": str,
    "report": {
      "schema": "scbe_stage6_regression_report_v1",
      "adapter": str,
      "base_model": str,
      "n_total": int,
      "n_pass": int,
      "pass_rate": float,
      "minimum_pass_rate": float,
      "must_pass_all_ok": bool,
      "overall_pass": bool,
      "constrained_gate_scaffold": bool,
      "results": [...]
    }
  }
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Verdict:
    run_name: str
    job_id: str
    path: Path
    overall_pass: bool | None
    must_pass_all_ok: bool | None
    n_pass: int | None
    n_total: int | None
    pass_rate: float | None
    scaffold: bool | None
    base_model: str | None
    adapter: str | None
    generated_utc: str | None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        if self.overall_pass is True and self.must_pass_all_ok is True:
            return "PASS"
        if self.overall_pass is False:
            return "FAIL"
        return "UNKNOWN"

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "run_name": self.run_name,
            "job_id": self.job_id,
            "status": self.status,
            "n_pass": self.n_pass,
            "n_total": self.n_total,
            "pass_rate": self.pass_rate,
            "scaffold": self.scaffold,
            "base_model": self.base_model,
            "generated_utc": self.generated_utc,
            "path": str(self.path),
        }


def parse_verdict_file(path: Path) -> Verdict | None:
    """Parse a single verdict .json; returns None on malformed."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    report = data.get("report") if isinstance(data.get("report"), dict) else {}
    run_name = path.parent.parent.name
    return Verdict(
        run_name=run_name,
        job_id=str(data.get("job_id", path.stem.split("_")[0])),
        path=path,
        overall_pass=report.get("overall_pass"),
        must_pass_all_ok=report.get("must_pass_all_ok"),
        n_pass=report.get("n_pass"),
        n_total=report.get("n_total"),
        pass_rate=report.get("pass_rate"),
        scaffold=report.get("constrained_gate_scaffold"),
        base_model=report.get("base_model"),
        adapter=report.get("adapter"),
        generated_utc=report.get("generated_utc"),
        raw=data,
    )


def load_verdicts(runs_root: Path, *, limit: int | None = None) -> list[Verdict]:
    """Return verdicts across all runs, sorted by mtime descending (newest first)."""

    if not runs_root.exists():
        return []

    paths: list[Path] = []
    for run_dir in runs_root.iterdir():
        eval_dir = run_dir / "eval"
        if not eval_dir.is_dir():
            continue
        for verdict_path in eval_dir.glob("*_verdict.json"):
            paths.append(verdict_path)

    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if limit is not None:
        paths = paths[:limit]

    out: list[Verdict] = []
    for path in paths:
        verdict = parse_verdict_file(path)
        if verdict is not None:
            out.append(verdict)
    return out
