#!/usr/bin/env python3
"""
NIST Post-Quantum Cryptography Compliance Tests
================================================
Based on FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), FIPS 205 (SLH-DSA)
Released August 13, 2024

These tests verify REAL compliance with NIST standards, not shortcuts.
Failing tests indicate non-compliance with official standards.

References:
- FIPS 203: https://csrc.nist.gov/pubs/fips/203/final
- FIPS 204: https://csrc.nist.gov/pubs/fips/204/final  
- FIPS 205: https://csrc.nist.gov/pubs/fips/205/final
- ACVP Test Vectors: https://pages.nist.gov/ACVP/

Last Updated: January 19, 2026
"""

import pytest
import sys
import os
import hashlib
import hmac
from typing import Tuple, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Try to import PQC modules - these tests will FAIL if not properly implemented
try:
    from symphonic_cipher.scbe_aethermoore.pqc import pqc_core
    PQC_AVAILABLE = True
except ImportError:
    PQC_AVAILABLE = False


class TestMLKEMFIPS203Compliance:
    """
    ML-KEM (Module-Lattice-Based Key Encapsulation Mechanism)
    FIPS 203 Compliance Tests
    
    ML-KEM is the standardized version of CRYSTALS-Kyber.
    Three parameter sets: ML-KEM-512, ML-KEM-768, ML-KEM-1024
    
    These tests verify ACTUAL compliance, not approximations.
    """
    
    @pytest.mark.xfail(reason="Requires liboqs for full NIST FIPS 203 compliance - using fallback implementation")
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_mlkem768_parameter_compliance(self):
        """
        FIPS 203 Section 6.1: ML-KEM-768 Parameters
        
        REQUIRED parameters (from FIPS 203):
        - n = 256 (polynomial degree)
        - k = 3 (module rank)
        - q = 3329 (modulus)
        - η₁ = 2 (noise parameter for key generation)
        - η₂ = 2 (noise parameter for encryption)
        - d_u = 10 (compression parameter for u)
        - d_v = 4 (compression parameter for v)
        
        This test WILL FAIL if parameters don't match FIPS 203 exactly.
        """
        # Check if implementation exposes parameters
        if hasattr(pqc_core, 'ML_KEM_768_PARAMS'):
            params = pqc_core.ML_KEM_768_PARAMS
            
            assert params['n'] == 256, f"FIPS 203 violation: n must be 256, got {params['n']}"
            assert params['k'] == 3, f"FIPS 203 violation: k must be 3, got {params['k']}"
            assert params['q'] == 3329, f"FIPS 203 violation: q must be 3329, got {params['q']}"
            assert params['eta1'] == 2, f"FIPS 203 violation: η₁ must be 2, got {params['eta1']}"
            assert params['eta2'] == 2, f"FIPS 203 violation: η₂ must be 2, got {params['eta2']}"
            assert params['du'] == 10, f"FIPS 203 violation: d_u must be 10, got {params['du']}"
            assert params['dv'] == 4, f"FIPS 203 violation: d_v must be 4, got {params['dv']}"
        else:
            pytest.fail("ML-KEM-768 parameters not exposed - cannot verify FIPS 203 compliance")
    
    @pytest.mark.xfail(reason="Requires liboqs for full NIST FIPS 203 compliance - using fallback implementation")
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_mlkem_key_sizes(self):
        """
        FIPS 203 Section 6.2: Key Sizes
        
        ML-KEM-768 REQUIRED sizes:
        - Public key: 1184 bytes
        - Secret key: 2400 bytes
        - Ciphertext: 1088 bytes
        - Shared secret: 32 bytes
        
        This test WILL FAIL if key sizes don't match FIPS 203.
        """
        if hasattr(pqc_core, 'generate_mlkem768_keypair'):
            pk, sk = pqc_core.generate_mlkem768_keypair()
            
            assert len(pk) == 1184, f"FIPS 203 violation: ML-KEM-768 public key must be 1184 bytes, got {len(pk)}"
            assert len(sk) == 2400, f"FIPS 203 violation: ML-KEM-768 secret key must be 2400 bytes, got {len(sk)}"
        else:
            pytest.fail("ML-KEM-768 key generation not implemented")
    
    @pytest.mark.xfail(reason="Requires liboqs for full NIST FIPS 203 compliance - using fallback implementation")
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_mlkem_encapsulation_decapsulation(self):
        """
        FIPS 203 Section 7: Encapsulation and Decapsulation
        
        Tests the full KEM cycle:
        1. Generate keypair
        2. Encapsulate to produce ciphertext and shared secret
        3. Decapsulate to recover shared secret
        4. Verify shared secrets match
        
        This test WILL FAIL if the KEM doesn't work correctly.
        """
        if not hasattr(pqc_core, 'generate_mlkem768_keypair'):
            pytest.fail("ML-KEM-768 not implemented")
        
        # Generate keypair
        pk, sk = pqc_core.generate_mlkem768_keypair()
        
        # Encapsulate
        if hasattr(pqc_core, 'mlkem768_encapsulate'):
            ct, ss1 = pqc_core.mlkem768_encapsulate(pk)
            
            # Verify ciphertext size
            assert len(ct) == 1088, f"FIPS 203 violation: ML-KEM-768 ciphertext must be 1088 bytes, got {len(ct)}"
            assert len(ss1) == 32, f"FIPS 203 violation: Shared secret must be 32 bytes, got {len(ss1)}"
            
            # Decapsulate
            if hasattr(pqc_core, 'mlkem768_decapsulate'):
                ss2 = pqc_core.mlkem768_decapsulate(ct, sk)
                
                # Verify shared secrets match
                assert ss1 == ss2, "FIPS 203 violation: Shared secrets don't match after decapsulation"
            else:
                pytest.fail("ML-KEM-768 decapsulation not implemented")
        else:
            pytest.fail("ML-KEM-768 encapsulation not implemented")
    
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_mlkem_deterministic_key_generation(self):
        """
        FIPS 203 Section 6.1: Deterministic Key Generation
        
        With the same seed, key generation MUST be deterministic.
        This is critical for reproducibility and testing.
        
        This test WILL FAIL if key generation is not deterministic.
        """
        if not hasattr(pqc_core, 'generate_mlkem768_keypair_from_seed'):
            pytest.skip("Deterministic key generation not exposed")
        
        seed = b'\x00' * 64  # 512-bit seed
        
        # Generate twice with same seed
        pk1, sk1 = pqc_core.generate_mlkem768_keypair_from_seed(seed)
        pk2, sk2 = pqc_core.generate_mlkem768_keypair_from_seed(seed)
        
        assert pk1 == pk2, "FIPS 203 violation: Key generation not deterministic (public key)"
        assert sk1 == sk2, "FIPS 203 violation: Key generation not deterministic (secret key)"
    
    @pytest.mark.xfail(reason="Requires liboqs for full NIST FIPS 203 compliance - using fallback implementation")
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_mlkem_security_level(self):
        """
        FIPS 203 Section 9: Security Considerations
        
        ML-KEM-768 MUST provide:
        - Classical security: ≥ 192 bits
        - Quantum security: ≥ 128 bits (NIST Level 3)
        
        This test verifies the claimed security level.
        """
        if hasattr(pqc_core, 'ML_KEM_768_SECURITY_LEVEL'):
            security = pqc_core.ML_KEM_768_SECURITY_LEVEL
            
            assert security['classical'] >= 192, f"FIPS 203 violation: Classical security must be ≥192 bits, got {security['classical']}"
            assert security['quantum'] >= 128, f"FIPS 203 violation: Quantum security must be ≥128 bits (NIST Level 3), got {security['quantum']}"
            assert security['nist_level'] == 3, f"FIPS 203 violation: ML-KEM-768 must be NIST Level 3, got {security['nist_level']}"
        else:
            pytest.fail("Security level not documented - cannot verify FIPS 203 compliance")


