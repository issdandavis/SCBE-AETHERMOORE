# src/browser/navigation_randomtest.py
"""Navigation Randomtest -- Monte Carlo + exhaustive web path testing.

Adapted from CSTM mass_tester.py pattern for web navigation graphs.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class NavPage:
    url: str
    links: List[str] = field(default_factory=list)
    forms: List[str] = field(default_factory=list)
    page_type: str = "unknown"


@dataclass
class NavigationGraph:
    pages: Dict[str, NavPage] = field(default_factory=dict)

    def add_page(self, url: str, links: List[str] = None, forms: List[str] = None, page_type: str = "unknown"):
        self.pages[url] = NavPage(url=url, links=links or [], forms=forms or [], page_type=page_type)


@dataclass
class NavCoverageReport:
    paths_tested: int = 0
    success_rate: float = 0.0
    coverage_pct: float = 0.0
    cold_paths: List[str] = field(default_factory=list)
    hot_paths: List[List[str]] = field(default_factory=list)
    dead_ends: List[str] = field(default_factory=list)
    failure_points: List[str] = field(default_factory=list)
    mean_steps: float = 0.0
    all_paths_found: int = 0
    suggested_skills: List[str] = field(default_factory=list)


class NavigationRandomtest:
    """Monte Carlo navigation testing -- randomly walk the site graph."""

    def __init__(self, iterations: int = 1000, max_steps: int = 20, seed: int = 42):
        self.iterations = iterations
        self.max_steps = max_steps
        self.seed = seed

    def run(self, graph: NavigationGraph, start: str = "/") -> NavCoverageReport:
        rng = random.Random(self.seed)
        visited_pages: Dict[str, int] = {}
        successes = 0
        total_steps = 0
        paths: List[List[str]] = []
        dead_ends: Set[str] = set()

        for _ in range(self.iterations):
            path = [start]
            current = start
            steps = 0
            stuck = False

            while steps < self.max_steps:
                page = graph.pages.get(current)
                if page is None or not page.links:
                    dead_ends.add(current)
                    stuck = True
                    break
                visited_pages[current] = visited_pages.get(current, 0) + 1
                next_url = rng.choice(page.links)
                path.append(next_url)
                current = next_url
                steps += 1

            if not stuck:
                successes += 1
                paths.append(path)
            total_steps += steps

        # Coverage = visited unique pages / total pages
        coverage = len(visited_pages) / len(graph.pages) if graph.pages else 0.0

        # Cold paths = pages never visited
        cold = [url for url in graph.pages if url not in visited_pages]

        # Hot paths = most successful paths (top 5)
        hot = sorted(paths, key=len)[:5] if paths else []

        return NavCoverageReport(
            paths_tested=self.iterations,
            success_rate=successes / self.iterations if self.iterations else 0.0,
            coverage_pct=coverage,
            cold_paths=cold,
            hot_paths=hot,
            dead_ends=list(dead_ends),
            failure_points=list(dead_ends),
            mean_steps=total_steps / self.iterations if self.iterations else 0.0,
        )


class NavigationQuicktest:
    """Exhaustive navigation -- find ALL paths via BFS/DFS."""

    def __init__(self, max_depth: int = 10):
        self.max_depth = max_depth

    def run(self, graph: NavigationGraph, start: str = "/") -> NavCoverageReport:
        all_paths: List[List[str]] = []
        visited_states: Set[str] = set()
        visited_pages: Set[str] = set()

        stack: List[Tuple[str, List[str]]] = [(start, [start])]
        while stack:
            current, path = stack.pop()
            # Use full path as state key to allow different routes to same node
            state_key = "->".join(path)
            if state_key in visited_states or len(path) > self.max_depth:
                continue
            visited_states.add(state_key)
            visited_pages.add(current)

            page = graph.pages.get(current)
            if page is None or not page.links:
                all_paths.append(path)
                continue

            has_extension = False
            for link in page.links:
                if link not in path:  # avoid cycles
                    stack.append((link, path + [link]))
                    has_extension = True

            if not has_extension:
                # All links lead to already-visited nodes in this path (cycle)
                all_paths.append(path)

        return NavCoverageReport(
            paths_tested=len(all_paths),
            all_paths_found=len(all_paths),
            coverage_pct=len(visited_pages) / len(graph.pages) if graph.pages else 0.0,
            success_rate=1.0,
        )
