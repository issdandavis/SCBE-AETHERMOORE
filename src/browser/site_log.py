# src/browser/site_log.py
"""Per-domain navigation memory for the Octopus Browser Kernel."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SiteLog:
    domain: str
    last_visited: str = ""
    login_method: Optional[str] = None
    navigation_map: Dict[str, str] = field(default_factory=dict)
    reliable_paths: List[List[str]] = field(default_factory=list)
    failure_patterns: List[str] = field(default_factory=list)
    custom_tools: List[str] = field(default_factory=list)
    page_type_map: Dict[str, str] = field(default_factory=dict)
    scrape_schema: Optional[Dict] = None
    visit_count: int = 0
    success_rate: float = 0.0
    status: str = "unknown"
    _successes: int = field(default=0, repr=False)

    def record_visit(
        self,
        path: List[str],
        success: bool,
        time_ms: int,
        failure_point: Optional[str] = None,
    ) -> None:
        self.visit_count += 1
        self.last_visited = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if success:
            self._successes += 1
            if path not in self.reliable_paths:
                self.reliable_paths.append(path)
        else:
            if failure_point and failure_point not in self.failure_patterns:
                self.failure_patterns.append(failure_point)
        self.success_rate = self._successes / self.visit_count if self.visit_count else 0.0
        self._update_status()

    def set_nav_target(self, name: str, selector: str) -> None:
        self.navigation_map[name] = selector

    def _update_status(self) -> None:
        if self.visit_count == 0:
            self.status = "unknown"
        elif self.visit_count < 10:
            self.status = "exploring"
        elif self.visit_count < 20 or self.success_rate < 0.9:
            self.status = "mapped"
        else:
            self.status = "reliable"

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("_successes", None)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SiteLog":
        successes = int(data.get("visit_count", 0) * data.get("success_rate", 0))
        data.pop("_successes", None)
        log = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        log._successes = successes
        return log


class SiteLogStore:
    def __init__(self, base_dir: str = "artifacts/site_logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, SiteLog] = {}

    def _path_for(self, domain: str) -> Path:
        safe = domain.replace("/", "_").replace(":", "_")
        return self.base_dir / f"{safe}.json"

    def get_or_create(self, domain: str) -> SiteLog:
        if domain in self._cache:
            return self._cache[domain]
        path = self._path_for(domain)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            log = SiteLog.from_dict(data)
        else:
            log = SiteLog(domain=domain)
        self._cache[domain] = log
        return log

    def save(self, log: SiteLog) -> None:
        path = self._path_for(log.domain)
        path.write_text(json.dumps(log.to_dict(), indent=2), encoding="utf-8")

    def list_domains(self) -> List[str]:
        return [p.stem for p in self.base_dir.glob("*.json")]
