from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts import probe_thermal_mirror
from src.minimal.mirror_problem_fft import make_banded_control, make_random_control


def test_analyze_control_matrix_emits_thermal_and_differential_summaries() -> None:
    analysis = probe_thermal_mirror.analyze_control_matrix(
        "banded",
        size=12,
        mode="flatten",
        alpha=1.0,
        heat_source="l2_norm",
        min_scale=0.1,
        seed=5,
    )

    assert analysis["control_kind"] == "banded"
    assert "thermal" in analysis["transform_summaries"]
    assert "D_w_t" in analysis["differential_summaries"]
    assert analysis["matrix_report"]["thermal_profile"]["variant"] == "phase_mirage"
    assert analysis["matrix_report"]["thermal_profile"]["source"] == "l2_norm"


def test_analyze_attention_stack_counts_layers_and_heads() -> None:
    banded = make_banded_control(8)
    random = make_random_control(8, seed=13)
    layer0 = np.stack([banded, random], axis=0)
    layer1 = np.stack([random, banded], axis=0)
    attentions = [layer0[np.newaxis, ...], layer1[np.newaxis, ...]]

    analysis = probe_thermal_mirror.analyze_attention_stack(
        attentions,
        mode="flatten",
        alpha=0.8,
        heat_source="l2_norm",
        min_scale=0.1,
        max_layers=2,
        max_heads=2,
    )

    assert analysis["layer_count"] == 2
    assert analysis["head_count"] == 4
    assert "original" in analysis["transform_summaries"]
    assert "thermal" in analysis["transform_summaries"]
    assert "D_s_t" in analysis["differential_summaries"]


def test_analyze_prompt_batch_aggregates_multiple_extractions() -> None:
    banded = make_banded_control(8)
    random = make_random_control(8, seed=13)
    extraction_a = {
        "prompt": "alpha",
        "sequence_length": 8,
        "token_count": 8,
        "attentions": [np.stack([banded, random], axis=0)[np.newaxis, ...]],
    }
    extraction_b = {
        "prompt": "beta",
        "sequence_length": 8,
        "token_count": 8,
        "attentions": [np.stack([random, banded], axis=0)[np.newaxis, ...]],
    }

    analysis = probe_thermal_mirror.analyze_prompt_batch(
        [extraction_a, extraction_b],
        mode="flatten",
        alpha=1.2,
        heat_source="l2_norm",
        min_scale=0.1,
        max_layers=1,
        max_heads=2,
    )

    assert analysis["prompt_count"] == 2
    assert analysis["head_count"] == 4
    assert len(analysis["prompt_reports"]) == 2
    assert analysis["transform_summaries"]["thermal"]["count"] == 4


def test_write_report_creates_json_bundle(tmp_path: Path) -> None:
    report = {
        "record_type": "thermal_mirror_probe_v1",
        "analysis": {"head_count": 1},
    }

    artifact = probe_thermal_mirror.write_report(report, output_root=tmp_path, label="demo/model")

    assert artifact.exists()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["analysis"]["head_count"] == 1


def test_main_control_json_smoke(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = probe_thermal_mirror.main(
        [
            "--control",
            "banded",
            "--size",
            "8",
            "--output-root",
            str(tmp_path),
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["control_kind"] == "banded"
    assert Path(payload["artifact_path"]).exists()
