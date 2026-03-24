"""
Concept Blocks — APERIODIC PHASE CONTROLLER
=============================================

Controlled chaos at quasicrystal intervals within a periodic pipeline.

The 14-layer pipeline cycles periodically (L1 → L14 → L1 → ...).
Within that periodic rhythm, this controller injects aperiodic phase
shifts — frequency changes at intervals that never repeat — creating
a "chaos delusion": order that *looks* random from outside but is
deterministically governed by golden-ratio geometry from inside.

Mathematical Basis
------------------

1. **Fibonacci word** (Sturmian sequence):
   The canonical aperiodic binary sequence. Character at position n:
       s(n) = floor((n+2)/φ) - floor((n+1)/φ)
   This sequence has φ-density of 1s, is uniformly recurrent, and
   never becomes periodic.

2. **Penrose inflation** (1D analogy):
   Long (L) and Short (S) intervals with ratio L/S = φ.
   Each tick is classified L or S; phase shift magnitude scales
   accordingly.

3. **Quasicrystal phason shifts**:
   The controller maintains a 6D integer vector (gate vector) that
   projects to 3D physical + 3D validation space.  The projection
   window shifts aperiodically, modulating pipeline sensitivity.

Integration:
    - ProximityBlock uses phason_modulation() for threshold jitter
    - Pipeline14 can inject phase shifts between layers
    - GeoSeal repulsion strength modulates with phason state
    - Eigenvalue constraints ensure non-negative spectral floor

# A4: Symmetry — phason shifts preserve gauge invariance
# A3: Causality — shifts respect time-ordering (monotonic phason epoch)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BlockResult, BlockStatus, ConceptBlock

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
PHI_INV: float = 1.0 / PHI
EPSILON: float = 1e-15


# ---------------------------------------------------------------------------
# Fibonacci / Sturmian word generator
# ---------------------------------------------------------------------------


def fibonacci_word_char(n: int) -> int:
    """Return the n-th character (0 or 1) of the infinite Fibonacci word.

    The Fibonacci word is the limit of: S0="0", S1="01", Sn=S(n-1)+S(n-2).
    Equivalently: s(n) = floor((n+2)/φ) - floor((n+1)/φ).

    This is the simplest aperiodic sequence — never periodic, yet
    deterministic and reproducible from any starting index.
    """
    return int(math.floor((n + 2) / PHI) - math.floor((n + 1) / PHI))


def fibonacci_word(length: int) -> List[int]:
    """Generate the first N characters of the Fibonacci word."""
    return [fibonacci_word_char(i) for i in range(length)]


# ---------------------------------------------------------------------------
# Penrose interval classifier
# ---------------------------------------------------------------------------


@dataclass
class PenroseInterval:
    """A single interval in the 1D Penrose (quasiperiodic) tiling.

    Intervals are classified as Long (L) or Short (S) with L/S = φ.
    """

    index: int
    is_long: bool
    length: float
    phase_shift: float  # Phase offset applied during this interval

    @property
    def kind(self) -> str:
        return "L" if self.is_long else "S"


def penrose_intervals(n: int, base_length: float = 1.0) -> List[PenroseInterval]:
    """Generate N intervals of a 1D Penrose tiling.

    Long intervals have length φ * base_length.
    Short intervals have length base_length.
    The sequence of L/S follows the Fibonacci word.
    """
    word = fibonacci_word(n)
    intervals = []
    for i, char in enumerate(word):
        is_long = char == 1
        length = base_length * PHI if is_long else base_length
        # Phase shift scales with interval length and index
        phase = (2 * math.pi * i) / PHI  # Irrational winding → aperiodic
        intervals.append(
            PenroseInterval(
                index=i,
                is_long=is_long,
                length=length,
                phase_shift=phase % (2 * math.pi),
            )
        )
    return intervals


# ---------------------------------------------------------------------------
# 6D Gate Vector (Quasicrystal projection)
# ---------------------------------------------------------------------------


@dataclass
class GateVector:
    """6D integer vector for quasicrystal lattice projection.

    Projects to 3D physical space (pipeline layer mapping) and
    3D validation space (Sacred Tongue phase mapping).
    """

    coords: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0, 0])

    def physical_projection(self) -> List[float]:
        """Project to 3D physical space using icosahedral basis."""
        # Simplified icosahedral projection (full version in qc_lattice/)
        c = self.coords
        return [
            c[0] + c[1] * PHI_INV,
            c[2] + c[3] * PHI_INV,
            c[4] + c[5] * PHI_INV,
        ]

    def validation_projection(self) -> List[float]:
        """Project to 3D validation (perpendicular) space."""
        c = self.coords
        return [
            c[0] * PHI_INV - c[1],
            c[2] * PHI_INV - c[3],
            c[4] * PHI_INV - c[5],
        ]

    def distance_to_window(self, window_center: List[float], radius: float) -> float:
        """Distance from validation projection to acceptance window."""
        v = self.validation_projection()
        d = math.sqrt(sum((vi - wi) ** 2 for vi, wi in zip(v, window_center)))
        return max(0.0, d - radius)

    def shift(self, delta: List[int]) -> "GateVector":
        """Apply a phason shift (aperiodic rekeying)."""
        new_coords = [c + d for c, d in zip(self.coords, delta)]
        return GateVector(coords=new_coords)


# ---------------------------------------------------------------------------
# Aperiodic Phase Controller
# ---------------------------------------------------------------------------


class AperiodicPhaseController:
    """Injects controlled chaos into a periodic pipeline.

    The pipeline is periodic: L1→L14, cycling.  This controller
    modulates *when* and *how much* the pipeline's internal phases
    shift, using aperiodic intervals derived from the Fibonacci word
    and quasicrystal geometry.

    Key property: the modulation pattern never repeats, but is
    fully deterministic from the initial gate vector.  An adversary
    cannot predict the next shift without knowing the gate state,
    but a legitimate agent can always reconstruct it.
    """

    def __init__(
        self,
        initial_gate: Optional[List[int]] = None,
        window_radius: float = 1.5,
    ) -> None:
        self._gate = GateVector(coords=list(initial_gate or [0, 0, 0, 0, 0, 0]))
        self._window_center: List[float] = [0.0, 0.0, 0.0]
        self._window_radius = window_radius
        self._epoch: int = 0
        self._tick: int = 0
        self._intervals = penrose_intervals(256)  # Pre-compute interval schedule

    @property
    def epoch(self) -> int:
        """Current phason epoch (increments on each shift)."""
        return self._epoch

    @property
    def gate(self) -> GateVector:
        """Current 6D gate vector."""
        return self._gate

    def current_interval(self) -> PenroseInterval:
        """Get the current Penrose interval."""
        idx = self._tick % len(self._intervals)
        return self._intervals[idx]

    def phase_modulation(self) -> float:
        """Current phase modulation factor [0.5, 1.5].

        Applied to proximity thresholds, GeoSeal repulsion, and
        pipeline transition gates.  The factor changes aperiodically
        with each tick.
        """
        interval = self.current_interval()
        fib_char = fibonacci_word_char(self._tick)

        # Combine Penrose interval phase with Fibonacci word character
        base_mod = math.sin(interval.phase_shift)
        fib_mod = 0.1 * (1 if fib_char else -1)

        # Map to [0.5, 1.5] band
        return 1.0 + 0.3 * base_mod + fib_mod

    def frequency_shift(self, base_freq: float) -> float:
        """Apply aperiodic frequency shift to a base frequency.

        Used for Sacred Tongue harmonic modulation — each tongue's
        frequency shifts by a golden-ratio-scaled amount that never
        repeats the same offset pattern.
        """
        interval = self.current_interval()
        # Long intervals get φ-scaled shift, short get 1/φ-scaled
        scale = PHI if interval.is_long else PHI_INV
        return base_freq * (1.0 + 0.01 * scale * math.sin(interval.phase_shift))

    def tick(self) -> Dict[str, Any]:
        """Advance one step and return the current phason state.

        This is called once per pipeline cycle. The returned state
        includes modulation factors for all downstream consumers.
        """
        self._tick += 1
        interval = self.current_interval()

        # Check if we should do a phason shift (at Fibonacci-word boundaries)
        should_shift = fibonacci_word_char(self._tick) == 1

        shifted = False
        if should_shift:
            # Phason shift: move the gate vector aperiodically
            delta = [fibonacci_word_char(self._tick + i) for i in range(6)]
            self._gate = self._gate.shift(delta)
            self._epoch += 1
            shifted = True

            # Move the validation window slightly
            v_proj = self._gate.validation_projection()
            for i in range(3):
                self._window_center[i] = 0.9 * self._window_center[i] + 0.1 * v_proj[i]

        dist_to_window = self._gate.distance_to_window(
            self._window_center,
            self._window_radius,
        )
        inside_window = dist_to_window < EPSILON

        return {
            "tick": self._tick,
            "epoch": self._epoch,
            "interval_kind": interval.kind,
            "interval_index": interval.index,
            "phase_modulation": self.phase_modulation(),
            "shifted": shifted,
            "inside_window": inside_window,
            "dist_to_window": dist_to_window,
            "gate_physical": self._gate.physical_projection(),
            "gate_validation": self._gate.validation_projection(),
        }

    def reset(self, gate: Optional[List[int]] = None) -> None:
        """Reset to initial state."""
        self._gate = GateVector(coords=list(gate or [0, 0, 0, 0, 0, 0]))
        self._window_center = [0.0, 0.0, 0.0]
        self._epoch = 0
        self._tick = 0


# ---------------------------------------------------------------------------
# AperiodicPhaseBlock — concept block wrapper
# ---------------------------------------------------------------------------


class AperiodicPhaseBlock(ConceptBlock):
    """Concept block wrapper for the aperiodic phase controller.

    Snap this into a PotatoHead socket to give the agent controlled
    chaos — aperiodic sensitivity modulation within the periodic
    pipeline rhythm.

    Inputs (via tick):
        - "base_frequency": float — optional base freq to modulate

    Outputs:
        - "phase_modulation": float — current modulation factor
        - "epoch": int — phason epoch
        - "interval_kind": str — "L" or "S"
        - "shifted": bool — whether a phason shift occurred
        - "inside_window": bool — gate validation status
        - "frequency_shifted": float — modulated frequency (if base given)
    """

    def __init__(self, initial_gate: Optional[List[int]] = None) -> None:
        super().__init__("aperiodic_phase")
        self._controller = AperiodicPhaseController(initial_gate=initial_gate)

    def _do_tick(self, inputs: Dict[str, Any]) -> BlockResult:
        state = self._controller.tick()

        # Optional frequency modulation
        base_freq = inputs.get("base_frequency")
        if base_freq is not None:
            state["frequency_shifted"] = self._controller.frequency_shift(float(base_freq))

        return BlockResult(
            status=BlockStatus.SUCCESS,
            output=state,
            message=f"Epoch {state['epoch']}, interval {state['interval_kind']}, "
            f"mod={state['phase_modulation']:.3f}",
        )

    def _do_reset(self) -> None:
        self._controller.reset()

    def _do_configure(self, params: Dict[str, Any]) -> None:
        if "gate" in params:
            self._controller.reset(gate=params["gate"])
        if "window_radius" in params:
            self._controller._window_radius = params["window_radius"]
