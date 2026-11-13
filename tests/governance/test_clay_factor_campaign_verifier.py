"""Independent inference controls for Clay multi-view factor campaigns."""

from __future__ import annotations

import copy

import pytest
import torch

from python.scbe import clay_multiview_factor_coverage as factor
from python.scbe import clay_paired_orbit_training as training
from python.scbe.clay_factor_campaign_verifier import (
    FactorCampaignVerificationError,
    independent_metrics,
    manual_mlp_logits,
    recompute_aggregate,
    recompute_gate,
)


def test_manual_forward_and_metrics_match_producer_without_model_helper() -> None:
    torch.manual_seed(20261113)
    model = training.StandardActionMLP(hidden_width=64).eval()
    features = torch.randn(257, training.FEATURE_WIDTH)
    labels = torch.randint(0, training.ACTION_COUNT, (257,))
    state = {name: value.detach().clone() for name, value in model.state_dict().items()}

    reference_logits = model(features)
    replay_logits = manual_mlp_logits(state, features)
    torch.testing.assert_close(replay_logits, reference_logits, rtol=1e-6, atol=1e-7)

    reference = training._metrics(reference_logits, labels, min_stable_support=8)
    replay, predictions = independent_metrics(replay_logits, labels, min_stable_support=8)
    assert predictions.tolist() == reference_logits.argmax(dim=-1).tolist()
    assert replay["confusion"] == reference["confusion"]
    for key, value in reference.items():
        if isinstance(value, float):
            assert replay[key] == pytest.approx(value, rel=1e-6, abs=1e-7)
        else:
            assert replay[key] == value


def _metric_row(
    value: float,
) -> dict[str, float | list[int] | list[float] | list[list[int]]]:
    return {
        "accuracy": value,
        "macro_f1": value - 0.01,
        "full_action_macro_f1": value - 0.02,
        "stable_macro_f1": value - 0.01,
        "worst_class_accuracy": value - 0.03,
        "worst_stable_class_accuracy": value - 0.03,
        "cross_entropy": 1.0 - value,
        "per_class_accuracy": [value] * 5,
        "supported_class_count": 5,
        "stable_class_count": 5,
        "stable_class_support_threshold": 1,
        "class_support": [20] * 5,
        "absent_true_classes": [],
        "sparse_true_classes": [],
        "predictions_into_absent_classes": 0,
        "confusion": [[20 if row == column else 0 for column in range(5)] for row in range(5)],
    }


def _synthetic_result() -> tuple[dict, list[dict]]:
    arms = list(factor.ARMS)
    primary = "multiview_random"
    controls = [arm for arm in arms if arm != primary]
    seeds = [17, 29, 41]
    held_sectors = [1, 4, 7]
    horses: list[dict] = []
    for held in held_sectors:
        for arm in arms:
            for seed_index, seed in enumerate(seeds):
                base = 0.78 + held * 0.001 + seed_index * 0.0005
                if arm == primary:
                    base += 0.08
                horses.append(
                    {
                        "held_sector": held,
                        "arm": arm,
                        "seed": seed,
                        "holdout": _metric_row(base),
                        "anchor": _metric_row(0.90 + seed_index * 0.001),
                        "selected_gradient_coherence": {"mean_cosine": 0.25},
                        "weight_effect": {"l2_drift": 3.0},
                    }
                )
    configuration = {
        "arms": arms,
        "primary_arm": primary,
        "controls": controls,
        "seeds": seeds,
        "held_sectors": held_sectors,
        "evaluation_records": 10_000,
    }
    body = {"configuration": configuration, "horses": horses}
    return {**body, "result_sha256": training.sha256_json(body)}, horses


def test_independent_aggregate_and_gate_match_producer_math() -> None:
    result, horses = _synthetic_result()
    expected_aggregate = training.aggregate(
        horses,
        arms=result["configuration"]["arms"],
        primary_arm=result["configuration"]["primary_arm"],
        controls=result["configuration"]["controls"],
    )
    assert recompute_aggregate(horses, configuration=result["configuration"]) == expected_aggregate
    assert recompute_gate(result, configuration=result["configuration"]) == factor.evaluate_factor_gate(result)


def test_independent_metrics_expose_changed_predictions() -> None:
    torch.manual_seed(7)
    model = training.StandardActionMLP(hidden_width=64).eval()
    features = torch.randn(64, training.FEATURE_WIDTH)
    labels = torch.randint(0, training.ACTION_COUNT, (64,))
    state = {name: value.detach().clone() for name, value in model.state_dict().items()}
    logits = manual_mlp_logits(state, features)
    receipt, _ = independent_metrics(logits, labels, min_stable_support=1)
    tampered = copy.deepcopy(state)
    tampered["output_layer.bias"][0] += 100.0
    changed, _ = independent_metrics(manual_mlp_logits(tampered, features), labels, min_stable_support=1)
    assert changed["confusion"] != receipt["confusion"]


def test_manual_forward_rejects_unknown_checkpoint_shape() -> None:
    with pytest.raises(FactorCampaignVerificationError, match="architecture"):
        manual_mlp_logits({"wrong": torch.zeros(1)}, torch.zeros(1, 37))
