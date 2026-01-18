"""
Quasicrystal Lattice Module for SCBE-AETHERMOORE

Provides geometric verification using:
- Icosahedral Quasicrystal (aperiodic 6D->3D projection)
- Polyhedral Hamiltonian Defense Manifold (16 canonical polyhedra)
- Integrated HMAC chain binding

Simple Usage:
    from symphonic_cipher.scbe_aethermoore.qc_lattice import quick_validate

    result = quick_validate("user123", "read_data")
    print(result.decision)  # ALLOW, DENY, QUARANTINE, or SNAP

Full Usage:
    from symphonic_cipher.scbe_aethermoore.qc_lattice import (
        IntegratedAuditChain,
        QuasicrystalLattice,
        PHDMHamiltonianPath
    )

    # Create audit chain with PQC
    chain = IntegratedAuditChain(use_pqc=True)

    # Add entries
    validation, signature = chain.add_entry("user", "action")

    # Verify everything
    is_valid, errors = chain.verify_all()
"""

# Quasicrystal Lattice
from .quasicrystal import (
    # Core classes
    QuasicrystalLattice,
    PQCQuasicrystalLattice,

    # Result types
    ValidationResult,
    ValidationStatus,
    LatticePoint,

    # Constants
    PHI,
    TAU,
)

# PHDM (Polyhedral Hamiltonian Defense Manifold)
from .phdm import (
    # Core classes
    Polyhedron,
    PolyhedronType,
    PHDMHamiltonianPath,
    PHDMDeviationDetector,
    HamiltonianNode,

    # Family functions
    get_phdm_family,
    get_family_summary,
    validate_all_polyhedra,

    # Coordinate generators
    create_tetrahedron_coords,
    create_cube_coords,
    create_octahedron_coords,
    create_dodecahedron_coords,
    create_icosahedron_coords,
)

# Integration with HMAC Chain
from .integration import (
    # Main classes
    QuasicrystalHMACChain,
    IntegratedAuditChain,

    # Result types
    IntegratedDecision,
    IntegratedValidation,

    # Convenience functions
    create_integrated_chain,
    quick_validate,

    # Constants
    NONCE_BYTES,
    KEY_LEN,
    AUDIT_CHAIN_IV,
)

__all__ = [
    # Quasicrystal
    "QuasicrystalLattice",
    "PQCQuasicrystalLattice",
    "ValidationResult",
    "ValidationStatus",
    "LatticePoint",
    "PHI",
    "TAU",

    # PHDM
    "Polyhedron",
    "PolyhedronType",
    "PHDMHamiltonianPath",
    "PHDMDeviationDetector",
    "HamiltonianNode",
    "get_phdm_family",
    "get_family_summary",
    "validate_all_polyhedra",
    "create_tetrahedron_coords",
    "create_cube_coords",
    "create_octahedron_coords",
    "create_dodecahedron_coords",
    "create_icosahedron_coords",

    # Integration
    "QuasicrystalHMACChain",
    "IntegratedAuditChain",
    "IntegratedDecision",
    "IntegratedValidation",
    "create_integrated_chain",
    "quick_validate",
    "NONCE_BYTES",
    "KEY_LEN",
    "AUDIT_CHAIN_IV",
]

__version__ = "1.0.0"
