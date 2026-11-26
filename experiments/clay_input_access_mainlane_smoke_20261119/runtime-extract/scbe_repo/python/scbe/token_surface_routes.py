"""Exact case and grammar addresses for existing token-routing geometry.

This module does not define a new tokenizer and does not add information to a
token. It exposes two deterministic views of an already observed surface:

* reversible one-code-point upper/lower choices are binary coordinates; and
* an explicitly receipted S/V/O role can be transported through the six
  existing tongue orders.

The Cartesian address is algebraic, so callers can select one possibility
without materializing the potentially exponential case table. The resulting
numeric projection is suitable for ``AlgebraicRadialTokenTable`` weights, but
its usefulness is an unmeasured hypothesis rather than a learned capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Final

SCHEMA: Final = "scbe.token-surface-route.v1"
ROLES: Final = ("S", "V", "O")
TONGUE_ORDER_SEQUENCE: Final = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_ORDERS: Final = {
    "KO": "SOV",
    "AV": "SVO",
    "RU": "VSO",
    "CA": "OVS",
    "UM": "VOS",
    "DR": "OSV",
}
CASE_SECTORS: Final = {
    "uncased": 0,
    "lower": 1,
    "upper": 2,
    "title": 3,
    "mixed": 4,
}


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


GRAMMAR_MAPPING_ID: Final = sha256(_canonical_json(TONGUE_ORDERS)).hexdigest()


def normalize_surface(surface: str) -> str:
    """Match the prime catalog's canonical word normalization."""

    return surface.casefold().replace("’", "'")


def _simple_case_pair(character: str) -> tuple[str, str] | None:
    """Return a reversible one-code-point lower/upper pair when one exists."""

    lower = character.lower()
    upper = character.upper()
    if len(lower) != 1 or len(upper) != 1 or lower == upper:
        return None
    return lower, upper


def _case_kind(trits: tuple[int, ...]) -> str:
    cased = tuple(value for value in trits if value)
    if not cased:
        return "uncased"
    if all(value < 0 for value in cased):
        return "lower"
    if all(value > 0 for value in cased):
        return "upper"
    if cased[0] > 0 and all(value < 0 for value in cased[1:]):
        return "title"
    return "mixed"


@dataclass(frozen=True, slots=True)
class SurfaceCaseProfile:
    """Exact observed case plus a reversible binary subspace.

    ``signed_trits`` covers every code point: upper is ``+1``, lower is
    ``-1``, and uncased is ``0``. ``binary_positions`` is narrower: it only
    includes characters whose lower and upper forms are each one code point,
    so indexed variants never silently change token length.
    """

    surface: str
    normalized: str
    signed_trits: tuple[int, ...]
    binary_positions: tuple[int, ...]
    binary_bits: tuple[int, ...]
    case_index: int
    variant_count: int
    kind: str
    case_sector: int
    transition_count: int


def surface_case_profile(surface: str) -> SurfaceCaseProfile:
    if not isinstance(surface, str) or not surface:
        raise ValueError("surface must be a nonempty string")
    trits: list[int] = []
    positions: list[int] = []
    bits: list[int] = []
    for position, character in enumerate(surface):
        trit = 1 if character.isupper() else (-1 if character.islower() else 0)
        trits.append(trit)
        pair = _simple_case_pair(character)
        if pair is None:
            continue
        lower, upper = pair
        positions.append(position)
        if character == upper:
            bits.append(1)
        elif character == lower:
            bits.append(0)
        else:
            bits.append(int(trit > 0))

    case_index = 0
    for bit in bits:
        case_index = (case_index << 1) | bit
    transition_count = sum(left != right for left, right in zip(bits, bits[1:]))
    signed = tuple(trits)
    kind = _case_kind(signed)
    return SurfaceCaseProfile(
        surface=surface,
        normalized=normalize_surface(surface),
        signed_trits=signed,
        binary_positions=tuple(positions),
        binary_bits=tuple(bits),
        case_index=case_index,
        variant_count=1 << len(positions),
        kind=kind,
        case_sector=CASE_SECTORS[kind],
        transition_count=transition_count,
    )


def case_variant(surface: str, case_index: int) -> str:
    """Derive one exact case variant by integer address, without enumeration."""

    profile = surface_case_profile(surface)
    if not isinstance(case_index, int) or isinstance(case_index, bool):
        raise TypeError("case_index must be an integer")
    if case_index < 0 or case_index >= profile.variant_count:
        raise ValueError(f"case_index must be in [0, {profile.variant_count - 1}]")
    characters = list(surface)
    width = len(profile.binary_positions)
    for ordinal, position in enumerate(profile.binary_positions):
        bit = (case_index >> (width - ordinal - 1)) & 1
        characters[position] = (
            characters[position].upper() if bit else characters[position].lower()
        )
    return "".join(characters)


@dataclass(frozen=True, slots=True)
class GrammarRoute:
    tongue: str
    order: str
    role: str
    slot: int
    tongue_index: int


def grammar_route(role: str, tongue: str) -> GrammarRoute:
    """Place an observed grammatical role in one existing tongue order."""

    normalized_role = str(role).upper()
    normalized_tongue = str(tongue).upper()
    if normalized_role not in ROLES:
        raise ValueError("role must be an explicitly observed S, V, or O")
    if normalized_tongue not in TONGUE_ORDERS:
        raise ValueError("tongue must be one of KO, AV, RU, CA, UM, or DR")
    order = TONGUE_ORDERS[normalized_tongue]
    return GrammarRoute(
        tongue=normalized_tongue,
        order=order,
        role=normalized_role,
        slot=order.index(normalized_role),
        tongue_index=TONGUE_ORDER_SEQUENCE.index(normalized_tongue),
    )


