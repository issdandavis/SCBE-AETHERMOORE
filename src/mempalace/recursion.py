from __future__ import annotations

from collections import deque
from typing import Callable, Dict, Iterable, List, Optional, Set, TypeVar

from src.mempalace.rooms import Room

PHI = (1 + 5 ** 0.5) / 2
T = TypeVar("T")


def _corridor_targets(room: Room) -> Iterable[int]:
    for targets in room.corridors.values():
        for target in targets:
            yield target


def walk_dfs(
    palace: Dict[int, Room],
    start: int,
    visited: Optional[Set[int]] = None,
) -> Set[int]:
    """Classic recursive depth-first walk. Memoized via a shared visited set."""
    if visited is None:
        visited = set()
    if start in visited or start not in palace:
        return visited
    visited.add(start)
    for next_id in _corridor_targets(palace[start]):
        walk_dfs(palace, next_id, visited)
    return visited


def walk_bfs(palace: Dict[int, Room], start: int) -> List[int]:
    """Queue-based breadth-first walk returning visit order."""
    if start not in palace:
        return []
    visited: Set[int] = {start}
    queue: deque[int] = deque([start])
    order: List[int] = []
    while queue:
        current = queue.popleft()
        order.append(current)
        for next_id in _corridor_targets(palace[current]):
            if next_id not in visited:
                visited.add(next_id)
                queue.append(next_id)
    return order


def zoom(
    palace: Dict[int, Room],
    start: int,
    depth: int,
    fn: Callable[[Room], T],
    visited: Optional[Set[int]] = None,
) -> List[T]:
    """Tree recursion: apply fn on each room reachable within depth hops."""
    if visited is None:
        visited = set()
    if depth < 0 or start in visited or start not in palace:
        return []
    visited.add(start)
    results: List[T] = [fn(palace[start])]
    for next_id in _corridor_targets(palace[start]):
        results.extend(zoom(palace, next_id, depth - 1, fn, visited))
    return results


def settle(
    palace: Dict[int, Room],
    start: int,
    iterations: int = 500,
    tol: float = 1e-10,
) -> Dict[int, float]:
    """Banach fixed-point iteration with phi-convex damping.
    Converges to the normalized dominant eigenvector of the neighbor-averaging map."""
    damp = 1.0 / PHI
    flow = 1.0 - damp  # 1/phi^2
    state: Dict[int, float] = {rid: 0.0 for rid in palace}
    state[start] = 1.0
    for _ in range(iterations):
        new_state: Dict[int, float] = {}
        for rid, room in palace.items():
            neighbors = list(room.neighbors())
            if neighbors:
                inflow = sum(state[n] for n in neighbors) / len(neighbors)
            else:
                inflow = 0.0
            new_state[rid] = state[rid] * damp + inflow * flow
        total = sum(new_state.values())
        if total > 0:
            new_state = {k: v / total for k, v in new_state.items()}
        delta = max(abs(new_state[k] - state[k]) for k in state)
        state = new_state
        if delta < tol:
            break
    return state


def fold_walk(
    palace: Dict[int, Room],
    start: int,
    fn: Callable[[T, Room], T],
    init: T,
) -> T:
    """Fold/reduce over a depth-first walk via tail-recursive descent."""
    visited: Set[int] = set()

    def _go(rid: int, acc: T) -> T:
        if rid in visited or rid not in palace:
            return acc
        visited.add(rid)
        acc = fn(acc, palace[rid])
        for next_id in _corridor_targets(palace[rid]):
            acc = _go(next_id, acc)
        return acc

    return _go(start, init)
