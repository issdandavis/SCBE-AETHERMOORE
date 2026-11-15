"""Capacity receipts for programmatically reprinted token trees."""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path

import pytest

from python.scbe.eot_token_lattice import TokenProbability, TokenTableDistribution
from python.scbe.token_tree_wafer_growth import (
    ExternalQuineWaferAdapter,
    TokenTreeGrowthSpec,
    grow_token_trees,
)
from python.scbe.token_honeycomb_nest import TokenNestError
from scripts.tokenizer.grow_token_tree_wafer import _load_table


class _FakeWafer:
    source_file = "fake-wafer.py"
    source_locator = "fake-wafer.py"
    source_sha256 = sha256(b"fake-wafer-v1").hexdigest()
    adapter_kind = "in-process-test-double"
    external_wafer_invoked = False
    rotor_magnitude = 1.0 / math.sqrt(3.0)
    rotor_angle_degrees = 30.0

    def project_byte(
        self,
        byte_value: int,
        *,
        depth: int,
        side: int,
        global_rotation_degrees: float,
        patch_orientation: int,
        patch_rotation_degrees: float,
    ) -> dict[str, float | int]:
        opcode = byte_value & 63
        orientation = byte_value >> 6
        patch = patch_rotation_degrees if orientation == patch_orientation else 0.0
        angle_degrees = opcode * 137.50776405 + orientation * 90.0 + global_rotation_degrees + patch
        angle = math.radians(angle_degrees)
        radius = (1.0 + opcode / 64.0) * self.rotor_magnitude**depth
        return {
            "byte_cell": byte_value,
            "opcode_cell": opcode,
            "orientation": orientation,
            "depth": depth,
            "side": side,
            "angle_degrees": angle_degrees,
            "x": side * radius * math.cos(angle),
            "y": radius * math.sin(angle),
            "z": depth + (0.1 if side < 0 else 0.0),
            "radius": radius,
        }

    def quine_probe(self, *, opcode: int, depth: int, side: int, phase: float) -> dict[str, object]:
        return {
            "kind": "fake-variable-injection-quine",
            "template_hash": "fake",
            "rendered_sha256": sha256(f"{opcode}:{depth}:{side}:{phase}".encode()).hexdigest(),
            "self_check": True,
            "binary_roundtrip": True,
            "primary_consistent": True,
        }


def _base_table() -> TokenTableDistribution:
    return TokenTableDistribution(
        "base",
        (
            TokenProbability(0, b"alpha".hex(), 0.35),
            TokenProbability(1, b"alpine".hex(), 0.20),
            TokenProbability(2, b"beta".hex(), 0.25),
            TokenProbability(3, b"gamma".hex(), 0.20),
        ),
        tokenizer_fingerprint="unit-fixture",
    )


def test_growth_counts_distinct_views_and_weight_fields_without_byte_rewrite() -> None:
    result = grow_token_trees(
        _base_table(),
        _FakeWafer(),
        TokenTreeGrowthSpec(generations=8, depth_cycle=4, seed=7),
    )
    metrics = result["metrics"]
    assert metrics["built_tree_count"] == 8
    assert metrics["unique_view_count"] == 8
    assert metrics["unique_measure_count"] == 8
    assert metrics["unique_combined_tree_count"] == 8
    assert metrics["capacity_is_lower_bound_when_no_collision"] is True
    assert metrics["first_collision"] is None
    assert metrics["all_quine_probes_pass"] is True
    assert metrics["maximum_path_reconstruction_abs_error"] <= 1e-12
    assert metrics["generated_token_row_count"] == 32
    assert len({row["topology_sha256"] for row in result["records"]}) == 1
    assert all(
        row["token_path_projection"]["projection_mode"] == "ordered-full-decoded-byte-path" for row in result["records"]
    )
    assert all(row["token_path_projection"]["unique_quantized_token_path_signals"] == 4 for row in result["records"])
    assert result["wafer_adapter"]["external_wafer_invoked"] is False
    assert result["claim_boundary"]["byte_identity_changed"] is False
    assert result["claim_boundary"]["neural_weights_trained"] is False


def test_growth_is_replay_deterministic() -> None:
    spec = TokenTreeGrowthSpec(generations=3, seed=11)
    left = grow_token_trees(_base_table(), _FakeWafer(), spec)
    right = grow_token_trees(_base_table(), _FakeWafer(), spec)
    assert left["receipt_sha256"] == right["receipt_sha256"]


def test_growth_receipt_is_independent_of_input_row_order() -> None:
    base = _base_table()
    reversed_base = TokenTableDistribution(
        base.table_id,
        tuple(reversed(base.tokens)),
        tokenizer_fingerprint=base.tokenizer_fingerprint,
    )
    spec = TokenTreeGrowthSpec(generations=3, seed=5)
    forward = grow_token_trees(base, _FakeWafer(), spec)
    reverse = grow_token_trees(reversed_base, _FakeWafer(), spec)
    assert forward["receipt_sha256"] == reverse["receipt_sha256"]


REAL_WAFER = Path(r"C:\dev\clay-wafer-net\clay_wafer_net\wafer_6d_quine.py")


@pytest.mark.skipif(not REAL_WAFER.is_file(), reason="local quine-wafer lane unavailable")
def test_real_quine_wafer_adapter_executes_existing_variable_injection() -> None:
    adapter = ExternalQuineWaferAdapter(REAL_WAFER.parents[1])
    result = grow_token_trees(
        _base_table(),
        adapter,
        TokenTreeGrowthSpec(generations=3, depth_cycle=3),
    )
    assert result["wafer_adapter"]["external_wafer_invoked"] is True
    assert result["metrics"]["all_quine_probes_pass"] is True
    assert result["metrics"]["unique_combined_tree_count"] == 3


def test_b256_loader_rejects_content_drift_under_stale_declared_hash(
    tmp_path: Path,
) -> None:
    tokens = [
        {"id": 0, "hex": "61", "length": 1},
        {"id": 1, "hex": "62", "length": 1},
    ]
    hash_body = {
        "schema": "clay.b256-token-table.v1",
        "tokens": tokens,
        "special_token_ids": [0],
    }
    payload = {
        **hash_body,
        "tokenizer_sha256": "1" * 64,
        "table_sha256": sha256(
            json.dumps(
                hash_body,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
    }
    payload["tokens"][1] = {"id": 1, "hex": "63", "length": 1}
    path = tmp_path / "drifted.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TokenNestError, match="SHA-256"):
        _load_table(path, None, "uniform")
