from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts" / "experiments" / "multiview_perspective_reasoning.py"
SPEC = importlib.util.spec_from_file_location("multiview_perspective_reasoning", SOURCE)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def test_six_tongues_round_trip_every_byte() -> None:
    result = M.verify_round_trips()
    assert result["checks"] == 1536
    assert result["passed"] == 1536
    assert result["failures"] == []


def test_perspectives_keep_truth_stance_and_reason_separate() -> None:
    reasons = {
        M.disagreement_reason(state, lens)
        for state in range(M.N_STATES)
        for lens in range(M.N_LENSES)
    }
    traps = [
        state
        for state in range(M.N_STATES)
        if M.majority([M.lens_stance(state, lens) for lens in range(M.N_LENSES)])
        != M.truth_for(state)
    ]
    assert reasons == set(range(7))
    assert len(traps) == 22


def test_transition_holdout_contains_each_inverse() -> None:
    train, heldout = M.transition_split()
    train_keys = {(start, operation) for start, operation, _ in train}
    heldout_keys = {(start, operation) for start, operation, _ in heldout}
    assert train_keys.isdisjoint(heldout_keys)
    assert len(train) + len(heldout) == M.N_STATES * len(M.OP_DELTAS)
    for _start, operation, target in heldout:
        inverse = int(M.INVERSE_INDEX[operation])
        assert (target, inverse) in heldout_keys


def test_feature_arms_are_shape_matched_and_finite() -> None:
    for mode in ("aligned", "ordinary", "shuffled", "random"):
        values = M.build_features(mode)
        assert values.shape == (M.N_STATES, len(M.TONGUES), M.INPUT_DIM)
        assert torch.isfinite(values).all()


def test_all_arms_have_identical_parameter_count() -> None:
    counts = [sum(parameter.numel() for parameter in M.PerspectiveTransitionNet().parameters()) for _ in M.ARMS]
    assert len(set(counts)) == 1


def test_same_seed_cpu_replay_is_exact() -> None:
    device = torch.device("cpu")
    M.configure_determinism(device)
    arm = next(arm for arm in M.ARMS if arm.name == "aligned_relational_cycle")
    left, _ = M.train_arm(arm, seed=71, steps=2, device=device, trace_every=2)
    right, _ = M.train_arm(arm, seed=71, steps=2, device=device, trace_every=2)
    assert M.model_state_sha256(left) == M.model_state_sha256(right)


def test_wrong_predictions_cannot_pass_accuracy() -> None:
    target = torch.arange(M.N_STATES)
    assert M.accuracy(target, target) == 1.0
    shifted = (target + 1) % M.N_STATES
    assert M.accuracy(shifted, target) == 0.0
