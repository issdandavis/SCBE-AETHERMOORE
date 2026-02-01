"""
Generate test vectors for Python ↔ TypeScript interoperability testing.

Since Python uses XChaCha20-Poly1305 (24-byte nonce) and TypeScript uses
ChaCha20-Poly1305 (12-byte nonce), encryption interop isn't direct.

This generates test vectors for:
1. Sacred Tongue encoding (should be byte-identical across languages)
2. Key derivation (PBKDF2 fallback mode)
3. Envelope structure validation

Run: python tests/interop/generate_vectors.py
Output: tests/interop/test_vectors.json
"""

import json
import hashlib
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.crypto.sacred_tongues import (
    SACRED_TONGUE_TOKENIZER,
    SECTION_TONGUES,
    TONGUES,
)


def generate_sacred_tongue_vectors():
    """Generate test vectors for Sacred Tongue encoding."""
    vectors = []

    # Test all tongues with specific byte patterns
    test_patterns = [
        bytes([0x00]),  # First byte
        bytes([0xFF]),  # Last byte
        bytes([0x00, 0x01, 0x02, 0x03]),  # Sequential
        bytes([0xDE, 0xAD, 0xBE, 0xEF]),  # Classic pattern
        b"Hello",  # ASCII text
        bytes(range(16)),  # First 16 bytes
        bytes(range(256)),  # All bytes
    ]

    for tongue_code in TONGUES.keys():
        for i, data in enumerate(test_patterns):
            tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(tongue_code, data)
            vectors.append({
                "type": "sacred_tongue_encode",
                "tongue": tongue_code,
                "input_hex": data.hex(),
                "expected_tokens": tokens,
                "description": f"Tongue {tongue_code}, pattern {i}",
            })

    return vectors


def generate_section_mapping_vectors():
    """Generate test vectors for section → tongue mapping."""
    vectors = []

    test_data = bytes([0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77])

    for section, tongue_code in SECTION_TONGUES.items():
        tokens = SACRED_TONGUE_TOKENIZER.encode_section(section, test_data)
        vectors.append({
            "type": "section_encode",
            "section": section,
            "expected_tongue": tongue_code,
            "input_hex": test_data.hex(),
            "expected_tokens": tokens,
            "description": f"Section {section} → Tongue {tongue_code}",
        })

    return vectors


def generate_bijectivity_vectors():
    """Generate vectors proving bijectivity (encode → decode → original)."""
    vectors = []

    for tongue_code in TONGUES.keys():
        # Test specific bytes
        for b in [0, 1, 127, 128, 254, 255]:
            data = bytes([b])
            tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(tongue_code, data)
            decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(tongue_code, tokens)

            vectors.append({
                "type": "bijectivity",
                "tongue": tongue_code,
                "byte_value": b,
                "token": tokens[0],
                "roundtrip_hex": decoded.hex(),
                "is_equal": data == decoded,
            })

    return vectors


def generate_token_format_vectors():
    """Generate vectors showing expected token format."""
    vectors = []

    for tongue_code, spec in TONGUES.items():
        # Document the tongue specification
        vectors.append({
            "type": "tongue_spec",
            "tongue": tongue_code,
            "name": spec.name,
            "domain": spec.domain,
            "prefix_count": len(spec.prefixes),
            "suffix_count": len(spec.suffixes),
            "first_prefix": spec.prefixes[0],
            "last_prefix": spec.prefixes[15],
            "first_suffix": spec.suffixes[0],
            "last_suffix": spec.suffixes[15],
            "sample_token_0x00": f"{spec.prefixes[0]}'{spec.suffixes[0]}",
            "sample_token_0xFF": f"{spec.prefixes[15]}'{spec.suffixes[15]}",
        })

    return vectors


def generate_pbkdf2_vectors():
    """Generate PBKDF2 key derivation vectors (fallback mode)."""
    import hashlib

    vectors = []

    test_cases = [
        (b"password", b"salt" * 4),
        (b"test-password-123", bytes(16)),
        (b"", b"emptypwd" * 2),
    ]

    for password, salt in test_cases:
        # Match TypeScript PBKDF2 parameters
        key = hashlib.pbkdf2_hmac('sha256', password, salt, 100000, dklen=32)

        vectors.append({
            "type": "pbkdf2",
            "password_hex": password.hex(),
            "salt_hex": salt.hex(),
            "iterations": 100000,
            "key_length": 32,
            "expected_key_hex": key.hex(),
            "description": f"PBKDF2-SHA256 with password len={len(password)}",
        })

    return vectors


def main():
    """Generate all test vectors and save to JSON."""
    vectors = {
        "version": "1.0.0",
        "description": "RWP v3.0 Python ↔ TypeScript interoperability test vectors",
        "generated_by": "Python",
        "sacred_tongue_encode": generate_sacred_tongue_vectors(),
        "section_mapping": generate_section_mapping_vectors(),
        "bijectivity": generate_bijectivity_vectors(),
        "tongue_specs": generate_token_format_vectors(),
        "pbkdf2": generate_pbkdf2_vectors(),
    }

    # Calculate summary
    total = sum(len(v) for k, v in vectors.items() if isinstance(v, list))
    vectors["summary"] = {
        "total_vectors": total,
        "sacred_tongue_encode": len(vectors["sacred_tongue_encode"]),
        "section_mapping": len(vectors["section_mapping"]),
        "bijectivity": len(vectors["bijectivity"]),
        "tongue_specs": len(vectors["tongue_specs"]),
        "pbkdf2": len(vectors["pbkdf2"]),
    }

    # Save to file
    output_path = Path(__file__).parent / "test_vectors.json"
    with open(output_path, "w") as f:
        json.dump(vectors, f, indent=2)

    print(f"Generated {total} test vectors -> {output_path}")
    print(f"  Sacred Tongue encode: {vectors['summary']['sacred_tongue_encode']}")
    print(f"  Section mapping: {vectors['summary']['section_mapping']}")
    print(f"  Bijectivity: {vectors['summary']['bijectivity']}")
    print(f"  Tongue specs: {vectors['summary']['tongue_specs']}")
    print(f"  PBKDF2: {vectors['summary']['pbkdf2']}")


if __name__ == "__main__":
    main()
