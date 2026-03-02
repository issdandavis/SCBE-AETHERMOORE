# src/browser/jitter_engine.py
"""Anti-detection jitter for Octopus Browser tentacles."""
from __future__ import annotations

import random
from typing import Dict, List, Tuple

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/122.0.2365.92",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 Mobile Safari/604.1",
]

DEFAULT_VIEWPORTS = [
    (1920, 1080), (1366, 768), (1440, 900), (1536, 864),
    (1280, 720), (1600, 900), (2560, 1440), (1024, 768),
]


class JitterEngine:
    def __init__(
        self,
        timing_range_ms: Tuple[int, int] = (200, 2000),
        user_agents: List[str] = None,
        viewports: List[Tuple[int, int]] = None,
        seed: int = 42,
    ):
        self.timing_range_ms = timing_range_ms
        self.user_agents = user_agents or DEFAULT_USER_AGENTS
        self.viewports = viewports or DEFAULT_VIEWPORTS
        self._rng = random.Random(seed)

    def next_delay_ms(self) -> int:
        return self._rng.randint(self.timing_range_ms[0], self.timing_range_ms[1])

    def next_user_agent(self) -> str:
        return self._rng.choice(self.user_agents)

    def next_viewport(self) -> Tuple[int, int]:
        return self._rng.choice(self.viewports)

    def to_dict(self) -> Dict:
        return {
            "timing_range_ms": list(self.timing_range_ms),
            "user_agents": self.user_agents,
            "viewports": [list(v) for v in self.viewports],
        }
