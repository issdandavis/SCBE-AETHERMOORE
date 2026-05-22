"""Go-board narrative engine: a domain-agnostic legality kernel + a narrative-combat adapter.

The kernel (`kernel.Board`) decides legality; callers only propose moves. This is the
publishable core of the "SCBE Board Kernel" idea — no domain words, no SCBE imports.
"""

from .kernel import Board, IllegalMove, MoveResult, Observation

__all__ = ["Board", "IllegalMove", "MoveResult", "Observation"]
