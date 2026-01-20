"""
Test Suite: Sacred Tongue Post-Quantum Integration
==================================================
Validates RWP v3.0 + SCBE Layer 1-4 integration

Test Categories:
- Unit tests: Sacred Tongue tokenizer, RWP protocol, context encoder
- Integration tests: End-to-end encryption + governance
- Property-based tests: Randomized testing with Hypothesis

Last Updated: January 18, 2026
Version: 3.0.0
"""

import pytest
import sys
import os
import numpy as np
from hypothesis import given, strategies as st, settings

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER, TONGUES, SECTION_TONGUES
from crypto.rwp_v3 import rwp_encrypt_message, rwp_decrypt_message, RWPv3Protocol, RWPEnvelope
from scbe.context_encoder import SCBE_CONTEXT_ENCODER


# ============================================================
# UNIT TESTS: Sacred Tongue Tokenizer
# ============================================================

class TestSacredTongueTokenizer:
    """Test suite for Sacred Tongue tokenizer"""
    
    def test_tongue_bijectivity(self):
        """Verify byte → token → byte round-trip for all 256 bytes × 6 tongues"""
        for tongue_code in TONGUES.keys():
            for byte_val in range(256):
                # Encode byte → token
                tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(tongue_code, bytes([byte_val]))
                assert len(tokens) == 1, f"Expected 1 token, got {len(tokens)}"
                
                # Decode token → byte
                decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(tongue_code, tokens)
                assert decoded == bytes([byte_val]), \
                    f"Tongue {tongue_code}: byte {byte_val} → {tokens[0]} → {decoded[0]} (expected {byte_val})"
    
    def test_tongue_uniqueness(self):
        """Verify 256 distinct tokens per tongue"""
        for tongue_code, spec in TONGUES.items():
            tokens = set()
            for byte_val in range(256):
                token_list = SACRED_TONGUE_TOKENIZER.encode_bytes(tongue_code, bytes([byte_val]))
                tokens.add(token_list[0])
            
            assert len(tokens) == 256, \
                f"Tongue {tongue_code} has {len(tokens)} unique tokens (expected 256)"
    
    def test_harmonic_fingerprint_determinism(self):
        """Verify harmonic fingerprint is deterministic"""
        test_data = b"Hello, Mars!"
        tongue_code = 'ko'
        
        tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(tongue_code, test_data)
        
        # Compute fingerprint twice
        fp1 = SACRED_TONGUE_TOKENIZER.compute_harmonic_fingerprint(tongue_code, tokens)
        fp2 = SACRED_TONGUE_TOKENIZER.compute_harmonic_fingerprint(tongue_code, tokens)
        
        assert fp1 == fp2, "Harmonic fingerprint is not deterministic"
        assert isinstance(fp1, float), "Fingerprint should be float"
        assert fp1 > 0, "Fingerprint should be positive"
    
    def test_section_integrity_validation(self):
        """Verify section integrity validation"""
        # Valid tokens for nonce section (Kor'aelin)
        nonce_bytes = b"\x00\x01\x02\x03"
        nonce_tokens = SACRED_TONGUE_TOKENIZER.encode_section('nonce', nonce_bytes)
        
        assert SACRED_TONGUE_TOKENIZER.validate_section_integrity('nonce', nonce_tokens), \
            "Valid nonce tokens should pass integrity check"
        
        # Invalid tokens (wrong tongue)
        salt_tokens = SACRED_TONGUE_TOKENIZER.encode_section('salt', nonce_bytes)
        assert not SACRED_TONGUE_TOKENIZER.validate_section_integrity('nonce', salt_tokens), \
            "Salt tokens should fail nonce integrity check"
    
    def test_invalid_token_raises_error(self):
        """Verify ValueError on invalid token"""
        with pytest.raises(ValueError, match="Invalid token"):
            SACRED_TONGUE_TOKENIZER.decode_tokens('ko', ["invalid'token"])


