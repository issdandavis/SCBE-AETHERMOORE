from __future__ import annotations

from hashlib import sha256
import json

import numpy as np
import pytest

from python.scbe.concept_exposure_ledger import (
    ConceptExposureLedger,
    ExposureSample,
    class_balanced_probabilities,
    weight_effect_receipt,
)


def _sample(
    name: str,
    concept: str,
    variant: str,
    *,
    split: str = "train",
    source: str = "train-family",
) -> ExposureSample:
    return ExposureSample(
        sample_id=name,
        payload_sha256=sha256(name.encode()).hexdigest(),
        concept_id=concept,
        variant_id=variant,
        source_family=source,
        split=split,
    )


def _samples() -> list[ExposureSample]:
    return [
        _sample("a0", "a", "left"),
        _sample("a1", "a", "right"),
        _sample("b0", "b", "left"),
        _sample("b1", "b", "right"),
        _sample("holdout", "a", "center", split="holdout", source="eval-family"),
    ]


def test_holdout_has_no_sampling_index_or_observation_path() -> None:
    ledger = ConceptExposureLedger(_samples(), gradient_width=2)
    probabilities = ledger.sampling_probabilities()

    assert probabilities.shape == (4,)
    assert np.isclose(probabilities.sum(), 1.0)
    assert "holdout" not in ledger.train_sample_ids
    with pytest.raises(ValueError, match="holdout"):
        ledger.observe_batch(["holdout"], [0.5], [[1.0, 0.0]])


def test_train_and_evaluation_source_families_must_be_disjoint() -> None:
    samples = _samples()
    samples[-1] = _sample("holdout", "a", "center", split="holdout", source="train-family")

    with pytest.raises(ValueError, match="disjoint"):
        ConceptExposureLedger(samples, gradient_width=2)


def test_underexposed_concept_and_variant_receive_more_mass() -> None:
    ledger = ConceptExposureLedger(_samples(), gradient_width=2, exploration_floor=0.05)
    for _ in range(20):
        ledger.observe_batch(
            ["a0", "a1"],
            [0.3, 0.3],
            [[1.0, 0.0], [1.0, 0.0]],
        )
    probabilities = ledger.sampling_probabilities()
    by_id = dict(zip(ledger.train_sample_ids, probabilities, strict=True))

    assert by_id["b0"] + by_id["b1"] > by_id["a0"] + by_id["a1"]
    assert np.all(probabilities > 0.0)
    assert float(probabilities.max() / probabilities.min()) <= 64.0


def test_report_tracks_variants_and_elite_gradient_coherence_without_payloads() -> None:
    ledger = ConceptExposureLedger(
        _samples(),
        gradient_width=2,
        minimum_exposures_per_concept=2,
        saturation_loss=1.0,
    )
    ledger.observe_batch(["a0", "a1"], [0.8, 0.7], [[1.0, 0.0], [1.0, 0.0]])
    ledger.observe_batch(["a0", "a1"], [0.4, 0.3], [[1.0, 0.0], [1.0, 0.0]])
    report = ledger.report()

    assert report["concepts"]["a"]["variants_seen"] == 2
    assert report["concepts"]["a"]["elite_gradient_count"] == 2
    assert report["concepts"]["a"]["elite_gradient_coherence"] == pytest.approx(1.0)
    assert report["authority"]["execution"] == "NONE"
    serialized = json.dumps(report)
    assert "payload_sha256" not in serialized
    assert "holdout" not in report["train_source_families"]


def test_checkpoint_state_round_trips_exactly_and_rejects_another_manifest() -> None:
    ledger = ConceptExposureLedger(_samples(), gradient_width=2)
    ledger.observe_batch(["a0", "b1"], [0.7, 1.2], [[1.0, 0.0], [0.0, 1.0]])
    state = ledger.state_dict()
    restored = ConceptExposureLedger(_samples(), gradient_width=2)
    restored.restore_state(state)

    assert restored.state_dict() == state
    assert np.array_equal(restored.sampling_probabilities(), ledger.sampling_probabilities())

    changed = _samples()
    changed[0] = _sample("different", "a", "left")
    other = ConceptExposureLedger(changed, gradient_width=2)
    with pytest.raises(ValueError, match="manifest mismatch"):
        other.restore_state(state)


def test_class_balanced_control_assigns_equal_concept_mass() -> None:
    samples = [
        _sample("a0", "a", "0"),
        _sample("a1", "a", "1"),
        _sample("a2", "a", "2"),
        _sample("b0", "b", "0"),
    ]
    probabilities = class_balanced_probabilities(samples)

    assert probabilities[:3].sum() == pytest.approx(0.5)
    assert probabilities[3] == pytest.approx(0.5)


def test_weight_effect_receipt_binds_real_change() -> None:
    initial = np.zeros((2, 3), dtype=np.float64)
    final = initial.copy()
    final[1, 2] = 0.25
    receipt = weight_effect_receipt(initial, final)

    assert receipt["changed_scalars"] == 1
    assert receipt["delta_l2"] == pytest.approx(0.25)
    assert receipt["initial_sha256"] != receipt["final_sha256"]
    assert len(receipt["receipt_sha256"]) == 64
