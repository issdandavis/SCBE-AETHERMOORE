#!/usr/bin/env python3
"""
Aethermoore CLI Tool
====================

Command-line interface for the SCBE-AETHERMOORE cryptographic system.

Commands:
  encode            Encode data into Sacred Tongue tokens
  decode            Decode Sacred Tongue tokens to data
  xlate             Cross-translate tokens between tongues
  blend             Blend tokens from multiple tongues
  unblend           Reverse a blend operation
  geoseal-encrypt   Encrypt data with GeoSeal
  geoseal-decrypt   Decrypt GeoSeal envelope
  egg-create        Create a Sacred Egg
  egg-hatch         Hatch a Sacred Egg
  selftest          Run self-tests

Usage:
  python tools/aethermoore.py encode --tongue KO --input "Hello World"
  python tools/aethermoore.py decode --tongue KO --tokens ko_abc123,ko_def456
  python tools/aethermoore.py xlate --from KO --to DR --tokens ko_abc123,ko_def456
  python tools/aethermoore.py geoseal-encrypt --key hex_key --input "secret"
  python tools/aethermoore.py egg-create --tongue KO --ritual solitary --input "secret"
  python tools/aethermoore.py egg-hatch --tongue KO --egg-file egg.json
  python tools/aethermoore.py selftest

@module tools/aethermoore
"""

import argparse
import hashlib
import hmac
import json
import math
import os
import struct
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# Constants (self-contained, no imports from src/)
# ============================================================================

PHI = (1 + math.sqrt(5)) / 2

TONGUES = {
    "KO": {"phase": 0, "weight": 1.00, "name": "Kor'aelin"},
    "AV": {"phase": 60, "weight": round(PHI, 2), "name": "Avali"},
    "RU": {"phase": 120, "weight": round(PHI**2, 2), "name": "Runethic"},
    "CA": {"phase": 180, "weight": round(PHI**3, 2), "name": "Cassisivadan"},
    "UM": {"phase": 240, "weight": round(PHI**4, 2), "name": "Umbroth"},
    "DR": {"phase": 300, "weight": round(PHI**5, 2), "name": "Draumric"},
}

TONGUE_IDS = list(TONGUES.keys())


# ============================================================================
# Lexicon & Tokenizer (standalone reimplementation)
# ============================================================================


class Lexicons:
    """256-token bijective lexicons per tongue."""

    def __init__(self):
        self._lexicons: Dict[str, List[str]] = {}
        for tongue in TONGUE_IDS:
            self._lexicons[tongue] = self._generate_lexicon(tongue)

    def _generate_lexicon(self, tongue: str) -> List[str]:
        tokens = []
        for i in range(256):
            seed = f"{tongue}:{i}:sacred_lexicon_v1"
            h = hashlib.sha256(seed.encode()).hexdigest()[:8]
            tokens.append(f"{tongue.lower()}_{h}")
        return tokens

    def encode_byte(self, tongue: str, byte_val: int) -> str:
        return self._lexicons[tongue][byte_val & 0xFF]

    def decode_token(self, tongue: str, token: str) -> int:
        try:
            return self._lexicons[tongue].index(token)
        except ValueError:
            raise ValueError(f"Unknown token '{token}' for tongue {tongue}")

    def get_lexicon(self, tongue: str) -> List[str]:
        return self._lexicons[tongue]


class TongueTokenizer:
    def __init__(self, lexicons: Optional[Lexicons] = None):
        self.lexicons = lexicons or Lexicons()

    def encode(self, data: bytes, tongue: str) -> List[str]:
        return [self.lexicons.encode_byte(tongue, b) for b in data]

    def decode(self, tokens: List[str], tongue: str) -> bytes:
        return bytes([self.lexicons.decode_token(tongue, t) for t in tokens])


class CrossTokenizer:
    def __init__(self, lexicons: Optional[Lexicons] = None):
        self.lexicons = lexicons or Lexicons()
        self.tokenizer = TongueTokenizer(self.lexicons)

    def translate(self, tokens: List[str], source: str, target: str) -> List[str]:
        raw = self.tokenizer.decode(tokens, source)
        return self.tokenizer.encode(raw, target)


# ============================================================================
# GeoSeal (standalone)
# ============================================================================


