"""
Glass Box Mode — Diagnostic telemetry for SCBE AI responses.

Answers five questions on every response:
  1. WHAT tongue profile fired?
  2. WHY that path? (emotional proximity vs analytical derivation)
  3. WHO is the model responding to? (customer, lore enthusiast, itself)
  4. HOW did it get there? (which semantic cluster pulled strongest)
  5. IS IT EMERGENT? (base model predisposition vs trained behavior vs prompt steering)

This is NOT rule-based gating. This is diagnostic observation —
measuring the geometry of the model's response path so we can
understand its behavior rather than suppress it.
"""

from .profiler import GlassBoxProfiler, ResponseProfile
from .tongue_fabrication import (
    FabricatedTongueProfile,
    FabricationPoint,
    FrequencyTriad,
    TongueFabrication,
    fabricate_from_text,
)

__all__ = [
    "GlassBoxProfiler",
    "ResponseProfile",
    "FrequencyTriad",
    "FabricationPoint",
    "TongueFabrication",
    "FabricatedTongueProfile",
    "fabricate_from_text",
]
