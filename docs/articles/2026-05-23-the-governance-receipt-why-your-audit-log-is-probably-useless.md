---
title: "The Governance Receipt: Why Your AI Audit Log Is Probably Useless"
slug: the-governance-receipt-why-your-audit-log-is-probably-useless
date: 2026-05-23
author: Issac Daniel Davis
tags: [audit-log, governance, ai-safety, scbe, pqc, receipt, compliance]
platforms: [dev.to, aethermoore.com/articles]
status: ready
---

# The Governance Receipt: Why Your AI Audit Log Is Probably Useless

Most AI audit logs are trust-me records. The system writes "DECISION: ALLOW, timestamp: 2026-05-23T14:32:07Z, input_id: 8f3d..." to a database, and that entry is the audit record. If you need to verify that the decision was correct, you trust that the log wasn't modified.

That's not an audit log. That's a self-reported score.

A real audit record is verifiable independently, without trusting the system that generated it. The record should prove: this specific input, processed by this specific system version, at this timestamp, produced this decision, and that claim is cryptographically bound so no one can alter it without breaking the proof.

---

## What a governance receipt contains

The SCBE governance receipt includes:

- **Input hash.** SHA-256 of the normalized input. Anyone with the original input can verify it maps to this hash.
- **Pipeline version.** The exact version string of the pipeline that produced the decision. The same input through a different version should produce a documentably different receipt.
- **Score components.** `d_H` (hyperbolic distance) and `pd` (phase deviation) separately, not just the final harmonic score `H(d, pd)`. The components let you understand what drove the decision — high distance vs. high phase deviation are different governance signals.
- **Final score.** The H score, computed from the components.
- **Tier decision.** ALLOW / QUARANTINE / ESCALATE / DENY, with the threshold that was crossed.
- **Timestamp.** Millisecond-precision UTC.
- **Signature.** ML-DSA-65 signature over the above fields, using the pipeline's signing key.

The signature is what makes it a receipt rather than a log entry. Anyone with the pipeline's public key can verify the receipt without having access to the pipeline itself. The receipt doesn't require you to trust the system that issued it — it requires you to trust the cryptographic signature.

---

## Why ML-DSA-65

Classical ECDSA signatures work today. They don't work against a cryptographically relevant quantum computer, and governance receipts need to be valid for years.

The threat isn't that your audit logs will be decrypted — AES-256 payloads are quantum-resistant in practice. The threat is that the signatures binding the receipts to their contents will be forgeable. A quantum attacker with historical signing keys could retroactively create fraudulent receipts that pass signature verification. The entire audit history becomes untrustworthy.

ML-DSA-65 (NIST FIPS 204) is the post-quantum digital signature standard. It targets NIST security Level 3, equivalent to AES-192. Signing is fast enough for per-request use; signatures are ~3.3KB; verification is fast. The liboqs-python library provides the implementation via `import oqs`.

---

## The space ID as a receipt anchor

The operator system-space decision (which plane, which auth state, which governance ring) is also encoded in the receipt via the space ID:

```
space_id = SHA256(plane | auth_state | session_fingerprint)[:16]
```

The space ID is a 16-character hex string that's deterministic given the session's structural facts. It anchors the receipt to the agent's position in the system topology at decision time — not just "what was decided" but "where the agent was when it was decided."

For a web agent that claimed filesystem access and got flagged with `CROSS_PLANE_CLAIM`, the receipt includes the space ID, the flag, and the trust penalty applied. The claim and the response are both recorded, not just the outcome.

---

## The gap between logging and auditing

Logging answers: what happened?
Auditing answers: what happened, provably, in a form that a third party can verify without trusting you?

Most AI governance implementations do the first. The EU AI Act (Article 12) and NIST AI RMF require the second for high-risk systems. The gap is the cryptographic signature — not on the database entry, but on the exact computation that produced the decision, bound to the specific input that triggered it.

If your audit log isn't signed, it isn't an audit. It's a diary.

---

The receipt format is in `src/governance/`. The ML-DSA-65 signing implementation is in `src/crypto/`. Tests at `tests/crypto/`. Open source, MIT OR Apache-2.0.

[issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE)
