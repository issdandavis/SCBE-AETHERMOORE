"""Smoke test for scripts/build_cross_tongue_project.py.

Verifies the dual-bijection contract on a tiny project:
  L1: byte-level round-trip per (algorithm, tongue)
  L2: cross-tongue byte invariance per source
  L3: slot-aligned semantic bijection (identical slot order across all 6 tongues)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# Import the builder (script-style import)
sys.path.insert(0, str(ROOT / "scripts"))
import build_cross_tongue_project as builder  # noqa: E402


@pytest.fixture(scope="module")
def bundle():
    algos = builder.PROJECT_SPECS["arithmetic_basics"]
    return builder.build_bundle("arithmetic_basics", algos)


def test_summary_all_green(bundle):
    s = bundle["summary"]
    assert s["all_green"], f"bundle not green: {s}"
    assert s["byte_round_trip_all_ok"]
    assert s["cross_tongue_invariance_all_ok"]
    assert s["slot_alignment_all_ok"]


def test_six_tongues_per_algorithm(bundle):
    for algo in bundle["algorithms"]:
        impls = algo["implementations"]
        assert set(impls.keys()) == {"ko", "av", "ru", "ca", "um", "dr"}


def test_byte_round_trip_per_pair(bundle):
    proofs = bundle["bijection_proofs"]["byte_round_trip"]
    for algo_name, per_tongue in proofs.items():
        for tongue, info in per_tongue.items():
            assert info["ok"], f"byte round-trip failed: {algo_name}/{tongue}"
            assert info["n_tokens"] > 0


def test_cross_tongue_invariance(bundle):
    proofs = bundle["bijection_proofs"]["cross_tongue_invariance"]
    for algo_name, per_tongue in proofs.items():
        for tongue, info in per_tongue.items():
            assert info["ok"], f"cross-tongue invariance failed: {algo_name}/{tongue} at {info['fail_at']}"


def test_slot_alignment(bundle):
    proofs = bundle["bijection_proofs"]["slot_alignment"]
    for algo_name, info in proofs.items():
        assert info["ok"], f"slot alignment failed: {algo_name} ({info['error']})"


def test_slot_order_identical_across_tongues(bundle):
    """Hard form of L3: every tongue's slot keys must match the manifest order exactly."""
    for algo in bundle["algorithms"]:
        expected = algo["slot_order"]
        for tongue, impl in algo["implementations"].items():
            actual = list(impl["slots"].keys())
            assert actual == expected, (
                f"{algo['name']}/{tongue} slot drift: {actual} != {expected}"
            )


def test_tokenizer_seal_decodes_to_source(bundle):
    """The 'tokenizer_seal' (encoded token list) must decode back to the rendered source."""
    from crypto.sacred_tongues import SacredTongueTokenizer
    tok = SacredTongueTokenizer()
    for algo in bundle["algorithms"]:
        for tongue, impl in algo["implementations"].items():
            tokens = impl["tokenizer_seal"]
            decoded = tok.decode_tokens(tongue, tokens)
            assert decoded == impl["rendered"].encode("utf-8"), (
                f"{algo['name']}/{tongue}: seal decode != rendered source"
            )


def test_write_bundle_round_trip(tmp_path, bundle):
    out = tmp_path / "proj"
    bundle_path = builder.write_bundle(bundle, out)
    assert bundle_path.exists()
    loaded = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert loaded["summary"]["all_green"]
    assert loaded["project"] == "arithmetic_basics"
