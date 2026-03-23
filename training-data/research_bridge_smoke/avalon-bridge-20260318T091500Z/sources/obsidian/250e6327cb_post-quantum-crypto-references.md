# Post-Quantum Crypto References

> Academic foundations for ML-KEM (Kyber), ML-DSA (Dilithium), and dual-lattice security.

## NIST Standards (FIPS)

1. **NIST FIPS 203 (2024)** "Module-Lattice-Based Key-Encapsulation Mechanism Standard" (ML-KEM)
   - Formerly Kyber. Our implementation uses ML-KEM-768.
   - Security: ~2^192 against known quantum attacks
   - Relevant to: `kyber_encaps()`, `kyber_decaps()` in `six-tongues-cli.py`

2. **NIST FIPS 204 (2024)** "Module-Lattice-Based Digital Signature Standard" (ML-DSA)
   - Formerly Dilithium. Our implementation uses ML-DSA-65.
   - Relevant to: `dsa_sign()`, `dsa_verify()` in `six-tongues-cli.py`

## Lattice Cryptography Foundations

3. **Regev, O. (2005)** "On Lattices, Learning with Errors, Random Linear Codes, and Cryptography" — STOC
   - Foundational paper establishing LWE hardness
   - Relevant to: [[Dual Lattice Framework]] (MLWE security assumption)

4. **Peikert, C. (2016)** "A Decade of Lattice Cryptography" — Foundations and Trends in TCS
   - Comprehensive survey of lattice crypto
   - Relevant to: Understanding why dual-lattice consensus provides ~2^192 security

5. **Ajtai, M. (1996)** "Generating Hard Instances of Lattice Problems" — STOC
   - Worst-case to average-case reduction for lattice problems
   - Relevant to: Security guarantees of our lattice-based system

## Dual-Lattice Consensus

6. **Lyubashevsky, V. et al. (2010)** "On Ideal Lattices and Learning with Errors Over Rings" — EUROCRYPT
   - Ring-LWE foundation for module lattices
   - Relevant to: Why breaking one of KEM/DSA is insufficient (AND logic)

## Key Insight for SCBE

The [[Dual Lattice Framework]] requires BOTH ML-KEM (MLWE) AND ML-DSA (MSIS) to validate simultaneously within time window dt < epsilon. Breaking the system requires breaking both independent hard problems:
- **min(security_Kyber, security_Dilithium) = ~2^192**

## Cross-References
- [[Dual Lattice Framework]] — Our implementation
- [[14-Layer Architecture]] — PQC is Layer 14
- [[Grand Unified Statement]] — GeoSeal envelope uses dual-lattice
