from __future__ import annotations

import json
from pathlib import Path

import findings_task
import load_vqcc_corpus as loader
import vqcc_task


ROOT = Path(__file__).resolve().parent


def test_prepared_campaign_spec_matches_executable_pins() -> None:
    spec = json.loads((ROOT / "CAMPAIGN_SPEC.json").read_text(encoding="utf-8"))
    dataset = spec["dataset"]
    assert dataset == {
        "id": loader.DATASET_ID,
        "version": loader.DATASET_VERSION,
        "manifest_sha256": loader.EXPECTED_MANIFEST_SHA256,
        "counts": loader.EXPECTED_COUNTS,
    }
    assert spec["status"] == "PREPARED_ONLY"
    assert not any(
        spec[name]
        for name in (
            "execution_authorized",
            "training_authorized",
            "cloud_mutation_authorized",
            "checkpoint_promotion_authorized",
            "competition_submission_authorized",
        )
    )
    assert tuple(spec["training"]["arms"]) == vqcc_task.REQUIRED_ARMS
    assert len(set(spec["training"]["seeds"])) == 3
    assert spec["training"]["runner"] is None
    assert spec["training"]["steps"] is None
    assert spec["promotion"]["adjudicator"] == "findings_task.judge_finding_campaign"
    assert spec["promotion"]["adjudicator_status"] == "IMPLEMENTED_NOT_EXECUTED"
    assert set(spec["promotion"]["must_beat_controls"]) == set(vqcc_task.REQUIRED_ARMS) - {
        "candidate"
    }
    assert findings_task.REQUIRED_ARMS == vqcc_task.REQUIRED_ARMS
    assert "finding-binding campaign promotion adjudicator" not in spec["open_gates"]
    assert spec["campaign_split"]["finding_family_edges"] == [
        "link",
        "family_target",
        "supersedes",
    ]
    assert spec["campaign_split"]["related_cards_policy"].startswith("cross-reference")
    assert spec["storage_gate"] == {"minimum_writable_bytes": 25 * 2**30, "lowered": False}


def test_sampling_caps_cover_only_implemented_campaign_lanes() -> None:
    spec = json.loads((ROOT / "CAMPAIGN_SPEC.json").read_text(encoding="utf-8"))
    expected = {"public.experimental_findings", "public.gate_count"}
    for role in ("train", "holdout"):
        config = spec["sampling"][role]
        assert set(config["lane_caps"]) == expected
        assert all(type(value) is int and value > 0 for value in config["lane_caps"].values())
        assert config["total_token_budget"] > 0
