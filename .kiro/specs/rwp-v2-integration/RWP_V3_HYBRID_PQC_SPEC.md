# RWP v3.0: Hybrid Post-Quantum Cryptography Specification

**Feature**: rwp-v2-integration (Future Enhancement)  
**Version**: 3.0.0 (Planned)  
**Status**: Mathematical Specification Complete  
**Dependencies**: RWP v2.1 (Current), liboqs or PQC library (Future)  
**Last Updated**: January 18, 2026

---

## Overview

RWP v3.0 introduces hybrid post-quantum cryptography (PQC) using NIST-approved ML-DSA-65 (FIPS 204) combined with classical HMAC-SHA256 signatures. This "belt-and-suspenders" approach ensures security even if one primitive is compromised.

### Key Features

- **Hybrid Security**: Both classical and PQC signatures must verify
- **Crypto-Agility**: Three modes (classical-only, hybrid, PQC-only)
- **Quantum Resistance**: 128-bit security against quantum attacks
- **Backward Compatible**: Extends RWP v2.1 envelope structure
- **Domain Separation**: Sacred Tongues prevent cross-domain confusion

---

## Security Analysis

### 1. Classical Security (HMAC-SHA256)

```
Hash output:           256 bits
Collision resistance:  128 bits (birthday bound)
Preimage resistance:   256 bits
Post-quantum (Grover): 128 bits (√2^256 = 2^128)
```

### 2. Post-Quantum Security (ML-DSA-65)

```
Standard:              NIST FIPS 204
Security level:        NIST Level 3
Classical security:    ~128 bits
Quantum security:      ~128 bits
Public key size:       1952 bytes
Signature size:        3309 bytes
```

### 3. Hybrid Mode Security

```
Combined security:     max(HMAC, ML-DSA) = 128 bits quantum
Attack requirement:    Must break BOTH primitives
If HMAC broken:        ML-DSA still protects (128-bit quantum)
If ML-DSA broken:      HMAC still protects (128-bit quantum)
```

### 4. Multi-Signature Consensus

For k independent signatures, attacker must forge all k:

```
k=2 signatures: ~256 bits (capped by hash output)
k=3 signatures: ~256 bits (capped by hash output)
k=4 signatures: ~256 bits (capped by hash output)
k=6 signatures: ~256 bits (capped by hash output)
```

### 5. Replay Protection

```
Nonce:                 128-bit random
Collision probability: 2^-64 for 2^32 messages
Timestamp window:      60 seconds (configurable)
Combined:              Time + nonce prevents replay
```

### 6. Domain Separation

```
Purpose:               Prevent cross-domain signature confusion
Method:                Prepend tongue prefix before hashing
Security:              sig_KO cannot be used as sig_AV
```

---

## Protocol Specification

### Envelope Structure

```python
@dataclass
class RWP3Envelope:
    """RWP v3.0 envelope with hybrid PQC support."""
    version: str = "3.0"
    mode: HybridPQCMode = HybridPQCMode.HYBRID
    primary_tongue: SacredTongue = SacredTongue.KORAELIN
    timestamp: int = 0
    nonce: bytes = b""
    payload: bytes = b""
    aad: bytes = b""
    
    # Classical signatures (HMAC-SHA256)
    classical_sigs: Dict[SacredTongue, bytes] = None
    
    # Post-quantum signatures (ML-DSA-65)
    pqc_sigs: Dict[SacredTongue, bytes] = None
```

### Hybrid Modes

```python
class HybridPQCMode(Enum):
    CLASSICAL_ONLY = "classical"  # HMAC-SHA256 only
    HYBRID = "hybrid"             # HMAC + ML-DSA (recommended)
    PQC_ONLY = "pqc"              # ML-DSA only (future)
```

### Signature Generation

#### Classical Signature (HMAC-SHA256)

```python
def sign_tongue(tongue: SacredTongue,
                key: bytes,
                payload: bytes,
                nonce: bytes,
                timestamp: int,
                aad: bytes = b"") -> bytes:
    """Domain-separated HMAC-SHA256 signature.
    
    sig = HMAC-SHA256(key, tongue_prefix || payload || nonce || timestamp || aad)
    """
    message = tongue.value + payload + nonce + struct.pack(">Q", timestamp) + aad
    return hmac.new(key, message, hashlib.sha256).digest()
```

