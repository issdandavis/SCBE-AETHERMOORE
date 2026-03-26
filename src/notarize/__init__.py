"""SCBE Notarization Service — Cryptographic document attestation.

Hash any data with SHA-256, encode in Sacred Tongues, sign with PQC,
issue a timestamped certificate. Like what the USPTO does, but yours.

Usage:
    from src.notarize import notarize, verify

    cert = notarize(b"my document content", tongue="DR", signer="issac")
    valid = verify(cert)
"""

from .service import (
    notarize,
    verify,
    NotarizationCert,
    batch_notarize,
    cert_to_json,
    cert_from_json,
)

__all__ = [
    "notarize",
    "verify",
    "NotarizationCert",
    "batch_notarize",
    "cert_to_json",
    "cert_from_json",
]
