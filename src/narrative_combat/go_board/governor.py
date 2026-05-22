"""Governed study move: web search as a move on the board.

A Study move samples outside sources without committing a stone — a probe move that buys
knowledge. It is *governed*: an allowlist decides whether a query may run, every call is
audited, and results are cached by ``(seed, turn_index, query)`` so the same encounter+seed
produces the same fight even once a real backend is wired in.

Fully local — no SCBE governance imports. The default backend is an offline stub, mirroring the
LLMTranslator's deterministic fallback: the engine works with no network, and a real web-search
backend is an opt-in v2 swap behind the same interface.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol


class StudyBackend(Protocol):
    name: str

    def search(self, query: str) -> tuple[str, ...]:  # pragma: no cover - interface only
        ...


class StubSearchBackend:
    """Offline default: returns nothing, deterministically. Real web search is a v2 swap."""

    name = "stub"

    def search(self, query: str) -> tuple[str, ...]:
        return ()


@dataclass(frozen=True)
class StudyRecord:
    """One audited study call — the trail a reviewer reads."""

    query: str
    decision: str  # "allow" | "deny" | "cached"
    backend: str
    latency_ms: float
    results: tuple[str, ...]


class SearchGovernor:
    """Decides whether a study query may run, audits every call, and caches results."""

    def __init__(
        self,
        backend: StudyBackend | None = None,
        allow_terms: list[str] | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.backend: StudyBackend = backend or StubSearchBackend()
        self.allow_terms = allow_terms  # None = allow anything; else the query must contain one
        self.timeout = timeout
        self.audit: list[StudyRecord] = []
        self._cache: dict[tuple[int, int, str], tuple[str, ...]] = {}

    def study(self, query: str, *, seed: int, turn_index: int) -> tuple[str, ...]:
        if self.allow_terms is not None and not any(term.lower() in query.lower() for term in self.allow_terms):
            self.audit.append(StudyRecord(query, "deny", self.backend.name, 0.0, ()))
            return ()

        key = (seed, turn_index, query)
        if key in self._cache:
            results = self._cache[key]
            self.audit.append(StudyRecord(query, "cached", self.backend.name, 0.0, results))
            return results

        start = time.perf_counter()
        try:
            results = tuple(self.backend.search(query))
        except Exception:
            results = ()
        latency_ms = (time.perf_counter() - start) * 1000.0
        self._cache[key] = results
        self.audit.append(StudyRecord(query, "allow", self.backend.name, latency_ms, results))
        return results
