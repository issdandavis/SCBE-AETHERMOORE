# Post-Quantum Cryptography in Practice: How SCBE-AETHERMOORE Prepares for Q-Day

*Implementing NIST's ML-KEM and ML-DSA standards in a real AI safety framework*

---

## The Quantum Threat Timeline

Quantum computers powerful enough to break RSA and elliptic curve cryptography are expected within the next decade. When that day arrives — "Q-Day" — every system relying on classical cryptography becomes vulnerable. Not just vulnerable *then*, but vulnerable *now*: adversaries harvesting encrypted traffic today can decrypt it once quantum computers arrive ("harvest now, decrypt later").

For AI safety systems, this is an existential concern. If an attacker can break the cryptographic integrity of a governance pipeline, they can forge safety attestations, tamper with decision logs, and bypass security layers entirely.

## NIST's Post-Quantum Standards

In 2024, NIST finalized three post-quantum cryptographic standards:

- **ML-KEM** (Module-Lattice-Based Key Encapsulation Mechanism, formerly CRYSTALS-Kyber): Secure key exchange resistant to quantum attacks
- **ML-DSA** (Module-Lattice-Based Digital Signature Algorithm, formerly CRYSTALS-Dilithium): Digital signatures resistant to quantum attacks
- **SLH-DSA** (Stateless Hash-Based Digital Signature Algorithm, formerly SPHINCS+): Hash-based signatures as a fallback

These algorithms are based on the hardness of lattice problems, which remain intractable even for quantum computers.

## SCBE-AETHERMOORE's PQC Implementation

SCBE integrates post-quantum cryptography at every trust boundary:

### Key Encapsulation: ML-KEM-768

```typescript
// Key generation
const { publicKey, secretKey } = await mlKem768.keyGen();

// Encapsulation (sender side)
const { ciphertext, sharedSecret } = await mlKem768.encapsulate(publicKey);

// Decapsulation (receiver side)
const sharedSecret = await mlKem768.decapsulate(ciphertext, secretKey);
```

ML-KEM-768 provides 192-bit security against classical attacks and is believed to offer equivalent security against quantum attacks. SCBE uses it for:

- Securing inter-layer communication in the 14-layer pipeline
- Protecting fleet communication between governance agents
- Key agreement for encrypted telemetry channels

### Digital Signatures: ML-DSA-65

```typescript
// Signing a governance decision
const signature = await mlDsa65.sign(decisionPayload, signingKey);

// Verification
const isValid = await mlDsa65.verify(decisionPayload, signature, verifyKey);
```

ML-DSA-65 provides 128-bit security and is used for:

- Signing governance decisions (ALLOW/QUARANTINE/ESCALATE/DENY)
- Authenticating pipeline layer outputs
- Non-repudiation of safety attestations
- Signing axiom compliance proofs

### Symmetric Encryption: AES-256-GCM

For bulk data encryption, SCBE uses AES-256-GCM, which is already quantum-resistant (Grover's algorithm only halves the effective key length, so 256-bit keys still provide 128-bit quantum security).

## The Migration Challenge: Algorithm Name Changes

A practical challenge we encountered: the `liboqs` library (which provides PQC implementations) renamed algorithms to match NIST's final standard names:

| Old Name | New Name |
|----------|----------|
| `Dilithium3` | `ML-DSA-65` |
| `Kyber768` | `ML-KEM-768` |

This broke existing code that referenced the old names. Our solution is a fallback pattern:

```python
def _select_dsa_algorithm():
    """Try new NIST name first, fall back to old name."""
    try:
        sig = oqs.Signature("ML-DSA-65")
        return "ML-DSA-65"
    except oqs.MechanismNotSupportedError:
        return "Dilithium3"
```

This ensures compatibility across different `liboqs` versions without requiring coordinated upgrades.

## PQC + Hyperbolic Geometry: Defense in Depth

SCBE's innovation is not just using PQC — it is combining PQC with hyperbolic geometric scaling. The two defenses are orthogonal:

**Hyperbolic geometry** makes adversarial *intent* exponentially expensive. The further you drift from safe operation in the Poincare ball, the more it costs.

**Post-quantum cryptography** makes adversarial *tampering* computationally infeasible. Even with a quantum computer, you cannot forge signatures, decrypt communications, or break key exchange.

Together, they create a defense where:
- You cannot *afford* to be adversarial (geometric cost)
- You cannot *fake* being safe (cryptographic integrity)
- You cannot *wait for quantum computers* to break either defense

## Practical Considerations

### Performance

ML-KEM-768 key generation takes approximately 0.1ms. ML-DSA-65 signing takes approximately 0.5ms. These are fast enough for real-time use in the pipeline without noticeable latency.

### Key Sizes

PQC keys are larger than classical keys:

| Algorithm | Public Key | Private Key | Signature/Ciphertext |
|-----------|-----------|-------------|---------------------|
| ML-KEM-768 | 1,184 bytes | 2,400 bytes | 1,088 bytes |
| ML-DSA-65 | 1,952 bytes | 4,032 bytes | 3,309 bytes |
| RSA-2048 (classical) | 256 bytes | 1,192 bytes | 256 bytes |

The size increase is manageable for SCBE's use case — governance decisions and pipeline attestations are relatively infrequent compared to, say, TLS handshakes.

### Testing Strategy

SCBE tests PQC implementations at three levels:

1. **L2-unit**: Individual algorithm correctness (keygen → encapsulate → decapsulate roundtrip)
2. **L5-security**: Boundary enforcement (reject invalid ciphertexts, detect tampered signatures)
3. **L6-adversarial**: Attack simulations (replay attacks, key substitution, oracle queries)

## Getting Started

SCBE-AETHERMOORE ships with PQC support out of the box. The TypeScript implementation uses native bindings where available and falls back to JavaScript implementations:

```bash
npm install scbe-aethermoore
```

```typescript
import { createEnvelope, verifyEnvelope } from 'scbe-aethermoore/crypto';

// Create a PQC-secured envelope
const envelope = await createEnvelope(payload, signingKey, encryptionKey);

// Verify and decrypt
const result = await verifyEnvelope(envelope, verifyKey, decryptionKey);
```

The Python implementation uses `liboqs` directly:

```bash
pip install liboqs-python
```

---

*Q-Day is coming. The question is whether your AI safety infrastructure will survive it.*

*SCBE-AETHERMOORE is open source at [github.com/issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE).*

*Support development on [Ko-fi](https://ko-fi.com/izdandavis).*
