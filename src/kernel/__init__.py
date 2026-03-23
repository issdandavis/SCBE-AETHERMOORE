"""
SCBE Dual-Core Memory Kernel
==============================

GeoKernel (brainstem) + MemoryLattice (spinal cord)
with 7 memory layers and quasi-lattice bridge.
"""

from src.kernel.dual_core import (
    DualCoreKernel,
    GeoKernel,
    MemoryLattice,
    MemoryLayer,
    MemoryEntry,
    KernelStack,
    PHDMClassifier,
    quasi_project,
    ICO_MATRIX,
)

__all__ = [
    "DualCoreKernel",
    "GeoKernel",
    "MemoryLattice",
    "MemoryLayer",
    "MemoryEntry",
    "KernelStack",
    "PHDMClassifier",
    "quasi_project",
    "ICO_MATRIX",
]
