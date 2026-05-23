---
title: "Post-Quantum Cryptography in the AI Agent Pipeline: What We're Actually Protecting"
slug: post-quantum-cryptography-in-the-ai-agent-pipeline
date: 2026-05-23
author: Issac Daniel Davis
tags: [post-quantum, pqc, cryptography, ai-agents, ml-kem, ml-dsa, scbe]
platforms: [dev.to, aethermoore.com/articles]
status: ready
---

# Post-Quantum Cryptography in the AI Agent Pipeline: What We're Actually Protecting

Most discussions of post-quantum cryptography focus on the cryptographic algorithms themselves — ML-KEM-768 replacing Kyber768, ML-DSA-65 replacing Dilithium3, the NIST standardization process, the timeline for quantum computers that could break RSA. That framing is correct but incomplete for AI systems.

The specific problem in an AI agent pipeline isn't just "encrypt the data." It's "authenticate the governance receipt."

---

## What a governance receipt is

When SCBE's 14-layer pipeline evaluates an input and returns a decision (ALLOW / QUARANTINE / ESCALATE / DENY), it stamps a receipt: a record of what was evaluated, when, by which pipeline version, with what score, to what decision. That receipt is the audit trail. It's how you prove after the fact that governance happened, that a specific input was reviewed by the framework, and that the result was X.

If you can forge a governance receipt, you can claim governance happened when it didn't. An adversary who compromises the receipt chain can insert false ALLOW decisions into the audit log. The downstream system trusts the audit log; the attack is invisible.

Classical signature schemes (ECDSA, RSA) protect the receipt chain now. A cryptographically relevant quantum computer would break that protection retroactively — receipts signed today could be forged in the future, invalidating the entire audit history.

---

## What we're using

SCBE's crypto layer (`src/crypto/`) implements:

- **ML-KEM-768** (formerly Kyber768) — key encapsulation for session key exchange between agents
- **ML-DSA-65** (formerly Dilithium3) — digital signatures for governance receipt authentication
- **AES-256-GCM** — symmetric encryption for the receipt payload itself

The NIST standardization renamed Kyber → ML-KEM and Dilithium → ML-DSA in 2024. Older versions of liboqs still use the old names. The codebase handles both via a fallback pattern:

```python
def _select_dsa_algorithm():
    available = oqs.get_enabled_sig_mechanisms()
    if "ML-DSA-65" in available:
        return "ML-DSA-65"
    return "Dilithium3"  # fallback for older liboqs
```

This runs at import time. Systems with liboqs 0.14.1+ get ML-DSA-65. Older installations fall back to Dilithium3 automatically without a config change.

---

## Why ML-DSA-65 specifically

The three NIST PQC signature finalists were ML-DSA (lattice), SLH-DSA (hash-based), and FALCON (lattice). We chose ML-DSA-65 for three reasons:

**Performance.** SLH-DSA (SPHINCS+) produces very large signatures and is slow to sign. FALCON requires constant-time floating-point arithmetic that's difficult to implement securely on all hardware. ML-DSA-65 is fast to sign, fast to verify, produces moderate-size signatures (~3.3KB), and has a straightforward implementation.

**Security level.** ML-DSA-65 targets NIST Level 3 — equivalent to AES-192. That's above what we need for most governance receipts, but governance receipts need to be valid for a long time. Signing conservatively.

**Library support.** liboqs-python (0.14.1) has stable ML-DSA-65 support. The C library underneath is maintained by the Open Quantum Safe project. We're not implementing this ourselves.

---

## The agent key rotation problem

Multi-agent systems have an additional problem: every agent needs a key pair, keys need to rotate periodically, and rotation needs to happen without a gap in the audit chain. With classical keys, rotation is cheap — a new ECDSA key pair is a few milliseconds. ML-DSA-65 key generation is slightly slower but still fast enough for rotation cycles on the order of hours or days.

The current implementation does session-bound key generation: each agent session generates a fresh ML-DSA-65 key pair and registers the public key with the governance ledger before beginning work. Governance receipts from that session are signed with the session key and can be verified against the ledger.

This means session keys are short-lived, which bounds the exposure of any single key compromise. The governance ledger itself is signed with a longer-lived root key.

---

## What's not post-quantum

Transport between agents currently uses AES-256-GCM for the payload with ML-KEM-768 for key encapsulation. The session negotiation itself is post-quantum. The payload encryption is symmetric AES-256, which is quantum-resistant in practice — Grover's algorithm halves the effective key length, but AES-256 at half strength is still AES-128 equivalent, which is fine.

What is not post-quantum: the existing ECDSA signatures on commits and tags in the git history. Those are classical signatures on public data. Forging a commit signature would require a quantum attacker with access to the signing key's historical state. This is low priority compared to protecting live governance receipts.

---

## The code

PQC primitives are in `src/crypto/`. The Python implementation uses `liboqs-python` via `import oqs`. The TypeScript implementation uses `@noble/post-quantum` for pure-JS PQC.

```typescript
import { ml_kem768 } from '@noble/post-quantum/ml-kem';
import { ml_dsa65 } from '@noble/post-quantum/ml-dsa';
```

Tests in `tests/crypto/`. Running `npm test` covers the TypeScript layer; `PYTHONPATH=. python -m pytest tests/ -v` covers the Python layer.

Full repo: [issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE)
