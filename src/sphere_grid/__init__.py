"""
SCBE Sphere Grid — FFX-style auto-generated skill tree backed by 21D CanonicalState.

One system, three interpretations:
  1. Agent interface: skill routing and governance-gated orchestration
  2. Game interface: FFX Sphere Grid visual progression
  3. Security interface: geometric impossibility enforcement

Modules:
  canonical_state  — 21D state vector, ds², harmonic wall, factories
  grid_generator   — auto-generate grid topology from operational telemetry
  grid_navigator   — A* pathfinding on hyperbolic manifold
  skill_registry   — discover and index all skills as grid nodes
"""

from .canonical_state import (
    CanonicalState,
    compute_ds_squared,
    harmonic_wall_cost,
    compute_rho_e,
    make_creature_state,
    make_player_state,
)
