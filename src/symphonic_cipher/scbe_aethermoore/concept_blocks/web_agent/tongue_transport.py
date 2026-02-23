"""
SCBE Web Agent — Sacred Tongue Transport Layer
=================================================

Bridges the Six Tongues tokenizer and GeoSeal encryption with the
ContentBuffer posting pipeline. Enables:

1. Encoding outbound posts in Sacred Tongue tokens
2. GeoSeal-wrapping posts with context metadata before publishing
3. Decoding inbound tongue-encoded messages from other agents
4. Cross-tongue translation of content between platforms

This is how SCBE agents communicate securely over public channels —
the content looks like exotic text but carries byte-exact payloads.

Integrates with:
- six-tongues-cli.py  (Lexicons, CrossTokenizer, GeoSeal)
- buffer_integration   (ContentBuffer, Platform, PostContent)
- semantic_antivirus    (pre-scan before tongue encoding)
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Resolve import path for six-tongues-cli at project root
# Walk up from this file until we find six-tongues-cli.py
import importlib.util as _ilu

def _find_cli():
    """Search upward for six-tongues-cli.py."""
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        candidate = os.path.join(d, "six-tongues-cli.py")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    raise FileNotFoundError("Cannot find six-tongues-cli.py in any parent directory")

_cli_path = _find_cli()
_cli_spec = _ilu.spec_from_file_location("six_tongues_cli", _cli_path)
_six_tongues = _ilu.module_from_spec(_cli_spec)
_cli_spec.loader.exec_module(_six_tongues)

# Pull in the classes we need
Lexicons = _six_tongues.Lexicons
TongueTokenizer = _six_tongues.TongueTokenizer
CrossTokenizer = _six_tongues.CrossTokenizer
TONGUES = _six_tongues.TONGUES

# GeoSeal functions
geoseal_encrypt = _six_tongues.geoseal_encrypt
geoseal_decrypt = _six_tongues.geoseal_decrypt
kem_keygen = _six_tongues.kem_keygen
dsa_keygen = _six_tongues.dsa_keygen

from .buffer_integration import (
    ContentBuffer,
    Platform,
    PlatformPublisher,
    PostContent,
    PublishResult,
    ScheduledPost,
)


# ---------------------------------------------------------------------------
#  Tongue encoding modes
# ---------------------------------------------------------------------------

TONGUE_PLATFORM_MAP: Dict[str, str] = {
    # Default tongue per platform (domain separation)
    "twitter": "KO",     # Flow/intent — short posts
    "linkedin": "AV",    # Diplomacy/context — professional
    "bluesky": "RU",     # Binding — decentralized protocol
    "mastodon": "CA",    # Bitcraft — federated tech
    "wordpress": "DR",   # Structure — long-form
    "medium": "DR",      # Structure — articles
    "github": "CA",      # Bitcraft — code
    "huggingface": "UM", # Veil — model cards
    "custom": "KO",      # Default
}


@dataclass
class TongueEnvelope:
    """A tongue-encoded message with optional GeoSeal."""

    tongue: str
    tokens: List[str]
    encoded_text: str
    original_bytes: bytes
    geoseal: Optional[Dict[str, Any]] = None
    attestation: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
#  TongueTransport — encode/decode/seal messages
# ---------------------------------------------------------------------------

class TongueTransport:
    """
    Encode, decode, and seal messages using Sacred Tongues + GeoSeal.

    Usage::

        transport = TongueTransport()

        # Encode a message for Twitter in KO tongue
        envelope = transport.encode("Hello agents!", tongue="KO")
        print(envelope.encoded_text)
        # → "sil'or kor'ei vel'ia ..."

        # Decode back
        original = transport.decode(envelope.encoded_text, tongue="KO")
        assert original == b"Hello agents!"

        # GeoSeal for location-bound messaging
        sealed = transport.seal(
            "Classified intel",
            tongue="DR",
            context=[48.118, -123.430, 0.7, 1.0, -2.0, 0.5],
        )
    """

    def __init__(self) -> None:
        self._lex = Lexicons()
        self._tok = TongueTokenizer(self._lex)
        self._xtok = CrossTokenizer(self._tok)

        # Generate session keypair for GeoSeal
        self._kem_pk, self._kem_sk = kem_keygen()
        self._dsa_pk, self._dsa_sk = dsa_keygen()

    def encode(self, text: str, tongue: str = "KO") -> TongueEnvelope:
        """Encode text into Sacred Tongue tokens."""
        tongue = tongue.upper()
        data = text.encode("utf-8")
        tokens = self._tok.encode_bytes(tongue, data)
        encoded = " ".join(tokens)
        return TongueEnvelope(
            tongue=tongue,
            tokens=tokens,
            encoded_text=encoded,
            original_bytes=data,
        )

    def decode(self, token_text: str, tongue: str = "KO") -> bytes:
        """Decode Sacred Tongue tokens back to bytes."""
        tongue = tongue.upper()
        tokens = self._tok.normalize_token_stream(token_text)
        return self._tok.decode_tokens(tongue, tokens)

    def decode_text(self, token_text: str, tongue: str = "KO") -> str:
        """Decode Sacred Tongue tokens to UTF-8 string."""
        return self.decode(token_text, tongue).decode("utf-8", errors="replace")

    def translate(
        self,
        token_text: str,
        src: str,
        dst: str,
        attest_key: Optional[bytes] = None,
    ) -> TongueEnvelope:
        """Cross-translate tokens from one tongue to another."""
        src, dst = src.upper(), dst.upper()
        out_tokens, attest = self._xtok.retokenize(
            src, dst, token_text,
            attest_key=attest_key or b"scbe-transport",
        )
        import dataclasses as dc
        return TongueEnvelope(
            tongue=dst,
            tokens=out_tokens,
            encoded_text=" ".join(out_tokens),
            original_bytes=self._tok.decode_tokens(dst, out_tokens),
            attestation=dc.asdict(attest),
        )

    def blend(self, data: bytes, pattern: Optional[List[str]] = None) -> str:
        """Blend bytes across multiple tongues. Returns JSON."""
        if pattern is None:
            pattern = ["KO", "KO", "AV", "RU", "CA", "UM", "DR"]
        pairs = self._xtok.blend(pattern, data)
        return json.dumps({"pattern": pattern, "pairs": pairs})

    def unblend(self, blend_json: str) -> bytes:
        """Reverse a blended stream."""
        js = json.loads(blend_json)
        pairs = [(tg, tok) for tg, tok in js["pairs"]]
        return self._xtok.unblend(js["pattern"], pairs)

    def seal(
        self,
        text: str,
        tongue: str = "DR",
        context: Optional[List[float]] = None,
    ) -> TongueEnvelope:
        """Encode text in tongue, then GeoSeal-wrap with context."""
        tongue = tongue.upper()
        data = text.encode("utf-8")
        tokens = self._tok.encode_bytes(tongue, data)
        encoded = " ".join(tokens)

        ctx = context or [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        pt_b64 = base64.b64encode(data).decode()
        kem_pk_b64 = base64.b64encode(self._kem_pk).decode()
        dsa_sk_b64 = base64.b64encode(self._dsa_sk).decode()

        envelope = geoseal_encrypt(pt_b64, ctx, kem_pk_b64, dsa_sk_b64)

        return TongueEnvelope(
            tongue=tongue,
            tokens=tokens,
            encoded_text=encoded,
            original_bytes=data,
            geoseal=envelope,
        )

    def unseal(
        self,
        geoseal_env: Dict[str, Any],
        context: Optional[List[float]] = None,
    ) -> Optional[bytes]:
        """Verify and unwrap a GeoSeal envelope. Returns plaintext or None."""
        ctx = context or [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        kem_sk_b64 = base64.b64encode(self._kem_sk).decode()
        dsa_pk_b64 = base64.b64encode(self._dsa_pk).decode()

        ok, pt = geoseal_decrypt(geoseal_env, ctx, kem_sk_b64, dsa_pk_b64)
        return pt if ok else None

    def tongue_for_platform(self, platform: str) -> str:
        """Get default tongue for a platform."""
        return TONGUE_PLATFORM_MAP.get(platform.lower(), "KO")

    def encode_for_post(
        self,
        text: str,
        platform: str,
        tongue: Optional[str] = None,
        seal_context: Optional[List[float]] = None,
    ) -> PostContent:
        """
        Encode text into a tongue-encoded PostContent ready for the Buffer.

        Args:
            text: Original plaintext
            platform: Target platform name
            tongue: Override tongue (default: platform-specific)
            seal_context: If provided, GeoSeal-wrap the content

        Returns:
            PostContent with tongue-encoded text and metadata
        """
        tg = (tongue or self.tongue_for_platform(platform)).upper()

        if seal_context:
            env = self.seal(text, tongue=tg, context=seal_context)
            return PostContent(
                text=env.encoded_text,
                metadata={
                    "tongue": tg,
                    "geoseal": env.geoseal,
                    "original_length": len(text),
                    "transport": "tongue+geoseal",
                },
            )
        else:
            env = self.encode(text, tongue=tg)
            return PostContent(
                text=env.encoded_text,
                metadata={
                    "tongue": tg,
                    "original_length": len(text),
                    "transport": "tongue",
                },
            )