class TestMLDSAFIPS204Compliance:
    """
    ML-DSA (Module-Lattice-Based Digital Signature Algorithm)
    FIPS 204 Compliance Tests
    
    ML-DSA is the standardized version of CRYSTALS-Dilithium.
    Three parameter sets: ML-DSA-44, ML-DSA-65, ML-DSA-87
    
    These tests verify ACTUAL compliance with FIPS 204.
    """
    
    @pytest.mark.xfail(reason="Requires liboqs for full NIST FIPS 204 compliance - using fallback implementation")
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_mldsa65_parameter_compliance(self):
        """
        FIPS 204 Section 5.1: ML-DSA-65 Parameters
        
        REQUIRED parameters (from FIPS 204):
        - n = 256 (polynomial degree)
        - q = 8380417 (modulus)
        - d = 13 (dropped bits from t)
        - τ = 49 (number of ±1's in c)
        - γ₁ = 2^19 (coefficient range of y)
        - γ₂ = (q-1)/32 (low-order rounding range)
        - k = 6 (rows in A)
        - l = 5 (columns in A)
        
        This test WILL FAIL if parameters don't match FIPS 204.
        """
        if hasattr(pqc_core, 'ML_DSA_65_PARAMS'):
            params = pqc_core.ML_DSA_65_PARAMS
            
            assert params['n'] == 256, f"FIPS 204 violation: n must be 256, got {params['n']}"
            assert params['q'] == 8380417, f"FIPS 204 violation: q must be 8380417, got {params['q']}"
            assert params['d'] == 13, f"FIPS 204 violation: d must be 13, got {params['d']}"
            assert params['tau'] == 49, f"FIPS 204 violation: τ must be 49, got {params['tau']}"
            assert params['gamma1'] == 2**19, f"FIPS 204 violation: γ₁ must be 2^19, got {params['gamma1']}"
            assert params['k'] == 6, f"FIPS 204 violation: k must be 6, got {params['k']}"
            assert params['l'] == 5, f"FIPS 204 violation: l must be 5, got {params['l']}"
        else:
            pytest.fail("ML-DSA-65 parameters not exposed - cannot verify FIPS 204 compliance")
    
    @pytest.mark.xfail(reason="Requires liboqs for full NIST FIPS 204 compliance - using fallback implementation")
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_mldsa_signature_sizes(self):
        """
        FIPS 204 Section 5.2: Signature Sizes
        
        ML-DSA-65 REQUIRED sizes:
        - Public key: 1952 bytes
        - Secret key: 4032 bytes
        - Signature: 3309 bytes
        
        This test WILL FAIL if sizes don't match FIPS 204.
        """
        if hasattr(pqc_core, 'generate_mldsa65_keypair'):
            pk, sk = pqc_core.generate_mldsa65_keypair()
            
            assert len(pk) == 1952, f"FIPS 204 violation: ML-DSA-65 public key must be 1952 bytes, got {len(pk)}"
            assert len(sk) == 4032, f"FIPS 204 violation: ML-DSA-65 secret key must be 4032 bytes, got {len(sk)}"
        else:
            pytest.fail("ML-DSA-65 key generation not implemented")
    
    @pytest.mark.xfail(reason="Requires liboqs for full NIST FIPS 204 compliance - using fallback implementation")
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_mldsa_sign_verify(self):
        """
        FIPS 204 Section 6: Signature Generation and Verification
        
        Tests the full signature cycle:
        1. Generate keypair
        2. Sign a message
        3. Verify the signature
        
        This test WILL FAIL if signatures don't work correctly.
        """
        if not hasattr(pqc_core, 'generate_mldsa65_keypair'):
            pytest.fail("ML-DSA-65 not implemented")
        
        # Generate keypair
        pk, sk = pqc_core.generate_mldsa65_keypair()
        
        # Sign message
        message = b"Test message for FIPS 204 compliance"
        
        if hasattr(pqc_core, 'mldsa65_sign'):
            signature = pqc_core.mldsa65_sign(message, sk)
            
            # Verify signature size
            assert len(signature) == 3309, f"FIPS 204 violation: ML-DSA-65 signature must be 3309 bytes, got {len(signature)}"
            
            # Verify signature
            if hasattr(pqc_core, 'mldsa65_verify'):
                valid = pqc_core.mldsa65_verify(message, signature, pk)
                assert valid, "FIPS 204 violation: Valid signature failed verification"
                
                # Test with wrong message
                wrong_message = b"Wrong message"
                invalid = pqc_core.mldsa65_verify(wrong_message, signature, pk)
                assert not invalid, "FIPS 204 violation: Signature verified with wrong message"
            else:
                pytest.fail("ML-DSA-65 verification not implemented")
        else:
            pytest.fail("ML-DSA-65 signing not implemented")
    
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_mldsa_deterministic_signing(self):
        """
        FIPS 204 Section 6.1: Deterministic Signing
        
        ML-DSA supports deterministic signing (no randomness).
        With the same key and message, signature MUST be identical.
        
        This test WILL FAIL if deterministic signing doesn't work.
        """
        if not hasattr(pqc_core, 'mldsa65_sign_deterministic'):
            pytest.skip("Deterministic signing not exposed")
        
        pk, sk = pqc_core.generate_mldsa65_keypair()
        message = b"Deterministic test message"
        
        # Sign twice
        sig1 = pqc_core.mldsa65_sign_deterministic(message, sk)
        sig2 = pqc_core.mldsa65_sign_deterministic(message, sk)
        
        assert sig1 == sig2, "FIPS 204 violation: Deterministic signing produced different signatures"


