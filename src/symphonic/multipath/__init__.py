"""Multipath encoder — Prism->Rainbow->Beam.

One source function -> canonical FnIR -> 6 parallel tongue emissions.
"""

from .band import CellArbitration, arbitrate_cell, closure_check, summarize_closure
from ._trit_common import TritTable, ReducerMeta, PHI_WEIGHTS, TONGUE_NAMES
from .trit_table_KO import TABLE as KO_TABLE
from .trit_table_AV import TABLE as AV_TABLE
from .trit_table_RU import TABLE as RU_TABLE
from .trit_table_UM import TABLE as UM_TABLE
from .trit_table_DR import TABLE as DR_TABLE
from . import trit_table_CA as _ca_module

# CA predates the shared TritTable scaffold and exposes matrices at
# module level. Expose it as a namespace for uniform access.
CA_TABLE = _ca_module

TRIT_TABLES = {
    "KO": KO_TABLE,
    "AV": AV_TABLE,
    "RU": RU_TABLE,
    "CA": CA_TABLE,
    "UM": UM_TABLE,
    "DR": DR_TABLE,
}

__all__ = [
    "CellArbitration",
    "arbitrate_cell",
    "closure_check",
    "summarize_closure",
    "TritTable",
    "ReducerMeta",
    "PHI_WEIGHTS",
    "TONGUE_NAMES",
    "KO_TABLE",
    "AV_TABLE",
    "RU_TABLE",
    "CA_TABLE",
    "UM_TABLE",
    "DR_TABLE",
    "TRIT_TABLES",
]
