# Thread: Post-Quantum Cryptography in Practice

---

Q-Day — when quantum computers break RSA and elliptic curve crypto — is coming within the decade.

"Harvest now, decrypt later" attacks are already happening.

Here's how SCBE-AETHERMOORE is quantum-ready TODAY:

---

We implement NIST's finalized post-quantum standards:

ML-KEM-768 (formerly Kyber) — key encapsulation
ML-DSA-65 (formerly Dilithium) — digital signatures
AES-256-GCM — symmetric (already quantum-resistant at 256-bit)

Based on lattice problems that even quantum computers can't crack.

---

Where PQC is used in SCBE:

- ML-KEM-768: Securing inter-layer pipeline communication, fleet agent comms, encrypted telemetry
- ML-DSA-65: Signing governance decisions (ALLOW/DENY), authenticating layer outputs, non-repudiation of safety attestations

---

Performance is production-ready:

ML-KEM-768 keygen: ~0.1ms
ML-DSA-65 signing: ~0.5ms

Key sizes are larger than RSA (1.2KB vs 256B public keys) but manageable for governance-frequency operations.

---

The real innovation: PQC + hyperbolic geometry = orthogonal defense.

Hyperbolic geometry makes adversarial INTENT exponentially expensive.
PQC makes adversarial TAMPERING computationally infeasible.

You can't afford to be adversarial AND you can't fake being safe.

---

Even with a quantum computer, you can't:
- Forge governance signatures
- Decrypt pipeline communications
- Break key exchange
- Game the hyperbolic cost scaling

Both defenses are independently quantum-resistant.

Open source: github.com/issdandavis/SCBE-AETHERMOORE

#PostQuantum #Cryptography #AISafety #QuantumComputing
