"""
Concept Blocks — PLAN
=====================

A* path-finding over arbitrary graphs.  Maps to SCBE Layer 6 (navigation).

The ``GraphAdapter`` ABC lets the same algorithm work on:
- 2D/3D grid maps  (drone / game NPC)
- URL link graphs   (web navigation)
- Abstract state spaces  (decision planning)

PlanBlock
---------
ConceptBlock wrapper — feed a start/goal into ``tick()`` and get the
optimal path back.
"""

from __future__ import annotations

import heapq
import math
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Generic, Hashable, List, Optional, TypeVar

from .base import BlockResult, BlockStatus, ConceptBlock

N = TypeVar("N", bound=Hashable)


# -- graph adapter -----------------------------------------------------------

class GraphAdapter(ABC, Generic[N]):
    """Interface that A* needs from any graph."""

    @abstractmethod
    def neighbours(self, node: N) -> List[N]:
        ...

    @abstractmethod
    def cost(self, current: N, neighbour: N) -> float:
        ...

    @abstractmethod
    def heuristic(self, node: N, goal: N) -> float:
        ...


# -- grid adapter (spatial navigation) --------------------------------------

class GridAdapter(GraphAdapter[tuple]):
    """2D grid where nodes are (row, col) tuples."""

    DIRECTIONS_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    DIRECTIONS_8 = DIRECTIONS_4 + [(-1, -1), (-1, 1), (1, -1), (1, 1)]

    def __init__(
        self,
        rows: int,
        cols: int,
        blocked: Optional[set] = None,
        diagonal: bool = False,
    ) -> None:
        self.rows = rows
        self.cols = cols
        self._blocked = blocked or set()
        self._dirs = self.DIRECTIONS_8 if diagonal else self.DIRECTIONS_4

    def neighbours(self, node: tuple) -> List[tuple]:
        r, c = node
        out = []
        for dr, dc in self._dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols and (nr, nc) not in self._blocked:
                out.append((nr, nc))
        return out

    def cost(self, current: tuple, neighbour: tuple) -> float:
        dr = abs(current[0] - neighbour[0])
        dc = abs(current[1] - neighbour[1])
        return math.sqrt(dr * dr + dc * dc)

    def heuristic(self, node: tuple, goal: tuple) -> float:
        return math.sqrt((node[0] - goal[0]) ** 2 + (node[1] - goal[1]) ** 2)


# -- URL graph adapter (web navigation) -------------------------------------

class URLGraphAdapter(GraphAdapter[str]):
    """Graph where nodes are URLs and edges are hyperlinks.

    Provide a ``link_extractor(url) -> List[str]`` callable.
    """

    def __init__(
        self,
        link_extractor: Callable[[str], List[str]],
        cost_fn: Optional[Callable[[str, str], float]] = None,
        heuristic_fn: Optional[Callable[[str, str], float]] = None,
    ) -> None:
        self._extract = link_extractor
        self._cost_fn = cost_fn or (lambda _a, _b: 1.0)
        self._heuristic_fn = heuristic_fn or (lambda _a, _b: 0.0)

    def neighbours(self, node: str) -> List[str]:
        return self._extract(node)

    def cost(self, current: str, neighbour: str) -> float:
        return self._cost_fn(current, neighbour)

    def heuristic(self, node: str, goal: str) -> float:
        return self._heuristic_fn(node, goal)


# -- A* search ---------------------------------------------------------------

def a_star_search(
    graph: GraphAdapter[N],
    start: N,
    goal: N,
    max_expansions: int = 50_000,
) -> Optional[List[N]]:
    """Return shortest path from *start* to *goal*, or ``None``."""

    open_set: List[tuple] = [(0.0, 0, start)]  # (f, tiebreak, node)
    came_from: Dict[N, N] = {}
    g_score: Dict[N, float] = {start: 0.0}
    counter = 1

    while open_set:
        _f, _cnt, current = heapq.heappop(open_set)

        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            return list(reversed(path))

        if counter > max_expansions:
            return None

        for nb in graph.neighbours(current):
            tentative = g_score[current] + graph.cost(current, nb)
            if tentative < g_score.get(nb, float("inf")):
                came_from[nb] = current
                g_score[nb] = tentative
                f = tentative + graph.heuristic(nb, goal)
                heapq.heappush(open_set, (f, counter, nb))
                counter += 1

    return None


# -- concept block wrapper ---------------------------------------------------

class PlanBlock(ConceptBlock):
    """Concept block wrapping A* path-finding.

    tick(inputs):
        inputs["start"]  — start node
        inputs["goal"]   — goal node
        inputs["graph"]  — (optional) GraphAdapter; uses stored adapter if absent
    returns:
        BlockResult with output={"path": list, "cost": float, "expansions": int}
    """

    def __init__(self, graph: Optional[GraphAdapter] = None, name: str = "PLAN") -> None:
        super().__init__(name)
        self._graph = graph

    def _do_tick(self, inputs: Dict[str, Any]) -> BlockResult:
        graph = inputs.get("graph", self._graph)
        if graph is None:
            return BlockResult(
                status=BlockStatus.FAILURE,
                message="No graph adapter provided",
            )

        start = inputs["start"]
        goal = inputs["goal"]
        max_exp = inputs.get("max_expansions", 50_000)

        path = a_star_search(graph, start, goal, max_expansions=max_exp)

        if path is None:
            return BlockResult(
                status=BlockStatus.FAILURE,
                output={"path": [], "cost": float("inf")},
                message="No path found",
            )

        cost = 0.0
        for i in range(len(path) - 1):
            cost += graph.cost(path[i], path[i + 1])

        return BlockResult(
            status=BlockStatus.SUCCESS,
            output={"path": path, "cost": cost, "steps": len(path)},
        )

    def _do_configure(self, params: Dict[str, Any]) -> None:
        if "graph" in params:
            self._graph = params["graph"]
