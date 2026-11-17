from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import pytest

from python.scbe import clay_byte_embedding_thaw_campaign as campaign
from python.scbe.clay_frozen_multiview_adapter import atomic_json
from scripts.research.build_clay_frozen_multiview_kaggle_packet import (
    descriptor,
    deterministic_zip,
    write_json,
)
from scripts.research.run_clay_byte_embedding_thaw_kaggle_recovery import (
    DESCRIPTOR_SCHEMA,
    MANIFEST_NAME,
    PACKET_SCHEMA,
    _verify_manifest_self_hash,
    aggregate_terminal_results,
    extract_and_verify_packet,
    materialize_run_view,
    parse_args,
    publish_exact_file,
    qualify_recovery_replay,
    sha256_file,
    stable_hash,
)


def _manifest_body(payload: Path) -> dict:
    return {
        "schema": PACKET_SCHEMA,
        "authority": {"training": "NONE"},
        "files": [descriptor(payload, relative_to=payload.parents[1])],
        "file_count": 1,
        "payload_bytes": payload.stat().st_size,
    }


def test_self_hashed_packet_extracts_and_rejects_tampering(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    payload = packet / "payload" / "fixture.bin"
    payload.parent.mkdir(parents=True)
    payload.write_bytes(b"sealed-weight-bytes")
    body = _manifest_body(payload)
    packet_id = stable_hash(body)
    manifest = {
        **body,
        "packet_id": packet_id,
        "manifest_body_sha256": packet_id,
        "self_hash_rule": "excluded seal fields",
    }
    write_json(packet / MANIFEST_NAME, manifest)
    archive = tmp_path / "packet.packet"
    deterministic_zip(packet, archive)
    descriptor_path = tmp_path / "PACKET_DESCRIPTOR.json"
    write_json(
        descriptor_path,
        {
            "schema": DESCRIPTOR_SCHEMA,
            "dataset_id": "fixture/recovery",
            "packet_id": packet_id,
            "archive": descriptor(archive),
            "packet_manifest": descriptor(packet / MANIFEST_NAME),
        },
    )

    _, loaded = extract_and_verify_packet(
        descriptor_path,
        json.loads(descriptor_path.read_text(encoding="utf-8")),
        tmp_path / "runtime",
    )
    assert loaded["packet_id"] == packet_id

    tampered = dict(loaded)
    tampered["payload_bytes"] += 1
    with pytest.raises(RuntimeError, match="self-hash"):
        _verify_manifest_self_hash(tampered)


def _prediction(example: int, correct: bool) -> dict:
    return {
        "example_index": example,
        "correct": correct,
        "prediction": 0 if correct else 1,
        "target": 0,
        "sector": 0,
    }


def _row(arm: str, seed: int, correct: int) -> dict:
    predictions = [_prediction(index, index < correct) for index in range(2)]
    score = correct / 2
    return {
        "schema": "fixture.horse-result",
        "status": "COMPLETE",
        "arm": arm,
        "seed": seed,
        "steps": 18_000,
        "trainable_parameters": 256,
        "metrics": {"accuracy": score, "macro_f1": score},
        "predictions": predictions,
        "counting_accuracy": 1.0,
        "parent_counting_accuracy": 1.0,
        "base_parent_bit_identical": True,
        "thaw_receipt": {"changed_byte_rows": 1},
    }


def test_aggregation_reads_terminal_results_without_training(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    packet = tmp_path / "packet"
    staged = tmp_path / "staged-run"
    baseline_path = packet / "payload" / "baseline" / "RESULT.json"
    baseline_path.parent.mkdir(parents=True)
    staged.mkdir()
    config = campaign.ThawCampaignConfig(
        baseline_run=r"C:\fixture\baseline",
        baseline_manifest_sha256="a" * 64,
        baseline_result_sha256="b" * 64,
        dataset_manifest_sha256="c" * 64,
        seeds=(11, 12, 13),
        grow_steps=18_000,
        checkpoint_every=500,
        batch_size=128,
        learning_rate=0.002,
        threads=2,
        device="cpu",
        source_dir=r"C:\fixture\source",
        source_hashes={"policy": "d" * 64},
    )
    write_json(
        staged / "RUN_MANIFEST.json",
        {"schema": "fixture.manifest", "config": asdict(config)},
    )
    learned = []
    scores = {
        campaign.PRIMARY: 2,
        campaign.STATIC: 1,
        campaign.SHUFFLED: 1,
    }
    for seed in config.seeds:
        for arm in config.arms:
            row = _row(arm, seed, scores[arm])
            learned.append(row)
            write_json(staged / "horses" / f"{arm}-seed-{seed}" / "RESULT.json", row)
    baseline = {"per_arm": {arm: [_row(arm, seed, 1) for seed in config.seeds] for arm in campaign.IMPORTED_CONTROLS}}
    write_json(baseline_path, baseline)
    monkeypatch.setattr(
        "scripts.research.run_clay_byte_embedding_thaw_kaggle_recovery._import_runtime",
        lambda _: (campaign, object(), atomic_json),
    )

    result = aggregate_terminal_results(packet, staged)

    assert result["status"] == "COMPLETE"
    assert result["config"] == json.loads(json.dumps(asdict(config), sort_keys=True))
    assert len(result["per_arm"][campaign.PRIMARY]) == 3
    assert (staged / "RESULT.json").is_file()
    assert not any(path.name.endswith(".pt") for path in staged.rglob("*"))


def test_materialized_view_preserves_input_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    original = source / "horses" / "a" / "MODEL.pt"
    original.parent.mkdir(parents=True)
    original.write_bytes(b"immutable-model")

    receipt = materialize_run_view(source, tmp_path / "view")

    assert receipt["files"] == 1
    assert (tmp_path / "view" / "horses" / "a" / "MODEL.pt").read_bytes() == b"immutable-model"
    assert original.read_bytes() == b"immutable-model"


def test_publish_surface_contains_only_exact_result_bytes(tmp_path: Path) -> None:
    staged = tmp_path / "runtime" / "writable-run" / "RESULT.json"
    staged.parent.mkdir(parents=True)
    staged.write_bytes(b'{"status":"COMPLETE"}\n')
    published = tmp_path / "working" / "run" / "RESULT.json"

    publish_exact_file(staged, published)

    assert published.read_bytes() == staged.read_bytes()
    assert [
        path.relative_to(tmp_path / "working").as_posix()
        for path in (tmp_path / "working").rglob("*")
        if path.is_file()
    ] == ["run/RESULT.json"]


def test_default_runtime_is_outside_kaggle_published_working_tree() -> None:
    args = parse_args([])

    assert "/kaggle/working" not in args.runtime_root.as_posix()
    assert args.output_root == Path("/kaggle/working/clay-byte-thaw-aggregation-replay")


def test_recovery_qualification_keeps_inference_fail_closed(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    baseline_root = packet / "payload" / "baseline"
    historical = packet / "authorities" / "baseline_verifier" / "clay_frozen_multiview_replay.py"
    historical.parent.mkdir(parents=True)
    historical.write_bytes(b"historical verifier\n")
    seeds = (20261134, 20261135, 20261136)
    aggregate_rows = []
    for seed in seeds:
        parent = _row("parent", seed, 1)
        write_json(baseline_root / "parents" / f"seed-{seed}" / "RESULT.json", parent)
        aggregate_rows.append(
            {
                "arm": "no_intervention_adapter",
                "seed": seed,
                "metrics": parent["metrics"],
                "predictions": parent["predictions"],
                "counting_accuracy": parent["counting_accuracy"],
                "parent_counting_accuracy": parent["counting_accuracy"],
                "trainable_parameters": 0,
            }
        )
    write_json(
        baseline_root / "RESULT.json",
        {"per_arm": {"no_intervention_adapter": aggregate_rows}},
    )
    write_json(
        baseline_root / "INDEPENDENT_REPLAY.json",
        {"independent_dataset_builder_sha256": sha256_file(historical)},
    )
    raw = {
        "status": "FAIL_INDEPENDENT_INFERENCE_REPLAY",
        "errors": [
            "baseline independent replay verifier binding is stale",
            *[f"no_intervention_adapter seed {seed}: terminal baseline result differs" for seed in seeds],
        ],
        "model_receipts": [{"prediction_mismatches": 0} for _ in range(15)],
        "max_metric_delta": 0.0,
        "aggregate_comparison_delta": 0.0,
        "aggregate_paired_delta": 0.0,
        "ledger": {"rows": 22_500},
    }

    passed = qualify_recovery_replay(packet, raw, tolerance=1e-12)
    assert passed["status"] == "PASS_RECOVERY_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION"
    assert passed["errors"] == []
    assert len(passed["recovery_adjustments"]) == 4

    raw["model_receipts"][0]["prediction_mismatches"] = 1
    failed = qualify_recovery_replay(packet, raw, tolerance=1e-12)
    assert failed["status"] == "FAIL_RECOVERY_INDEPENDENT_INFERENCE_REPLAY"
