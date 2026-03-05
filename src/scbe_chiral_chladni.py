from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import math
from typing import Iterable, Literal, Sequence, Tuple

Dimension6 = Tuple[float, float, float, float, float, float]
Handedness = Literal["L", "R"]


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
    if sum(v * v for v in values) >= 1.0:
        raise ValueError("manifold point must lie strictly inside the Poincare unit ball")
    return values  # type: ignore[return-value]


def _format_manifold(manifold: Dimension6) -> str:
    return ",".join(f"{v:.12g}" for v in manifold)


def _payload_digest(payload: bytes) -> str:
    return hashlib.blake2s(payload, digest_size=16).hexdigest()


@dataclass(frozen=True)
class ChiralModeAddress:
    """
    Signed + chiral Chladni address.

    - sign(n), sign(m): namespace / quadrant metadata
    - |n|, |m|: modal magnitudes
    - handedness: physically distinct branch ("L" or "R")
    - chiral_weight: strength of the non-mirror perturbation

    With chiral_weight=0, this reduces to the standard antisymmetric
    cosine-cosine Chladni field.
    """

    n: int
    m: int
    handedness: Handedness = "R"
    chiral_weight: float = 0.125
    phase_offset: float = math.pi / 7.0

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or not isinstance(self.m, int):
            raise TypeError("n and m must be integers")
        if self.n == 0 or self.m == 0:
            raise ValueError("0 is reserved as the phase separator")
        if abs(self.n) == abs(self.m):
            raise ValueError("degenerate mode: |n| must differ from |m|")
        if self.handedness not in ("L", "R"):
            raise ValueError("handedness must be 'L' or 'R'")
        if not math.isfinite(self.chiral_weight) or self.chiral_weight < 0.0:
            raise ValueError("chiral_weight must be finite and >= 0")
        if not math.isfinite(self.phase_offset):
            raise ValueError("phase_offset must be finite")

    @property
    def magnitudes(self) -> tuple[int, int]:
        return abs(self.n), abs(self.m)

    @property
    def quadrant(self) -> tuple[int, int]:
        return _sign(self.n), _sign(self.m)

    @property
    def chirality(self) -> float:
        return 1.0 if self.handedness == "R" else -1.0

    def signed_label(self) -> str:
        return f"{self.n}:{self.m}:{self.handedness}"

    def physical_label(self) -> str:
        n, m = self.magnitudes
        return f"{n}:{m}"

    def base_field(self, x: float, y: float) -> float:
        n, m = self.magnitudes
        pi = math.pi
        return (
            math.cos(n * pi * x) * math.cos(m * pi * y)
            - math.cos(m * pi * x) * math.cos(n * pi * y)
        )

    def chiral_component(self, x: float, y: float) -> float:
        """
        Reflection-breaking perturbation.

        This is intentionally not antisymmetric under x <-> y.
        It makes L/R branches distinct in the field itself, not only in metadata.
        """
        n, m = self.magnitudes
        pi = math.pi
        phi = self.phase_offset

        return (
            math.sin(n * pi * x + phi) * math.cos(m * pi * y - phi)
            - math.sin(m * pi * x - phi) * math.cos(n * pi * y + phi)
        )

    def raw_field(self, x: float, y: float) -> float:
        return self.base_field(x, y) + self.chirality * self.chiral_weight * self.chiral_component(x, y)

    def readout(self, x: float, y: float) -> float:
        return abs(self.raw_field(x, y))

    def anti_mirror_residual(self, x: float, y: float) -> float:
        """
        For the base field this is zero because F(y, x) = -F(x, y).
        Nonzero residual means diagonal mirror antisymmetry has been broken.
        """
        return self.raw_field(x, y) + self.raw_field(y, x)

    def breaks_diagonal_mirror(
        self,
        samples: Sequence[tuple[float, float]] | None = None,
        tol: float = 1e-9,
    ) -> bool:
        if samples is None:
            samples = (
                (0.13, 0.27),
                (0.41, 0.19),
                (0.73, 0.62),
            )
        return any(abs(self.anti_mirror_residual(x, y)) > tol for x, y in samples)


@dataclass(frozen=True)
class EggSeal:
    payload_digest: str
    binding_token: str
    seal: str
    realm: str


def derive_binding_token(
    mode: ChiralModeAddress,
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
        f"bind|realm={realm}|n={n}|m={m}|qn={qn}|qm={qm}|"
        f"hand={mode.handedness}|weight={mode.chiral_weight:.12g}|"
        f"phase={mode.phase_offset:.12g}|manifold={_format_manifold(M)}"
    ).encode("utf-8")

    return hashlib.blake2b(body, key=secret_key, digest_size=32).hexdigest()


def seal_egg(
    payload: bytes,
    mode: ChiralModeAddress,
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

    body = f"seal|realm={realm}|payload={payload_hash}|binding={binding_token}".encode("utf-8")
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
    mode: ChiralModeAddress,
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
    source: ChiralModeAddress,
    target: ChiralModeAddress,
) -> bool:
    return source.quadrant != target.quadrant or source.handedness != target.handedness


def derive_separator_token(
    source: ChiralModeAddress,
    target: ChiralModeAddress,
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
    source: ChiralModeAddress,
    target: ChiralModeAddress,
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
