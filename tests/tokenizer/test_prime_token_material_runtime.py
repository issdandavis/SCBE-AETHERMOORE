from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from torch import nn

from python.scbe.prime_token_catalog import VIEW_NAMES
from python.scbe.prime_token_material_runtime import (
    CASE_MANIFEST_SCHEMA,
    EVALUATOR_RECEIPT_SCHEMA,
    RUNTIME_SCHEMA,
    build_runtime,
)
from python.scbe.prime_token_training import sha256_file
import python.scbe.prime_token_material_runtime as runtime_module


class _Route:
    def initial_state(self, lanes: torch.Tensor) -> torch.Tensor:
        return lanes.mean(dim=(-1, -2))

    def step(self, hidden, state, index):
        return hidden, state, {"index": index}


class _Core(nn.Module):
    def __init__(self):
        super().__init__()
        width, vocab, block_size = 8, 16, 8
        self.config = SimpleNamespace(d_model=width, block_size=block_size, route_mode="off")
        self.token = nn.Embedding(vocab, width)
        self.position = nn.Embedding(block_size, width)
        self.blocks = nn.ModuleList([nn.Linear(width, width, bias=False)])
        self.tilts = nn.ModuleList([nn.Identity()])
        self.route = _Route()
        self.lane_decoders = nn.ModuleList([nn.Linear(width, vocab) for _ in range(2)])
        self.final_norm = nn.LayerNorm(width)
        self.head = nn.Linear(width, vocab, bias=False)

    def input(self, token_ids: torch.Tensor):
        hidden = self.token(token_ids)
        lanes = torch.stack((hidden, hidden * 0.5), dim=2)
        return hidden, lanes, lanes.clone()

    def forward(self, token_ids, *, return_diagnostics=False, return_aux=False):
        hidden, route_lanes, raw_lanes = self.input(token_ids)
        positions = torch.arange(token_ids.shape[1], device=token_ids.device)
        hidden = hidden + self.position(positions)[None, :, :]
        traces = []
        state = self.route.initial_state(route_lanes)
        for index, (block, tilt) in enumerate(zip(self.blocks, self.tilts, strict=True)):
            hidden = tilt(block(hidden))
            if self.config.route_mode != "off":
                hidden, state, trace = self.route.step(hidden, state, index)
                traces.append(trace)
        logits = self.head(self.final_norm(hidden))
        aux = None
        if return_aux:
            aux = {
                "lane_logits": torch.stack(
                    [decoder(raw_lanes[:, :, index]) for index, decoder in enumerate(self.lane_decoders)], dim=2
                )
            }
        if return_diagnostics and return_aux:
            return logits, traces, aux
        if return_diagnostics:
            return logits, traces
        if return_aux:
            return logits, aux
        return logits


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _record(name: str, family: str) -> dict:
    return {
        "canonical_id": f"token:{name}",
        "section_id": f"section:{name}",
        "source_family": family,
        "views": {view: {"surface": name, "view": view, "index": index} for index, view in enumerate(VIEW_NAMES)},
    }


def _case(record_id: str, split: str, family: str, target: int) -> dict:
    return {
        "record_id": record_id,
        "split": split,
        "source_family": family,
        "token_ids": [1, 2, 3, 4, 5],
        "targets": [2, 3, 4, target, 6],
        "owner_positions": [1],
        "output_positions": [3],
        "records": [_record(record_id, family)],
    }


def _fixture(tmp_path: Path, *, arm: str = "canonical_six_view_reader") -> dict:
    source = tmp_path / "source.json"
    split = tmp_path / "split.json"
    _write_json(source, {"schema": "fixture.source.v1"})
    _write_json(split, {"schema": "fixture.split.v1"})
    rows = {
        "train": [_case("train-1", "train", "family-train", 5)],
        "validation": [_case("validation-1", "validation", "family-validation", 5)],
        "final_test": [_case("final-1", "final_test", "family-final", 6)],
        "ordinary": [{"id": "ordinary-1", "token_ids": [1, 2, 3]}],
        "retention": [{"id": "retention-1", "token_ids": [3, 2, 1]}],
    }
    descriptors = {}
    for lane, lane_rows in rows.items():
        path = tmp_path / f"{lane}.jsonl"
        _write_jsonl(path, lane_rows)
        descriptors[lane] = {"path": path.name, "sha256": sha256_file(path), "count": len(lane_rows)}
    manifest = tmp_path / "cases.json"
    evaluator = tmp_path / "evaluator.json"
    _write_json(
        evaluator,
        {
            "schema": EVALUATOR_RECEIPT_SCHEMA,
            "allowed_output_token_ids": [5, 6],
            "relationship_class_by_token_id": {"5": "route", "6": "route"},
            "function_class_by_token_id": {"5": "left", "6": "right"},
            "scoring": "full-vocabulary-argmax_then_exact_and_class_equivalence",
        },
    )
    _write_json(
        manifest,
        {
            "schema": CASE_MANIFEST_SCHEMA,
            "source_disjoint": True,
            "exact_evaluator_receipt_sha256": sha256_file(evaluator),
            "allowed_output_token_ids": [5, 6],
            "relationship_class_by_token_id": {"5": "route", "6": "route"},
            "function_class_by_token_id": {"5": "left", "6": "right"},
            "files": descriptors,
        },
    )
    return {
        "schema": RUNTIME_SCHEMA,
        "arm": arm,
        "seed": 17,
        "source_manifest": str(source),
        "source_manifest_sha256": sha256_file(source),
        "split_manifest": str(split),
        "split_manifest_sha256": sha256_file(split),
        "cases_manifest": str(manifest),
        "cases_manifest_sha256": sha256_file(manifest),
        "evaluator_receipt": str(evaluator),
        "evaluator_receipt_sha256": sha256_file(evaluator),
        "reader_rank": 4,
        "parent": {},
    }


@pytest.mark.parametrize("arm", ["canonical_six_view_reader", "no_intervention"])
def test_runtime_builds_source_disjoint_examples_and_multi_metric_evaluator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, arm: str
) -> None:
    monkeypatch.setattr(runtime_module, "_load_parent", lambda _config: _Core())
    payload = build_runtime(_fixture(tmp_path, arm=arm))
    assert payload["identity"]["arm"] == arm
    assert payload["train_examples"][0].splits == ("train",)
    assert {case["splits"][0] for case in payload["replay_cases"]} == {"validation", "final_test"}
    evaluation = payload["evaluate"](payload["model"], arm)
    assert set(evaluation["metrics"]) >= {
        "accuracy",
        "relationship",
        "function",
        "bounded_margin",
        "bounded_entropy",
        "throughput",
    }
    assert len(evaluation["per_example"]) == 2
    assert {row["source_family"] for row in evaluation["per_example"]} == {
        "family-validation",
        "family-final",
    }
    assert evaluation["metrics"]["frozen_parent_retention"] == 1.0


def test_runtime_rejects_case_manifest_hash_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_module, "_load_parent", lambda _config: _Core())
    config = _fixture(tmp_path)
    Path(config["cases_manifest"]).write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="case manifest hash differs"):
        build_runtime(config)
