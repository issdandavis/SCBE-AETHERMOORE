"""Schema test for the motion_assembly overlay (draft v1).

Locks the three rules from docs/specs/MOTION_ASSEMBLY_SCHEMA.md:
  1. motion_assembly is nested under semantic_expression.
  2. ASCII-only field names (no Greek glyphs).
  3. Motion is a domain overlay; existing code-packet lanes are intact.

The fixture is an in-memory packet that simulates what a real
code-packet emitter would produce for a drone CTBR row. We validate
schema invariants without invoking the geoseal_cli subprocess so the
test is fast and hermetic.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

REQUIRED_TOP_LEVEL_LANES: tuple[str, ...] = (
    "version",
    "binary",
    "tokenizer",
    "transport",
    "labels",
    "language_views",
    "braille_lane",
    "stisa",
    "structural_parse",
    "scip_symbol_index",
    "semantic_token_bridge",
    "route_ir",
    "execution_lane",
    "native_tokenization",
    "atomic_states",
    "ternary_semantics",
    "semantic_expression",
)

REQUIRED_INVARIANT_KEYS: tuple[str, ...] = (
    "joint_limits_ok",
    "motor_saturation_ok",
    "attitude_bounds_ok",
    "energy_budget_ok",
    "collision_free",
    "morphology_transition_safe",
)

ROLE_VOCAB: frozenset[str] = frozenset({"lead", "dynamics", "perception", "comms", "sensor", "auth", "free"})

MORPHOLOGY_VOCAB: frozenset[str] = frozenset({"separated", "combining", "combined", "transitioning"})

PILOT_LAYER_VOCAB: frozenset[str] = frozenset(
    {"strategic", "tactical", "trajectory", "attitude_rate", "perception", "operator"}
)

FORBIDDEN_BRANDING_SUBSTRINGS: tuple[str, ...] = (
    "megazord",
    "morphin",
    "zord",
    "power_ranger",
    "power ranger",
)

ASCII_ONLY_RE = re.compile(r"^[\x00-\x7f]+$")


def _fixture_packet() -> dict[str, Any]:
    """A minimal packet shaped like a drone CTBR row with motion overlay."""

    return {
        "version": "scbe-code-weight-packet-v1",
        "binary": {"byte_count": 32, "bits": ["01000100"] * 32},
        "tokenizer": {"conlang": "Cassisivadan", "tongue": "CA", "token_count": 4},
        "transport": {"tongue": "CA", "tokens": ["cass'a", "cass'e"]},
        "labels": {
            "conlang": "Cassisivadan",
            "anchor_runtime": "mjcf",
            "anchor_spirit": "dynamics",
        },
        "language_views": [
            {"language": "python", "tongue": "KO"},
            {"language": "typescript", "tongue": "AV"},
            {"language": "rust", "tongue": "RU"},
            {"language": "c", "tongue": "CA"},
            {"language": "julia", "tongue": "UM"},
            {"language": "haskell", "tongue": "DR"},
        ],
        "braille_lane": {"version": "scbe-braille-cell-lane-v1"},
        "stisa": {"version": "scbe-stisa-surface-v1", "field_definitions": [None] * 8},
        "structural_parse": {"provider": "tree_sitter"},
        "scip_symbol_index": {"provider": "tree_sitter_symbol_graph"},
        "semantic_token_bridge": {"provider": "tree_sitter_semantic_tokens"},
        "route_ir": {"schema_version": "scbe_route_ir_v1"},
        "execution_lane": {
            "schema_version": "scbe_execution_lane_v1",
            "core_lanes": ["binary"],
        },
        "native_tokenization": {"schema_version": "scbe_native_tokenization_surface_v1"},
        "atomic_states": [{"token": "thrust", "element": {"symbol": "Fe"}}],
        "ternary_semantics": {"version": "scbe-ternary-semantics-v1"},
        "semantic_expression": {
            "label": "drone_hover_hold",
            "gloss": "hold position with neutral attitude",
            "quarks": ["thrust_apply", "rate_hold"],
            "motion_assembly": {
                "schema_version": "scbe-motion-assembly-v1",
                "platform_id": "drone_03",
                "swarm_id": None,
                "role": "dynamics",
                "morphology_state": "separated",
                "combine_topology": None,
                "pilot_layers": [
                    {
                        "layer": "tactical",
                        "model_id": "neural_fly_residual_v2",
                        "confidence": 0.91,
                        "action_token": None,
                        "action_vector": [0.55, 0.0, 0.0, 0.0],
                        "action_chunk_fast": None,
                        "horizon_H": None,
                        "control_hz": 100.0,
                    },
                ],
                "comm_graph": {
                    "edges": [],
                    "global_clock_t": 12.347,
                    "local_clock_t": 12.341,
                },
                "embodiment_passport": {
                    "urdf_uri": None,
                    "mjcf_uri": "models/quad_5in.xml",
                    "dof_schema": [],
                    "thrust_to_weight": 4.2,
                    "motor_count": 4,
                },
                "invariants": {
                    "joint_limits_ok": True,
                    "motor_saturation_ok": True,
                    "attitude_bounds_ok": True,
                    "energy_budget_ok": True,
                    "collision_free": True,
                    "morphology_transition_safe": True,
                },
            },
        },
    }


# ---------------------------------------------------------------------------
# Rule 1: motion_assembly is nested under semantic_expression, not top-level
# ---------------------------------------------------------------------------


def test_motion_assembly_is_nested_under_semantic_expression() -> None:
    packet = _fixture_packet()
    assert "motion_assembly" not in packet
    assert "motion_assembly" in packet["semantic_expression"]
    assert packet["semantic_expression"]["motion_assembly"]["schema_version"] == ("scbe-motion-assembly-v1")


# ---------------------------------------------------------------------------
# Rule 2: ASCII-only field names everywhere
# ---------------------------------------------------------------------------


def _walk_keys(obj: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.append(k)
            keys.extend(_walk_keys(v))
    elif isinstance(obj, list):
        for item in obj:
            keys.extend(_walk_keys(item))
    return keys


def test_all_field_names_are_ascii() -> None:
    packet = _fixture_packet()
    for key in _walk_keys(packet):
        assert ASCII_ONLY_RE.match(key), f"non-ASCII field name: {key!r}"


def test_no_greek_glyphs_in_serialized_packet() -> None:
    packet = _fixture_packet()
    blob = json.dumps(packet, ensure_ascii=False)
    for glyph in ("ω", "Ω", "θ", "φ", "π", "Δ"):
        assert glyph not in blob, f"forbidden glyph in serialized packet: {glyph}"


# ---------------------------------------------------------------------------
# Rule 3: existing 12+ lanes are intact (motion is overlay, not spine)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lane", REQUIRED_TOP_LEVEL_LANES)
def test_existing_code_packet_lane_present(lane: str) -> None:
    packet = _fixture_packet()
    assert lane in packet, f"required code-packet lane missing: {lane}"


# ---------------------------------------------------------------------------
# anchor_runtime and anchor_spirit both required (don't flatten the system)
# ---------------------------------------------------------------------------


def test_labels_carry_both_anchor_runtime_and_anchor_spirit() -> None:
    packet = _fixture_packet()
    labels = packet["labels"]
    assert "anchor_runtime" in labels
    assert "anchor_spirit" in labels
    assert isinstance(labels["anchor_runtime"], str) and labels["anchor_runtime"]
    assert isinstance(labels["anchor_spirit"], str) and labels["anchor_spirit"]
    assert labels["anchor_runtime"] != labels["anchor_spirit"]


# ---------------------------------------------------------------------------
# motion_assembly internal structure
# ---------------------------------------------------------------------------


def _motion(packet: dict[str, Any]) -> dict[str, Any]:
    return packet["semantic_expression"]["motion_assembly"]


def test_role_is_in_closed_vocabulary() -> None:
    packet = _fixture_packet()
    assert _motion(packet)["role"] in ROLE_VOCAB


def test_morphology_state_is_in_closed_vocabulary() -> None:
    packet = _fixture_packet()
    assert _motion(packet)["morphology_state"] in MORPHOLOGY_VOCAB


def test_pilot_layers_non_empty_and_layer_in_vocabulary() -> None:
    packet = _fixture_packet()
    layers = _motion(packet)["pilot_layers"]
    assert isinstance(layers, list) and len(layers) >= 1
    for entry in layers:
        assert entry["layer"] in PILOT_LAYER_VOCAB
        assert isinstance(entry["model_id"], str) and entry["model_id"]
        assert 0.0 <= float(entry["confidence"]) <= 1.0


def test_at_least_one_pilot_layer_carries_ctbr_action_vector() -> None:
    """CTBR action vectors are length 4: [thrust_norm, omega_x, omega_y, omega_z]."""

    packet = _fixture_packet()
    layers = _motion(packet)["pilot_layers"]
    ctbr_layers = [
        layer for layer in layers if layer.get("action_vector") is not None and len(layer["action_vector"]) == 4
    ]
    assert ctbr_layers, "expected at least one pilot_layer with CTBR action_vector"
    for layer in ctbr_layers:
        thrust = layer["action_vector"][0]
        assert 0.0 <= float(thrust) <= 1.0, f"thrust_norm out of [0,1]: {thrust}"


# ---------------------------------------------------------------------------
# Invariants must be explicit booleans (no None, no string flags)
# ---------------------------------------------------------------------------


def test_invariants_are_explicit_booleans() -> None:
    packet = _fixture_packet()
    invariants = _motion(packet)["invariants"]
    for key in REQUIRED_INVARIANT_KEYS:
        assert key in invariants, f"required invariant missing: {key}"
        value = invariants[key]
        assert isinstance(value, bool), f"invariant {key!r} must be bool, got {type(value).__name__}: {value!r}"


# ---------------------------------------------------------------------------
# No forbidden branding/theming fields anywhere in the packet
# ---------------------------------------------------------------------------


def test_no_forbidden_branding_in_keys_or_values() -> None:
    packet = _fixture_packet()
    blob = json.dumps(packet).lower()
    for forbidden in FORBIDDEN_BRANDING_SUBSTRINGS:
        assert forbidden not in blob, f"forbidden branding substring in packet: {forbidden!r}"


# ---------------------------------------------------------------------------
# Sanity: the fixture round-trips through json without loss
# ---------------------------------------------------------------------------


def test_fixture_packet_round_trips_through_json() -> None:
    packet = _fixture_packet()
    blob = json.dumps(packet)
    restored = json.loads(blob)
    assert restored == packet
