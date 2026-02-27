"""Rosetta-LCDA: Multilingual Concept Mapping + Linguistic Dimensional Analysis.

Provides:
  - RosettaStone: concept mapping across natural languages, conlangs, and Sacred Tongues
  - LCDAProjector: custom embedding dimensions for SCBE governance properties
  - DualEntropicDefenseEngine: dual entropy channels for anomaly detection
  - LanguageGraph: weighted relationship graph between language systems
"""

from .rosetta_core import RosettaStone, RosettaConcept, LanguageSystem
from .lcda import LCDAProjector, LCDADimension
from .dede import DualEntropicDefenseEngine, DEDESignal
from .language_graph import LanguageGraph

__all__ = [
    "RosettaStone",
    "RosettaConcept",
    "LanguageSystem",
    "LCDAProjector",
    "LCDADimension",
    "DualEntropicDefenseEngine",
    "DEDESignal",
    "LanguageGraph",
]