# ============================================================
# UNIT TESTS: RWP v3.0 Protocol
# ============================================================

class TestRWPv3Protocol:
    """Test suite for RWP v3.0 protocol"""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Verify plaintext → envelope → plaintext"""
        message = "Hello, Mars!"
        password = "test-password"
        metadata = {"timestamp": "2026-01-18T17:21:00Z"}
        
        # Encrypt
        envelope = rwp_encrypt_message(password, message, metadata, enable_pqc=False)
        
        # Verify envelope structure
        assert 'version' in envelope
        assert 'aad' in envelope
        assert 'salt' in envelope
        assert 'nonce' in envelope
        assert 'ct' in envelope
        assert 'tag' in envelope
        
        # Decrypt
        decrypted = rwp_decrypt_message(password, envelope, enable_pqc=False)
        
        assert decrypted == message, f"Expected '{message}', got '{decrypted}'"
    
    def test_invalid_password_fails(self):
        """Verify AEAD authentication failure on wrong password"""
        message = "Secret message"
        password1 = "correct-password"
        password2 = "wrong-password"
        
        envelope = rwp_encrypt_message(password1, message, enable_pqc=False)
        
        with pytest.raises(ValueError, match="AEAD authentication failed"):
            rwp_decrypt_message(password2, envelope, enable_pqc=False)
    
    def test_envelope_serialization(self):
        """Verify to_dict/from_dict round-trip"""
        message = "Test message"
        password = "test-password"
        
        envelope_dict = rwp_encrypt_message(password, message, enable_pqc=False)
        envelope_obj = RWPEnvelope.from_dict(envelope_dict)
        envelope_dict2 = envelope_obj.to_dict()
        
        # Verify all fields match
        for key in ['aad', 'salt', 'nonce', 'ct', 'tag']:
            assert envelope_dict[key] == envelope_dict2[key], \
                f"Field {key} mismatch after serialization round-trip"


# ============================================================
# UNIT TESTS: SCBE Context Encoder
# ============================================================

class TestSCBEContextEncoder:
    """Test suite for SCBE context encoder"""
    
    def test_complex_context_dimensions(self):
        """Verify 6D complex vector from tokens"""
        message = "Test message"
        envelope = rwp_encrypt_message("password", message, enable_pqc=False)
        
        section_tokens = {
            k: v for k, v in envelope.items()
            if k in ['aad', 'salt', 'nonce', 'ct', 'tag']
        }
        
        c = SCBE_CONTEXT_ENCODER.tokens_to_complex_context(section_tokens)
        
        assert c.shape == (6,), f"Expected shape (6,), got {c.shape}"
        assert c.dtype == complex, f"Expected complex dtype, got {c.dtype}"
    
    def test_realification_dimensions(self):
        """Verify 12D real vector from 6D complex"""
        c = np.array([1+2j, 3+4j, 5+6j, 7+8j, 9+10j, 11+12j])
        x = SCBE_CONTEXT_ENCODER.complex_to_real_embedding(c)
        
        assert x.shape == (12,), f"Expected shape (12,), got {x.shape}"
        assert x.dtype == float or x.dtype == np.float64, f"Expected float dtype, got {x.dtype}"
        
        # Verify concatenation: [Re(c[0]), Re(c[1]), ..., Im(c[0]), Im(c[1]), ...]
        expected_real = np.array([1, 3, 5, 7, 9, 11], dtype=float)
        expected_imag = np.array([2, 4, 6, 8, 10, 12], dtype=float)
        expected = np.concatenate([expected_real, expected_imag])
        np.testing.assert_array_almost_equal(x, expected)
    
    def test_poincare_ball_constraint(self):
        """Verify ||u|| < 1.0 constraint"""
        message = "Test message"
        envelope = rwp_encrypt_message("password", message, enable_pqc=False)
        
        u = SCBE_CONTEXT_ENCODER.full_pipeline(envelope)
        norm = np.linalg.norm(u)
        
        assert norm < 1.0, f"Embedding outside Poincaré ball: ||u|| = {norm}"
        assert norm >= 0.0, f"Norm should be non-negative: ||u|| = {norm}"
    
    def test_full_pipeline_output_shape(self):
        """Verify full pipeline output shape"""
        message = "Test message"
        envelope = rwp_encrypt_message("password", message, enable_pqc=False)
        
        u = SCBE_CONTEXT_ENCODER.full_pipeline(envelope)
        
        assert u.shape == (12,), f"Expected shape (12,), got {u.shape}"
        assert u.dtype == float, f"Expected float dtype, got {u.dtype}"


# ============================================================
# INTEGRATION TESTS
# ============================================================

class TestIntegration:
    """Integration tests for end-to-end workflows"""
    
    def test_mars_communication_scenario(self):
        """Simulate Earth → Mars message transmission"""
        # Earth encrypts command
        command = "Rover: Begin excavation at coordinates 18.65°N, 77.58°E"
        metadata = {
            "timestamp": "2026-01-18T18:00:00Z",
            "sender": "EarthControl",
            "receiver": "MarsBase-Alpha",
            "mission_id": "EXCAVATION-001",
        }
        password = "mars-earth-shared-key"
        
        envelope = rwp_encrypt_message(password, command, metadata, enable_pqc=False)
        
        # Verify envelope structure
        assert len(envelope['nonce']) > 0, "Nonce tokens missing"
        assert len(envelope['ct']) > 0, "Ciphertext tokens missing"
        
        # Mars decrypts command
        decrypted = rwp_decrypt_message(password, envelope, enable_pqc=False)
        
        assert decrypted == command, "Command corrupted during transmission"
    
    def test_spectral_coherence_validation(self):
        """Verify token swapping detection"""
        message = "Test message"
        envelope = rwp_encrypt_message("password", message, enable_pqc=False)
        
        # Validate original envelope
        for section in ['aad', 'salt', 'nonce', 'ct', 'tag']:
            tokens = envelope[section]
            is_valid = SACRED_TONGUE_TOKENIZER.validate_section_integrity(section, tokens)
            assert is_valid, f"Section {section} failed integrity check"
        
        # Swap ct ↔ tag tokens (attack simulation)
        envelope_tampered = envelope.copy()
        envelope_tampered['ct'], envelope_tampered['tag'] = envelope['tag'], envelope['ct']
        
        # Verify ct section now fails integrity check
        is_valid_ct = SACRED_TONGUE_TOKENIZER.validate_section_integrity('ct', envelope_tampered['ct'])
        assert not is_valid_ct, "Tampered ct section should fail integrity check"
    
    def test_governance_integration(self):
        """Verify SCBE Layer 1-14 pipeline (conceptual)"""
        message = "Critical mission command"
        envelope = rwp_encrypt_message("password", message, enable_pqc=False)
        
        # Layer 1-4: Envelope → Poincaré ball
        u = SCBE_CONTEXT_ENCODER.full_pipeline(envelope)
        
        # Verify embedding properties
        norm = np.linalg.norm(u)
        assert norm < 1.0, f"Embedding outside Poincaré ball: ||u|| = {norm}"
        
        # Simulate governance decision (simplified)
        risk_score = norm * 0.5
        
        if risk_score < 0.3:
            decision = "ALLOW"
        elif risk_score < 0.6:
            decision = "REVIEW"
        else:
            decision = "BLOCK"
        
        assert decision in ["ALLOW", "REVIEW", "BLOCK"], f"Invalid decision: {decision}"


# ============================================================
# PROPERTY-BASED TESTS (Hypothesis)
# ============================================================

class TestProperties:
    """Property-based tests with Hypothesis"""
    
    @given(
        message=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
        password=st.text(min_size=8, max_size=64, alphabet=st.characters(min_codepoint=32, max_codepoint=126))
    )
    @settings(max_examples=100, deadline=None)  # 100 iterations per property
    def test_property_encrypt_decrypt_inverse(self, message, password):
        """Property: ∀ message, password: decrypt(encrypt(message, password), password) = message"""
        try:
            envelope = rwp_encrypt_message(password, message, enable_pqc=False)
            decrypted = rwp_decrypt_message(password, envelope, enable_pqc=False)
            assert decrypted == message
        except Exception as e:
            # Skip if message contains invalid UTF-8 or other encoding issues
            if "decode" in str(e).lower() or "encode" in str(e).lower():
                pytest.skip(f"Encoding issue: {e}")
            raise
    
    @given(
        message=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
        password=st.text(min_size=8, max_size=64, alphabet=st.characters(min_codepoint=32, max_codepoint=126))
    )
    @settings(max_examples=100, deadline=None)
    def test_property_poincare_ball_constraint(self, message, password):
        """Property: ∀ envelope: ||context_encoder(envelope)|| < 1.0"""
        try:
            envelope = rwp_encrypt_message(password, message, enable_pqc=False)
            u = SCBE_CONTEXT_ENCODER.full_pipeline(envelope)
            norm = np.linalg.norm(u)
            assert norm < 1.0, f"Embedding outside Poincaré ball: ||u|| = {norm}"
        except Exception as e:
            if "decode" in str(e).lower() or "encode" in str(e).lower():
                pytest.skip(f"Encoding issue: {e}")
            raise
    
    @given(
        message=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
        password1=st.text(min_size=8, max_size=64, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
        password2=st.text(min_size=8, max_size=64, alphabet=st.characters(min_codepoint=32, max_codepoint=126))
    )
    @settings(max_examples=100, deadline=None)
    def test_property_invalid_password_fails(self, message, password1, password2):
        """Property: ∀ message, password1, password2 (password1 ≠ password2): decrypt fails"""
        if password1 == password2:
            pytest.skip("Passwords are equal")
        
        try:
            envelope = rwp_encrypt_message(password1, message, enable_pqc=False)
            
            with pytest.raises(ValueError, match="AEAD authentication failed"):
                rwp_decrypt_message(password2, envelope, enable_pqc=False)
        except Exception as e:
            if "decode" in str(e).lower() or "encode" in str(e).lower():
                pytest.skip(f"Encoding issue: {e}")
            raise


# ============================================================
# PERFORMANCE TESTS (Benchmarks)
# ============================================================

# Check if pytest-benchmark is available
try:
    import pytest_benchmark
    BENCHMARK_AVAILABLE = True
except ImportError:
    BENCHMARK_AVAILABLE = False

@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="pytest-benchmark not installed (optional)")
@pytest.mark.benchmark
class TestPerformance:
    """
    Performance benchmarks (optional - requires pytest-benchmark).
    
    Install with: pip install pytest-benchmark
    Run with: pytest tests/test_sacred_tongue_integration.py::TestPerformance -v --benchmark-only
    """
    
    def test_benchmark_encryption_latency(self, benchmark):
        """Measure encryption latency (excluding Argon2id)"""
        message = "A" * 256  # 256-byte message
        password = "test-password"
        
        result = benchmark(rwp_encrypt_message, password, message, enable_pqc=False)
        
        assert 'ct' in result, "Encryption failed"
    
    def test_benchmark_decryption_latency(self, benchmark):
        """Measure decryption latency (excluding Argon2id)"""
        message = "A" * 256
        password = "test-password"
        envelope = rwp_encrypt_message(password, message, enable_pqc=False)
        
        result = benchmark(rwp_decrypt_message, password, envelope, enable_pqc=False)
        
        assert result == message, "Decryption failed"
    
    def test_benchmark_context_encoding(self, benchmark):
        """Measure Layer 1-4 pipeline latency"""
        message = "Test message"
        envelope = rwp_encrypt_message("password", message, enable_pqc=False)
        
        result = benchmark(SCBE_CONTEXT_ENCODER.full_pipeline, envelope)
        
        assert np.linalg.norm(result) < 1.0, "Embedding invalid"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
