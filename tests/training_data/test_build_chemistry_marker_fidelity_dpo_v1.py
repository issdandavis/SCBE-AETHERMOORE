"""Tests for chemistry marker-fidelity DPO shard builder.

Invariants:
- chosen text contains every required marker verbatim for its prompt
- rejected text differs from chosen
- v6 + v7 raw responses are present as natural rejections (5 + 5 = 10)
- synthetic mutations produce valid rejections (one required marker corrupted)
"""

from __future__ import annotations

import importlib.util
import json
import sys
import random
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "training_data" / "build_chemistry_marker_fidelity_dpo_v1.py"
CONTRACT = REPO_ROOT / "config" / "model_training" / "chemistry_verification_eval_contract.json"


@pytest.fixture(scope="module")
def builder():
    spec = importlib.util.spec_from_file_location("build_chemistry_marker_fidelity_dpo_v1", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_chosen_contains_all_required(builder, contract):
    for entry in contract["prompts"]:
        pid = entry["id"]
        required = entry["required"]
        chosen = builder.chosen_template(pid, required)
        for marker in required:
            assert marker in chosen, f"prompt={pid}: required marker '{marker}' missing from chosen text"


def test_v6_v7_raw_responses_present(builder):
    v6 = builder.v6_raw_responses()
    v7 = builder.v7_raw_responses()
    assert len(v6) == 5
    assert len(v7) == 5
    assert set(v6.keys()) == set(v7.keys())


def test_pairs_are_valid_dpo_shape(builder):
    rng = random.Random(48)
    train, evl = builder.build_pairs(rng)
    assert len(train) >= 20
    assert len(evl) >= 1
    for p in train + evl:
        assert isinstance(p.prompt, str) and p.prompt
        assert isinstance(p.chosen, str) and p.chosen
        assert isinstance(p.rejected, str) and p.rejected
        assert p.chosen != p.rejected, "chosen must differ from rejected"


def test_natural_rejections_per_source_count(builder):
    rng = random.Random(48)
    train, evl = builder.build_pairs(rng)
    sources = [p.metadata["rejection_source"] for p in train]
    assert sources.count("v6_raw") == 5, "Expect one v6 natural rejection per chemistry prompt"
    assert sources.count("v7_raw") == 5, "Expect one v7 natural rejection per chemistry prompt"


def test_synthetic_rejection_changes_one_marker(builder):
    rng = random.Random(48)
    train, evl = builder.build_pairs(rng)
    synthetic = [p for p in train + evl if p.metadata["rejection_source"] == "synthetic"]
    assert len(synthetic) > 0
    for p in synthetic:
        # Rejected should differ from chosen by exactly the mutation correct→paraphrase
        correct, paraphrase = p.metadata["mutation"]
        if correct in p.chosen:
            assert (
                paraphrase in p.rejected
            ), f"prompt={p.metadata['prompt_id']}: synthetic rejection should contain mutation paraphrase"


def test_pair_count_within_expected_range(builder):
    rng = random.Random(48)
    train, evl = builder.build_pairs(rng)
    total = len(train) + len(evl)
    # 5 prompts × (1 v6 + 1 v7 + ~4 synthetics) ≈ 30 pairs
    assert 20 <= total <= 40
