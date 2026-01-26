# Integrating Quantum Key Distribution (QKD) into SCBE-AETHERMOORE

This document proposes a modular QKD integration that complements PQC.
QKD provides information-theoretic key exchange (eavesdropping is detectable),
while PQC provides algorithmic resistance to quantum computers.

Summary:
- Security: BB84/E91 generate shared symmetric keys and detect eavesdroppers via error rates.
- Auditability: hash and log QKD error rates and alerts (Layer 13 telemetry).
- Governance: allow QKD only on approved channels; fallback to classical PQC if unavailable.
- Practical limits: needs hardware; range constraints (typically 100-200km fiber).
- Edge cases: noisy environments; mitigate with error correction (e.g., Cascade protocol).

---

## Layer 9: Authentication Envelope (Initial Key Exchange)

Goal: if QKD is available, derive the initial session key via QKD; otherwise use the existing
classical flow.

Proposed behavior:
- If env var SCBE_QKD_ENABLED=true, attempt QKD handshake.
- On eavesdrop detection, deny access (403).
- On failure, fall back to classical key derivation.

Pseudo-code (Python):

```python
import os
import secrets
from fastapi import Depends, HTTPException
# from qkd_sim import bb84_protocol, EavesdropDetected

async def verify_api_key(scbe_api_key: str = Depends(API_KEY_HEADER)):
    if os.getenv('SCBE_QKD_ENABLED') == 'true':
        try:
            # shared_key = bb84_protocol(quantum_channel_endpoint=os.getenv('QKD_ENDPOINT'))
            # logger.info("QKD session established")
            # return shared_key
            pass
        except Exception:
            raise HTTPException(403, "Quantum eavesdrop detected - access denied")

    # Classical fallback (existing behavior)
    # ...
```

Notes:
- Error rates should be logged as hashes (privacy-preserving audit).
- Require a minimum channel security policy before enabling QKD.

---

## Layer 12: Entropic Defense Engine (Key Rotation and Entropy Injection)

Goal: incorporate QKD bits into HKDF-based key rotation for extra entropy.

Pseudo-code (TypeScript):

```typescript
import { hkdf } from '@noble/hashes/hkdf';
import { sha3_256 } from '@noble/hashes/sha3';
// import { qkdBb84 } from 'qkd-sim';

async function rotateKeyWithQkd(currentKey: string): Promise<Uint8Array> {
  if (process.env.SCBE_QKD_ENABLED === 'true') {
    // const qkdKey = await qkdBb84({ endpoint: process.env.QKD_ENDPOINT });
    // if (qkdKey.errorRate > 0.11) throw new Error('QKD eavesdrop detected');
    // return hkdf(sha3_256, Buffer.from(currentKey + qkdKey.sharedBits), 'SCBE-ENTROPIC-SALT-v1', crypto.randomBytes(16), 32);
  }
  return hkdf(sha3_256, currentKey, 'SCBE-ENTROPIC-SALT-v1', crypto.randomBytes(16), 32);
}
```

Governance:
- Key rotation interval controlled by policy (e.g., SCBE_REKEY_DAYS=90).
- If QKD error rate exceeds threshold, trigger fail-to-noise or risk amplification.

---

## Layer 14: Hybrid QKD + PQC

Goal: use QKD for symmetric encryption keys and PQC signatures for authenticity.

Pseudo-code (Python):

```python
# from cryptography.hazmat.primitives.asymmetric import dilithium
# from aes_gcm import encrypt, decrypt
# from hashlib import sha3_256

# def hybrid_qkd_encrypt(data: bytes, qkd_key: bytes, private_dilithium: bytes) -> bytes:
#     signer = dilithium.Dilithium2(private_dilithium)
#     signature = signer.sign(qkd_key)
#     ciphertext = encrypt(data, qkd_key)
#     return signature + ciphertext

# def hybrid_qkd_decrypt(bundle: bytes, public_dilithium: bytes, qkd_key: bytes) -> bytes:
#     signature, ciphertext = bundle[:dilithium.SIGNATURE_SIZE], bundle[dilithium.SIGNATURE_SIZE:]
#     verifier = dilithium.Dilithium2(public_dilithium)
#     verifier.verify(signature, qkd_key)
#     return decrypt(ciphertext, qkd_key)
```

Notes:
- Bundle size increases due to signature.
- If QKD fails, fallback to ML-KEM encapsulation (existing PQC flow).

---

## Implementation Steps

1) Add optional dependencies for simulation (e.g., qiskit or a lightweight QKD sim).
2) Add a qkd/ submodule (simulation only) to keep QKD optional and non-breaking.
3) Add tests for error-rate detection and fallback behavior; skip if QKD disabled.
4) Log QKD telemetry in Layer 13 (hashed error rates).

---

## Testing

- Unit tests: QKD error detection, fallback to classical, and HKDF mixing.
- Integration: End-to-end key negotiation with SCBE_QKD_ENABLED=true in a simulated environment.
- CI: Skip QKD tests when QKD is not enabled or hardware is absent.
