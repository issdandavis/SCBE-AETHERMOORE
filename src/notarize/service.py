"""SCBE Notarization Service — Cryptographic document attestation with Sacred Tongue encoding.

Combines:
  1. SHA-256 hash (standard, verifiable by anyone)
  2. SHA-3-256 hash (quantum-resistant alternative)
  3. Sacred Tongue encoding of the hash (SCBE-proprietary layer)
  4. HMAC signature (integrity + authenticity)
  5. Timestamp + nonce (replay protection)

The certificate proves: this exact data existed at this exact time,
attested by this signer, encoded in this Sacred Tongue.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import List, Optional

# ── Sacred Tongue token tables (subset for hash encoding) ──────────────────

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

# Each tongue has a 256-token vocabulary for encoding bytes
# Using deterministic generation matching cli_toolkit.py
_PREFIXES = {
    "KO": ["ik'", "sor'", "lin'", "kor'", "thal'", "vex'", "dor'", "mak'"],
    "AV": ["ael'", "vir'", "sen'", "lum'", "pax'", "tor'", "vel'", "zan'"],
    "RU": ["groth'", "sten'", "drak'", "fyr'", "keld'", "bron'", "thun'", "gal'"],
    "CA": ["steam'", "gear'", "rivet'", "piston'", "valve'", "cog'", "bolt'", "flux'"],
    "UM": ["thorn'", "shade'", "mist'", "void'", "dusk'", "veil'", "ash'", "grim'"],
    "DR": ["fizz'", "pop'", "bub'", "snap'", "whiz'", "zip'", "spark'", "glow'"],
}
_SUFFIXES = [
    "el",
    "or",
    "in",
    "ak",
    "ul",
    "sa",
    "ri",
    "yn",
    "on",
    "ar",
    "ik",
    "eth",
    "ix",
    "um",
    "os",
    "an",
    "ir",
    "al",
    "uk",
    "ez",
    "om",
    "at",
    "is",
    "en",
    "ob",
    "av",
    "ep",
    "ux",
    "id",
    "ag",
    "ot",
    "un",
]


def _build_vocab(tongue: str) -> list[str]:
    p = _PREFIXES.get(tongue, _PREFIXES["KO"])
    vocab = []
    for i in range(256):
        vocab.append(p[i % len(p)] + _SUFFIXES[i // len(p) % len(_SUFFIXES)])
    return vocab


_VOCABS = {t: _build_vocab(t) for t in TONGUES}
_REVERSE = {t: {tok: i for i, tok in enumerate(v)} for t, v in _VOCABS.items()}


def tongue_encode(data: bytes, tongue: str = "DR") -> str:
    """Encode bytes as Sacred Tongue tokens."""
    vocab = _VOCABS.get(tongue, _VOCABS["DR"])
    return " ".join(vocab[b] for b in data)


def tongue_decode(tokens: str, tongue: str = "DR") -> bytes:
    """Decode Sacred Tongue tokens back to bytes. Fails on unknown tokens."""
    rev = _REVERSE.get(tongue, _REVERSE["DR"])
    result = []
    for t in tokens.split():
        if t not in rev:
            raise ValueError(f"Unknown token '{t}' in tongue '{tongue}' — possible tampering or corruption")
        result.append(rev[t])
    return bytes(result)


# ── Notarization Certificate ──────────────────────────────────────────────


@dataclass
class NotarizationCert:
    """A cryptographic attestation that specific data existed at a specific time."""

    # Identity
    cert_id: str
    version: str = "1.0"

    # Hashes (dual: standard + quantum-resistant)
    sha256: str = ""
    sha3_256: str = ""

    # Sacred Tongue encoding of the SHA-256 hash
    tongue: str = "DR"
    tongue_encoded_hash: str = ""

    # Signature
    signer: str = ""
    hmac_sha256: str = ""  # HMAC of the canonical cert content

    # Timestamp + anti-replay
    timestamp: float = 0.0
    timestamp_iso: str = ""
    nonce: str = ""

    # Metadata
    data_size: int = 0
    content_type: str = ""
    description: str = ""

    # Provenance
    system: str = "SCBE-AETHERMOORE"
    patent: str = "USPTO #63/961,403"


def _canonical(cert: NotarizationCert) -> str:
    """Deterministic JSON for HMAC signing (excludes the HMAC field itself)."""
    d = asdict(cert)
    d.pop("hmac_sha256", None)
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def notarize(
    data: bytes,
    tongue: str = "DR",
    signer: str = "issac",
    signing_key: str = "",
    content_type: str = "",
    description: str = "",
) -> NotarizationCert:
    """Notarize data — produce a cryptographic attestation certificate.

    Args:
        data: Raw bytes to notarize.
        tongue: Sacred Tongue for hash encoding (default DR = Schema/Attestation).
        signer: Who is attesting.
        signing_key: HMAC key (defaults to signer name if empty).
        content_type: MIME type or description of the data format.
        description: Human-readable description of what's being notarized.

    Returns:
        NotarizationCert with all fields populated.
    """
    now = time.time()
    key = (signing_key or signer).encode("utf-8")

    # Dual hashes
    sha256_hex = hashlib.sha256(data).hexdigest()
    sha3_hex = hashlib.sha3_256(data).hexdigest()

    # Sacred Tongue encoding of the SHA-256 hash bytes
    sha256_bytes = bytes.fromhex(sha256_hex)
    encoded = tongue_encode(sha256_bytes, tongue)

    cert = NotarizationCert(
        cert_id=f"scbe-cert-{int(now)}-{os.urandom(4).hex()}",
        sha256=sha256_hex,
        sha3_256=sha3_hex,
        tongue=tongue,
        tongue_encoded_hash=encoded,
        signer=signer,
        timestamp=now,
        timestamp_iso=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        nonce=os.urandom(16).hex(),
        data_size=len(data),
        content_type=content_type,
        description=description,
    )

    # HMAC signature over the canonical cert
    canonical = _canonical(cert)
    cert.hmac_sha256 = hmac.new(key, canonical.encode(), hashlib.sha256).hexdigest()

    return cert


def verify(cert: NotarizationCert, signing_key: str = "") -> bool:
    """Verify a notarization certificate's HMAC signature.

    Args:
        cert: The certificate to verify.
        signing_key: HMAC key (defaults to signer name if empty).

    Returns:
        True if the signature is valid.
    """
    key = (signing_key or cert.signer).encode("utf-8")
    canonical = _canonical(cert)
    expected = hmac.new(key, canonical.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, cert.hmac_sha256)


def batch_notarize(
    items: list[tuple[bytes, str]],
    tongue: str = "DR",
    signer: str = "issac",
    signing_key: str = "",
) -> list[NotarizationCert]:
    """Notarize multiple items. Each item is (data, description)."""
    return [
        notarize(data, tongue=tongue, signer=signer, signing_key=signing_key, description=desc) for data, desc in items
    ]


def cert_to_json(cert: NotarizationCert) -> str:
    """Serialize a certificate to JSON."""
    return json.dumps(asdict(cert), indent=2)


def cert_from_json(json_str: str) -> NotarizationCert:
    """Deserialize a certificate from JSON."""
    return NotarizationCert(**json.loads(json_str))