def _derive_key(secret: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    prk = hmac.new(salt, secret, hashlib.sha256).digest()
    okm = b""
    prev = b""
    for i in range(1, (length + 31) // 32 + 1):
        prev = hmac.new(prk, prev + info + bytes([i]), hashlib.sha256).digest()
        okm += prev
    return okm[:length]


def geoseal_encrypt(plaintext: bytes, key: bytes, geo_coords: Tuple[float, float, float] = (0.0, 0.0, 0.0)) -> Dict[str, Any]:
    salt = os.urandom(16)
    geo_info = struct.pack("!fff", *geo_coords)
    derived = _derive_key(key, salt, b"geoseal:v1:" + geo_info)
    pad = (derived * ((len(plaintext) // 32) + 1))[:len(plaintext)]
    ciphertext = bytes(p ^ k for p, k in zip(plaintext, pad))
    tag = hmac.new(derived, ciphertext + geo_info, hashlib.sha256).digest()[:16]
    return {
        "ciphertext": ciphertext.hex(),
        "salt": salt.hex(),
        "tag": tag.hex(),
        "geo": list(geo_coords),
        "version": "geoseal-v1",
    }


def geoseal_decrypt(envelope: Dict[str, Any], key: bytes, geo_coords: Optional[Tuple[float, float, float]] = None) -> bytes:
    salt = bytes.fromhex(envelope["salt"])
    ciphertext = bytes.fromhex(envelope["ciphertext"])
    stored_tag = bytes.fromhex(envelope["tag"])
    coords = tuple(envelope["geo"]) if geo_coords is None else geo_coords
    geo_info = struct.pack("!fff", *coords)
    derived = _derive_key(key, salt, b"geoseal:v1:" + geo_info)
    expected_tag = hmac.new(derived, ciphertext + geo_info, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(stored_tag, expected_tag):
        raise ValueError("GeoSeal authentication failed")
    pad = (derived * ((len(ciphertext) // 32) + 1))[:len(ciphertext)]
    return bytes(c ^ k for c, k in zip(ciphertext, pad))


# ============================================================================
# Sacred Egg (standalone)
# ============================================================================


class SacredEggIntegrator:
    def __init__(self, master_key: Optional[bytes] = None):
        self.master_key = master_key or os.urandom(32)
        self.lexicons = Lexicons()
        self.tokenizer = TongueTokenizer(self.lexicons)

    def _derive_egg_key(self, egg_id: str, tongue: str) -> bytes:
        info = f"sacred_egg:{egg_id}:{tongue}".encode()
        return _derive_key(self.master_key, b"egg_salt_v1", info)

    def create_egg(self, payload: bytes, tongue: str, ritual_mode: str = "solitary",
                   ritual_tongues: Optional[List[str]] = None,
                   geo_coords: Tuple[float, float, float] = (0.0, 0.0, 0.0)) -> Dict[str, Any]:
        egg_id = hashlib.sha256(os.urandom(32)).hexdigest()[:16]
        tokens = self.tokenizer.encode(payload, tongue)
        token_data = json.dumps(tokens).encode()
        key = self._derive_egg_key(egg_id, tongue)
        envelope = geoseal_encrypt(token_data, key, geo_coords)

        if ritual_mode == "solitary":
            r_tongues = [tongue]
        elif ritual_mode == "triadic":
            r_tongues = ritual_tongues or [tongue, "RU", "UM"]
        elif ritual_mode == "ring_descent":
            r_tongues = ritual_tongues or TONGUE_IDS[:3]
        else:
            r_tongues = [tongue]

        weight_threshold = 0.0
        if ritual_mode == "triadic":
            weight_threshold = sum(TONGUES[t]["weight"] for t in r_tongues[:2])

        return {
            "egg_id": egg_id,
            "ritual_mode": ritual_mode,
            "sealed_payload": envelope,
            "tongue": tongue,
            "ritual_tongues": r_tongues,
            "weight_threshold": weight_threshold,
            "created_at": time.time(),
        }

    def hatch_egg(self, egg: Dict[str, Any], provided_tongues: List[str],
                  geo_coords: Optional[Tuple[float, float, float]] = None) -> Dict[str, Any]:
        ritual_mode = egg["ritual_mode"]
        tongue = egg["tongue"]

        # Validate ritual
        if ritual_mode == "solitary":
            if tongue not in provided_tongues:
                return {"success": False, "error": f"Wrong tongue: need {tongue}"}
        elif ritual_mode == "triadic":
            missing = [t for t in egg["ritual_tongues"] if t not in provided_tongues]
            if missing:
                return {"success": False, "error": f"Missing tongues: {missing}"}
            total_weight = sum(TONGUES[t]["weight"] for t in provided_tongues if t in TONGUE_IDS)
            if total_weight < egg["weight_threshold"]:
                return {"success": False, "error": "Weight threshold not met"}
        elif ritual_mode == "ring_descent":
            for i, expected in enumerate(egg["ritual_tongues"]):
                if i >= len(provided_tongues) or provided_tongues[i] != expected:
                    return {"success": False, "error": f"Ring {i} mismatch"}

        # Decrypt
        try:
            key = self._derive_egg_key(egg["egg_id"], tongue)
            token_data = geoseal_decrypt(egg["sealed_payload"], key, geo_coords)
            tokens = json.loads(token_data.decode())
            payload = self.tokenizer.decode(tokens, tongue)
            return {"success": True, "payload": payload.decode("utf-8", errors="replace"), "tokens": len(tokens)}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================================
# CLI Commands
# ============================================================================


def cmd_encode(args):
    """Encode input into Sacred Tongue tokens."""
    tokenizer = TongueTokenizer()
    data = args.input.encode() if args.input else sys.stdin.buffer.read()
    tokens = tokenizer.encode(data, args.tongue.upper())
    if args.json:
        print(json.dumps({"tongue": args.tongue.upper(), "tokens": tokens, "count": len(tokens)}))
    else:
        print(",".join(tokens))


def cmd_decode(args):
    """Decode Sacred Tongue tokens to data."""
    tokenizer = TongueTokenizer()
    tokens = [t.strip() for t in args.tokens.split(",")]
    data = tokenizer.decode(tokens, args.tongue.upper())
    if args.json:
        print(json.dumps({"tongue": args.tongue.upper(), "data": data.decode("utf-8", errors="replace")}))
    else:
        sys.stdout.buffer.write(data)
        print()


def cmd_xlate(args):
    """Cross-translate tokens between tongues."""
    cross = CrossTokenizer()
    source_tokens = [t.strip() for t in args.tokens.split(",")]
    target_tokens = cross.translate(source_tokens, args.source.upper(), args.target.upper())
    if args.json:
        print(json.dumps({
            "source": args.source.upper(),
            "target": args.target.upper(),
            "source_tokens": source_tokens,
            "target_tokens": target_tokens,
        }))
    else:
        print(",".join(target_tokens))


def cmd_blend(args):
    """Blend tokens from multiple tongues into a combined form."""
    tokenizer = TongueTokenizer()
    tongues = [t.strip().upper() for t in args.tongues.split(",")]
    data = args.input.encode()

    blend_result = {}
    for tongue in tongues:
        tokens = tokenizer.encode(data, tongue)
        weight = TONGUES[tongue]["weight"]
        blend_result[tongue] = {"tokens": tokens, "weight": weight}

    total_weight = sum(TONGUES[t]["weight"] for t in tongues)
    blend_result["_meta"] = {
        "total_weight": round(total_weight, 2),
        "tongue_count": len(tongues),
        "phi_ratio": round(PHI, 6),
    }

    print(json.dumps(blend_result, indent=2))


def cmd_unblend(args):
    """Extract a specific tongue's tokens from a blend."""
    blend = json.loads(args.blend)
    tongue = args.tongue.upper()

    if tongue not in blend:
        print(f"Error: tongue {tongue} not found in blend", file=sys.stderr)
        sys.exit(1)

    tokenizer = TongueTokenizer()
    tokens = blend[tongue]["tokens"]
    data = tokenizer.decode(tokens, tongue)
    print(data.decode("utf-8", errors="replace"))


def cmd_geoseal_encrypt(args):
    """Encrypt data with GeoSeal."""
    key = bytes.fromhex(args.key)
    data = args.input.encode() if args.input else sys.stdin.buffer.read()
    geo = tuple(float(x) for x in args.geo.split(",")) if args.geo else (0.0, 0.0, 0.0)
    envelope = geoseal_encrypt(data, key, geo)
    print(json.dumps(envelope, indent=2))


def cmd_geoseal_decrypt(args):
    """Decrypt GeoSeal envelope."""
    key = bytes.fromhex(args.key)
    envelope = json.loads(args.envelope) if args.envelope else json.load(sys.stdin)
    geo = tuple(float(x) for x in args.geo.split(",")) if args.geo else None
    plaintext = geoseal_decrypt(envelope, key, geo)
    print(plaintext.decode("utf-8", errors="replace"))


def cmd_egg_create(args):
    """Create a Sacred Egg."""
    master_key = bytes.fromhex(args.master_key) if args.master_key else os.urandom(32)
    integrator = SacredEggIntegrator(master_key)
    data = args.input.encode() if args.input else sys.stdin.buffer.read()
    ritual_tongues = [t.strip().upper() for t in args.ritual_tongues.split(",")] if args.ritual_tongues else None
    geo = tuple(float(x) for x in args.geo.split(",")) if args.geo else (0.0, 0.0, 0.0)

    egg = integrator.create_egg(
        payload=data,
        tongue=args.tongue.upper(),
        ritual_mode=args.ritual,
        ritual_tongues=ritual_tongues,
        geo_coords=geo,
    )

    output = {
        "egg": egg,
        "master_key": master_key.hex(),
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Egg saved to {args.output}")
    else:
        print(json.dumps(output, indent=2))


def cmd_egg_hatch(args):
    """Hatch a Sacred Egg."""
    if args.egg_file:
        with open(args.egg_file) as f:
            data = json.load(f)
    else:
        data = json.loads(sys.stdin.read())

    egg = data["egg"]
    master_key = bytes.fromhex(data["master_key"])
    integrator = SacredEggIntegrator(master_key)

    tongues = [t.strip().upper() for t in args.tongues.split(",")]
    geo = tuple(float(x) for x in args.geo.split(",")) if args.geo else None

    result = integrator.hatch_egg(egg, tongues, geo)
    print(json.dumps(result, indent=2))


def cmd_selftest(args):
    """Run self-tests."""
    print("Aethermoore CLI Self-Test")
    print("=" * 50)

    lexicons = Lexicons()
    tokenizer = TongueTokenizer(lexicons)
    cross = CrossTokenizer(lexicons)

    test_data = b"Hello, Aethermoore!"

    # Test 1: Encode/decode round-trip for each tongue
    print("\n1. Encode/Decode Round-Trip")
    for tongue in TONGUE_IDS:
        tokens = tokenizer.encode(test_data, tongue)
        decoded = tokenizer.decode(tokens, tongue)
        assert decoded == test_data, f"Round-trip failed for {tongue}"
        print(f"   {tongue}: {len(tokens)} tokens - PASS")

    # Test 2: Cross-translation
    print("\n2. Cross-Translation")
    for src, tgt in [("KO", "DR"), ("AV", "UM"), ("RU", "CA")]:
        tokens_src = tokenizer.encode(test_data, src)
        tokens_tgt = cross.translate(tokens_src, src, tgt)
        decoded = tokenizer.decode(tokens_tgt, tgt)
        assert decoded == test_data, f"Cross-xlate failed {src}->{tgt}"
        print(f"   {src} -> {tgt}: PASS")

    # Test 3: GeoSeal
    print("\n3. GeoSeal Encrypt/Decrypt")
    key = os.urandom(32)
    envelope = geoseal_encrypt(test_data, key)
    decrypted = geoseal_decrypt(envelope, key)
    assert decrypted == test_data, "GeoSeal round-trip failed"
    print("   PASS")

    # Test 4: Sacred Egg
    print("\n4. Sacred Egg Create/Hatch")
    integrator = SacredEggIntegrator()
    for mode in ["solitary", "triadic", "ring_descent"]:
        egg = integrator.create_egg(test_data, "KO", ritual_mode=mode)
        if mode == "solitary":
            tongues = ["KO"]
        elif mode == "triadic":
            tongues = egg["ritual_tongues"]
        else:
            tongues = egg["ritual_tongues"]
        result = integrator.hatch_egg(egg, tongues)
        assert result["success"], f"{mode} hatch failed: {result.get('error')}"
        print(f"   {mode}: PASS")

    print("\n" + "=" * 50)
    print("All self-tests passed!")


# ============================================================================
# Main
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        prog="aethermoore",
        description="SCBE-AETHERMOORE Cryptographic CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s encode --tongue KO --input "Hello World"
  %(prog)s decode --tongue KO --tokens ko_abc,ko_def
  %(prog)s xlate --source KO --target DR --tokens ko_abc,ko_def
  %(prog)s geoseal-encrypt --key $(python -c "import os; print(os.urandom(32).hex())") --input "secret"
  %(prog)s egg-create --tongue KO --ritual solitary --input "secret payload"
  %(prog)s selftest
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # encode
    p_encode = subparsers.add_parser("encode", help="Encode data to Sacred Tongue tokens")
    p_encode.add_argument("--tongue", required=True, choices=TONGUE_IDS, help="Target tongue")
    p_encode.add_argument("--input", "-i", help="Input string (or stdin)")
    p_encode.add_argument("--json", action="store_true", help="Output as JSON")

    # decode
    p_decode = subparsers.add_parser("decode", help="Decode Sacred Tongue tokens")
    p_decode.add_argument("--tongue", required=True, choices=TONGUE_IDS, help="Source tongue")
    p_decode.add_argument("--tokens", required=True, help="Comma-separated tokens")
    p_decode.add_argument("--json", action="store_true", help="Output as JSON")

    # xlate
    p_xlate = subparsers.add_parser("xlate", help="Cross-translate between tongues")
    p_xlate.add_argument("--source", required=True, choices=TONGUE_IDS, help="Source tongue")
    p_xlate.add_argument("--target", required=True, choices=TONGUE_IDS, help="Target tongue")
    p_xlate.add_argument("--tokens", required=True, help="Comma-separated source tokens")
    p_xlate.add_argument("--json", action="store_true", help="Output as JSON")

    # blend
    p_blend = subparsers.add_parser("blend", help="Blend tokens from multiple tongues")
    p_blend.add_argument("--tongues", required=True, help="Comma-separated tongue IDs")
    p_blend.add_argument("--input", "-i", required=True, help="Input string")

    # unblend
    p_unblend = subparsers.add_parser("unblend", help="Extract tongue from blend")
    p_unblend.add_argument("--tongue", required=True, choices=TONGUE_IDS, help="Tongue to extract")
    p_unblend.add_argument("--blend", required=True, help="JSON blend data")

    # geoseal-encrypt
    p_gsenc = subparsers.add_parser("geoseal-encrypt", help="GeoSeal encrypt")
    p_gsenc.add_argument("--key", required=True, help="Hex-encoded 32-byte key")
    p_gsenc.add_argument("--input", "-i", help="Input string (or stdin)")
    p_gsenc.add_argument("--geo", help="lat,lon,alt coordinates")

    # geoseal-decrypt
    p_gsdec = subparsers.add_parser("geoseal-decrypt", help="GeoSeal decrypt")
    p_gsdec.add_argument("--key", required=True, help="Hex-encoded 32-byte key")
    p_gsdec.add_argument("--envelope", "-e", help="JSON envelope (or stdin)")
    p_gsdec.add_argument("--geo", help="lat,lon,alt coordinates")

    # egg-create
    p_ecreate = subparsers.add_parser("egg-create", help="Create a Sacred Egg")
    p_ecreate.add_argument("--tongue", required=True, choices=TONGUE_IDS, help="Primary tongue")
    p_ecreate.add_argument("--ritual", default="solitary", choices=["solitary", "triadic", "ring_descent"])
    p_ecreate.add_argument("--ritual-tongues", help="Comma-separated tongues for ritual")
    p_ecreate.add_argument("--input", "-i", help="Payload string (or stdin)")
    p_ecreate.add_argument("--output", "-o", help="Output file path")
    p_ecreate.add_argument("--master-key", help="Hex-encoded master key")
    p_ecreate.add_argument("--geo", help="lat,lon,alt coordinates")

    # egg-hatch
    p_ehatch = subparsers.add_parser("egg-hatch", help="Hatch a Sacred Egg")
    p_ehatch.add_argument("--tongues", required=True, help="Comma-separated tongues for ritual")
    p_ehatch.add_argument("--egg-file", help="Egg JSON file (or stdin)")
    p_ehatch.add_argument("--geo", help="lat,lon,alt coordinates")

    # selftest
    subparsers.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if not args.command:
        # If no command, run selftest
        cmd_selftest(args)
        return

    commands = {
        "encode": cmd_encode,
        "decode": cmd_decode,
        "xlate": cmd_xlate,
        "blend": cmd_blend,
        "unblend": cmd_unblend,
        "geoseal-encrypt": cmd_geoseal_encrypt,
        "geoseal-decrypt": cmd_geoseal_decrypt,
        "egg-create": cmd_egg_create,
        "egg-hatch": cmd_egg_hatch,
        "selftest": cmd_selftest,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
