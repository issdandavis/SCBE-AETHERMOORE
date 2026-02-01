#!/usr/bin/env python3
"""
SixTongues CLI - Sacred Tongue Encoding & Encryption Tool
==========================================================
Command-line interface for the Six Sacred Tongues cryptographic encoding system.

Part of the SCBE-AETHERMOORE AI Safety Framework.
https://github.com/anthropics/scbe-aethermoore

License: MIT
Version: 1.0.0
"""

import argparse
import sys
import json
import os
import hashlib
import secrets
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Version info
__version__ = "1.0.0"
__author__ = "SCBE-AETHERMOORE Team"

# ============================================================
# TONGUE SPECIFICATIONS
# ============================================================

@dataclass(frozen=True)
class TongueSpec:
    """Sacred Tongue specification with cryptographic binding."""
    code: str
    name: str
    prefixes: Tuple[str, ...]
    suffixes: Tuple[str, ...]
    domain: str
    harmonic_frequency: float

    def __post_init__(self):
        if len(self.prefixes) != 16 or len(self.suffixes) != 16:
            raise ValueError(f"Tongue {self.code} requires exactly 16 prefixes and 16 suffixes")


# The Six Sacred Tongues
KOR_AELIN = TongueSpec(
    code="ko",
    name="Kor'aelin",
    prefixes=("sil", "kor", "vel", "zar", "keth", "thul", "nav", "ael",
              "ra", "med", "gal", "lan", "joy", "good", "nex", "vara"),
    suffixes=("a", "ae", "ei", "ia", "oa", "uu", "eth", "ar",
              "or", "il", "an", "en", "un", "ir", "oth", "esh"),
    domain="nonce/flow/intent",
    harmonic_frequency=440.0,
)

AVALI = TongueSpec(
    code="av",
    name="Avali",
    prefixes=("saina", "talan", "vessa", "maren", "oriel", "serin", "nurel", "lirea",
              "kiva", "lumen", "calma", "ponte", "verin", "nava", "sela", "tide"),
    suffixes=("a", "e", "i", "o", "u", "y", "la", "re",
              "na", "sa", "to", "mi", "ve", "ri", "en", "ul"),
    domain="aad/header/metadata",
    harmonic_frequency=523.25,
)

RUNETHIC = TongueSpec(
    code="ru",
    name="Runethic",
    prefixes=("khar", "drath", "bront", "vael", "ur", "mem", "krak", "tharn",
              "groth", "basalt", "rune", "sear", "oath", "gnarl", "rift", "iron"),
    suffixes=("ak", "eth", "ik", "ul", "or", "ar", "um", "on",
              "ir", "esh", "nul", "vek", "dra", "kh", "va", "th"),
    domain="salt/binding",
    harmonic_frequency=293.66,
)

CASSISIVADAN = TongueSpec(
    code="ca",
    name="Cassisivadan",
    prefixes=("bip", "bop", "klik", "loopa", "ifta", "thena", "elsa", "spira",
              "rythm", "quirk", "fizz", "gear", "pop", "zip", "mix", "chass"),
    suffixes=("a", "e", "i", "o", "u", "y", "ta", "na",
              "sa", "ra", "lo", "mi", "ki", "zi", "qwa", "sh"),
    domain="ciphertext/bitcraft",
    harmonic_frequency=659.25,
)

UMBROTH = TongueSpec(
    code="um",
    name="Umbroth",
    prefixes=("veil", "zhur", "nar", "shul", "math", "hollow", "hush", "thorn",
              "dusk", "echo", "ink", "wisp", "bind", "ache", "null", "shade"),
    suffixes=("a", "e", "i", "o", "u", "ae", "sh", "th",
              "ak", "ul", "or", "ir", "en", "on", "vek", "nul"),
    domain="redaction/veil",
    harmonic_frequency=196.0,
)

DRAUMRIC = TongueSpec(
    code="dr",
    name="Draumric",
    prefixes=("anvil", "tharn", "mek", "grond", "draum", "ektal", "temper", "forge",
              "stone", "steam", "oath", "seal", "frame", "pillar", "rivet", "ember"),
    suffixes=("a", "e", "i", "o", "u", "ae", "rak", "mek",
              "tharn", "grond", "vek", "ul", "or", "ar", "en", "on"),
    domain="tag/structure",
    harmonic_frequency=392.0,
)

