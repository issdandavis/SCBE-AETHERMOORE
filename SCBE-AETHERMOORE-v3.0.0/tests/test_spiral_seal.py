"""
Tests for SpiralSeal SS1 implementation.

Last Updated: January 18, 2026
Version: 2.0.0
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from symphonic_cipher.scbe_aethermoore.spiral_seal import (
    SpiralSealSS1,
    SacredTongueTokenizer,
    encode_to_spelltext,
    decode_from_spelltext,
)
from symphonic_cipher.scbe_aethermoore.spiral_seal.sacred_tongues import (
    TONGUES, format_ss1_blob, parse_ss1_blob
)
from symphonic_cipher.scbe_aethermoore.spiral_seal.seal import seal, unseal


class TestSacredTongueTokenizer:
    """Tests for Sacred Tongue spell-text encoding."""
    
    def test_all_tongues_have_256_tokens(self):
        """Each tongue should have exactly 256 unique tokens (16×16)."""
        for code, tongue in TONGUES.items():
            assert len(tongue.prefixes) == 16, f"{code} has {len(tongue.prefixes)} prefixes"
            assert len(tongue.suffixes) == 16, f"{code} has {len(tongue.suffixes)} suffixes"
            
            # Verify all 256 tokens are unique
            tokenizer = SacredTongueTokenizer(code)
            tokens = set()
            for b in range(256):
                token = tokenizer.encode_byte(b)
                assert token not in tokens, f"Duplicate token in {code}: {token}"
                tokens.add(token)
            assert len(tokens) == 256
    
    def test_roundtrip_single_byte(self):
        """Encoding and decoding a single byte should be lossless."""
        for code in TONGUES.keys():
            tokenizer = SacredTongueTokenizer(code)
            for b in range(256):
                token = tokenizer.encode_byte(b)
                decoded = tokenizer.decode_token(token)
                assert decoded == b, f"Roundtrip failed for {code}: {b} -> {token} -> {decoded}"
    
    def test_roundtrip_bytes(self):
        """Encoding and decoding arbitrary bytes should be lossless."""
        test_data = b"Hello, SpiralSeal!"
        
        for code in TONGUES.keys():
            tokenizer = SacredTongueTokenizer(code)
            encoded = tokenizer.encode(test_data)
            decoded = tokenizer.decode(encoded)
            assert decoded == test_data, f"Roundtrip failed for {code}"
    
    def test_token_format(self):
        """Tokens should have the format 'prefix'suffix'."""
        tokenizer = SacredTongueTokenizer('ko')  # Kor'aelin
        
        # Byte 0x00 should be first prefix + first suffix
        token = tokenizer.encode_byte(0x00)
        assert token == "sil'a"
        
        # Byte 0xFF should be last prefix + last suffix
        token = tokenizer.encode_byte(0xFF)
        assert token == "vara'esh"
        
        # Byte 0x2A (42) = prefix[2] + suffix[10]
        token = tokenizer.encode_byte(0x2A)
        assert token == "vel'an"
    
    def test_section_encoding(self):
        """Section-specific encoding should use correct tongues."""
        test_data = b"\x00\x01\x02"
        
        # Salt uses Runethic (ru)
        salt_encoded = encode_to_spelltext(test_data, 'salt')
        assert 'ru:' in salt_encoded
        
        # Nonce uses Kor'aelin (ko)
        nonce_encoded = encode_to_spelltext(test_data, 'nonce')
        assert 'ko:' in nonce_encoded
        
        # Ciphertext uses Cassisivadan (ca)
        ct_encoded = encode_to_spelltext(test_data, 'ct')
        assert 'ca:' in ct_encoded


class TestSS1Format:
    """Tests for SS1 blob formatting and parsing."""
    
    def test_format_and_parse_roundtrip(self):
        """Formatting and parsing SS1 blob should be lossless."""
        salt = b'\x01\x02\x03\x04'
        nonce = b'\x05\x06\x07\x08'
        ciphertext = b'\x09\x0a\x0b\x0c'
        tag = b'\x0d\x0e\x0f\x10'
        
        blob = format_ss1_blob(
            kid='k01',
            aad='service=test',
            salt=salt,
            nonce=nonce,
            ciphertext=ciphertext,
            tag=tag
        )
        
        assert blob.startswith('SS1|')
        
        parsed = parse_ss1_blob(blob)
        assert parsed['version'] == 'SS1'
        assert parsed['kid'] == 'k01'
        assert parsed['aad'] == 'service=test'
        assert parsed['salt'] == salt
        assert parsed['nonce'] == nonce
        assert parsed['ct'] == ciphertext
        assert parsed['tag'] == tag