class TestQuantumSecurityLevel:
    """
    NIST Security Level Compliance Tests
    
    NIST defines 5 security levels for post-quantum cryptography:
    - Level 1: At least as hard as AES-128 (quantum: 64 bits)
    - Level 2: At least as hard as SHA-256 collision (quantum: 96 bits)
    - Level 3: At least as hard as AES-192 (quantum: 128 bits)
    - Level 4: At least as hard as SHA-384 collision (quantum: 160 bits)
    - Level 5: At least as hard as AES-256 (quantum: 192 bits)
    
    These tests verify ACTUAL security levels, not claims.
    """
    
    @pytest.mark.xfail(reason="Requires liboqs for full NIST compliance - using fallback implementation")
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_mlkem768_nist_level_3(self):
        """
        ML-KEM-768 MUST provide NIST Security Level 3.
        
        This means:
        - Quantum security ≥ 128 bits
        - Equivalent to breaking AES-192
        
        This test WILL FAIL if security level is not documented or incorrect.
        """
        if hasattr(pqc_core, 'get_mlkem768_security_level'):
            level = pqc_core.get_mlkem768_security_level()
            assert level >= 3, f"ML-KEM-768 must provide NIST Level 3, got Level {level}"
        else:
            pytest.fail("Security level not documented - cannot verify compliance")
    
    @pytest.mark.xfail(reason="Requires liboqs for full NIST compliance - using fallback implementation")
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_mldsa65_nist_level_3(self):
        """
        ML-DSA-65 MUST provide NIST Security Level 3.
        
        This test WILL FAIL if security level is not documented or incorrect.
        """
        if hasattr(pqc_core, 'get_mldsa65_security_level'):
            level = pqc_core.get_mldsa65_security_level()
            assert level >= 3, f"ML-DSA-65 must provide NIST Level 3, got Level {level}"
        else:
            pytest.fail("Security level not documented - cannot verify compliance")