# All tongues indexed by code
TONGUES: Dict[str, TongueSpec] = {
    "ko": KOR_AELIN,
    "av": AVALI,
    "ru": RUNETHIC,
    "ca": CASSISIVADAN,
    "um": UMBROTH,
    "dr": DRAUMRIC,
}

# Section-to-tongue canonical mapping
SECTION_TONGUES = {
    "nonce": "ko",
    "aad": "av",
    "salt": "ru",
    "ct": "ca",
    "ciphertext": "ca",
    "tag": "dr",
    "redact": "um",
}


# ============================================================
# ENCODING / DECODING
# ============================================================

def byte_to_token(byte_val: int, tongue: TongueSpec) -> str:
    """Convert a single byte (0-255) to a Sacred Tongue token."""
    hi = (byte_val >> 4) & 0x0F
    lo = byte_val & 0x0F
    return f"{tongue.prefixes[hi]}'{tongue.suffixes[lo]}"


def token_to_byte(token: str, tongue: TongueSpec) -> int:
    """Convert a Sacred Tongue token back to a byte."""
    if "'" not in token:
        raise ValueError(f"Invalid token format: {token}")

    prefix, suffix = token.split("'", 1)

    try:
        hi = tongue.prefixes.index(prefix)
    except ValueError:
        raise ValueError(f"Unknown prefix '{prefix}' for tongue {tongue.code}")

    try:
        lo = tongue.suffixes.index(suffix)
    except ValueError:
        raise ValueError(f"Unknown suffix '{suffix}' for tongue {tongue.code}")

    return (hi << 4) | lo


def encode_bytes(data: bytes, tongue_code: str = "ko") -> str:
    """Encode bytes to Sacred Tongue tokens (space-separated)."""
    tongue = TONGUES.get(tongue_code)
    if not tongue:
        raise ValueError(f"Unknown tongue: {tongue_code}")

    tokens = [byte_to_token(b, tongue) for b in data]
    return " ".join(tokens)


def decode_tokens(token_string: str, tongue_code: str = "ko") -> bytes:
    """Decode Sacred Tongue tokens back to bytes."""
    tongue = TONGUES.get(tongue_code)
    if not tongue:
        raise ValueError(f"Unknown tongue: {tongue_code}")

    tokens = token_string.strip().split()
    byte_values = [token_to_byte(t, tongue) for t in tokens]
    return bytes(byte_values)


# ============================================================
# SIMPLE ENCRYPTION (XOR-based demo, NOT for production)
# For production use, integrate with RWP v3 protocol
# ============================================================

def derive_key(password: str, salt: bytes, length: int = 32) -> bytes:
    """Simple key derivation using SHA-256 (demo only)."""
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, dklen=length)


def encrypt_message(plaintext: str, password: str) -> dict:
    """
    Encrypt a message and return Sacred Tongue encoded envelope.

    Returns dict with:
    - nonce: Kor'aelin encoded
    - salt: Runethic encoded
    - ct: Cassisivadan encoded ciphertext
    - tag: Draumric encoded auth tag
    """
    # Generate random nonce and salt
    nonce = secrets.token_bytes(24)
    salt = secrets.token_bytes(16)

    # Derive key
    key = derive_key(password, salt)

    # Simple XOR encryption (demo only - use XChaCha20-Poly1305 in production)
    plaintext_bytes = plaintext.encode('utf-8')
    keystream = hashlib.sha256(key + nonce).digest()
    while len(keystream) < len(plaintext_bytes):
        keystream += hashlib.sha256(keystream).digest()

    ciphertext = bytes(p ^ k for p, k in zip(plaintext_bytes, keystream[:len(plaintext_bytes)]))

    # Simple auth tag (demo only)
    tag = hashlib.sha256(key + ciphertext + nonce).digest()[:16]

    return {
        "version": "sixtongues-1.0",
        "nonce": encode_bytes(nonce, "ko"),
        "salt": encode_bytes(salt, "ru"),
        "ct": encode_bytes(ciphertext, "ca"),
        "tag": encode_bytes(tag, "dr"),
    }


def decrypt_message(envelope: dict, password: str) -> str:
    """Decrypt a Sacred Tongue encoded envelope."""
    # Decode components
    nonce = decode_tokens(envelope["nonce"], "ko")
    salt = decode_tokens(envelope["salt"], "ru")
    ciphertext = decode_tokens(envelope["ct"], "ca")
    expected_tag = decode_tokens(envelope["tag"], "dr")

    # Derive key
    key = derive_key(password, salt)

    # Verify tag
    computed_tag = hashlib.sha256(key + ciphertext + nonce).digest()[:16]
    if computed_tag != expected_tag:
        raise ValueError("Authentication failed: invalid password or tampered ciphertext")

    # Decrypt
    keystream = hashlib.sha256(key + nonce).digest()
    while len(keystream) < len(ciphertext):
        keystream += hashlib.sha256(keystream).digest()

    plaintext_bytes = bytes(c ^ k for c, k in zip(ciphertext, keystream[:len(ciphertext)]))
    return plaintext_bytes.decode('utf-8')


