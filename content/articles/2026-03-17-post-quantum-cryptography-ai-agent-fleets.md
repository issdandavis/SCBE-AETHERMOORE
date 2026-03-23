# Post-Quantum Cryptography for AI Agent Fleets

Every governance decision your AI fleet makes -- allow, deny, quarantine -- is only as trustworthy as the cryptography protecting it. If an adversary can forge a signature on a governance verdict, your entire safety pipeline is theater. And with quantum computers progressing from lab curiosities to engineering milestones, the window to retrofit quantum-resistant cryptography is closing faster than most teams realize.

SCBE-AETHERMOORE ships post-quantum cryptography (PQC) as a first-class citizen, not an afterthought. Here is how and why.

## The Threat Model

NIST finalized ML-KEM (formerly CRYSTALS-Kyber) and ML-DSA (formerly CRYSTALS-Dilithium) as federal standards in August 2024. The rationale: a cryptographically relevant quantum computer could break RSA-2048 and ECDSA-256 within hours. Every governance decision signed with classical crypto today could be retroactively forged tomorrow.

For AI agent fleets this is catastrophic. If an attacker harvests encrypted governance logs now ("harvest now, decrypt later"), they can later:

1. **Forge ALLOW decisions** to inject malicious agent behavior
2. **Tamper with audit trails** to hide safety violations
3. **Impersonate validators** in consensus votes

## The RWP v3 Envelope System

SCBE's Real World Protocol v3 layers five cryptographic primitives into a single envelope:

| Layer | Primitive | Purpose |
|-------|-----------|---------|
| 1 | Argon2id (RFC 9106) | Password to key derivation |
| 2 | ML-KEM-768 | Quantum-resistant key encapsulation |
| 3 | XChaCha20-Poly1305 | Authenticated encryption (AEAD) |
| 4 | ML-DSA-65 | Quantum-resistant digital signatures |
| 5 | Sacred Tongue encoding | Semantic binding to 6D trust space |

The envelope structure maps each cryptographic field to a specific "Sacred Tongue" -- a tokenization language that binds the ciphertext to a position in hyperbolic trust space. This means encrypted governance decisions are not just confidential; they are geometrically anchored.

```python
from src.crypto.rwp_v3 import RWPv3Protocol

# Initialize with post-quantum extensions enabled
protocol = RWPv3Protocol(enable_pqc=True)

# Encrypt a governance decision
envelope = protocol.encrypt(
    password=b"fleet-master-key",
    plaintext=b'{"decision": "ALLOW", "agent": "sheep-a1b2c3d4", "confidence": 0.94}',
    aad=b'{"timestamp": "2026-03-17T12:00:00Z", "flock_id": "production-fleet"}',
    ml_kem_public_key=kem_public_key,
    ml_dsa_private_key=dsa_signing_key,
)

# The envelope fields are Sacred Tongue tokens, not raw bytes
print(envelope.aad)    # Avali tokens
print(envelope.ct)     # Cassisivadan tokens
print(envelope.tag)    # Draumric tokens
```

## Why AI Governance Needs PQC Now

The argument for waiting -- "quantum computers are years away" -- ignores three realities of AI fleet governance:

**1. Audit trails must survive decades.** If you are deploying AI agents under the EU AI Act (enforcement begins August 2026), your compliance records need to be tamper-proof for the lifetime of the system. A governance log signed with ECDSA today is a liability in 2030.

**2. Agent-to-agent communication is high-value.** AI fleets exchange thousands of governance decisions per hour. Each one is a potential forgery target. ML-DSA-65 signatures are 3,293 bytes -- larger than ECDSA, but verification is fast enough for real-time agent consensus.

**3. The migration cost only grows.** Every month you wait, you accumulate more classical-crypto artifacts that need re-signing. SCBE handles the migration gracefully with algorithm negotiation:

```python
def _select_sig_algorithm() -> str:
    """Try ML-DSA-65 first, fall back to Dilithium3 for older liboqs."""
    if not OQS_AVAILABLE:
        return "ML-DSA-65"
    enabled = oqs.get_enabled_sig_mechanisms()
    return "ML-DSA-65" if "ML-DSA-65" in enabled else "Dilithium3"
```

This pattern means SCBE works with both the NIST-finalized names and the older draft names, so you are never blocked by a library version mismatch.

## Signed Governance Decisions in Practice

Here is the full flow when a fleet of AI agents votes on whether to allow an action:

1. Each validator agent casts a vote (ALLOW / QUARANTINE / DENY)
2. Votes are packed into a balanced ternary word (see the trinary module)
3. The consensus result is serialized as JSON
4. RWP v3 encrypts the result with Argon2id + XChaCha20-Poly1305
5. ML-DSA-65 signs the entire envelope (AAD + salt + nonce + ciphertext + tag)
6. The signed envelope is stored in the audit log

An attacker wanting to forge this decision must simultaneously:
- Break ML-KEM-768 (lattice-based, NIST Level 3)
- Forge an ML-DSA-65 signature (lattice-based, NIST Level 3)
- Defeat the Argon2id KDF (memory-hard, 64MB cost)
- Produce valid Sacred Tongue tokens that pass geometric consistency checks

Each layer independently resists quantum attack. Together, they form a defense that scales combinatorially.

## Getting Started

SCBE-AETHERMOORE is open source. To try the PQC envelope system:

```bash
pip install scbe-aethermoore argon2-cffi pycryptodome liboqs-python
```

```python
from src.crypto.rwp_v3 import rwp_encrypt_message, rwp_decrypt_message

# Encrypt with classical crypto (works without liboqs)
envelope = rwp_encrypt_message("my-password", "Governance: ALLOW agent-7 deploy")

# Decrypt
plaintext = rwp_decrypt_message("my-password", envelope)
```

The full source lives at [github.com/issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE) under `src/crypto/rwp_v3.py`.

Post-quantum cryptography is not a luxury for AI governance. It is table stakes. The question is not whether to migrate, but how much technical debt you are willing to accumulate before you do.
