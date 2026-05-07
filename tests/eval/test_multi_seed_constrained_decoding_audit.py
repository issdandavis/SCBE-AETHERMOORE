"""Tests for constrained-decoding multi-seed audit helpers."""

from __future__ import annotations

from scripts.eval.multi_seed_constrained_decoding_audit import prefix_plus_noisy_continuation_model


def test_noisy_continuation_is_stable_for_same_seed_and_temperature() -> None:
    prompt = {
        "id": "x",
        "required": ["REQUIRED_MARKERS=x"],
        "forbidden": ["FORBIDDEN_TOKEN"],
    }
    model = prefix_plus_noisy_continuation_model(forbidden_collision_rate=0.5)

    a = model(prompt, 7, 0.4)
    b = model(dict(prompt), 7, 0.4)

    assert a == b
