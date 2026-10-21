from __future__ import annotations

import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = ROOT / "scripts" / "experiments"
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

import export_spiral_staircase_snap_weights as EXPORT  # noqa: E402
import spiral_staircase_lattice_snap as SNAP  # noqa: E402
import spiral_staircase_reasoning as COUPLED  # noqa: E402


def test_safetensors_round_trip_preserves_exact_model_state(tmp_path: Path) -> None:
    torch.manual_seed(71)
    model = SNAP.LatticeSnapStaircaseNet()
    expected = COUPLED.model_state_sha256(model)
    path = tmp_path / "weights.safetensors"

    receipt = EXPORT.save_verified_checkpoint(
        model,
        path,
        expected_state_sha256=expected,
        metadata={"schema": "test"},
    )

    assert receipt["reload_verified"] is True
    assert receipt["state_sha256"] == expected
    assert receipt["parameter_count"] == 60020
    assert path.is_file()
