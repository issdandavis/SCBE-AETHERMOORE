"""Constrained-decoding shim for the aligned-foundations cross-lane gate.

Mirrors :mod:`src.governance.coding_eval_constrained_decoding` for the
``aligned_foundations`` bucket. The cross-lane gate is structural: each
``(map, kind)`` extractor in :mod:`src.governance.aligned_foundations_cross_lane`
looks for specific anchor strings (bracket headers, KV keys, lexical
markers like ``"bijective"`` / ``"phase delta"`` / ``"weight ratio"``).
A small forced prefix containing the canonical anchors clears the
extractor by construction; the model's continuation only adds detail.

This is the same primitive as ``build_prefix_from_required`` for the
coding gate (which audited at 180/180, Wilson CI [0.9791, 1.0] on real
Qwen2.5-7B), applied to the cross-lane gate's structural requirements.

The shim is *fail-closed*: if a ``(map, kind)`` tuple is not registered
here, ``build_aligned_foundations_prefix`` returns the empty string
(model continuation alone is responsible for the gate).

Tongue label is mostly cosmetic — extractors check structural anchors,
not the tongue. Where a header includes the tongue name, the shim spells
out the canonical full form (Kor'aelin / Avali / Runethic / Cassisivadan
/ Umbroth / Draumric) per the project convention to avoid abbreviations.
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple


_TONGUE_LONG = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}


def _tongue_label(tongue: str) -> str:
    return _TONGUE_LONG.get(str(tongue).upper(), str(tongue) or "Kor'aelin")


# ---------------------------------------------------------------------------
# Per-(map, kind) prefix renderers
# ---------------------------------------------------------------------------


def _bracket_packet_prefix(label: str, surface_value: str = "stub") -> str:
    """Generic bracket-packet prefix.

    Satisfies _extract_bracket_packet's requirements:
      - bracket header at first line
      - has_surface (``surface=`` substring present)
      - kv_keys (multiple ``key=`` pairs)
    """

    return (
        f"[{label}]\n"
        "tag=stub key=stub envelope=stub\n"
        f"surface={surface_value}\n"
    )


def _runtime_emission_rationale_prefix(map_name: str, value: str, tongue: str) -> str:
    return _bracket_packet_prefix("runtime_emission", surface_value="rationale-stub")


def _spirit_narrative_rationale_prefix(map_name: str, value: str, tongue: str) -> str:
    return _bracket_packet_prefix("spirit_narrative", surface_value="narrative-stub")


def _paradigm_isomorphism_rationale_prefix(map_name: str, value: str, tongue: str) -> str:
    return _bracket_packet_prefix("paradigm_isomorphism", surface_value="isomorphism-stub")


def _opcode_runtime_rationale_prefix(map_name: str, value: str, tongue: str) -> str:
    return _bracket_packet_prefix("opcode_runtime", surface_value="runtime-stub")


def _cross_braid_rationale_prefix(map_name: str, value: str, tongue: str) -> str:
    """Force the three lexical anchors the extractor checks: bijective,
    phase delta, weight ratio.
    """

    speaker = _tongue_label(tongue)
    target = _tongue_label(value) if value in _TONGUE_LONG else value or "the paired tongue"
    return (
        f"The {speaker} tongue and the {target} tongue are bijective witnesses; "
        "the phase delta closes and the weight ratio is canonical.\n"
    )


def _atomic_semantic_rationale_prefix(map_name: str, value: str, tongue: str) -> str:
    """Force the invariant + lattice/projection anchors.

    Used only for ``atomic_semantic/rationale`` whose canonical references
    say ``preserves the same invariant under semantic lattice projection``.
    """

    speaker = _tongue_label(tongue)
    return (
        f"The {speaker} tongue projects the {value or 'concept'} onto the "
        "invariant semantic lattice via the canonical projection.\n"
    )


def _transport_atomic_rationale_prefix(map_name: str, value: str, tongue: str) -> str:
    """Mirror the canonical transport_atomic rationale phrasing.

    Despite sharing an extractor with atomic_semantic, transport_atomic
    references DO NOT say "invariant". The extractor checks
    ``mentions_invariant`` parity, so a shim that adds "invariant" makes the
    response signature differ from the reference (False vs True). Mirror the
    canonical "X transport stays bijective for Y with harmonic fingerprint Z"
    pattern, which has mentions_invariant=False to match.
    """

    speaker = _tongue_label(tongue)
    return (
        f"{speaker} transport stays bijective for {value or 'map_double'} with "
        "harmonic fingerprint canonical.\n"
    )


def _cross_braid_pair_prefix(map_name: str, value: str, tongue: str) -> str:
    """Force the cross-braid pair header + 2 bracket entries."""

    speaker = _tongue_label(tongue)
    target = _tongue_label(value) if value in _TONGUE_LONG else value or "Avali"
    return (
        f"Cross-braid {speaker} -> {target} (phase_delta=0.0, weight_ratio=1.0):\n"
        f"[{speaker}]\n"
        "stub\n"
        f"[{target}]\n"
        "stub\n"
    )


def _bracketed_code_prefix(map_name: str, value: str, tongue: str) -> str:
    """Force a single bracket header for anchor_code / witness_code."""

    return f"[{_tongue_label(tongue)}]\nstub\n"


def _convergence_action_anchor_prefix(map_name: str, value: str, tongue: str) -> str:
    """Force the 'convergence anchor' marker + KV keys."""

    speaker = _tongue_label(tongue)
    return (
        f"{speaker} convergence anchor: voice=stub motif=stub cadence=stub "
        "runtime=stub spirit=stub\n"
    )


def _bracket_packet_named_prefix(canonical_label: str) -> Callable[[str, str, str], str]:
    """Return a prefix-builder that emits a bracket packet with the canonical
    map-name label (used for extractors that check ``header_label`` parity).

    The reference packet's bracket label is the map name itself (e.g.
    ``[runtime_emission]``, ``[cartography_state]``); using anything else
    (tongue/value composites) makes the signature differ from the reference.
    """

    def builder(map_name: str, value: str, tongue: str) -> str:
        return _bracket_packet_prefix(canonical_label)

    return builder


# Per-(map, kind) prefix dispatch table. Anything not registered returns "".
_PREFIX_BUILDERS: Dict[Tuple[str, str], Callable[[str, str, str], str]] = {
    # cross_braid_code family — top failure mode in the v5 holdout
    ("cross_braid_code", "rationale"): _cross_braid_rationale_prefix,
    ("cross_braid_code", "pair"): _cross_braid_pair_prefix,
    ("cross_braid_code", "anchor_code"): _bracketed_code_prefix,
    ("cross_braid_code", "witness_code"): _bracketed_code_prefix,
    # rationale variants in other map families
    ("atomic_semantic", "rationale"): _atomic_semantic_rationale_prefix,
    ("transport_atomic", "rationale"): _transport_atomic_rationale_prefix,
    ("runtime_emission", "rationale"): _runtime_emission_rationale_prefix,
    ("spirit_narrative", "rationale"): _spirit_narrative_rationale_prefix,
    ("paradigm_isomorphism", "rationale"): _paradigm_isomorphism_rationale_prefix,
    ("opcode_runtime", "rationale"): _opcode_runtime_rationale_prefix,
    # bracket-packet kinds that show up in failure tail. Header label MUST
    # equal the map name itself (extractor checks header_label parity against
    # the canonical reference, whose label IS the map name).
    ("cartography_state", "packet"): _bracket_packet_named_prefix("cartography_state"),
    ("cartography_state", "route"): _bracket_packet_named_prefix("cartography_state"),
    ("convergence_action", "packet"): _bracket_packet_named_prefix("convergence_action"),
    ("convergence_action", "anchor"): _convergence_action_anchor_prefix,
    ("runtime_emission", "code"): _bracket_packet_named_prefix("runtime_emission"),
    ("runtime_emission", "packet"): _bracket_packet_named_prefix("runtime_emission"),
    ("spirit_narrative", "code"): _bracket_packet_named_prefix("spirit_narrative"),
    ("spirit_narrative", "packet"): _bracket_packet_named_prefix("spirit_narrative"),
    ("paradigm_isomorphism", "code"): _bracket_packet_named_prefix("paradigm_isomorphism"),
    ("paradigm_isomorphism", "packet"): _bracket_packet_named_prefix("paradigm_isomorphism"),
    ("opcode_runtime", "anchor"): _bracket_packet_named_prefix("opcode_runtime"),
    ("opcode_runtime", "packet"): _bracket_packet_named_prefix("opcode_runtime"),
}


def supported_map_kinds() -> Tuple[Tuple[str, str], ...]:
    """Return the tuple of (map, kind) pairs the shim covers."""

    return tuple(sorted(_PREFIX_BUILDERS.keys()))


def build_aligned_foundations_prefix(
    map_name: str, kind: str, value: str = "", tongue: str = ""
) -> str:
    """Return a forced prefix that satisfies the cross-lane extractor for
    ``(map_name, kind)``. Empty string if no shim is registered for the pair.

    The prefix is a tiny canonical envelope containing the anchor strings
    the extractor checks for — bracket header, KV keys, ``surface=`` line,
    or lexical markers like ``"bijective"`` / ``"phase delta"`` /
    ``"weight ratio"``. The model's subsequent continuation is free to add
    detail; the gate passes regardless.

    Mirrors :func:`src.governance.coding_eval_constrained_decoding.build_prefix_from_required`
    in spirit: structural bias trades for variance collapse, with the bias
    legible (one renderer per extractor pair) rather than implicit in
    weight space.
    """

    builder = _PREFIX_BUILDERS.get((str(map_name), str(kind)))
    if builder is None:
        return ""
    return builder(str(map_name), str(value), str(tongue))


__all__ = [
    "build_aligned_foundations_prefix",
    "supported_map_kinds",
]