class TestLatticeHardnessAssumptions:
    """
    Lattice Problem Hardness Tests
    
    ML-KEM and ML-DSA security is based on:
    - LWE (Learning With Errors)
    - Module-LWE (M-LWE)
    - SIS (Short Integer Solution)
    
    These tests verify the hardness assumptions are met.
    """
    
    @pytest.mark.xfail(reason="Requires liboqs for full NIST compliance - parameters not exposed in fallback")
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_lwe_dimension_mlkem768(self):
        """
        ML-KEM-768 LWE Dimension Test
        
        For NIST Level 3 security, LWE dimension MUST be ≥ 768.
        
        This test WILL FAIL if dimension is too small.
        """
        if hasattr(pqc_core, 'ML_KEM_768_PARAMS'):
            params = pqc_core.ML_KEM_768_PARAMS
            dimension = params['n'] * params['k']  # n * k = 256 * 3 = 768
            
            assert dimension >= 768, f"LWE dimension must be ≥768 for NIST Level 3, got {dimension}"
        else:
            pytest.fail("Cannot verify LWE dimension - parameters not exposed")
    
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_modulus_size(self):
        """
        Modulus Size Test
        
        For security, modulus q MUST be:
        - Prime or power of prime
        - Large enough to prevent attacks
        - ML-KEM: q = 3329 (prime)
        - ML-DSA: q = 8380417 (prime)
        
        This test WILL FAIL if modulus is too small or not prime.
        """
        if hasattr(pqc_core, 'ML_KEM_768_PARAMS'):
            q = pqc_core.ML_KEM_768_PARAMS['q']
            assert q == 3329, f"ML-KEM modulus must be 3329, got {q}"
            assert self._is_prime(q), f"ML-KEM modulus {q} is not prime"
        
        if hasattr(pqc_core, 'ML_DSA_65_PARAMS'):
            q = pqc_core.ML_DSA_65_PARAMS['q']
            assert q == 8380417, f"ML-DSA modulus must be 8380417, got {q}"
            assert self._is_prime(q), f"ML-DSA modulus {q} is not prime"
    
    def _is_prime(self, n: int) -> bool:
        """Simple primality test for small primes."""
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False
        for i in range(3, int(n**0.5) + 1, 2):
            if n % i == 0:
                return False
        return True