# ============================================================
# CLI COMMANDS
# ============================================================

def cmd_encode(args):
    """Encode command: convert input to Sacred Tongue tokens."""
    tongue_code = args.tongue

    if args.input:
        data = args.input.encode('utf-8')
    elif args.file:
        with open(args.file, 'rb') as f:
            data = f.read()
    elif args.hex:
        data = bytes.fromhex(args.hex)
    else:
        # Read from stdin
        data = sys.stdin.buffer.read()

    result = encode_bytes(data, tongue_code)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(result)
    else:
        print(result)


def cmd_decode(args):
    """Decode command: convert Sacred Tongue tokens back to bytes."""
    tongue_code = args.tongue

    if args.input:
        token_string = args.input
    elif args.file:
        with open(args.file, 'r') as f:
            token_string = f.read()
    else:
        token_string = sys.stdin.read()

    data = decode_tokens(token_string, tongue_code)

    if args.output:
        with open(args.output, 'wb') as f:
            f.write(data)
    elif args.hex:
        print(data.hex())
    else:
        try:
            print(data.decode('utf-8'))
        except UnicodeDecodeError:
            print(data.hex())


def cmd_encrypt(args):
    """Encrypt command: encrypt a message using Sacred Tongues."""
    if args.message:
        plaintext = args.message
    elif args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            plaintext = f.read()
    else:
        plaintext = sys.stdin.read()

    password = args.password
    if not password:
        import getpass
        password = getpass.getpass("Password: ")

    envelope = encrypt_message(plaintext, password)

    output = json.dumps(envelope, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
    else:
        print(output)


def cmd_decrypt(args):
    """Decrypt command: decrypt a Sacred Tongue envelope."""
    if args.file:
        with open(args.file, 'r') as f:
            envelope = json.load(f)
    elif args.envelope:
        envelope = json.loads(args.envelope)
    else:
        envelope = json.load(sys.stdin)

    password = args.password
    if not password:
        import getpass
        password = getpass.getpass("Password: ")

    try:
        plaintext = decrypt_message(envelope, password)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(plaintext)
        else:
            print(plaintext)
    except ValueError as e:
        print(f"Decryption failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_list_tongues(args):
    """List all available Sacred Tongues."""
    print("The Six Sacred Tongues:")
    print("=" * 60)

    for code, tongue in TONGUES.items():
        print(f"\n[{tongue.code.upper()}] {tongue.name}")
        print(f"    Domain: {tongue.domain}")
        print(f"    Harmonic: {tongue.harmonic_frequency} Hz")
        print(f"    Prefixes: {', '.join(tongue.prefixes[:4])}...")
        print(f"    Suffixes: {', '.join(tongue.suffixes[:4])}...")
        print(f"    Tokens: 16×16 = 256 unique words")

    print("\n" + "=" * 60)
    print("\nSection Mapping (canonical):")
    for section, code in SECTION_TONGUES.items():
        tongue = TONGUES[code]
        print(f"  {section:12} -> {tongue.name} ({code})")


def cmd_validate(args):
    """Validate a custom lexicon file."""
    with open(args.file, 'r') as f:
        lexicon = json.load(f)

    errors = []
    loaded = []

    for tongue_def in lexicon.get("tongues", []):
        code = tongue_def.get("code", "??")
        try:
            if len(code) != 2:
                raise ValueError(f"Code must be 2 characters")
            if len(tongue_def.get("prefixes", [])) != 16:
                raise ValueError(f"Must have exactly 16 prefixes")
            if len(tongue_def.get("suffixes", [])) != 16:
                raise ValueError(f"Must have exactly 16 suffixes")

            # Check for duplicates
            prefixes = tongue_def["prefixes"]
            suffixes = tongue_def["suffixes"]
            if len(set(prefixes)) != 16:
                raise ValueError("Duplicate prefixes found")
            if len(set(suffixes)) != 16:
                raise ValueError("Duplicate suffixes found")

            loaded.append(code)
            print(f"  [OK] {tongue_def.get('name', code)} ({code})")
        except (ValueError, KeyError) as e:
            errors.append(f"{code}: {e}")
            print(f"  [FAIL] {code}: {e}")

    print()
    if errors:
        print(f"Validation failed: {len(errors)} errors, {len(loaded)} valid")
        sys.exit(1)
    else:
        print(f"Validation passed: {len(loaded)} tongues valid")


def cmd_demo(args):
    """Run an interactive demo of the Six Sacred Tongues."""
    print("=" * 60)
    print("  SixTongues Demo - Sacred Tongue Encoding")
    print("=" * 60)

    sample = "Hello, World!"
    print(f"\nOriginal text: {sample}")
    print(f"Hex: {sample.encode().hex()}")

    print("\nEncoded in each tongue:")
    for code, tongue in TONGUES.items():
        encoded = encode_bytes(sample.encode(), code)
        print(f"\n  [{code.upper()}] {tongue.name}:")
        print(f"      {encoded}")

    print("\n" + "-" * 60)
    print("Encryption Demo (password: 'demo123')")
    print("-" * 60)

    envelope = encrypt_message(sample, "demo123")
    print(f"\nEncrypted envelope:")
    print(json.dumps(envelope, indent=2))

    decrypted = decrypt_message(envelope, "demo123")
    print(f"\nDecrypted: {decrypted}")

    print("\n" + "=" * 60)
    print("Demo complete! Try: sixtongues encode -i 'your message'")
    print("=" * 60)


# ============================================================
# MAIN CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="sixtongues",
        description="SixTongues CLI - Sacred Tongue Encoding & Encryption",
        epilog="Part of the SCBE-AETHERMOORE AI Safety Framework"
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Encode command
    encode_parser = subparsers.add_parser("encode", help="Encode bytes to Sacred Tongue tokens")
    encode_parser.add_argument("-t", "--tongue", default="ko", choices=list(TONGUES.keys()),
                              help="Tongue to use (default: ko)")
    encode_parser.add_argument("-i", "--input", help="Input string to encode")
    encode_parser.add_argument("-f", "--file", help="Input file to encode")
    encode_parser.add_argument("-x", "--hex", help="Hex input to encode")
    encode_parser.add_argument("-o", "--output", help="Output file")
    encode_parser.set_defaults(func=cmd_encode)

    # Decode command
    decode_parser = subparsers.add_parser("decode", help="Decode Sacred Tongue tokens to bytes")
    decode_parser.add_argument("-t", "--tongue", default="ko", choices=list(TONGUES.keys()),
                              help="Tongue to use (default: ko)")
    decode_parser.add_argument("-i", "--input", help="Token string to decode")
    decode_parser.add_argument("-f", "--file", help="File containing tokens")
    decode_parser.add_argument("-o", "--output", help="Output file")
    decode_parser.add_argument("-x", "--hex", action="store_true", help="Output as hex")
    decode_parser.set_defaults(func=cmd_decode)

    # Encrypt command
    encrypt_parser = subparsers.add_parser("encrypt", help="Encrypt a message")
    encrypt_parser.add_argument("-m", "--message", help="Message to encrypt")
    encrypt_parser.add_argument("-f", "--file", help="File to encrypt")
    encrypt_parser.add_argument("-p", "--password", help="Encryption password")
    encrypt_parser.add_argument("-o", "--output", help="Output file for envelope")
    encrypt_parser.set_defaults(func=cmd_encrypt)

    # Decrypt command
    decrypt_parser = subparsers.add_parser("decrypt", help="Decrypt an envelope")
    decrypt_parser.add_argument("-e", "--envelope", help="JSON envelope string")
    decrypt_parser.add_argument("-f", "--file", help="Envelope file")
    decrypt_parser.add_argument("-p", "--password", help="Decryption password")
    decrypt_parser.add_argument("-o", "--output", help="Output file for plaintext")
    decrypt_parser.set_defaults(func=cmd_decrypt)

    # List tongues command
    list_parser = subparsers.add_parser("list", help="List all Sacred Tongues")
    list_parser.set_defaults(func=cmd_list_tongues)

    # Validate lexicon command
    validate_parser = subparsers.add_parser("validate", help="Validate a custom lexicon file")
    validate_parser.add_argument("file", help="Lexicon JSON file to validate")
    validate_parser.set_defaults(func=cmd_validate)

    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run interactive demo")
    demo_parser.set_defaults(func=cmd_demo)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