#### PQC Signature (ML-DSA-65)

```python
def ml_dsa_sign(tongue: SacredTongue,
                sk: bytes,  # Secret key
                message: bytes) -> bytes:
    """ML-DSA-65 signature (NIST FIPS 204).
    
    Production implementation:
        from oqs import Signature
        sig = Signature("ML-DSA-65")
        signature = sig.sign(message)
    
    Parameters:
        - Security level: NIST Level 3 (~128-bit quantum)
        - Public key size: 1952 bytes
        - Signature size: 3309 bytes
    """
    # Domain separation: prepend tongue prefix
    pqc_message = tongue.value + message
    
    # Production: Use liboqs
    # signature = sig.sign(pqc_message)
    
    return signature
```

### Verification

#### Hybrid Verification

```python
def verify_roundtable_v3(envelope: RWP3Envelope,
                         classical_keyring: Dict[SacredTongue, bytes],
                         pqc_keyring: Dict[SacredTongue, bytes],
                         required_tongues: List[SacredTongue],
                         replay_window_ms: int = 60000) -> Tuple[bool, List[SacredTongue]]:
    """Verify RWP v3.0 envelope with hybrid signatures.
    
    In HYBRID mode, BOTH classical and PQC signatures must verify.
    """
    verified = []
    
    for tongue in required_tongues:
        classical_ok = False
        pqc_ok = False
        
        # Verify classical signature
        if envelope.mode in [HybridPQCMode.CLASSICAL_ONLY, HybridPQCMode.HYBRID]:
            if tongue in envelope.classical_sigs and tongue in classical_keyring:
                classical_ok = verify_tongue(
                    tongue,
                    classical_keyring[tongue],
                    envelope.payload,
                    envelope.nonce,
                    envelope.timestamp,
                    envelope.classical_sigs[tongue],
                    envelope.aad,
                    replay_window_ms
                )
        
        # Verify PQC signature
        if envelope.mode in [HybridPQCMode.PQC_ONLY, HybridPQCMode.HYBRID]:
            if tongue in envelope.pqc_sigs and tongue in pqc_keyring:
                message = envelope.payload + envelope.nonce + \
                          struct.pack(">Q", envelope.timestamp) + envelope.aad
                pqc_message = tongue.value + message
                pqc_ok = ml_dsa_verify(
                    tongue,
                    pqc_keyring[tongue],
                    pqc_message,
                    envelope.pqc_sigs[tongue]
                )
        
        # Check mode requirements
        if envelope.mode == HybridPQCMode.CLASSICAL_ONLY and classical_ok:
            verified.append(tongue)
        elif envelope.mode == HybridPQCMode.PQC_ONLY and pqc_ok:
            verified.append(tongue)
        elif envelope.mode == HybridPQCMode.HYBRID and classical_ok and pqc_ok:
            verified.append(tongue)
    
    success = len(verified) >= len(required_tongues)
    return success, verified
```

---

## Quantum Threat Timeline

### Current Status (2025)

- No cryptographically relevant quantum computers exist
- RSA-2048, ECDSA-256, HMAC-SHA256 remain secure
- NIST PQC standards published (FIPS 203, 204, 205)

### Near-Term (2030)