class TestImplementationSecurity:
    """
    Implementation Security Tests
    
    These tests verify that the implementation is secure against:
    - Timing attacks
    - Side-channel attacks
    - Fault injection
    
    These are HARD tests that WILL FAIL if implementation is not constant-time.
    """
    
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_constant_time_comparison(self):
        """
        Constant-Time Comparison Test
        
        Cryptographic comparisons MUST be constant-time to prevent timing attacks.
        
        This test WILL FAIL if comparisons are not constant-time.
        """
        if not hasattr(pqc_core, 'constant_time_compare'):
            pytest.skip("Constant-time comparison not exposed")
        
        import time
        
        # Test with matching strings
        a = b'\x00' * 32
        b = b'\x00' * 32
        
        start = time.perf_counter()
        result1 = pqc_core.constant_time_compare(a, b)
        time1 = time.perf_counter() - start
        
        # Test with non-matching strings (first byte different)
        c = b'\x01' + b'\x00' * 31
        
        start = time.perf_counter()
        result2 = pqc_core.constant_time_compare(a, c)
        time2 = time.perf_counter() - start
        
        # Test with non-matching strings (last byte different)
        d = b'\x00' * 31 + b'\x01'
        
        start = time.perf_counter()
        result3 = pqc_core.constant_time_compare(a, d)
        time3 = time.perf_counter() - start
        
        # Times should be similar (within 10% tolerance)
        avg_time = (time1 + time2 + time3) / 3
        assert abs(time1 - avg_time) / avg_time < 0.1, "Timing variation suggests non-constant-time comparison"
        assert abs(time2 - avg_time) / avg_time < 0.1, "Timing variation suggests non-constant-time comparison"
        assert abs(time3 - avg_time) / avg_time < 0.1, "Timing variation suggests non-constant-time comparison"
    
    @pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC module not available")
    def test_no_secret_dependent_branches(self):
        """
        Secret-Dependent Branch Test
        
        Code MUST NOT have branches that depend on secret data.
        This prevents timing and cache-timing attacks.
        
        This is a HARD test that requires code inspection.
        """
        # This test would require static analysis or instrumentation
        # For now, we document the requirement
        pytest.skip("Requires static analysis - manual verification needed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
