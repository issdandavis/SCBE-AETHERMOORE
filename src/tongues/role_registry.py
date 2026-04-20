from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.ca_lexicon import LANG_MAP
from src.pantheon.registry import REALM_NAMES, RealmName

RoleName = Literal["transport_atomic", "paradigm_isomorphism", "runtime_emission", "spirit_narrative"]
TongueName = Literal["KO", "AV", "RU", "CA", "UM", "DR"]

ROLE_NAMES: tuple[RoleName, ...] = (
    "transport_atomic",
    "paradigm_isomorphism",
    "runtime_emission",
    "spirit_narrative",
)

AUTHORITY_FILES: dict[RoleName, tuple[str, ...]] = {
    "transport_atomic": (
        "src/crypto/sacred_tongues.py",
        "python/scbe/atomic_tokenization.py",
    ),
    "paradigm_isomorphism": (
        "python/scbe/tongue_code_lanes.py",
        "notes/System Library/Repository Mirror/docs/specs/TONGUE_ISOMORPHISM_PROOF.md",
    ),
    "runtime_emission": (
        "src/ca_lexicon/__init__.py",
    ),
    "spirit_narrative": (
        "memory + docs",
    ),
}

PARADIGM_ISOMORPHISM_MAP: dict[str, str] = {
    "KO": "lisp",
    "AV": "python",
    "RU": "forth",
    "CA": "sql",
    "UM": "assembly",
    "DR": "make",
}

OPCODE_RUNTIME_MAP: dict[str, str] = {
    "CA": "c",
}

RUNTIME_EMISSION_MAP: dict[str, str] = {tongue.upper(): lane for tongue, lane in LANG_MAP.items()}

SPIRIT_NARRATIVE_MAP: dict[str, str] = {
    "KO": "python",
    "AV": "javascript",
    "RU": "rust",
    "CA": "mathematica",
    "UM": "haskell",
    "DR": "markdown",
}

TRANSPORT_ATOMIC_MAP: dict[RealmName, dict[str, str]] = {
    "objectness": {
        tongue: "color,area,bbox_h,bbox_w,density,centroid_r,centroid_c,perimeter,holes,"
        "touches_border,is_square,is_symmetric_h,is_symmetric_v,bbox_area"
        for tongue in RUNTIME_EMISSION_MAP
    },
    "numbers": {
        tongue: "component_count,color_count,rank_global,rank_in_color,count_delta,parity,repetition_score"
        for tongue in RUNTIME_EMISSION_MAP
    },
    "geometry": {
        tongue: "z=col+i*row,bbox_fill_ratio,shape_growth,symmetry_x,symmetry_y,rotation_signature"
        for tongue in RUNTIME_EMISSION_MAP
    },
    "agent": {
        tongue: "delta_r,delta_c,centroid_shift,trajectory_sign,gravity_axis,motif_extension"
        for tongue in RUNTIME_EMISSION_MAP
    },
}

LEGACY_CODE_LANE_REGISTRY: dict[str, dict[str, str]] = {
    "computational_isomorphism": PARADIGM_ISOMORPHISM_MAP,
    "opcode_runtime": OPCODE_RUNTIME_MAP,
}

TONGUE_NAMES: tuple[TongueName, ...] = tuple(PARADIGM_ISOMORPHISM_MAP.keys())  # type: ignore[assignment]


@dataclass(frozen=True, slots=True)
class TongueJobTable:
    tongue: str
    transport_atomic: str
    paradigm_isomorphism: str
    runtime_emission: str
    spirit_narrative: str


@dataclass(frozen=True, slots=True)
class RoleBinding:
    realm: RealmName
    role: RoleName
    tongue: str
    value: str
    authority_files: tuple[str, ...]


def _normalize_tongue(tongue: str) -> TongueName:
    normalized = tongue.upper()
    if normalized not in TONGUE_NAMES:
        raise KeyError(f"Unknown tongue: {tongue}")
    return normalized  # type: ignore[return-value]


def _build_role_binding_index() -> dict[tuple[RealmName, RoleName, TongueName], RoleBinding]:
    index: dict[tuple[RealmName, RoleName, TongueName], RoleBinding] = {}
    for realm in REALM_NAMES:
        for tongue in TONGUE_NAMES:
            index[(realm, "transport_atomic", tongue)] = RoleBinding(
                realm=realm,
                role="transport_atomic",
                tongue=tongue,
                value=TRANSPORT_ATOMIC_MAP[realm][tongue],
                authority_files=AUTHORITY_FILES["transport_atomic"],
            )
            index[(realm, "paradigm_isomorphism", tongue)] = RoleBinding(
                realm=realm,
                role="paradigm_isomorphism",
                tongue=tongue,
                value=PARADIGM_ISOMORPHISM_MAP[tongue],
                authority_files=AUTHORITY_FILES["paradigm_isomorphism"],
            )
            index[(realm, "runtime_emission", tongue)] = RoleBinding(
                realm=realm,
                role="runtime_emission",
                tongue=tongue,
                value=RUNTIME_EMISSION_MAP[tongue],
                authority_files=AUTHORITY_FILES["runtime_emission"],
            )
            index[(realm, "spirit_narrative", tongue)] = RoleBinding(
                realm=realm,
                role="spirit_narrative",
                tongue=tongue,
                value=SPIRIT_NARRATIVE_MAP[tongue],
                authority_files=AUTHORITY_FILES["spirit_narrative"],
            )
    return index


ROLE_BINDING_INDEX: dict[tuple[RealmName, RoleName, TongueName], RoleBinding] = _build_role_binding_index()


def resolve_tongue_jobs(tongue: str, *, transport_realm: RealmName = "objectness") -> TongueJobTable:
    normalized = _normalize_tongue(tongue)
    return TongueJobTable(
        tongue=normalized,
        transport_atomic=TRANSPORT_ATOMIC_MAP[transport_realm][normalized],
        paradigm_isomorphism=PARADIGM_ISOMORPHISM_MAP[normalized],
        runtime_emission=RUNTIME_EMISSION_MAP[normalized],
        spirit_narrative=SPIRIT_NARRATIVE_MAP[normalized],
    )


def resolve_binding(realm: RealmName, role: RoleName, tongue: str) -> RoleBinding:
    normalized = _normalize_tongue(tongue)
    return ROLE_BINDING_INDEX[(realm, role, normalized)]


def resolve_authority(tongue: str, role: RoleName, *, realm: RealmName = "objectness") -> str:
    return resolve_binding(realm, role, tongue).value


def iter_role_bindings() -> tuple[RoleBinding, ...]:
    return tuple(ROLE_BINDING_INDEX.values())


__all__ = [
    "AUTHORITY_FILES",
    "LEGACY_CODE_LANE_REGISTRY",
    "OPCODE_RUNTIME_MAP",
    "PARADIGM_ISOMORPHISM_MAP",
    "ROLE_NAMES",
    "RUNTIME_EMISSION_MAP",
    "RoleBinding",
    "RoleName",
    "ROLE_BINDING_INDEX",
    "SPIRIT_NARRATIVE_MAP",
    "TONGUE_NAMES",
    "TongueName",
    "TRANSPORT_ATOMIC_MAP",
    "TongueJobTable",
    "iter_role_bindings",
    "resolve_authority",
    "resolve_binding",
    "resolve_tongue_jobs",
]
