"""Toy CRT-RSA fault localization with exact six-phase syndromes.

This module joins four existing SCBE ideas without replacing the mandatory RSA
verification step:

* CRT-RSA exposes two independently checked branches per private operation.
* Three operations provide six expected-zero verification residuals.
* Exact Eisenstein-integer DFT bins locate a single non-zero residual.
* A multi-hash receipt can be bound to a Sacred Egg identity and GeoSeal.

The RSA helpers are deliberately toy-only.  Production private-key operations
must use a maintained cryptographic library, blinding, constant-time code, and
the final public verification ``m**e == c (mod n)`` before releasing a result.
The syndrome is diagnostic evidence, never permission to repair or release a
faulty private operation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
from dataclasses import dataclass
from functools import reduce
from operator import mul
from typing import Any, Iterable, Mapping, Sequence

from .geo_fenced_seal import seal_with_geo_fence, unseal_with_geo_check
from .sacred_eggs import SacredEgg
from .sealed_memory_packets import Secret
from .sacred_tongues import SACRED_TONGUE_TOKENIZER

SLOT_LABELS = ("op0:p", "op0:q", "op1:p", "op1:q", "op2:p", "op2:q")
RECEIPT_SCHEMA = "scbe.crt_fault_syndrome.v1"
ROSS_LATTICE_SCHEMA = "scbe.sacred_tongue_ross_lattice.v1"

TONGUE_CODES = ("ko", "av", "ru", "ca", "um", "dr")
TONGUE_ANGLES_DEGREES = (0, 60, 120, 180, 240, 300)
# phi**k written exactly as a + b*phi, using phi**2 = phi + 1.
TONGUE_PHI_WEIGHTS = ((1, 0), (0, 1), (1, 1), (1, 2), (2, 3), (3, 5))

# zeta_6**j represented exactly as a + b*zeta_6, where zeta_6**2 = zeta_6 - 1.
EISENSTEIN_POWERS = ((1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1))
Eisenstein = tuple[int, int]


@dataclass(frozen=True)
class ToyRSAKey:
    """Small RSA key material for deterministic tests only."""

    p: int
    q: int
    e: int
    d: int
    d_p: int
    d_q: int
    q_inv: int
    n: int


@dataclass(frozen=True)
class CRTResult:
    """Two CRT branch values and their Garner recombination."""

    m_p: int
    m_q: int
    value: int


@dataclass(frozen=True)
class FaultLocation:
    """A location inferred under the explicit single-fault model."""

    index: int
    label: str
    residual: int


@dataclass(frozen=True)
class CRTBatch:
    """Three toy CRT operations and their six branch residuals."""

    ciphertexts: tuple[int, int, int]
    results: tuple[CRTResult, CRTResult, CRTResult]
    residuals: tuple[int, int, int, int, int, int]
    public_verification: tuple[bool, bool, bool]


@dataclass(frozen=True)
class FoldedInteger:
    """Signed integer represented by least-significant-first base-M folds."""

    sign: int
    modulus_product: int
    digits: tuple[int, ...]

    @property
    def folds(self) -> int:
        return len(self.digits)


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def make_toy_rsa_key(p: int = 1009, q: int = 1013, e: int = 65537) -> ToyRSAKey:
    """Build a deterministic, insecurely small RSA key for tests and demos."""
    if p == q or not _is_prime(p) or not _is_prime(q):
        raise ValueError("toy RSA requires two distinct primes")
    phi = (p - 1) * (q - 1)
    if math.gcd(e, phi) != 1:
        raise ValueError("public exponent is not invertible modulo phi(n)")
    d = pow(e, -1, phi)
    return ToyRSAKey(
        p=p,
        q=q,
        e=e,
        d=d,
        d_p=d % (p - 1),
        d_q=d % (q - 1),
        q_inv=pow(q, -1, p),
        n=p * q,
    )


def _recombine(m_p: int, m_q: int, key: ToyRSAKey) -> int:
    h = ((m_p - m_q) * key.q_inv) % key.p
    return m_q + h * key.q


def crt_private_operation(ciphertext: int, key: ToyRSAKey) -> CRTResult:
    """Run the textbook CRT private operation on a toy key."""
    m_p = pow(ciphertext % key.p, key.d_p, key.p)
    m_q = pow(ciphertext % key.q, key.d_q, key.q)
    return CRTResult(m_p=m_p, m_q=m_q, value=_recombine(m_p, m_q, key))


def inject_branch_fault(result: CRTResult, branch: str, delta: int, key: ToyRSAKey) -> CRTResult:
    """Inject a deterministic branch fault for a bounded defensive test."""
    if delta == 0:
        raise ValueError("fault delta must be non-zero")
    if branch == "p":
        m_p = (result.m_p + delta) % key.p
        m_q = result.m_q
    elif branch == "q":
        m_p = result.m_p
        m_q = (result.m_q + delta) % key.q
    else:
        raise ValueError("branch must be 'p' or 'q'")
    return CRTResult(m_p=m_p, m_q=m_q, value=_recombine(m_p, m_q, key))


def public_verification(ciphertext: int, result: int, key: ToyRSAKey) -> bool:
    """Mandatory release gate for the toy private operation."""
    return pow(result, key.e, key.n) == ciphertext % key.n


def branch_residual(ciphertext: int, branch_value: int, modulus: int, e: int) -> int:
    """Return zero exactly when one CRT branch passes public verification."""
    return (pow(branch_value, e, modulus) - ciphertext) % modulus


def build_crt_batch(
    ciphertexts: Sequence[int],
    key: ToyRSAKey,
    *,
    fault_slot: int | None = None,
    fault_delta: int = 1,
) -> CRTBatch:
    """Build six expected-zero branch checks from exactly three operations."""
    if len(ciphertexts) != 3:
        raise ValueError("hexaphase CRT batch requires exactly three ciphertexts")
    if fault_slot is not None and not 0 <= fault_slot < 6:
        raise ValueError("fault_slot must be in [0, 6)")

    normalized = tuple(int(value) for value in ciphertexts)
    results = [crt_private_operation(ciphertext, key) for ciphertext in normalized]
    if fault_slot is not None:
        operation_index, branch_index = divmod(fault_slot, 2)
        branch = "p" if branch_index == 0 else "q"
        results[operation_index] = inject_branch_fault(results[operation_index], branch, fault_delta, key)

    residuals: list[int] = []
    checks: list[bool] = []
    for ciphertext, result in zip(normalized, results):
        residuals.append(branch_residual(ciphertext, result.m_p, key.p, key.e))
        residuals.append(branch_residual(ciphertext, result.m_q, key.q, key.e))
        checks.append(public_verification(ciphertext, result.value, key))

    return CRTBatch(
        ciphertexts=normalized,
        results=tuple(results),  # type: ignore[arg-type]
        residuals=tuple(residuals),  # type: ignore[arg-type]
        public_verification=tuple(checks),  # type: ignore[arg-type]
    )


def exact_hexaphase_spectrum(values: Sequence[int]) -> tuple[Eisenstein, ...]:
    """Return all six DFT bins using exact Eisenstein-integer arithmetic."""
    if len(values) != 6:
        raise ValueError("hexaphase spectrum requires exactly six integers")
    bins: list[Eisenstein] = []
    for k in range(6):
        a_total = 0
        b_total = 0
        for j, value in enumerate(values):
            a, b = EISENSTEIN_POWERS[(j * k) % 6]
            a_total += int(value) * a
            b_total += int(value) * b
        bins.append((a_total, b_total))
    return tuple(bins)


def zero_syndrome(values: Sequence[int]) -> bool:
    """Check the complementary bin-0/bin-1 zero certificate."""
    spectrum = exact_hexaphase_spectrum(values)
    return spectrum[0] == (0, 0) and spectrum[1] == (0, 0)


def locate_single_fault(values: Sequence[int]) -> FaultLocation | None:
    """Locate one bad slot from bins 0 and 1 under a single-fault assumption.

    More than one bad slot can imitate another syndrome, so callers must treat
    this as diagnostic metadata.  The independent public RSA verification is
    the authority for rejection.
    """
    spectrum = exact_hexaphase_spectrum(values)
    delta, bin0_b = spectrum[0]
    if bin0_b != 0 or delta == 0:
        return None
    bin1 = spectrum[1]
    matches = []
    for index, (a, b) in enumerate(EISENSTEIN_POWERS):
        if bin1 == (delta * a, delta * b):
            matches.append(index)
    if len(matches) != 1:
        return None
    index = matches[0]
    return FaultLocation(index=index, label=SLOT_LABELS[index], residual=delta)


def bellcore_factor_for_toy(ciphertext: int, faulty_result: int, key: ToyRSAKey) -> int | None:
    """Demonstrate the Bellcore factor leak on the deterministic toy key."""
    factor = math.gcd(pow(faulty_result, key.e, key.n) - ciphertext, key.n)
    return factor if 1 < factor < key.n else None


def crt_modulus_product(moduli: Iterable[int]) -> int:
    """Validate pairwise coprimality and return the CRT modulus product."""
    values = tuple(int(modulus) for modulus in moduli)
    if not values or any(modulus <= 1 for modulus in values):
        raise ValueError("CRT moduli must all be greater than one")
    for index, left in enumerate(values):
        for right in values[index + 1 :]:
            if math.gcd(left, right) != 1:
                raise ValueError("CRT moduli must be pairwise coprime")
    return reduce(mul, values, 1)


def crt_certificate_matches(reference: int, candidate: int, moduli: Iterable[int]) -> bool:
    """Return true iff the candidate error is a multiple of the CRT product."""
    product = crt_modulus_product(moduli)
    return (candidate - reference) % product == 0


def fold_integer(value: int, modulus_product: int) -> FoldedInteger:
    """Rebase an integer into successive base-M remainder/quotient folds."""
    if modulus_product <= 1:
        raise ValueError("modulus_product must be greater than one")
    sign = -1 if value < 0 else 1
    remaining = abs(int(value))
    digits: list[int] = []
    while remaining:
        remaining, remainder = divmod(remaining, modulus_product)
        digits.append(remainder)
    if not digits:
        digits.append(0)
        sign = 0
    return FoldedInteger(sign=sign, modulus_product=modulus_product, digits=tuple(digits))


def unfold_integer(folded: FoldedInteger) -> int:
    """Reconstruct the exact integer from its rebase folds."""
    magnitude = 0
    for digit in reversed(folded.digits):
        if not 0 <= digit < folded.modulus_product:
            raise ValueError("fold digit is outside the base-M range")
        magnitude = magnitude * folded.modulus_product + digit
    return folded.sign * magnitude


def build_syndrome_receipt(batch: CRTBatch) -> dict[str, Any]:
    """Create a JSON-safe internal receipt without serializing key material."""
    spectrum = exact_hexaphase_spectrum(batch.residuals)
    location = locate_single_fault(batch.residuals)
    return {
        "schema_version": RECEIPT_SCHEMA,
        "slot_labels": list(SLOT_LABELS),
        "residuals": list(batch.residuals),
        "spectrum": [list(value) for value in spectrum],
        "zero_syndrome_01": zero_syndrome(batch.residuals),
        "single_fault_location": (
            None
            if location is None
            else {"index": location.index, "label": location.label, "residual": location.residual}
        ),
        "public_verification": list(batch.public_verification),
        "release_allowed": all(batch.public_verification),
    }


def canonical_receipt_bytes(receipt: Mapping[str, Any]) -> bytes:
    """Serialize a receipt deterministically for hashing and sealing."""
    return json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def receipt_hashes(payload: bytes) -> dict[str, str]:
    """Return independent standard-library hashes for a syndrome receipt."""
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "sha3_256": hashlib.sha3_256(payload).hexdigest(),
        "blake2b_256": hashlib.blake2b(payload, digest_size=32).hexdigest(),
    }


def build_ross_lattice(payload: bytes) -> dict[str, Any]:
    """Commit a payload to six weighted, angled 256-node tongue lattices.

    ``Ross lattice`` is used here as the project term for a six-axis phase
    lattice.  Every axis commits the complete byte-to-token codebook (256
    nodes) and a tongue-specific projection of the payload.  The manifest is
    compact: it stores hashes, not the 1,536 public token strings.

    The phi weights are algebraic pairs rather than floats.  For example,
    ``(3, 5)`` means ``3 + 5*phi == phi**5``.
    """
    axes: list[dict[str, Any]] = []
    for index, (code, angle, weight) in enumerate(zip(TONGUE_CODES, TONGUE_ANGLES_DEGREES, TONGUE_PHI_WEIGHTS)):
        codebook = SACRED_TONGUE_TOKENIZER.byte_to_token[code]
        if len(codebook) != 256 or len(set(codebook)) != 256:
            raise ValueError("Sacred Tongue codebook is not a 256-node bijection")

        codebook_document = {
            "tongue": code,
            "angle_degrees": angle,
            "phi_weight": list(weight),
            "nodes": [[byte, token] for byte, token in enumerate(codebook)],
        }
        projection_document = {
            "tongue": code,
            "angle_degrees": angle,
            "phi_weight": list(weight),
            "tokens": SACRED_TONGUE_TOKENIZER.encode_bytes(code, payload),
        }
        axes.append(
            {
                "axis": index,
                "tongue": code,
                "angle_degrees": angle,
                "phi_weight": {"a": weight[0], "b": weight[1], "basis": "a+b*phi"},
                "node_count": 256,
                "codebook_sha3_256": hashlib.sha3_256(canonical_receipt_bytes(codebook_document)).hexdigest(),
                "projection_blake2b_256": hashlib.blake2b(
                    canonical_receipt_bytes(projection_document), digest_size=32
                ).hexdigest(),
            }
        )

    root_document = {
        "schema_version": ROSS_LATTICE_SCHEMA,
        "shape": [6, 256],
        "node_count": 6 * 256,
        "axes": axes,
    }
    return {
        **root_document,
        "root_sha256": hashlib.sha256(canonical_receipt_bytes(root_document)).hexdigest(),
    }


def seal_syndrome_receipt(
    secret: Secret,
    egg: SacredEgg,
    receipt: Mapping[str, Any],
    *,
    geo_fence: Mapping[str, Any],
    tongue: str = "ca",
) -> dict[str, Any]:
    """Multi-hash and GeoSeal a receipt bound to a Sacred Egg shell."""
    payload = canonical_receipt_bytes(receipt)
    metadata = {
        "receipt_schema": RECEIPT_SCHEMA,
        "egg_id": egg.egg_id,
        "egg_shell_sha256": egg.get_shell().hex(),
        "receipt_hashes": receipt_hashes(payload),
        "ross_lattice": build_ross_lattice(payload),
    }
    return seal_with_geo_fence(
        secret,
        payload,
        geo_fence=geo_fence,
        label="crt_fault_syndrome",
        tongue=tongue,
        metadata=metadata,
    )


def unseal_syndrome_receipt(
    secret: Secret,
    egg: SacredEgg,
    packet: Mapping[str, Any],
    *,
    current_location: Mapping[str, Any],
) -> dict[str, Any]:
    """Geo-unseal and verify all receipt hashes plus the Egg binding."""
    opened = unseal_with_geo_check(secret, packet, current_location=current_location)
    payload = opened["payload"]
    metadata = opened["metadata"]

    expected_shell = egg.get_shell().hex()
    identity_ok = hmac.compare_digest(str(metadata.get("egg_id", "")), egg.egg_id) and hmac.compare_digest(
        str(metadata.get("egg_shell_sha256", "")), expected_shell
    )
    recorded_hashes = metadata.get("receipt_hashes")
    actual_hashes = receipt_hashes(payload)
    hashes_ok = isinstance(recorded_hashes, Mapping) and all(
        hmac.compare_digest(str(recorded_hashes.get(name, "")), digest) for name, digest in actual_hashes.items()
    )
    recorded_lattice = metadata.get("ross_lattice")
    actual_lattice = build_ross_lattice(payload)
    lattice_ok = isinstance(recorded_lattice, Mapping) and hmac.compare_digest(
        canonical_receipt_bytes(recorded_lattice), canonical_receipt_bytes(actual_lattice)
    )
    if metadata.get("receipt_schema") != RECEIPT_SCHEMA or not identity_ok or not hashes_ok or not lattice_ok:
        raise ValueError("syndrome receipt verification failed")

    try:
        receipt = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("syndrome receipt verification failed") from exc
    if not isinstance(receipt, dict) or receipt.get("schema_version") != RECEIPT_SCHEMA:
        raise ValueError("syndrome receipt verification failed")
    return {
        "receipt": receipt,
        "receipt_hashes": actual_hashes,
        "ross_lattice": actual_lattice,
        "egg_id": egg.egg_id,
        "geo_fence_check": opened["geo_fence_check"],
    }


__all__ = [
    "CRTBatch",
    "CRTResult",
    "EISENSTEIN_POWERS",
    "FaultLocation",
    "FoldedInteger",
    "RECEIPT_SCHEMA",
    "ROSS_LATTICE_SCHEMA",
    "SLOT_LABELS",
    "ToyRSAKey",
    "TONGUE_ANGLES_DEGREES",
    "TONGUE_CODES",
    "TONGUE_PHI_WEIGHTS",
    "bellcore_factor_for_toy",
    "branch_residual",
    "build_crt_batch",
    "build_ross_lattice",
    "build_syndrome_receipt",
    "canonical_receipt_bytes",
    "crt_certificate_matches",
    "crt_modulus_product",
    "crt_private_operation",
    "exact_hexaphase_spectrum",
    "fold_integer",
    "inject_branch_fault",
    "locate_single_fault",
    "make_toy_rsa_key",
    "public_verification",
    "receipt_hashes",
    "seal_syndrome_receipt",
    "unfold_integer",
    "unseal_syndrome_receipt",
    "zero_syndrome",
]
