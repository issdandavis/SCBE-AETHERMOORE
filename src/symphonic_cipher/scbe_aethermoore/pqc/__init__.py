"""
PQC Module - Post-Quantum Cryptography for SCBE-AETHERMOORE

Provides quantum-resistant cryptographic primitives using liboqs:
- Kyber768: Key Encapsulation Mechanism (KEM) for secure key exchange
- Dilithium3: Digital signatures for audit chain integrity
- PQC-enhanced HMAC chains for Layer 0 integration
- PQC-signed audit entries for governance audit trails

Falls back gracefully to hashlib-based mock if liboqs is not installed.

Installation:
    pip install liboqs-python

Usage:
    from symphonic_cipher.scbe_aethermoore.pqc import (
        Kyber768, Dilithium3,
        PQCHMACChain, PQCAuditChain,
        is_liboqs_available
    )

    # Check backend
    if is_liboqs_available():
        print("Using liboqs for quantum-resistant crypto")
    else:
        print("Using mock implementation (development mode)")

    # Key encapsulation
    keypair = Kyber768.generate_keypair()
    result = Kyber768.encapsulate(keypair.public_key)

    # Digital signatures
    sig_keypair = Dilithium3.generate_keypair()
    signature = Dilithium3.sign(sig_keypair.secret_key, b"message")

    # PQC HMAC chain
    chain = PQCHMACChain.create_new()
    chain.append(b"entry 1")

    # PQC audit chain
    audit = PQCAuditChain.create_new()
    audit.add_entry("user", "action", AuditDecision.ALLOW)
"""

# Core PQC primitives
from .pqc_core import (
    # Key encapsulation
    Kyber768,
    KyberKeyPair,
    EncapsulationResult,

    # Digital signatures
    Dilithium3,
    DilithiumKeyPair,
    SignatureResult,

    # Backend detection
    PQCBackend,
    get_backend,
    is_liboqs_available,

    # Hybrid key derivation
    derive_hybrid_key,
    generate_pqc_session_keys,
    verify_pqc_session,

    # Constants
    KYBER768_PUBLIC_KEY_SIZE,
    KYBER768_SECRET_KEY_SIZE,
    KYBER768_CIPHERTEXT_SIZE,
    KYBER768_SHARED_SECRET_SIZE,
    DILITHIUM3_PUBLIC_KEY_SIZE,
    DILITHIUM3_SECRET_KEY_SIZE,
    DILITHIUM3_SIGNATURE_SIZE,
)

# PQC HMAC chain (Layer 0 integration)
from .pqc_hmac import (
    # Key derivation
    KeyDerivationMode,
    PQCKeyMaterial,
    PQCHMACState,
    pqc_derive_hmac_key,
    pqc_recover_hmac_key,

    # HMAC chain operations
    pqc_hmac_chain_tag,
    pqc_verify_hmac_chain,
    PQCHMACChain,

    # State management
    create_pqc_hmac_state,
    migrate_classical_chain,

    # Constants
    NONCE_BYTES,
    KEY_LEN,
    AUDIT_CHAIN_IV,
)

# PQC Harmonic Enhancement (AETHERMOORE integration)
from .pqc_harmonic import (
    SecurityDimension,
    HarmonicKeyMaterial,
    harmonic_key_stretch,
    fast_harmonic_key,
    HarmonicPQCSession,
    create_harmonic_pqc_session,
    verify_harmonic_pqc_session,
    Vector6DKey,
    derive_key_from_vector,
    vector_proximity_key,
    analyze_harmonic_security,
    print_security_table,
    HarmonicKyberOrchestrator,
    HARMONIC_SCALE_TABLE,
    BASE_SECURITY_BITS,
)

# PQC Audit chain
from .pqc_audit import (
    # Audit types
    AuditDecision,
    PQCAuditEntry,
    AuditChainVerification,

    # Audit chain
    PQCAuditChain,

    # Standalone signatures
    create_audit_entry_signature,
    verify_audit_entry_signature,

    # Integration helper
    PQCAuditIntegration,
)

__all__ = [
    # Core - Key Encapsulation
    "Kyber768",
    "KyberKeyPair",
    "EncapsulationResult",

    # Core - Digital Signatures
    "Dilithium3",
    "DilithiumKeyPair",
    "SignatureResult",

    # Core - Backend
    "PQCBackend",
    "get_backend",
    "is_liboqs_available",

    # Core - Hybrid
    "derive_hybrid_key",
    "generate_pqc_session_keys",
    "verify_pqc_session",

    # Core - Constants
    "KYBER768_PUBLIC_KEY_SIZE",
    "KYBER768_SECRET_KEY_SIZE",
    "KYBER768_CIPHERTEXT_SIZE",
    "KYBER768_SHARED_SECRET_SIZE",
    "DILITHIUM3_PUBLIC_KEY_SIZE",
    "DILITHIUM3_SECRET_KEY_SIZE",
    "DILITHIUM3_SIGNATURE_SIZE",

    # HMAC - Key Derivation
    "KeyDerivationMode",
    "PQCKeyMaterial",
    "PQCHMACState",
    "pqc_derive_hmac_key",
    "pqc_recover_hmac_key",

    # HMAC - Chain Operations
    "pqc_hmac_chain_tag",
    "pqc_verify_hmac_chain",
    "PQCHMACChain",

    # HMAC - State Management
    "create_pqc_hmac_state",
    "migrate_classical_chain",

    # HMAC - Constants
    "NONCE_BYTES",
    "KEY_LEN",
    "AUDIT_CHAIN_IV",

    # Audit - Types
    "AuditDecision",
    "PQCAuditEntry",
    "AuditChainVerification",

    # Audit - Chain
    "PQCAuditChain",

    # Audit - Standalone
    "create_audit_entry_signature",
    "verify_audit_entry_signature",

    # Audit - Integration
    "PQCAuditIntegration",

    # Harmonic Enhancement
    "SecurityDimension",
    "HarmonicKeyMaterial",
    "harmonic_key_stretch",
    "fast_harmonic_key",
    "HarmonicPQCSession",
    "create_harmonic_pqc_session",
    "verify_harmonic_pqc_session",
    "Vector6DKey",
    "derive_key_from_vector",
    "vector_proximity_key",
    "analyze_harmonic_security",
    "print_security_table",
    "HarmonicKyberOrchestrator",
    "HARMONIC_SCALE_TABLE",
    "BASE_SECURITY_BITS",
]

__version__ = "1.0.0"
__author__ = "SCBE-AETHERMOORE Team"
