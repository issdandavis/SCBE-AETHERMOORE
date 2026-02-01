#!/usr/bin/env python3
"""
Six Tongues Tokenizer + GeoSeal CLI
SCBE-AETHERMOORE cryptographic toolkit for conlang tokenization and context-aware sealing.

Author: Issac Daniel Davis
License: MIT
Version: 1.0.0
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
from typing import Dict, List, Tuple, Optional

# Only dependency
try:
    import numpy as np
except ImportError:
    print("Error: numpy is required. Install with: pip install numpy", file=sys.stderr)
    sys.exit(1)

# ==============================================================================
# SACRED TONGUES CONFIGURATION
# ==============================================================================

# The Six Sacred Tongues - each maps 256 bytes bijectively to tokens
TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

# Tongue prefixes and syllable patterns
TONGUE_CONFIG = {
    "KO": {"prefix": "ko", "vowels": "aeiou", "cons": "krtsnml"},
    "AV": {"prefix": "av", "vowels": "aeiou", "cons": "vlnrths"},
    "RU": {"prefix": "ru", "vowels": "aeiou", "cons": "rnthskm"},
    "DR": {"prefix": "dr", "vowels": "aeiou", "cons": "drmntls"},
    "CA": {"prefix": "ca", "vowels": "aeiou", "cons": "cstnrlm"},
    "UM": {"prefix": "um", "vowels": "aeiou", "cons": "mbrnstl"},
}

# Golden ratio weights for each tongue (used in harmonic operations)
PHI = (1 + np.sqrt(5)) / 2
TONGUE_WEIGHTS = {
    "KO": PHI ** 0,  # 1.000
    "AV": PHI ** 1,  # 1.618
    "RU": PHI ** 2,  # 2.618
    "CA": PHI ** 3,  # 4.236
    "UM": PHI ** 4,  # 6.854
    "DR": PHI ** 5,  # 11.090
}


def _generate_tongue_tokens(tongue: str) -> List[str]:
    """Generate 256 unique tokens for a tongue using syllable patterns."""
    cfg = TONGUE_CONFIG[tongue]
    prefix = cfg["prefix"]
    vowels = cfg["vowels"]
    cons = cfg["cons"]

    tokens = []

    # Generate tokens: prefix + consonant + vowel + optional consonant
    # We need exactly 256 tokens
    for i in range(256):
        # Use index to deterministically select syllable components
        c1_idx = i % len(cons)
        v_idx = (i // len(cons)) % len(vowels)
        c2_idx = (i // (len(cons) * len(vowels))) % (len(cons) + 1)

        c1 = cons[c1_idx]
        v = vowels[v_idx]
        c2 = cons[c2_idx - 1] if c2_idx > 0 else ""

        # Add numeric suffix if we've exhausted combinations
        suffix_num = i // (len(cons) * len(vowels) * (len(cons) + 1))
        suffix = str(suffix_num) if suffix_num > 0 else ""

        token = f"{prefix}'{c1}{v}{c2}{suffix}"
        tokens.append(token)

    # Ensure uniqueness (should already be unique by construction)
    assert len(set(tokens)) == 256, f"Token collision in {tongue}"
    return tokens


# Pre-generate all tongue token tables
_TONGUE_TOKENS: Dict[str, List[str]] = {}
_TONGUE_REVERSE: Dict[str, Dict[str, int]] = {}

for _tongue in TONGUES:
    _TONGUE_TOKENS[_tongue] = _generate_tongue_tokens(_tongue)
    _TONGUE_REVERSE[_tongue] = {tok: i for i, tok in enumerate(_TONGUE_TOKENS[_tongue])}


# ==============================================================================
# TOKENIZATION: ENCODE / DECODE
# ==============================================================================

def encode_bytes(data: bytes, tongue: str) -> str:
    """Encode bytes into Sacred Tongue tokens."""
    if tongue not in TONGUES:
        raise ValueError(f"Unknown tongue: {tongue}. Must be one of {TONGUES}")

    tokens = _TONGUE_TOKENS[tongue]
    return " ".join(tokens[b] for b in data)


def decode_tokens(token_str: str, tongue: str) -> bytes:
    """Decode Sacred Tongue tokens back to bytes."""
    if tongue not in TONGUES:
        raise ValueError(f"Unknown tongue: {tongue}. Must be one of {TONGUES}")

    reverse = _TONGUE_REVERSE[tongue]
    tokens = token_str.strip().split()

    result = []
    for tok in tokens:
        if tok not in reverse:
            raise ValueError(f"Unknown token '{tok}' for tongue {tongue}")
        result.append(reverse[tok])

    return bytes(result)


# ==============================================================================
# CROSS-TONGUE TRANSLATION
# ==============================================================================

def translate_tokens(token_str: str, src_tongue: str, dst_tongue: str) -> str:
    """Translate tokens from one tongue to another (preserves underlying bytes)."""
    if src_tongue not in TONGUES:
        raise ValueError(f"Unknown source tongue: {src_tongue}")
    if dst_tongue not in TONGUES:
        raise ValueError(f"Unknown destination tongue: {dst_tongue}")

    # Decode from source, encode to destination
    data = decode_tokens(token_str, src_tongue)
    return encode_bytes(data, dst_tongue)


# ==============================================================================
# BLEND / UNBLEND
# ==============================================================================

def parse_blend_pattern(pattern: str) -> List[Tuple[str, int]]:
    """Parse a blend pattern like 'KO:2,AV:1,DR:1' into [(tongue, count), ...]."""
    result = []
    for part in pattern.split(","):
        part = part.strip()
        if ":" not in part:
            raise ValueError(f"Invalid pattern part: {part}. Expected TONGUE:N format.")
        tongue, count_str = part.split(":", 1)
        tongue = tongue.strip().upper()
        if tongue not in TONGUES:
            raise ValueError(f"Unknown tongue in pattern: {tongue}")
        count = int(count_str.strip())
        if count < 1:
            raise ValueError(f"Count must be >= 1, got {count}")
        result.append((tongue, count))
    return result


def blend_bytes(data: bytes, pattern: List[Tuple[str, int]]) -> str:
    """Blend bytes into multiple tongues according to pattern."""
    # Calculate pattern cycle length
    cycle_len = sum(count for _, count in pattern)

    # Assign each byte to a tongue based on position in cycle
    tokens = []
    for i, byte_val in enumerate(data):
        pos_in_cycle = i % cycle_len

        # Find which tongue this position belongs to
        cumsum = 0
        for tongue, count in pattern:
            if pos_in_cycle < cumsum + count:
                # This byte goes to this tongue
                tokens.append(_TONGUE_TOKENS[tongue][byte_val])
                break
            cumsum += count

    return " ".join(tokens)


def unblend_tokens(token_str: str, pattern: List[Tuple[str, int]]) -> bytes:
    """Unblend a multi-tongue token stream back to bytes."""
    tokens = token_str.strip().split()
    cycle_len = sum(count for _, count in pattern)

    result = []
    for i, tok in enumerate(tokens):
        pos_in_cycle = i % cycle_len

        # Find which tongue this position belongs to
        cumsum = 0
        for tongue, count in pattern:
            if pos_in_cycle < cumsum + count:
                # This token should be from this tongue
                reverse = _TONGUE_REVERSE[tongue]
                if tok not in reverse:
                    raise ValueError(f"Token '{tok}' not valid for tongue {tongue} at position {i}")
                result.append(reverse[tok])
                break
            cumsum += count

    return bytes(result)


# ==============================================================================
# GEOSEAL: CONTEXT-AWARE ENCRYPTION
# ==============================================================================

GEOSEAL_VERSION = "1.0"
GEOSEAL_NONCE_BYTES = 16


def _derive_key(master_key: bytes, context: str) -> bytes:
    """Derive a context-specific key using HKDF-like construction."""
    return hashlib.pbkdf2_hmac("sha256", master_key, context.encode(), 10000, dklen=32)


def _healpix_index(lat: float, lon: float, nside: int = 64) -> int:
    """Simple HEALPix-like spatial index (approximate)."""
    # Normalize coordinates
    theta = np.radians(90 - lat)  # colatitude
    phi = np.radians(lon % 360)

    # Simple ring scheme approximation
    z = np.cos(theta)
    ring = int((1 - z) * nside)
    pixel_in_ring = int(phi / (2 * np.pi) * (4 * nside))

    return ring * 4 * nside + pixel_in_ring


def geoseal_encrypt(
    data: bytes,
    lat: float,
    lon: float,
    tag: str = "",
    master_key: Optional[bytes] = None,
    ttl_seconds: int = 3600,
) -> str:
    """
    Wrap data with a GeoSeal envelope.

    Returns a JSON string containing:
    - Encrypted payload (XOR with derived key stream for demo; real impl would use AES-GCM)
    - Context metadata (location hash, timestamp, tag)
    - HMAC signature
    """
    if master_key is None:
        master_key = os.urandom(32)

    nonce = os.urandom(GEOSEAL_NONCE_BYTES)
    timestamp = int(time.time())
    expires = timestamp + ttl_seconds

    # Spatial index
    spatial_idx = _healpix_index(lat, lon)

    # Derive encryption key from context
    context = f"geoseal:{spatial_idx}:{tag}:{nonce.hex()}"
    enc_key = _derive_key(master_key, context)

    # Simple XOR encryption (demo only - production should use AES-GCM)
    key_stream = np.frombuffer(
        hashlib.shake_256(enc_key + nonce).digest(len(data)),
        dtype=np.uint8
    )
    data_arr = np.frombuffer(data, dtype=np.uint8)
    encrypted = bytes(data_arr ^ key_stream)

    # Build envelope
    envelope = {
        "version": GEOSEAL_VERSION,
        "nonce": base64.urlsafe_b64encode(nonce).decode(),
        "spatial_idx": spatial_idx,
        "tag": tag,
        "timestamp": timestamp,
        "expires": expires,
        "payload": base64.urlsafe_b64encode(encrypted).decode(),
    }

    # Compute HMAC over envelope (excluding signature)
    # Use canonical JSON format: sorted keys, no extra whitespace
    envelope_bytes = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    sig = hmac.new(master_key, envelope_bytes, hashlib.sha256).hexdigest()
    envelope["sig"] = sig

    # Return with same canonical format so tampering is detectable
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"))


def geoseal_decrypt(
    envelope_json: str,
    master_key: bytes,
    expected_tag: Optional[str] = None,
    check_expiry: bool = True,
    expected_lat: Optional[float] = None,
    expected_lon: Optional[float] = None,
    location_tolerance: int = 100,  # spatial index units
) -> bytes:
    """
    Verify and decrypt a GeoSeal envelope.

    Raises ValueError if verification fails.
    """
    envelope = json.loads(envelope_json)

    # Check version
    if envelope.get("version") != GEOSEAL_VERSION:
        raise ValueError(f"Unsupported GeoSeal version: {envelope.get('version')}")

    # Verify signature
    sig = envelope.pop("sig", None)
    envelope_bytes = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    expected_sig = hmac.new(master_key, envelope_bytes, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(sig or "", expected_sig):
        raise ValueError("GeoSeal signature verification failed")

    # Check expiry
    if check_expiry and time.time() > envelope["expires"]:
        raise ValueError("GeoSeal envelope has expired")

    # Check tag
    if expected_tag is not None and envelope["tag"] != expected_tag:
        raise ValueError(f"Tag mismatch: expected '{expected_tag}', got '{envelope['tag']}'")

    # Check location (optional)
    if expected_lat is not None and expected_lon is not None:
        expected_idx = _healpix_index(expected_lat, expected_lon)
        if abs(envelope["spatial_idx"] - expected_idx) > location_tolerance:
            raise ValueError("GeoSeal location verification failed")

    # Decrypt
    nonce = base64.urlsafe_b64decode(envelope["nonce"])
    encrypted = base64.urlsafe_b64decode(envelope["payload"])

    context = f"geoseal:{envelope['spatial_idx']}:{envelope['tag']}:{nonce.hex()}"
    enc_key = _derive_key(master_key, context)

    key_stream = np.frombuffer(
        hashlib.shake_256(enc_key + nonce).digest(len(encrypted)),
        dtype=np.uint8
    )
    encrypted_arr = np.frombuffer(encrypted, dtype=np.uint8)
    decrypted = bytes(encrypted_arr ^ key_stream)

    return decrypted


# ==============================================================================
# SELF-TEST
# ==============================================================================

def selftest() -> bool:
    """Run comprehensive self-tests. Returns True if all pass."""
    print("Running Six Tongues + GeoSeal self-test...\n")
    all_passed = True

    # Test 1: Encode/decode round-trip for each tongue
    print("1. Encode/decode round-trip...")
    test_data = b"Hello, World! \x00\xff\x42"
    for tongue in TONGUES:
        encoded = encode_bytes(test_data, tongue)
        decoded = decode_tokens(encoded, tongue)
        if decoded != test_data:
            print(f"   FAIL: {tongue} round-trip mismatch")
            all_passed = False
        else:
            print(f"   OK: {tongue}")

    # Test 2: Cross-tongue translation
    print("\n2. Cross-tongue translation...")
    original = b"test data"
    ko_tokens = encode_bytes(original, "KO")
    for dst in ["AV", "RU", "CA", "UM", "DR"]:
        translated = translate_tokens(ko_tokens, "KO", dst)
        back_to_bytes = decode_tokens(translated, dst)
        if back_to_bytes != original:
            print(f"   FAIL: KO -> {dst} translation mismatch")
            all_passed = False
        else:
            print(f"   OK: KO -> {dst}")

    # Test 3: Blend/unblend
    print("\n3. Blend/unblend...")
    pattern_str = "KO:2,AV:1,DR:1"
    pattern = parse_blend_pattern(pattern_str)
    test_data = b"blend test with longer data"
    blended = blend_bytes(test_data, pattern)
    unblended = unblend_tokens(blended, pattern)
    if unblended != test_data:
        print(f"   FAIL: blend/unblend mismatch")
        all_passed = False
    else:
        print(f"   OK: pattern {pattern_str}")

    # Test 4: GeoSeal encrypt/decrypt
    print("\n4. GeoSeal encrypt/decrypt...")
    master_key = os.urandom(32)
    test_data = b"classified information"
    lat, lon = 48.118, -123.430
    tag = "test-seal"

    sealed = geoseal_encrypt(test_data, lat, lon, tag, master_key)
    try:
        unsealed = geoseal_decrypt(sealed, master_key, expected_tag=tag, check_expiry=False)
        if unsealed != test_data:
            print("   FAIL: GeoSeal decrypt mismatch")
            all_passed = False
        else:
            print("   OK: encrypt/decrypt round-trip")
    except Exception as e:
        print(f"   FAIL: GeoSeal error: {e}")
        all_passed = False

    # Test 5: GeoSeal signature verification
    print("\n5. GeoSeal tamper detection...")
    try:
        tampered = sealed.replace('"tag":"test-seal"', '"tag":"tampered"')
        geoseal_decrypt(tampered, master_key, check_expiry=False)
        print("   FAIL: tampered envelope was accepted")
        all_passed = False
    except ValueError:
        print("   OK: tampered envelope rejected")

    # Test 6: Token uniqueness
    print("\n6. Token table uniqueness...")
    for tongue in TONGUES:
        tokens = _TONGUE_TOKENS[tongue]
        if len(set(tokens)) != 256:
            print(f"   FAIL: {tongue} has duplicate tokens")
            all_passed = False
        else:
            print(f"   OK: {tongue} has 256 unique tokens")

    # Summary
    print("\n" + "=" * 40)
    if all_passed:
        print("selftest ok")
    else:
        print("selftest FAILED")

    return all_passed


# ==============================================================================
# CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Six Tongues Tokenizer + GeoSeal CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  echo -n "hello" | python sixtongues.py encode --tongue KO
  python sixtongues.py decode --tongue KO "ko'ka ko'ke ko'ki ko'ko ko'ku"
  python sixtongues.py xlate --src KO --dst AV < tokens.txt
  echo -n "secret" | python sixtongues.py blend --pattern KO:2,AV:1
  python sixtongues.py geoseal-encrypt --lat 48.1 --lon -123.4 --tag demo < data.txt
  python sixtongues.py  # runs selftest
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # encode
    p_encode = subparsers.add_parser("encode", help="Encode bytes to Sacred Tongue tokens")
    p_encode.add_argument("--tongue", "-t", required=True, choices=TONGUES, help="Target tongue")
    p_encode.add_argument("--text", help="Text to encode (reads stdin if not provided)")

    # decode
    p_decode = subparsers.add_parser("decode", help="Decode Sacred Tongue tokens to bytes")
    p_decode.add_argument("--tongue", "-t", required=True, choices=TONGUES, help="Source tongue")
    p_decode.add_argument("tokens", nargs="?", help="Tokens to decode (reads stdin if not provided)")

    # xlate
    p_xlate = subparsers.add_parser("xlate", help="Translate between tongues")
    p_xlate.add_argument("--src", "-s", required=True, choices=TONGUES, help="Source tongue")
    p_xlate.add_argument("--dst", "-d", required=True, choices=TONGUES, help="Destination tongue")
    p_xlate.add_argument("tokens", nargs="?", help="Tokens to translate (reads stdin if not provided)")

    # blend
    p_blend = subparsers.add_parser("blend", help="Blend bytes into multi-tongue stream")
    p_blend.add_argument("--pattern", "-p", required=True, help="Pattern like 'KO:2,AV:1,DR:1'")
    p_blend.add_argument("--text", help="Text to blend (reads stdin if not provided)")

    # unblend
    p_unblend = subparsers.add_parser("unblend", help="Unblend multi-tongue stream to bytes")
    p_unblend.add_argument("--pattern", "-p", required=True, help="Pattern like 'KO:2,AV:1,DR:1'")
    p_unblend.add_argument("tokens", nargs="?", help="Tokens to unblend (reads stdin if not provided)")

    # geoseal-encrypt
    p_seal = subparsers.add_parser("geoseal-encrypt", help="Wrap data with GeoSeal")
    p_seal.add_argument("--lat", type=float, required=True, help="Latitude")
    p_seal.add_argument("--lon", type=float, required=True, help="Longitude")
    p_seal.add_argument("--tag", default="", help="Context tag")
    p_seal.add_argument("--key", help="Master key (hex). Generated if not provided.")
    p_seal.add_argument("--ttl", type=int, default=3600, help="TTL in seconds (default: 3600)")

    # geoseal-decrypt
    p_unseal = subparsers.add_parser("geoseal-decrypt", help="Verify and unwrap GeoSeal")
    p_unseal.add_argument("--key", required=True, help="Master key (hex)")
    p_unseal.add_argument("--expect-tag", help="Expected tag (optional verification)")
    p_unseal.add_argument("--no-expiry-check", action="store_true", help="Skip expiry check")

    # tokens (list token table)
    p_tokens = subparsers.add_parser("tokens", help="List token table for a tongue")
    p_tokens.add_argument("--tongue", "-t", required=True, choices=TONGUES, help="Tongue to list")

    args = parser.parse_args()

    # No command = selftest
    if args.command is None:
        success = selftest()
        sys.exit(0 if success else 1)

    # Helper to read input
    def get_input(arg_value: Optional[str], binary: bool = False) -> bytes:
        if arg_value is not None:
            return arg_value.encode() if not binary else arg_value
        if binary:
            return sys.stdin.buffer.read()
        return sys.stdin.read().encode()

    def get_text_input(arg_value: Optional[str]) -> str:
        if arg_value is not None:
            return arg_value
        return sys.stdin.read()

    try:
        if args.command == "encode":
            data = get_input(args.text)
            print(encode_bytes(data, args.tongue))

        elif args.command == "decode":
            tokens = get_text_input(args.tokens)
            result = decode_tokens(tokens, args.tongue)
            sys.stdout.buffer.write(result)

        elif args.command == "xlate":
            tokens = get_text_input(args.tokens)
            print(translate_tokens(tokens, args.src, args.dst))

        elif args.command == "blend":
            data = get_input(args.text)
            pattern = parse_blend_pattern(args.pattern)
            print(blend_bytes(data, pattern))

        elif args.command == "unblend":
            tokens = get_text_input(args.tokens)
            pattern = parse_blend_pattern(args.pattern)
            result = unblend_tokens(tokens, pattern)
            sys.stdout.buffer.write(result)

        elif args.command == "geoseal-encrypt":
            data = sys.stdin.buffer.read()
            if args.key:
                master_key = bytes.fromhex(args.key)
            else:
                master_key = os.urandom(32)
                print(f"# Generated key: {master_key.hex()}", file=sys.stderr)

            sealed = geoseal_encrypt(data, args.lat, args.lon, args.tag, master_key, args.ttl)
            print(sealed)

        elif args.command == "geoseal-decrypt":
            envelope = sys.stdin.read()
            master_key = bytes.fromhex(args.key)

            result = geoseal_decrypt(
                envelope,
                master_key,
                expected_tag=args.expect_tag,
                check_expiry=not args.no_expiry_check,
            )
            sys.stdout.buffer.write(result)

        elif args.command == "tokens":
            tokens = _TONGUE_TOKENS[args.tongue]
            for i, tok in enumerate(tokens):
                print(f"{i:3d} (0x{i:02x}): {tok}")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except BrokenPipeError:
        sys.exit(0)


if __name__ == "__main__":
    main()