- Possible 1000+ logical qubits
- Still insufficient for breaking RSA-2048
- HMAC-SHA256 reduced to 128-bit security (Grover's algorithm)
- Recommendation: Deploy hybrid mode for crypto-agility

### Long-Term (2035+)

- Potential threat to RSA-2048, ECDSA-256
- HMAC-SHA256 still secure at 128-bit quantum level
- ML-DSA-65 designed for quantum resistance
- Hybrid mode provides maximum security

---

## Implementation Roadmap

### Phase 1: RWP v2.1 (Current - v3.1.0)

- ✅ Classical HMAC-SHA256 multi-signatures
- ✅ Sacred Tongues domain separation
- ✅ Replay protection (timestamp + nonce)
- ✅ Policy enforcement (standard, strict, secret, critical)

### Phase 2: RWP v3.0 Preparation (v3.2.0)

- [ ] Integrate liboqs or equivalent PQC library
- [ ] Implement ML-DSA-65 key generation
- [ ] Implement ML-DSA-65 signing/verification
- [ ] Add hybrid envelope structure
- [ ] Backward compatibility with v2.1

### Phase 3: RWP v3.0 Deployment (v3.3.0)

- [ ] Production hybrid mode deployment
- [ ] Key rotation procedures for PQC keys
- [ ] Performance optimization (signature batching)
- [ ] Monitoring and telemetry

### Phase 4: Full PQC Migration (v4.0.0)

- [ ] PQC-only mode for quantum-safe environments
- [ ] Deprecate classical-only mode
- [ ] Hardware acceleration (if available)
- [ ] Compliance certification (FIPS 140-3)

---

## Dependencies

### Required Libraries

#### Python

```python
# Classical cryptography (current)
import hashlib
import hmac
import secrets

# Post-quantum cryptography (future)
# Option 1: liboqs-python
from oqs import Signature

# Option 2: PQClean
from pqcrypto.sign.dilithium3 import generate_keypair, sign, verify
```

#### TypeScript/Node.js

```typescript
// Classical cryptography (current)
import crypto from 'crypto';

// Post-quantum cryptography (future)
// Option 1: node-oqs
import { Signature } from 'node-oqs';

// Option 2: WASM-based PQC
import { ml_dsa_65_sign, ml_dsa_65_verify } from 'pqc-wasm';
```

### Installation

```bash
# Python
pip install liboqs-python

# Node.js
npm install node-oqs
```

---

## Performance Considerations

### Signature Sizes

```
Classical (HMAC-SHA256):  32 bytes
ML-DSA-65:                3309 bytes
Hybrid (both):            3341 bytes
```

### Signing Performance (Estimated)

```
Classical:                <1 ms
ML-DSA-65:                ~2-5 ms
Hybrid:                   ~3-6 ms
```

### Verification Performance (Estimated)

```
Classical:                <1 ms
ML-DSA-65:                ~1-3 ms
Hybrid:                   ~2-4 ms
```

### Network Overhead

For k=3 tongues in hybrid mode:
```
Classical only:           96 bytes (3 × 32)
Hybrid:                   10,023 bytes (3 × 3341)
Overhead:                 ~100× increase
```

**Mitigation Strategies**:
- Signature compression (if supported by PQC library)
- Batch verification for multiple envelopes
- Selective hybrid mode (critical operations only)
- Network-level compression (gzip, brotli)

---

## Security Proofs

### Theorem 1: Hybrid Security

**Claim**: If either HMAC-SHA256 or ML-DSA-65 is secure, the hybrid scheme is secure.

**Proof Sketch**:
1. Attacker must forge both signatures to succeed
2. If HMAC is secure, attacker cannot forge classical signature
3. If ML-DSA is secure, attacker cannot forge PQC signature
4. Therefore, hybrid scheme is secure if at least one primitive is secure
5. Security level: max(128-bit HMAC, 128-bit ML-DSA) = 128-bit quantum

### Theorem 2: Domain Separation

**Claim**: Signatures from different Sacred Tongues cannot be confused.

**Proof Sketch**:
1. Each signature includes tongue prefix in message
2. sig_KO = HMAC(key, "KO" || message)
3. sig_AV = HMAC(key, "AV" || message)
4. Since "KO" ≠ "AV", sig_KO ≠ sig_AV (with overwhelming probability)
5. Attacker cannot use sig_KO to forge sig_AV

### Theorem 3: Replay Protection

**Claim**: Envelopes cannot be replayed outside the time window.

**Proof Sketch**:
1. Each envelope includes timestamp and random nonce
2. Verifier checks |t_now - t_envelope| ≤ window
3. Verifier maintains nonce cache for window duration
4. Duplicate nonces are rejected
5. Old envelopes (outside window) are rejected
6. Therefore, replay attacks are prevented

---

## Testing Requirements

### Unit Tests

- [ ] Classical signature generation/verification
- [ ] ML-DSA-65 signature generation/verification (with liboqs)
- [ ] Hybrid envelope creation
- [ ] Hybrid envelope verification
- [ ] Mode switching (classical, hybrid, PQC-only)
- [ ] Replay protection
- [ ] Domain separation

### Property-Based Tests

- [ ] **Property 1**: Hybrid verification succeeds iff both signatures valid
- [ ] **Property 2**: Domain separation prevents cross-tongue confusion
- [ ] **Property 3**: Replay protection rejects duplicate nonces
- [ ] **Property 4**: Timestamp validation rejects old envelopes
- [ ] **Property 5**: Multi-signature consensus requires k valid signatures

### Interoperability Tests

- [ ] Python ↔ TypeScript envelope exchange
- [ ] Classical-only ↔ Hybrid mode compatibility
- [ ] Key rotation without breaking existing envelopes
- [ ] Backward compatibility with RWP v2.1

### Performance Tests

- [ ] Signing throughput (envelopes/second)
- [ ] Verification throughput
- [ ] Memory usage (nonce cache)
- [ ] Network overhead (envelope size)

---

## Migration Guide

### From RWP v2.1 to v3.0

#### Step 1: Add PQC Library

```bash
pip install liboqs-python
```

#### Step 2: Generate PQC Keys

```python
from oqs import Signature

sig = Signature("ML-DSA-65")
public_key = sig.generate_keypair()
secret_key = sig.export_secret_key()

# Store securely
pqc_keyring = {
    SacredTongue.KORAELIN: secret_key,
    # ... other tongues
}
```

#### Step 3: Enable Hybrid Mode

```python
# Old (v2.1)
envelope = sign_roundtable(
    payload=payload,
    keyring=classical_keyring,
    tongues_to_sign=[SacredTongue.KORAELIN]
)

# New (v3.0 hybrid)
envelope = sign_roundtable_v3(
    payload=payload,
    classical_keyring=classical_keyring,
    pqc_keyring=pqc_keyring,
    tongues_to_sign=[SacredTongue.KORAELIN],
    mode=HybridPQCMode.HYBRID
)
```

#### Step 4: Update Verification

```python
# Old (v2.1)
success, verified = verify_roundtable(
    envelope=envelope,
    keyring=classical_keyring,
    required_tongues=[SacredTongue.KORAELIN]
)

# New (v3.0 hybrid)
success, verified = verify_roundtable_v3(
    envelope=envelope,
    classical_keyring=classical_keyring,
    pqc_keyring=pqc_keyring,
    required_tongues=[SacredTongue.KORAELIN]
)
```

---

## References

### Standards

- **NIST FIPS 204**: Module-Lattice-Based Digital Signature Standard (ML-DSA)
- **NIST FIPS 203**: Module-Lattice-Based Key-Encapsulation Mechanism Standard (ML-KEM)
- **RFC 2104**: HMAC: Keyed-Hashing for Message Authentication
- **NIST SP 800-208**: Recommendation for Stateful Hash-Based Signature Schemes

### Libraries

- **liboqs**: Open Quantum Safe - C library for quantum-resistant cryptography
- **liboqs-python**: Python bindings for liboqs
- **node-oqs**: Node.js bindings for liboqs
- **PQClean**: Clean, portable implementations of post-quantum cryptography

### Research Papers

- Ducas et al. (2018): "CRYSTALS-Dilithium: A Lattice-Based Digital Signature Scheme"
- Bernstein et al. (2015): "Post-quantum cryptography"
- NIST (2022): "Status Report on the Third Round of the NIST Post-Quantum Cryptography Standardization Process"

---

## Appendix: Complete Reference Implementation

See `rwp_v3_hybrid_pqc.py` for the complete reference implementation with:

- Sacred Tongues domain separation
- RWP v2.1 classical multi-signatures
- RWP v3.0 hybrid PQC signatures
- Security analysis and demonstrations
- Simulated ML-DSA-65 (replace with liboqs in production)

---

**Status**: Mathematical specification complete, awaiting PQC library integration  
**Next Steps**: Integrate liboqs, implement production ML-DSA-65, performance testing  
**Timeline**: Target v3.2.0 (Q3 2026) for hybrid mode deployment

---

*"Quantum-safe today, quantum-proof tomorrow."*

🔐 **Secure. Hybrid. Future-Proof.**