@dataclass(frozen=True, slots=True)
class TokenRouteAddress:
    """One point in case-variant x tongue-order possibility space."""

    surface: str
    normalized: str
    role: str
    tongue: str
    order: str
    slot: int
    case_index: int
    tongue_index: int
    address: int
    address_count: int
    grammar_mapping_id: str = GRAMMAR_MAPPING_ID
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        profile = surface_case_profile(self.surface)
        route = grammar_route(self.role, self.tongue)
        expected_address = (
            profile.case_index * len(TONGUE_ORDER_SEQUENCE) + route.tongue_index
        )
        if (
            self.normalized != profile.normalized
            or self.case_index != profile.case_index
        ):
            raise ValueError("route identity does not match its exact surface")
        if (self.order, self.slot, self.tongue_index) != (
            route.order,
            route.slot,
            route.tongue_index,
        ):
            raise ValueError("route grammar fields do not match the tongue authority")
        if self.address != expected_address:
            raise ValueError("route address does not match case and tongue coordinates")
        if self.address_count != profile.variant_count * len(TONGUE_ORDER_SEQUENCE):
            raise ValueError("route address_count does not match its bounded space")
        if self.grammar_mapping_id != GRAMMAR_MAPPING_ID or self.schema != SCHEMA:
            raise ValueError("route authority or schema mismatch")


def encode_route(surface: str, role: str, tongue: str) -> TokenRouteAddress:
    profile = surface_case_profile(surface)
    route = grammar_route(role, tongue)
    return TokenRouteAddress(
        surface=surface,
        normalized=profile.normalized,
        role=route.role,
        tongue=route.tongue,
        order=route.order,
        slot=route.slot,
        case_index=profile.case_index,
        tongue_index=route.tongue_index,
        address=profile.case_index * len(TONGUE_ORDER_SEQUENCE) + route.tongue_index,
        address_count=profile.variant_count * len(TONGUE_ORDER_SEQUENCE),
    )


def decode_route(surface: str, role: str, address: int) -> TokenRouteAddress:
    """Decode a bounded address into a case variant and grammar sector."""

    profile = surface_case_profile(surface)
    address_count = profile.variant_count * len(TONGUE_ORDER_SEQUENCE)
    if not isinstance(address, int) or isinstance(address, bool):
        raise TypeError("address must be an integer")
    if address < 0 or address >= address_count:
        raise ValueError(f"address must be in [0, {address_count - 1}]")
    case_index, tongue_index = divmod(address, len(TONGUE_ORDER_SEQUENCE))
    variant = case_variant(surface, case_index)
    return encode_route(variant, role, TONGUE_ORDER_SEQUENCE[tongue_index])


def projection_weights(route: TokenRouteAddress) -> tuple[float, ...]:
    """Project exact case/role/slot fields into eight bounded numeric lanes.

    The first four lanes describe the observed case pattern. The next three are
    an S/V/O one-hot carrier, and the final lane is the role's centered
    presentation slot (-1, 0, +1). These are correlated derived coordinates,
    not eight independent observations.
    """

    profile = surface_case_profile(route.surface)
    simple_count = len(profile.binary_bits)
    surface_length = len(route.surface)
    upper_count = sum(profile.binary_bits)
    case_balance = (
        (2.0 * upper_count - simple_count) / simple_count if simple_count else 0.0
    )
    cased_fraction = simple_count / surface_length
    transition_fraction = (
        profile.transition_count / (simple_count - 1) if simple_count > 1 else 0.0
    )
    weighted_denominator = math.fsum(
        position + 1 for position in profile.binary_positions
    )
    position_moment = (
        math.fsum(
            (position + 1) * (1.0 if bit else -1.0)
            for position, bit in zip(
                profile.binary_positions, profile.binary_bits, strict=True
            )
        )
        / weighted_denominator
        if weighted_denominator
        else 0.0
    )
    role_lanes = tuple(1.0 if route.role == role else 0.0 for role in ROLES)
    return (
        case_balance,
        cased_fraction,
        transition_fraction,
        position_moment,
        *role_lanes,
        float(route.slot - 1),
    )


def typed_feature_keys(route: TokenRouteAddress) -> dict[str, tuple[str, ...]]:
    """Return features for the catalog's existing lexical and speech views."""

    profile = surface_case_profile(route.surface)
    return {
        "lexical": (
            f"case:{profile.kind}",
            f"case-sector:{profile.case_sector}",
        ),
        "speech": (
            f"role:{route.role}",
            f"order:{route.order}",
            f"slot:{route.slot}",
            f"tongue:{route.tongue}",
        ),
    }


__all__ = [
    "CASE_SECTORS",
    "GRAMMAR_MAPPING_ID",
    "GrammarRoute",
    "ROLES",
    "SCHEMA",
    "SurfaceCaseProfile",
    "TONGUE_ORDERS",
    "TONGUE_ORDER_SEQUENCE",
    "TokenRouteAddress",
    "case_variant",
    "decode_route",
    "encode_route",
    "grammar_route",
    "normalize_surface",
    "projection_weights",
    "surface_case_profile",
    "typed_feature_keys",
]
