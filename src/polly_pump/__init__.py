"""Polly Pump — inference-time state retrieval, routing, and pre-stabilization.

The pump is the missing layer between accumulated knowledge (groundwater)
and Polly's speech (the lips). It turns tongue profiles and null patterns
into live behavior by:

1. SENSE  — profile the user's input (tongue coords, null pattern, geometry)
2. LOCATE — find the input's neighborhood in the aquifer
3. LIFT   — retrieve the right latent bundles
4. COMPOSE — build a structured pre-state for the model
5. RESPOND — model answers from the lifted bundle, not generic drift

Components:
- PumpPacket: compact state record attached to each query
- BundleRetriever: given a packet, pull nearest bundles from the aquifer
- ResponseStabilizer: compose one structured context block before generation
"""

from .packet import PumpPacket, sense
from .retriever import BundleRetriever, RetrievedBundle
from .stabilizer import stabilize
from .compiler import CompiledEvent, compile_event, compile_messages, compile_batch

__all__ = [
    "PumpPacket",
    "sense",
    "BundleRetriever",
    "RetrievedBundle",
    "stabilize",
    "CompiledEvent",
    "compile_event",
    "compile_messages",
    "compile_batch",
]
