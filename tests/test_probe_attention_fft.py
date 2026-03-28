from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts import probe_attention_fft
from src.minimal.mirror_problem_fft import make_banded_control, make_random_control


def test_parse_index_list_handles_empty_and_csv() -> None:
    assert probe_attention_fft.parse_index_list("") is None
    assert probe_attention_fft.parse_index_list("0, 2,5") == [0, 2, 5]


def test_resolve_prompts_uses_default_set_and_limit() -> None:
    prompts = probe_attention_fft.resolve_prompts(
        "",
        use_default_prompt_set=True,
        max_prompts=3,
    )

    assert len(prompts) == 3
    assert prompts[0] == probe_attention_fft.DEFAULT_PROMPT_SET[0]


def test_analyze_control_matrix_prefers_banded_for_banded_control() -> None:
    report = probe_attention_fft.analyze_control_matrix(
        "banded", size=16, mode="flatten", seed=5
    )

    assert report["closer_to_banded_than_random"] is True
    assert report["candidate"]["s_spec"] == pytest.approx(
        report["controls"]["banded"]["s_spec"]
    )


def test_analyze_attention_stack_counts_layers_and_heads() -> None:
    banded = make_banded_control(8)
    random = make_random_control(8, seed=13)
    layer0 = np.stack([banded, random], axis=0)
    layer1 = np.stack([random, banded], axis=0)
    attentions = [layer0[np.newaxis, ...], layer1[np.newaxis, ...]]

    analysis = probe_attention_fft.analyze_attention_stack(
        attentions,
        mode="flatten",
        max_layers=2,
        max_heads=2,
    )

    assert analysis["layer_count"] == 2
    assert analysis["head_count"] == 4
    assert len(analysis["layers"]) == 2
    assert analysis["average_s_spec"] > 0.0


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

    analysis = probe_attention_fft.analyze_prompt_batch(
        [extraction_a, extraction_b],
        mode="flatten",
        max_layers=1,
        max_heads=2,
    )

    assert analysis["prompt_count"] == 2
    assert analysis["layer_count"] == 1
    assert analysis["head_count"] == 2
    assert len(analysis["prompt_reports"]) == 2
    assert analysis["average_s_spec"] > 0.0


def test_write_report_creates_json_bundle(tmp_path: Path) -> None:
    report = {
        "record_type": "attention_fft_probe_v1",
        "analysis": {"head_count": 1},
    }

    artifact = probe_attention_fft.write_report(
        report, output_root=tmp_path, label="demo/model"
    )

    assert artifact.exists()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["analysis"]["head_count"] == 1


def test_build_report_includes_precision_drift_section() -> None:
    report = probe_attention_fft.build_report(
        analysis={"head_count": 1},
        token_env="HF_TOKEN",
        precision_drift={"prompt_count": 2, "average_s_spec": 0.4},
    )

    assert report["precision_drift"]["prompt_count"] == 2


def test_build_report_for_control_has_synthetic_model_id() -> None:
    report = probe_attention_fft.build_report(
        analysis={"head_count": 1},
        token_env="HF_TOKEN",
        control_kind="random",
    )

    assert report["model_id"] == "synthetic-control"
    assert report["control_kind"] == "random"


def test_main_control_json_smoke(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = probe_attention_fft.main(
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


def test_resolve_torch_dtype_accepts_known_and_rejects_unknown() -> None:
    class TorchStub:
        float32 = "float32"
        float64 = "float64"

    assert probe_attention_fft._resolve_torch_dtype(TorchStub, "float32") == "float32"
    with pytest.raises(ValueError):
        probe_attention_fft._resolve_torch_dtype(TorchStub, "not-a-real-dtype")


def test_analyze_precision_drift_aggregates_prompt_reports(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.probe_attention_fft.load_model_bundle",
        lambda model_id, **kwargs: probe_attention_fft.ModelBundle(
            model=object(),
            tokenizer=object(),
            model_id=model_id,
            source="stub",
            device=kwargs["requested_device"],
            dtype=str(kwargs["torch_dtype_name"]),
            base_model_id=None,
        ),
    )

    hidden_matrices = {
        "float32": {
            "alpha": np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float64),
            "beta": np.array([[0.5, 0.5], [0.5, 0.5]], dtype=np.float64),
        },
        "float64": {
            "alpha": np.array([[1.2, 0.0], [0.0, 1.3]], dtype=np.float64),
            "beta": np.array([[0.8, 0.4], [0.3, 0.9]], dtype=np.float64),
        },
    }

    def _fake_extract_hidden(bundle, prompt, *, max_length):
        matrix = hidden_matrices[bundle.dtype][prompt]
        return {
            "hidden_matrix": matrix,
            "sequence_length": matrix.shape[0],
            "feature_count": matrix.shape[1],
            "prompt": prompt,
        }

    monkeypatch.setattr(
        "scripts.probe_attention_fft.extract_hidden_matrix", _fake_extract_hidden
    )

    analysis = probe_attention_fft.analyze_precision_drift(
        "demo-model",
        ["alpha", "beta"],
        token=None,
        requested_device="cpu",
        attn_implementation="eager",
        max_length=16,
        dtype_a="float32",
        dtype_b="float64",
        mode="flatten",
    )

    assert analysis["prompt_count"] == 2
    assert analysis["source_models"]["a"]["dtype"] == "float32"
    assert analysis["source_models"]["b"]["dtype"] == "float64"
    assert analysis["max_abs_drift"] > 0.0
    assert len(analysis["prompt_reports"]) == 2
