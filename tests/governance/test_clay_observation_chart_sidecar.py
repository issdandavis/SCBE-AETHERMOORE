from __future__ import annotations

import copy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import random

import pytest
import torch

from python.scbe.clay_observation_chart_sidecar import (
    ObservationSidecarError,
    build_binding_ledger,
    build_observation_chart_sidecar,
    canonical_json,
    verify_binding_ledger,
    verify_observation_chart_sidecar,
    write_sidecar_create_once,
)


@dataclass(frozen=True)
class FakeState:
    tick: int
    coordinate: int

    def record(self) -> dict[str, int]:
        return {"tick": self.tick, "coordinate": self.coordinate}

    @property
    def sha256(self) -> str:
        return sha256(canonical_json(self.record()).encode("utf-8")).hexdigest()


class FakeProvider:
    source_hashes = {"fixture": "7" * 64}

    def training_sandboxes(self) -> tuple[int, ...]:
        return (0, 1, 2)

    def sample_state(self, sandbox: int, rng: random.Random) -> FakeState:
        del sandbox
        return FakeState(tick=rng.randrange(1, 1_000_000), coordinate=rng.randrange(-10_000, 10_000))

    def materialize(self, sandbox: int, state: FakeState) -> tuple[torch.Tensor, int, int]:
        base = torch.arange(37, dtype=torch.float32)
        feature = base + float(state.coordinate) / 1000.0 + float(sandbox) / 10.0
        return feature, (state.tick + sandbox) % 5, (state.coordinate + sandbox) % 8


def test_sidecar_keeps_canonical_observation_and_exact_separate_views() -> None:
    sidecar = build_observation_chart_sidecar(FakeProvider(), observation_count=4, seed=29)

    assert verify_observation_chart_sidecar(sidecar)
    assert sidecar["authority"] == "AUDIT_ONLY_NO_MODEL_INPUT_NO_TRAINING_NO_PROMOTION"
    for observation in sidecar["observations"]:
        assert {view["view_id"] for view in observation["views"]} == {0, 1, 2}
        assert {view["observation_sha256"] for view in observation["views"]} == {observation["observation_sha256"]}
        assert len({view["feature_sha256"] for view in observation["views"]}) == 3
        assert all(len(bytes.fromhex(view["feature_bytes_hex"])) == 148 for view in observation["views"])
    assert not {"prompt", "target", "model_input", "weight"}.intersection(sidecar)


def test_view_mutation_fails_without_rewriting_the_observation_anchor() -> None:
    sidecar = build_observation_chart_sidecar(FakeProvider(), observation_count=2, seed=31)
    mutated = copy.deepcopy(sidecar)
    anchor = mutated["observations"][0]["observation_sha256"]
    feature_hex = mutated["observations"][0]["views"][0]["feature_bytes_hex"]
    mutated["observations"][0]["views"][0]["feature_bytes_hex"] = (
        "00" if feature_hex[:2] != "00" else "01"
    ) + feature_hex[2:]

    assert mutated["observations"][0]["observation_sha256"] == anchor
    assert not verify_observation_chart_sidecar(mutated)


def test_state_change_moves_anchor_and_all_of_its_view_bindings() -> None:
    first = build_observation_chart_sidecar(FakeProvider(), observation_count=1, seed=41)
    second = build_observation_chart_sidecar(FakeProvider(), observation_count=1, seed=43)

    left = first["observations"][0]
    right = second["observations"][0]
    assert left["observation_sha256"] != right["observation_sha256"]
    assert {view["observation_sha256"] for view in left["views"]} == {left["observation_sha256"]}
    assert {view["observation_sha256"] for view in right["views"]} == {right["observation_sha256"]}


def test_rotated_control_preserves_exact_views_but_breaks_alignment() -> None:
    sidecar = build_observation_chart_sidecar(FakeProvider(), observation_count=5, seed=47)
    authority = build_binding_ledger(sidecar, mode="authority")
    rotated = build_binding_ledger(sidecar, mode="rotated_control")

    assert verify_binding_ledger(sidecar, authority)
    assert verify_binding_ledger(sidecar, rotated)
    assert sorted(row["feature_sha256"] for row in authority["rows"]) == sorted(
        row["feature_sha256"] for row in rotated["rows"]
    )
    assert all(row["anchor_observation_sha256"] == row["view_observation_sha256"] for row in authority["rows"])
    assert all(row["anchor_observation_sha256"] != row["view_observation_sha256"] for row in rotated["rows"])


def test_sidecar_write_is_explicit_create_once(tmp_path: Path) -> None:
    sidecar = build_observation_chart_sidecar(FakeProvider(), observation_count=2, seed=53)
    output = write_sidecar_create_once(tmp_path / "sidecar.json", sidecar)

    assert json.loads(output.read_text(encoding="utf-8")) == sidecar
    with pytest.raises(FileExistsError):
        write_sidecar_create_once(output, sidecar)


def test_rotated_control_rejects_a_single_observation() -> None:
    sidecar = build_observation_chart_sidecar(FakeProvider(), observation_count=1, seed=59)

    with pytest.raises(ObservationSidecarError, match="at least two"):
        build_binding_ledger(sidecar, mode="rotated_control")
