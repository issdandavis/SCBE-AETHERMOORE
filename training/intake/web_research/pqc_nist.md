# Post-Quantum Cryptography Standards (NIST)

NIST's Post-Quantum Cryptography project addresses the cryptographic threat from future quantum computers capable of breaking current public-key algorithms (RSA, ECC, DH). Three principal standards were released in August 2024, with additional candidates in progress.

## FIPS 203: ML-KEM (Module-Lattice-Based Key-Encapsulation Mechanism)

Algorithm origin: CRYSTALS-Kyber. Purpose: Key establishment (key encapsulation). Based on the hardness of the Module Learning with Errors (MLWE) problem over structured lattices.

Security levels and parameters:
- ML-KEM-512: NIST Security Level 1 (equivalent to AES-128)
- ML-KEM-768: NIST Security Level 3 (equivalent to AES-192)
- ML-KEM-1024: NIST Security Level 5 (equivalent to AES-256)

Key sizes are significantly larger than RSA/ECC but operations are very fast. ML-KEM-768 public key is 1,184 bytes, ciphertext is 1,088 bytes. Encapsulation and decapsulation are faster than RSA key exchange.

## FIPS 204: ML-DSA (Module-Lattice-Based Digital Signature Standard)

Algorithm origin: CRYSTALS-Dilithium. Purpose: Digital signatures. Based on the hardness of the Module Learning with Errors (MLWE) and Module Short Integer Solution (MSIS) problems.

Security levels:
- ML-DSA-44: NIST Security Level 2
- ML-DSA-65: NIST Security Level 3
- ML-DSA-87: NIST Security Level 5

Primary recommended algorithm for digital signatures in most applications. Deterministic signing (no random number generation needed during signing), reducing side-channel attack surface.

## FIPS 205: SLH-DSA (Stateless Hash-Based Digital Signature Standard)

Algorithm origin: SPHINCS+. Purpose: Digital signatures with conservative security assumptions. Based solely on hash function security — if the hash function is secure, the signature scheme is secure.

Provides a fallback signature scheme that does not depend on lattice hardness assumptions. Larger signatures than ML-DSA but based on minimal cryptographic assumptions. Recommended as a hedge against potential future breaks in lattice-based schemes.

## Additional Candidates

### FN-DSA (Falcon)
Selected for standardization as an additional digital signature scheme. Based on NTRU lattice problems with fast Fourier sampling. Produces shorter signatures than ML-DSA but more complex implementation requiring careful floating-point handling.

### HQC
Selected as a 4th-round candidate for key encapsulation standardization. Code-based cryptography providing an alternative to lattice-based ML-KEM. Based on the hardness of decoding random quasi-cyclic codes.

## Migration Timeline

Under NIST IR 8547: quantum-vulnerable algorithms (RSA, ECC, DH, DSA) will be deprecated by 2035. High-risk systems should transition earlier. Organizations should begin identifying quantum-vulnerable systems, developing migration plans, and implementing hybrid approaches (classical + post-quantum) as transitional measures. The National Cybersecurity Center of Excellence supports organizations in planning PQC migration.
