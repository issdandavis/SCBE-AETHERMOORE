from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from load_vqcc_corpus import (
    CorpusIntegrityError,
    SampleConfig,
    sample_corpus,
    write_sample,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _row(lane: str, ordinal: int, text: str | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "record_id": _digest(f"{lane}:{ordinal}"),
        "split": "train",
        "split_group": f"family-{lane}-{ordinal // 3}",
        "lane": lane,
        "source": "fixture",
    }
    if text is None:
        result.update(question=f"question {lane} {ordinal}", answer=f"answer {ordinal}")
    else:
        result["text"] = text
    return result


def _canonical_line(row: dict[str, object]) -> bytes:
    return (json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def _make_corpus(
    root: Path,
    rows: list[dict[str, object]],
    *,
    declared_train: int | None = None,
    roles: dict[str, str] | None = None,
) -> tuple[str, dict[str, int]]:
    root.mkdir()
    files: dict[str, dict[str, object]] = {}
    midpoint = max(1, len(rows) // 2)
    for index, group in enumerate((rows[:midpoint], rows[midpoint:])):
        if not group:
            continue
        name = f"train-{index:04d}.jsonl"
        raw = b"".join(_canonical_line(row) for row in group)
        (root / name).write_bytes(raw)
        files[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    counts = {"train": len(rows) if declared_train is None else declared_train, "holdout": 0, "ordinary": 0, "retention": 0}
    manifest = {
        "schema": "clay.vqcc-research-corpus.v1",
        "counts": counts,
        "lanes": dict(Counter(str(row["lane"]) for row in rows)),
        "files": files,
        "submission_archive_members": 0,
        "official_competition_mounts": 0,
        "model_checkpoints": 0,
    }
    raw_manifest = (json.dumps(manifest, indent=2) + "\n").encode()
    (root / "CORPUS_MANIFEST.json").write_bytes(raw_manifest)
    assignments = []
    roles = roles or {}
    for row in rows:
        lane = str(row["lane"])
        if not (lane.startswith("public.") or lane in {"owned.experimental_method", "owned.public_notebook_observation"}):
            continue
        assignments.append(
            {
                "record_id": row["record_id"],
                "split": roles.get(str(row["record_id"]), "train"),
                "family": row["split_group"],
                "lane": lane,
                "task": "fixture",
            }
        )
    (root / "row-assignments.jsonl").write_bytes(b"".join(_canonical_line(row) for row in assignments))
    return hashlib.sha256(raw_manifest).hexdigest(), counts


def _sample(root: Path, manifest_sha256: str, counts: dict[str, int], config: SampleConfig):
    assignments = root / "row-assignments.jsonl"
    return sample_corpus(
        root,
        config,
        assignments_path=assignments,
        expected_assignments_sha256=hashlib.sha256(assignments.read_bytes()).hexdigest(),
        expected_manifest_sha256=manifest_sha256,
        expected_counts=counts,
    )


def test_streaming_reservoir_is_deterministic_bounded_and_without_replacement(tmp_path: Path) -> None:
    rows = [_row("public.lane_a", i) for i in range(20)] + [_row("public.lane_b", i) for i in range(10)]
    root = tmp_path / "corpus"
    manifest_sha256, counts = _make_corpus(root, rows)
    config = SampleConfig(
        lane_caps={"public.lane_a": 5, "public.lane_b": 3},
        seed=71,
        max_chars_per_record=1_000,
        max_tokens_per_record=250,
        total_token_budget=2_000,
    )

    first = _sample(root, manifest_sha256, counts, config)
    second = _sample(root, manifest_sha256, counts, config)

    assert first == second
    assert Counter(row["lane"] for row in first.rows) == {"public.lane_a": 5, "public.lane_b": 3}
    assert len({row["record_id"] for row in first.rows}) == 8
    assert first.receipt["scan"]["train_rows"] == 30
    assert first.receipt["selection"]["sample_bytes"] < 20_000
    assert first.receipt["selection"]["record_ids_sha256"]
    assert first.receipt["selection"]["sample_sha256"]

    alternate = _sample(root, manifest_sha256, counts, SampleConfig(**{**config.__dict__, "seed": 72}))
    assert alternate.receipt["selection"]["record_ids_sha256"] != first.receipt["selection"]["record_ids_sha256"]


def test_character_token_and_total_budgets_are_enforced(tmp_path: Path) -> None:
    rows = [
        _row("public.lane_a", 0, "short"),
        _row("public.lane_a", 1, "x" * 21),
        _row("public.lane_a", 2, "é" * 10),
        _row("public.lane_a", 3, "tiny"),
    ]
    root = tmp_path / "corpus"
    manifest_sha256, counts = _make_corpus(root, rows)
    config = SampleConfig(
        lane_caps={"public.lane_a": 4},
        max_chars_per_record=20,
        max_tokens_per_record=12,
        total_token_budget=12,
    )

    result = _sample(root, manifest_sha256, counts, config)

    assert result.receipt["scan"]["excluded_by_character_cap"] == {"public.lane_a": 1}
    assert result.receipt["scan"]["excluded_by_token_cap"] == {"public.lane_a": 1}
    assert result.receipt["selection"]["token_proxy_total"] <= 12
    assert result.receipt["selection"]["rows"] in (1, 2)
    assert all(len(str(row["text"])) <= 20 for row in result.rows)


def test_shard_hash_and_row_count_must_match(tmp_path: Path) -> None:
    rows = [_row("public.lane_a", i) for i in range(6)]
    root = tmp_path / "corpus"
    manifest_sha256, counts = _make_corpus(root, rows)
    target = root / "train-0000.jsonl"
    raw = target.read_bytes()
    target.write_bytes(raw.replace(b"question public.lane_a 0", b"Question public.lane_a 0", 1))

    with pytest.raises(CorpusIntegrityError, match="hash differs"):
        _sample(root, manifest_sha256, counts, SampleConfig(lane_caps={"public.lane_a": 2}))

    count_root = tmp_path / "count-corpus"
    count_manifest, declared_counts = _make_corpus(count_root, rows, declared_train=7)
    with pytest.raises(CorpusIntegrityError, match="row count differs"):
        _sample(count_root, count_manifest, declared_counts, SampleConfig(lane_caps={"public.lane_a": 2}))


def test_manifest_hash_and_requested_lanes_are_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    manifest_sha256, counts = _make_corpus(root, [_row("public.lane_a", 0)])
    manifest = root / "CORPUS_MANIFEST.json"
    manifest.write_bytes(manifest.read_bytes() + b" ")
    with pytest.raises(CorpusIntegrityError, match="manifest hash differs"):
        _sample(root, manifest_sha256, counts, SampleConfig(lane_caps={"public.lane_a": 1}))

    clean = tmp_path / "clean"
    clean_sha, clean_counts = _make_corpus(clean, [_row("public.lane_a", 0)])
    with pytest.raises(ValueError, match="absent from the pinned manifest"):
        _sample(clean, clean_sha, clean_counts, SampleConfig(lane_caps={"public.missing": 1}))


def test_train_shards_are_streamed_without_path_read_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "corpus"
    manifest_sha256, counts = _make_corpus(root, [_row("public.lane_a", i) for i in range(8)])

    def forbidden_read_text(_self: Path, *_args: object, **_kwargs: object) -> str:
        raise AssertionError("training shards must not be loaded with Path.read_text")

    monkeypatch.setattr(Path, "read_text", forbidden_read_text)
    result = _sample(root, manifest_sha256, counts, SampleConfig(lane_caps={"public.lane_a": 2}))
    assert len(result.rows) == 2


def test_immutable_writer_refuses_existing_targets(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    manifest_sha256, counts = _make_corpus(root, [_row("public.lane_a", i) for i in range(4)])
    result = _sample(root, manifest_sha256, counts, SampleConfig(lane_caps={"public.lane_a": 2}))
    rows_path, receipt_path = tmp_path / "sample.jsonl", tmp_path / "receipt.json"

    write_sample(result, rows_path, receipt_path)
    assert hashlib.sha256(rows_path.read_bytes()).hexdigest() == result.receipt["selection"]["sample_sha256"]
    assert json.loads(receipt_path.read_text())["selection"]["record_ids"]

    before = (rows_path.read_bytes(), receipt_path.read_bytes())
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        write_sample(result, rows_path, receipt_path)
    assert (rows_path.read_bytes(), receipt_path.read_bytes()) == before


def test_same_output_path_and_invalid_config_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    manifest_sha256, counts = _make_corpus(root, [_row("public.lane_a", 0)])
    result = _sample(root, manifest_sha256, counts, SampleConfig(lane_caps={"public.lane_a": 1}))
    with pytest.raises(ValueError, match="must differ"):
        write_sample(result, tmp_path / "same", tmp_path / "same")
    with pytest.raises(ValueError, match="positive"):
        _sample(root, manifest_sha256, counts, SampleConfig(lane_caps={"public.lane_a": 1}, total_token_budget=0))


def test_real_v2_record_id_forms_are_accepted_and_junk_is_rejected(tmp_path: Path) -> None:
    record_ids = [
        "a" * 64,
        "train-000-9126bea12102c68d",
        "holdout-047-d648f8158cedd89d",
        "ordinary-003-c27d33137d1e5711",
        "retention-019-44be3c14fa632ab9",
        "notebook:" + "b" * 64,
        "owned-analysis:" + "c" * 64,
        "experimental-method:" + "d" * 64,
    ]
    rows = [_row("public.lane_a", index) for index in range(len(record_ids))]
    for row, record_id in zip(rows, record_ids, strict=True):
        row["record_id"] = record_id
    root = tmp_path / "corpus"
    manifest_sha256, counts = _make_corpus(root, rows)
    result = _sample(root, manifest_sha256, counts, SampleConfig(lane_caps={"public.lane_a": len(rows)}))
    assert {row["record_id"] for row in result.rows} == set(record_ids)

    bad_root = tmp_path / "bad-corpus"
    bad = _row("public.lane_a", 0)
    bad["record_id"] = "notebook:../../escape\n"
    bad_manifest, bad_counts = _make_corpus(bad_root, [bad])
    with pytest.raises(CorpusIntegrityError, match="Invalid record_id"):
        _sample(bad_root, bad_manifest, bad_counts, SampleConfig(lane_caps={"public.lane_a": 1}))


def test_campaign_assignment_role_is_strict_and_hash_pinned(tmp_path: Path) -> None:
    rows = [_row("public.lane_a", index) for index in range(6)]
    roles = {str(rows[0]["record_id"]): "holdout", str(rows[1]["record_id"]): "holdout"}
    root = tmp_path / "corpus"
    manifest_sha256, counts = _make_corpus(root, rows, roles=roles)

    holdout = _sample(
        root,
        manifest_sha256,
        counts,
        SampleConfig(lane_caps={"public.lane_a": 6}, campaign_role="holdout"),
    )
    assert {row["record_id"] for row in holdout.rows} == set(roles)
    assert holdout.receipt["campaign_assignments"]["selected_role"] == "holdout"
    assert holdout.receipt["campaign_assignments"]["roles"] == {"holdout": 2, "train": 4}

    assignments = root / "row-assignments.jsonl"
    original_sha256 = hashlib.sha256(assignments.read_bytes()).hexdigest()
    assignments.write_bytes(assignments.read_bytes().replace(b'"split":"train"', b'"split":"xxxxx"', 1))
    with pytest.raises(CorpusIntegrityError):
        sample_corpus(
            root,
            SampleConfig(lane_caps={"public.lane_a": 2}),
            assignments_path=assignments,
            expected_assignments_sha256=original_sha256,
            expected_manifest_sha256=manifest_sha256,
            expected_counts=counts,
        )


@pytest.mark.parametrize("mode", ["missing", "extra", "duplicate"])
def test_assignment_sidecar_rejects_missing_extra_and_duplicate_rows(tmp_path: Path, mode: str) -> None:
    rows = [_row("public.lane_a", index) for index in range(4)]
    root = tmp_path / mode
    manifest_sha256, counts = _make_corpus(root, rows)
    assignments = root / "row-assignments.jsonl"
    lines = assignments.read_bytes().splitlines(keepends=True)
    if mode == "missing":
        assignments.write_bytes(b"".join(lines[:-1]))
    elif mode == "extra":
        extra = {
            "record_id": "e" * 64,
            "split": "train",
            "family": "extra-family",
            "lane": "public.lane_a",
            "task": "fixture",
        }
        assignments.write_bytes(b"".join(lines) + _canonical_line(extra))
    else:
        assignments.write_bytes(b"".join(lines) + lines[-1])
    with pytest.raises(CorpusIntegrityError, match="assignment"):
        _sample(root, manifest_sha256, counts, SampleConfig(lane_caps={"public.lane_a": 2}))


def test_total_budget_retains_every_requested_lane_or_fails(tmp_path: Path) -> None:
    rows = [
        _row("public.lane_a", 0, "a"),
        _row("public.lane_a", 1, "a" * 20),
        _row("public.lane_b", 0, "bb"),
        _row("public.lane_b", 1, "b" * 20),
    ]
    root = tmp_path / "corpus"
    manifest_sha256, counts = _make_corpus(root, rows)
    exact_required = (1 + 3) + (2 + 3)
    result = _sample(
        root,
        manifest_sha256,
        counts,
        SampleConfig(
            lane_caps={"public.lane_a": 2, "public.lane_b": 2},
            max_tokens_per_record=100,
            total_token_budget=exact_required,
        ),
    )
    assert Counter(row["lane"] for row in result.rows) == {"public.lane_a": 1, "public.lane_b": 1}
    assert result.receipt["selection"]["token_proxy_total"] == exact_required

    with pytest.raises(ValueError, match="one row per requested positive lane"):
        _sample(
            root,
            manifest_sha256,
            counts,
            SampleConfig(
                lane_caps={"public.lane_a": 2, "public.lane_b": 2},
                max_tokens_per_record=100,
                total_token_budget=exact_required - 1,
            ),
        )
