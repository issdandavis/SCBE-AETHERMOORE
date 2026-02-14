"""
Multimodal Matrix (MMX) — Cross-modal coherence tensor for governance.

Layer 9.5: Sits between spectral coherence (L9-10) and harmonic scaling (L12).
Computes alignment, reliability, and governance scalars across modalities.
"""

from .mmx import compute_mmx, MMXResult

__all__ = ["compute_mmx", "MMXResult"]
