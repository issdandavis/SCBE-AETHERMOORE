"""SCBE DSL package: 8-primitive naming contract over the 14-layer substrate.

See artifacts/blind_spot_ledger/lanes/L_dsl_synthesis.md for the lane spec.
"""

from .primitives import (
    GRID_SIZE,
    GridState,
    Op,
    PRIMITIVE_TABLE,
    breath,
    compose,
    initial_state,
    mobius_phase,
    name_of,
    parse_program,
    phi_weight,
    run_program,
    seal,
    tongue_shift,
    vote,
    well_select,
)

__all__ = [
    "GRID_SIZE",
    "GridState",
    "Op",
    "PRIMITIVE_TABLE",
    "breath",
    "compose",
    "initial_state",
    "mobius_phase",
    "name_of",
    "parse_program",
    "phi_weight",
    "run_program",
    "seal",
    "tongue_shift",
    "vote",
    "well_select",
]
