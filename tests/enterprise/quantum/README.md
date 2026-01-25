# Quantum Attack Simulation Tests

Tests for validating post-quantum cryptography resistance against quantum algorithms.

## Test Files

- `shor_attack.test.ts` - Shor's algorithm simulation (RSA factoring)
- `grover_attack.test.ts` - Grover's algorithm simulation (key search)
- `mlkem_validation.test.ts` - ML-KEM (Kyber) quantum resistance
- `mldsa_validation.test.ts` - ML-DSA (Dilithium) quantum resistance
- `lattice_hardness.test.ts` - Lattice problem hardness validation
- `security_bits.test.ts` - Quantum security bits measurement

## Properties Tested

- **Property 1**: Shor's Algorithm Resistance (AC-1.1)
- **Property 2**: Grover's Algorithm Resistance (AC-1.2)
- **Property 3**: ML-KEM Quantum Resistance (AC-1.3)
- **Property 4**: ML-DSA Quantum Resistance (AC-1.4)
- **Property 5**: Lattice Problem Hardness (AC-1.5)
- **Property 6**: Quantum Security Bits ≥256 (AC-1.6)

## Target Metrics

- Quantum security bits: ≥256
- Post-quantum primitives: ML-KEM-768, ML-DSA-65
- Simulation limit: ~20 qubits (classical simulation)
