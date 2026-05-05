"""Read the night-training-watch rolling heartbeat line."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HEARTBEAT_REL = Path("artifacts") / "heartbeat" / "night_training_watch.line"


@dataclass(frozen=True)
class HeartbeatStatus:
    path: Path
    exists: bool
    line: str
    length: int
    success_count: int
    fail_count: int
    error_count: int

    @property
    def health(self) -> str:
        if not self.exists or self.length == 0:
            return "no_data"
        if self.fail_count == 0 and self.error_count == 0:
            return "all_green"
        if self.fail_count + self.error_count <= max(2, self.length // 20):
            return "mostly_green"
        if self.success_count == 0:
            return "all_red"
        return "degraded"

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "exists": self.exists,
            "line": self.line,
            "length": self.length,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "error_count": self.error_count,
            "health": self.health,
        }


def read_heartbeat(repo_root: Path, *, rel: Path = HEARTBEAT_REL) -> HeartbeatStatus:
    path = repo_root / rel
    if not path.exists():
        return HeartbeatStatus(
            path=path,
            exists=False,
            line="",
            length=0,
            success_count=0,
            fail_count=0,
            error_count=0,
        )

    try:
        line = path.read_text(encoding="ascii", errors="replace").strip("\r\n")
    except OSError:
        return HeartbeatStatus(
            path=path,
            exists=True,
            line="",
            length=0,
            success_count=0,
            fail_count=0,
            error_count=0,
        )

    counts = Counter(line)
    return HeartbeatStatus(
        path=path,
        exists=True,
        line=line,
        length=len(line),
        success_count=counts.get(".", 0),
        fail_count=counts.get("x", 0),
        error_count=counts.get("?", 0),
    )
