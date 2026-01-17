"""
Axiom-Grouped Module for SCBE-AETHERMOORE 14-Layer Pipeline

This module organizes the 14-layer governance pipeline by quantum axioms,
providing a principled categorization based on the mathematical properties
each layer satisfies.

Axiom Categories:
=================

1. UNITARITY AXIOM (Norm Preservation)
   - Layer 2: Realification (ℂᴰ → ℝ²ᴰ isometry)
   - Layer 4: Poincaré Embedding (direction-preserving)
   - Layer 7: Phase Transform (Möbius isometry)

2. LOCALITY AXIOM (Spatially-Bounded Operations)
   - Layer 3: Weighted Transform (diagonal metric)
   - Layer 8: Multi-Well Realms (bounded interaction)

3. CAUSALITY AXIOM (Time-Ordered Transforms)
   - Layer 6: Breathing Transform (time-dependent)
   - Layer 11: Triadic Temporal Distance
   - Layer 13: Decision & Risk Assessment

4. SYMMETRY AXIOM (Gauge Invariance)
   - Layer 5: Hyperbolic Distance (Möbius-invariant)
   - Layer 9: Spectral Coherence (O(n)-invariant)
   - Layer 10: Spin Coherence (U(1)-invariant)
   - Layer 12: Harmonic Scaling (order-preserving)

5. COMPOSITION AXIOM (Layer Composition Rules)
   - Layer 1: Complex Context State (entry point)
   - Layer 14: Audio Axis (exit point)

Layer-to-Axiom Mapping:
=======================
L1  → COMPOSITION (entry)
L2  → UNITARITY
L3  → LOCALITY
L4  → UNITARITY
L5  → SYMMETRY
L6  → CAUSALITY
L7  → UNITARITY
L8  → LOCALITY
L9  → SYMMETRY
L10 → SYMMETRY
L11 → CAUSALITY
L12 → SYMMETRY
L13 → CAUSALITY
L14 → COMPOSITION (exit)

Usage:
======
    from symphonic_cipher.scbe_aethermoore.axiom_grouped import (
        LAYER_TO_AXIOM,
        get_layer_axiom,
        get_axiom_layers,
        AxiomAwarePipeline,
    )

    # Get axiom for a layer
    axiom = get_layer_axiom(5)  # Returns "symmetry"

    # Get all layers for an axiom
    layers = get_axiom_layers("unitarity")  # Returns [2, 4, 7]

    # Execute full pipeline with axiom checking
    pipeline = AxiomAwarePipeline()
    output, states = pipeline.execute(context, t=0.0)
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass

# Import axiom modules
from . import unitarity_axiom
from . import locality_axiom
from . import causality_axiom
from . import symmetry_axiom
from . import composition_axiom


# ============================================================================
# Axiom Enumeration
# ============================================================================

class QuantumAxiom(Enum):
    """The five quantum axioms organizing the 14-layer pipeline."""
    UNITARITY = "unitarity"      # Norm preservation
    LOCALITY = "locality"        # Spatially-bounded
    CAUSALITY = "causality"      # Time-ordered
    SYMMETRY = "symmetry"        # Gauge invariance
    COMPOSITION = "composition"  # Layer composition


# ============================================================================
# Layer-to-Axiom Mapping
# ============================================================================

LAYER_TO_AXIOM: Dict[int, QuantumAxiom] = {
    1: QuantumAxiom.COMPOSITION,  # Entry point
    2: QuantumAxiom.UNITARITY,    # Realification (isometry)
    3: QuantumAxiom.LOCALITY,     # Weighted Transform (diagonal)
    4: QuantumAxiom.UNITARITY,    # Poincaré Embedding
    5: QuantumAxiom.SYMMETRY,     # Hyperbolic Distance (THE INVARIANT)
    6: QuantumAxiom.CAUSALITY,    # Breathing Transform (time-dep)
    7: QuantumAxiom.UNITARITY,    # Phase Transform (Möbius)
    8: QuantumAxiom.LOCALITY,     # Multi-Well Realms
    9: QuantumAxiom.SYMMETRY,     # Spectral Coherence
    10: QuantumAxiom.SYMMETRY,    # Spin Coherence
    11: QuantumAxiom.CAUSALITY,   # Triadic Temporal Distance
    12: QuantumAxiom.SYMMETRY,    # Harmonic Scaling
    13: QuantumAxiom.CAUSALITY,   # Decision Pipeline
    14: QuantumAxiom.COMPOSITION, # Exit point
}

# Reverse mapping: axiom -> layers
AXIOM_TO_LAYERS: Dict[QuantumAxiom, List[int]] = {
    QuantumAxiom.UNITARITY: [2, 4, 7],
    QuantumAxiom.LOCALITY: [3, 8],
    QuantumAxiom.CAUSALITY: [6, 11, 13],
    QuantumAxiom.SYMMETRY: [5, 9, 10, 12],
    QuantumAxiom.COMPOSITION: [1, 14],
}


def get_layer_axiom(layer_num: int) -> str:
    """
    Get the primary axiom for a layer.

    Args:
        layer_num: Layer number (1-14)

    Returns:
        Axiom name as string
    """
    if layer_num not in LAYER_TO_AXIOM:
        raise ValueError(f"Invalid layer number: {layer_num}. Must be 1-14.")
    return LAYER_TO_AXIOM[layer_num].value


def get_axiom_layers(axiom: str) -> List[int]:
    """
    Get all layers satisfying a given axiom.

    Args:
        axiom: Axiom name ("unitarity", "locality", "causality",
               "symmetry", or "composition")

    Returns:
        List of layer numbers
    """
    try:
        axiom_enum = QuantumAxiom(axiom.lower())
    except ValueError:
        raise ValueError(
            f"Unknown axiom: {axiom}. Must be one of: "
            f"{[a.value for a in QuantumAxiom]}"
        )
    return AXIOM_TO_LAYERS[axiom_enum]


# ============================================================================
# Layer Registry
# ============================================================================

@dataclass
class LayerInfo:
    """Complete information about a layer."""
    number: int
    name: str
    axiom: QuantumAxiom
    function: Callable
    inverse: Optional[Callable]
    description: str
    module: str


def get_layer_info(layer_num: int) -> LayerInfo:
    """Get complete information about a layer."""
    if layer_num not in LAYER_TO_AXIOM:
        raise ValueError(f"Invalid layer number: {layer_num}")

    axiom = LAYER_TO_AXIOM[layer_num]

    # Get from appropriate module
    if axiom == QuantumAxiom.UNITARITY:
        info = unitarity_axiom.UNITARITY_LAYERS[layer_num]
        module = "unitarity_axiom"
    elif axiom == QuantumAxiom.LOCALITY:
        info = locality_axiom.LOCALITY_LAYERS[layer_num]
        module = "locality_axiom"
    elif axiom == QuantumAxiom.CAUSALITY:
        info = causality_axiom.CAUSALITY_LAYERS[layer_num]
        module = "causality_axiom"
    elif axiom == QuantumAxiom.SYMMETRY:
        info = symmetry_axiom.SYMMETRY_LAYERS[layer_num]
        module = "symmetry_axiom"
    else:  # COMPOSITION
        info = composition_axiom.COMPOSITION_LAYERS[layer_num]
        module = "composition_axiom"

    return LayerInfo(
        number=layer_num,
        name=info["name"],
        axiom=axiom,
        function=info["function"],
        inverse=info.get("inverse"),
        description=info["description"],
        module=module
    )


def get_all_layers() -> Dict[int, LayerInfo]:
    """Get information about all 14 layers."""
    return {i: get_layer_info(i) for i in range(1, 15)}


# ============================================================================
# Axiom-Checking Decorators (Re-exported)
# ============================================================================

# Unitarity axiom decorator
unitarity_check = unitarity_axiom.unitarity_check

# Locality axiom decorator
locality_check = locality_axiom.locality_check

# Causality axiom decorator
causality_check = causality_axiom.causality_check

# Symmetry axiom decorator
symmetry_check = symmetry_axiom.symmetry_check

# Composition axiom decorator
composition_check = composition_axiom.composition_check


# ============================================================================
# Pipeline Execution (Re-exported)
# ============================================================================

# Full axiom-aware pipeline
AxiomAwarePipeline = composition_axiom.AxiomAwarePipeline

# Context input structure
ContextInput = composition_axiom.ContextInput

# Pipeline composition utilities
Pipeline = composition_axiom.Pipeline
compose = composition_axiom.compose
pipe = composition_axiom.pipe


# ============================================================================
# Verification Utilities
# ============================================================================

def verify_all_axioms(verbose: bool = False) -> Dict[str, bool]:
    """
    Verify all axioms across all layers.

    Returns:
        Dictionary mapping axiom names to verification results
    """
    results = {}

    # Unitarity
    u_passed = True
    for layer_num in AXIOM_TO_LAYERS[QuantumAxiom.UNITARITY]:
        info = unitarity_axiom.UNITARITY_LAYERS[layer_num]
        passed, _ = unitarity_axiom.verify_layer_unitarity(info["function"])
        u_passed = u_passed and passed
        if verbose and not passed:
            print(f"  Layer {layer_num} failed unitarity check")
    results["unitarity"] = u_passed

    # Locality
    l_passed = True
    for layer_num in AXIOM_TO_LAYERS[QuantumAxiom.LOCALITY]:
        info = locality_axiom.LOCALITY_LAYERS[layer_num]
        passed, _ = locality_axiom.verify_layer_locality(info["function"])
        l_passed = l_passed and passed
        if verbose and not passed:
            print(f"  Layer {layer_num} failed locality check")
    results["locality"] = l_passed

    # Causality
    c_passed = True
    for layer_num in AXIOM_TO_LAYERS[QuantumAxiom.CAUSALITY]:
        info = causality_axiom.CAUSALITY_LAYERS[layer_num]
        passed, _ = causality_axiom.verify_layer_causality(info["function"])
        c_passed = c_passed and passed
        if verbose and not passed:
            print(f"  Layer {layer_num} failed causality check")
    results["causality"] = c_passed

    # Symmetry
    s_passed = True
    for layer_num in AXIOM_TO_LAYERS[QuantumAxiom.SYMMETRY]:
        info = symmetry_axiom.SYMMETRY_LAYERS[layer_num]
        passed, _ = symmetry_axiom.verify_layer_symmetry(info["function"])
        s_passed = s_passed and passed
        if verbose and not passed:
            print(f"  Layer {layer_num} failed symmetry check")
    results["symmetry"] = s_passed

    # Composition
    comp_passed, issues = composition_axiom.verify_pipeline_composition()
    if verbose and not comp_passed:
        for issue in issues:
            print(f"  Composition issue: {issue}")
    results["composition"] = comp_passed

    return results


def print_layer_mapping() -> None:
    """Print the layer-to-axiom mapping in a formatted table."""
    print("\n" + "=" * 60)
    print("SCBE-AETHERMOORE 14-Layer Pipeline: Axiom Mapping")
    print("=" * 60)

    print("\n{:<6} {:<25} {:<15}".format("Layer", "Name", "Axiom"))
    print("-" * 60)

    for layer_num in range(1, 15):
        info = get_layer_info(layer_num)
        print("{:<6} {:<25} {:<15}".format(
            f"L{layer_num}",
            info.name[:24],
            info.axiom.value.upper()
        ))

    print("-" * 60)
    print("\nAxiom Summary:")
    for axiom in QuantumAxiom:
        layers = AXIOM_TO_LAYERS[axiom]
        print(f"  {axiom.value.upper():12} → Layers {layers}")


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Enums
    "QuantumAxiom",

    # Mappings
    "LAYER_TO_AXIOM",
    "AXIOM_TO_LAYERS",

    # Query functions
    "get_layer_axiom",
    "get_axiom_layers",
    "get_layer_info",
    "get_all_layers",

    # Decorators
    "unitarity_check",
    "locality_check",
    "causality_check",
    "symmetry_check",
    "composition_check",

    # Pipeline
    "AxiomAwarePipeline",
    "ContextInput",
    "Pipeline",
    "compose",
    "pipe",

    # Verification
    "verify_all_axioms",
    "print_layer_mapping",

    # Submodules
    "unitarity_axiom",
    "locality_axiom",
    "causality_axiom",
    "symmetry_axiom",
    "composition_axiom",
]
