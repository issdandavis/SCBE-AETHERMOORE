from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from python.scbe import clay_multiview_exposure_audit as audit
from python.scbe.clay_paired_orbit_training import sha256_json as producer_sha256_json
from python.scbe.clay_paired_orbit_training import (
    tensor_sha256 as producer_tensor_sha256,
)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _receipted(body: dict, field: str) -> dict:
    return {**body, field: producer_sha256_json(body)}


def _bank(path: Path, name: str, records: int = 7) -> str:
    features = torch.arange(records * audit.FEATURE_WIDTH, dtype=torch.float32).reshape(records, audit.FEATURE_WIDTH)
    labels = torch.arange(records, dtype=torch.int64) % audit.ACTION_COUNT
    sectors = torch.arange(records, dtype=torch.int64) % 8
    groups = torch.arange(records, dtype=torch.int64)
    views = torch.arange(records, dtype=torch.int64) % 3
    complete_groups = False
    body = {
        "name": name,
        "records": records,
        "feature_sha256": producer_tensor_sha256(features),
        "label_sha256": producer_tensor_sha256(labels),
        "sector_sha256": producer_tensor_sha256(sectors),
        "group_sha256": producer_tensor_sha256(groups),
        "view_sha256": producer_tensor_sha256(views),
        "complete_groups": complete_groups,
    }
    manifest = producer_sha256_json(body)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "features": features,
            "labels": labels,
            "sectors": sectors,
            "groups": groups,
            "views": views,
            "complete_groups": complete_groups,
            "manifest_sha256": manifest,
        },
        path,
    )
    return manifest


def _completed_campaign(root: Path, *, schema: str = audit.CAMPAIGN_SCHEMA) -> Path:
    arms = ["static_unique", "multiview_random"]
    seeds = [11, 29]
    held_sectors = [1]
    config = {
        "arms": arms,
        "primary_arm": "multiview_random",
        "controls": ["static_unique"],
        "seeds": seeds,
        "held_sectors": held_sectors,
        "steps": 5,
        "batch_size": 3,
        "records_per_arm": 7,
    }
    campaign_body = {
        "schema": schema,
        "created_at_utc": "2026-11-13T00:00:00+00:00",
        "configuration": config,
        "source_hashes": {"fixture": "0" * 64},
        "implementation_sha256": "1" * 64,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    campaign = _receipted(campaign_body, "campaign_sha256")
    _write_json(root / "CAMPAIGN.json", campaign)

    horses = []
    for held in held_sectors:
        manifests = {arm: _bank(root / "inputs" / f"held-{held}" / f"{arm}.pt", arm) for arm in arms}
        for arm in arms:
            for seed in seeds:
                horse_body = {
                    "schema": "clay.paired-orbit-horse.v2",
                    "held_sector": held,
                    "arm": arm,
                    "seed": seed,
                    "steps": config["steps"],
                    "batch_size": config["batch_size"],
                    "data_manifest_sha256": manifests[arm],
                    "holdout": {"accuracy": 0.5},
                    "promotion_authorized": False,
                    "partial_unfreeze_authorized": False,
                }
                horse = _receipted(horse_body, "result_sha256")
                _write_json(
                    root / "horses" / f"held-{held}" / f"{arm}-seed-{seed}" / "RESULT.json",
                    horse,
                )
                horses.append(horse)
    result_body = {
        "schema": schema,
        "campaign_sha256": campaign["campaign_sha256"],
        "state": audit.COMPLETE_STATE,
        "configuration": config,
        "horses": horses,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    _write_json(root / "RESULT.json", _receipted(result_body, "result_sha256"))
    return root


def test_replay_preserves_producer_call_boundaries() -> None:
    counts = audit.replay_uniform_exposure(7, held_sector=4, seed=29, steps=5, batch_size=3, call_block=2)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(4_000_029)
    explicit = torch.zeros(7, dtype=torch.int64)
    for _ in range(5):
        explicit += torch.bincount(torch.randint(0, 7, (3,), generator=generator), minlength=7)
    assert torch.equal(counts, explicit)
    assert counts.sum().item() == 15


def test_completed_campaign_emits_exact_outcome_agnostic_receipt(
    tmp_path: Path,
) -> None:
    root = _completed_campaign(tmp_path / "campaign")
    result = audit.audit_completed_campaign(root)
    assert result["schema"] == audit.SCHEMA
    assert len(result["horse_receipts"]) == 4
    assert len(result["schedules"]) == 2
    assert all(row["draws"] == 15 for row in result["schedules"])
    assert all(sum(row["row_exposure_counts"]) == 15 for row in result["schedules"])
    assert all(row["applies_to_arms"] == ["static_unique", "multiview_random"] for row in result["schedules"])
    assert result["outcome_values_used_for_exposure"] is False
    assert result["promotion_authorized"] is False
    assert result["partial_unfreeze_authorized"] is False


def test_hash_spread_campaign_schema_is_supported(tmp_path: Path) -> None:
    root = _completed_campaign(
        tmp_path / "campaign",
        schema="clay.multiview-hash-spread-campaign.v1",
    )
    result = audit.audit_completed_campaign(root)
    assert result["producer_result_sha256"]
    assert result["promotion_authorized"] is False


def test_manifest_tampering_fails_closed(tmp_path: Path) -> None:
    root = _completed_campaign(tmp_path / "campaign")
    path = root / "inputs" / "held-1" / "static_unique.pt"
    payload = torch.load(path, map_location="cpu", weights_only=True)
    payload["features"][0, 0] += 1.0
    torch.save(payload, path)
    with pytest.raises(audit.ExposureAuditError, match="manifest drift"):
        audit.audit_completed_campaign(root)


def test_incomplete_campaign_fails_closed(tmp_path: Path) -> None:
    root = _completed_campaign(tmp_path / "campaign")
    result_path = root / "RESULT.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    body = dict(result)
    body.pop("result_sha256")
    body["state"] = "RUNNING"
    _write_json(result_path, _receipted(body, "result_sha256"))
    with pytest.raises(audit.ExposureAuditError, match="not complete"):
        audit.audit_completed_campaign(root)


def test_writer_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "EXPOSURE_AUDIT.json"
    audit.write_audit(output, {"ok": True})
    with pytest.raises(audit.ExposureAuditError, match="refusing to overwrite"):
        audit.write_audit(output, {"ok": False})
