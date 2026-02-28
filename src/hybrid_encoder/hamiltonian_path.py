"""Hamiltonian Path Constraint -- no-repeat traversal through ternary lattice.

In the 6-trit Sacred Tongue space, there are 3^6 = 729 possible states.
A Hamiltonian path visits each state exactly once.  This constraint
ensures that repeated governance decisions don't create loops that
an adversary could exploit.

The encoder tracks visited states.  If a state has been visited,
it reports a traversal violation:
  - ALLOW: fresh state, never seen
  - QUARANTINE: state visited recently (within sliding window)
  - DENY: state visited too many times (replay attack signal)

This connects to the QuasicrystalLattice's defect detection:
forced periodicity (revisiting states) IS the same signal as
crystalline defects.

@layer Layer 5, Layer 9
@component HybridEncoder.HamiltonianPath
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Literal, Tuple

Decision = Literal["ALLOW", "QUARANTINE", "DENY"]

# Total states in 6-trit space
_TOTAL_STATES = 3 ** 6  # 729

# Thresholds for replay detection
_QUARANTINE_VISITS = 2
_DENY_VISITS = 4


class HamiltonianTraversal:
    """Track trit-state visits and enforce no-repeat traversal."""

    def __init__(self, window_size: int = _TOTAL_STATES):
        """Args:
            window_size: Sliding window of recent states (default 729).
        """
        self._visit_counts: Dict[Tuple[int, ...], int] = {}
        self._recent: OrderedDict[Tuple[int, ...], int] = OrderedDict()
        self._window_size = window_size

    def check(self, tongue_trits: List[int]) -> Tuple[bool, Decision, int]:
        """Check if this trit-state has been visited.

        Returns:
            (is_valid, suggested_decision, visit_count)

        is_valid:           True if this is a fresh state
        suggested_decision: ALLOW/QUARANTINE/DENY based on visit count
        visit_count:        how many times this state has been visited
        """
        key = tuple(tongue_trits[:6])
        count = self._visit_counts.get(key, 0)

        if count == 0:
            return True, "ALLOW", 0
        elif count < _DENY_VISITS:
            return False, "QUARANTINE", count
        else:
            return False, "DENY", count

    def record(self, tongue_trits: List[int]) -> None:
        """Record a visit to this trit-state."""
        key = tuple(tongue_trits[:6])

        # Update visit count
        self._visit_counts[key] = self._visit_counts.get(key, 0) + 1

        # Update recency window
        if key in self._recent:
            self._recent.move_to_end(key)
        else:
            self._recent[key] = 1

        # Evict oldest if window exceeded
        while len(self._recent) > self._window_size:
            evicted, _ = self._recent.popitem(last=False)
            if evicted in self._visit_counts:
                self._visit_counts[evicted] = max(0, self._visit_counts[evicted] - 1)
                if self._visit_counts[evicted] == 0:
                    del self._visit_counts[evicted]

    @property
    def unique_states_visited(self) -> int:
        """Number of unique states visited so far."""
        return len(self._visit_counts)

    @property
    def coverage(self) -> float:
        """Fraction of total state space covered (out of 729)."""
        return self.unique_states_visited / _TOTAL_STATES

    def reset(self) -> None:
        """Reset traversal history."""
        self._visit_counts.clear()
        self._recent.clear()
