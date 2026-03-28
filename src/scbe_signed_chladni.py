# src/scbe_signed_chladni.py
"""
Signed Chladni Mode Addressing — extends (n,m) to signed integers with
zero-boundary phase separation for resonance-gated storage.

Physical field depends on |n|, |m| (cosine is even).
Sign is preserved separately as quadrant metadata and must be included
in any seal / manifold binding / auth token.

Patent: continuation claim on USPTO #63/961,403.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import math
from typing import Iterable, Tuple

Dimension6 = Tuple[float, float, float, float, float, float]


def _sign(value: int) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _canonical_manifold(manifold: Iterable[float]) -> Dimension6:
    values = tuple(float(v) for v in manifold)
    if len(values) != 6:
        raise ValueError("manifold must be 6D")
    if any(not math.isfinite(v) for v in values):
        raise ValueError("manifold must contain only finite values")
    norm2 = sum(v * v for v in values)
    if norm2 >= 1.0:
        raise ValueError(
            "manifold point must lie strictly inside the Poincare unit ball"
        )
    return values  # type: ignore[return-value]


def _format_manifold(manifold: Dimension6) -> str:
    return ",".join(f"{v:.12g}" for v in manifold)


def _payload_digest(payload: bytes) -> str:
    return hashlib.blake2s(payload, digest_size=16).hexdigest()


@dataclass(frozen=True)
class SignedModeAddress:
    """
    Signed virtual address over a cosine-based Chladni evaluator.

    Physical field depends on |n|, |m|.
    Sign is preserved separately as quadrant metadata and must be included
    in any seal / manifold binding / auth token.
    """

    n: int
    m: int

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or not isinstance(self.m, int):
            raise TypeError("n and m must be integers")
        if self.n == 0 or self.m == 0:
            raise ValueError("0 is reserved as the phase separator")
        if abs(self.n) == abs(self.m):
            raise ValueError("degenerate mode: |n| must differ from |m|")

    @property
    def magnitudes(self) -> tuple[int, int]:
        return abs(self.n), abs(self.m)

    @property
    def quadrant(self) -> tuple[int, int]:
        return _sign(self.n), _sign(self.m)

    def raw_field(self, x: float, y: float) -> float:
        n, m = self.magnitudes
        return math.cos(n * math.pi * x) * math.cos(m * math.pi * y) - math.cos(
            m * math.pi * x
        ) * math.cos(n * math.pi * y)

    def readout(self, x: float, y: float) -> float:
        return abs(self.raw_field(x, y))

    def signed_label(self) -> str:
        return f"{self.n}:{self.m}"

    def physical_label(self) -> str:
        n, m = self.magnitudes
        return f"{n}:{m}"


def derive_binding_token(
    mode: SignedModeAddress,
    manifold: Iterable[float],
    secret_key: bytes,
    realm: str = "physical",
) -> str:
    if not secret_key:
        raise ValueError("secret_key must be non-empty")

    M = _canonical_manifold(manifold)
    n, m = mode.magnitudes
    qn, qm = mode.quadrant

    body = (
        f"binding|realm={realm}|n={n}|m={m}|qn={qn}|qm={qm}|"
        f"manifold={_format_manifold(M)}"
    ).encode("utf-8")

    return hashlib.blake2b(body, key=secret_key, digest_size=32).hexdigest()


@dataclass(frozen=True)
class EggSeal:
    payload_digest: str
    binding_token: str
    seal: str
    realm: str


def seal_egg(
    payload: bytes,
    mode: SignedModeAddress,
    manifold: Iterable[float],
    secret_key: bytes,
    realm: str = "physical",
) -> EggSeal:
    payload_hash = _payload_digest(payload)
    binding_token = derive_binding_token(
        mode=mode,
        manifold=manifold,
        secret_key=secret_key,
        realm=realm,
    )

    body = (
        f"seal|realm={realm}|payload={payload_hash}|binding={binding_token}"
    ).encode("utf-8")
    seal = hashlib.blake2b(body, key=secret_key, digest_size=32).hexdigest()

    return EggSeal(
        payload_digest=payload_hash,
        binding_token=binding_token,
        seal=seal,
        realm=realm,
    )


def verify_egg(
    egg_seal: EggSeal,
    payload: bytes,
    mode: SignedModeAddress,
    manifold: Iterable[float],
    secret_key: bytes,
    realm: str = "physical",
) -> bool:
    expected = seal_egg(
        payload=payload,
        mode=mode,
        manifold=manifold,
        secret_key=secret_key,
        realm=realm,
    )

    return (
        hmac.compare_digest(egg_seal.payload_digest, expected.payload_digest)
        and hmac.compare_digest(egg_seal.binding_token, expected.binding_token)
        and hmac.compare_digest(egg_seal.seal, expected.seal)
        and egg_seal.realm == expected.realm
    )


def transition_requires_separator(
    source: SignedModeAddress,
    target: SignedModeAddress,
) -> bool:
    return source.quadrant != target.quadrant


def derive_separator_token(
    source: SignedModeAddress,
    target: SignedModeAddress,
    manifold: Iterable[float],
    secret_key: bytes,
) -> str:
    if not secret_key:
        raise ValueError("secret_key must be non-empty")

    M = _canonical_manifold(manifold)
    body = (
        f"separator|src={source.signed_label()}|dst={target.signed_label()}|"
        f"manifold={_format_manifold(M)}"
    ).encode("utf-8")

    return hashlib.blake2b(body, key=secret_key, digest_size=32).hexdigest()


def authorize_transition(
    source: SignedModeAddress,
    target: SignedModeAddress,
    manifold: Iterable[float],
    secret_key: bytes,
    separator_token: str | None = None,
) -> bool:
    if not transition_requires_separator(source, target):
        return True
    if separator_token is None:
        return False

    expected = derive_separator_token(
        source=source,
        target=target,
        manifold=manifold,
        secret_key=secret_key,
    )
    return hmac.compare_digest(separator_token, expected)