class TestSpiralSealSS1:
    """Tests for the main SpiralSeal API."""
    
    def test_seal_unseal_roundtrip(self):
        """Sealing and unsealing should recover original plaintext."""
        master_secret = b'0' * 32  # Test key
        plaintext = b"My secret API key: sk-1234567890"
        aad = "service=openai;env=prod"
        
        ss = SpiralSealSS1(master_secret=master_secret, kid='k01')
        
        sealed = ss.seal(plaintext, aad=aad)
        assert sealed.startswith('SS1|')
        
        unsealed = ss.unseal(sealed, aad=aad)
        assert unsealed == plaintext
    
    def test_aad_mismatch_fails(self):
        """Unsealing with wrong AAD should fail."""
        master_secret = b'0' * 32
        plaintext = b"secret"
        
        ss = SpiralSealSS1(master_secret=master_secret)
        sealed = ss.seal(plaintext, aad="correct_aad")
        
        with pytest.raises(ValueError, match="AAD mismatch"):
            ss.unseal(sealed, aad="wrong_aad")
    
    def test_tampered_ciphertext_fails(self):
        """Tampered ciphertext should fail authentication."""
        master_secret = b'0' * 32
        plaintext = b"secret"
        
        ss = SpiralSealSS1(master_secret=master_secret)
        sealed = ss.seal(plaintext, aad="test")
        
        # Parse the blob, modify the tag bytes directly, then reformat
        from symphonic_cipher.scbe_aethermoore.spiral_seal.sacred_tongues import (
            parse_ss1_blob, format_ss1_blob
        )
        
        parsed = parse_ss1_blob(sealed)
        
        # Tamper with the tag (flip a byte)
        original_tag = parsed['tag']
        tampered_tag = bytes([original_tag[0] ^ 0xFF]) + original_tag[1:]
        
        # Reformat with tampered tag
        tampered_blob = format_ss1_blob(
            kid=parsed['kid'],
            aad=parsed['aad'],
            salt=parsed['salt'],
            nonce=parsed['nonce'],
            ciphertext=parsed['ct'],
            tag=tampered_tag
        )
        
        with pytest.raises(ValueError, match="Authentication failed"):
            ss.unseal(tampered_blob, aad="test")
    
    def test_convenience_functions(self):
        """Test one-shot seal/unseal functions."""
        master_secret = b'1' * 32
        plaintext = b"quick test"
        aad = "test"
        
        sealed = seal(plaintext, master_secret, aad=aad, kid='k02')
        assert 'kid=k02' in sealed
        
        unsealed = unseal(sealed, master_secret, aad=aad)
        assert unsealed == plaintext
    
    def test_key_rotation(self):
        """Key rotation should work correctly."""
        old_secret = b'old_key_' + b'0' * 24
        new_secret = b'new_key_' + b'1' * 24
        plaintext = b"rotate me"
        
        ss = SpiralSealSS1(master_secret=old_secret, kid='k01')
        sealed_old = ss.seal(plaintext, aad="test")
        
        # Rotate key
        ss.rotate_key('k02', new_secret)
        sealed_new = ss.seal(plaintext, aad="test")
        
        assert 'kid=k01' in sealed_old
        assert 'kid=k02' in sealed_new
        
        # Old blob should fail with new key
        with pytest.raises(ValueError):
            ss.unseal(sealed_old, aad="test")
    
    def test_status_report(self):
        """Status report should include backend info."""
        status = SpiralSealSS1.get_status()
        
        assert status['version'] == 'SS1'
        assert 'key_exchange' in status
        assert 'signatures' in status
        assert 'backend' in status['key_exchange']


class TestCryptoBackends:
    """Tests for cryptographic backend availability."""
    
    def test_utils_available(self):
        """Crypto utils should be importable."""
        from symphonic_cipher.scbe_aethermoore.spiral_seal.utils import (
            aes_gcm_encrypt, aes_gcm_decrypt, derive_key
        )
        
        key = b'0' * 32
        plaintext = b"test"
        
        nonce, ct, tag = aes_gcm_encrypt(key, plaintext)
        decrypted = aes_gcm_decrypt(key, nonce, ct, tag)
        
        assert decrypted == plaintext


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
