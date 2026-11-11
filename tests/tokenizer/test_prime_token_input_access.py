from __future__ import annotations

from argparse import Namespace
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from torch import nn

from python.scbe.prime_token_catalog import VIEW_NAMES
from python.scbe.prime_token_independent_replay import (
    load_adapter_read_only,
    reconstruct_packet_independently,
    replay_predictions,
    verify_no_intervention_parent,
    verify_replay_ledger,
)
from python.scbe.prime_token_input_access import (
    CONTROL_MODES,
    FEATURE_WIDTH,
    VIEW_WIDTH,
    FullSystemPrimeTokenInputAccessLM,
    PrimeTokenRecord,
    PrimeTokenInputReader,
    build_prime_token_batch,
)
from python.scbe.prime_token_training import (
    MaterialReleaseError,
    PrimeTrainingExample,
    admit_material_launch,
    load_adapter_checkpoint,
    module_state_sha256,
    new_training_state,
    save_adapter_checkpoint,
    sha256_file,
    train_steps,
)
from scripts.tokenizer.run_prime_token_input_access import validate_evaluation_result
import scripts.tokenizer.run_prime_token_input_access as material_runner


def _record(name: str, family: str = "family-a") -> PrimeTokenRecord:
    return PrimeTokenRecord(
        canonical_id=f"token:{name}",
        section_id=f"section:{name}",
        source_family=family,
        views={
            view: {
                "surface": name,
                "view": view,
                "length": len(name),
                "index": index,
            }
            for index, view in enumerate(VIEW_NAMES)
        },
    )


class _Route:
    def initial_state(self, lanes: torch.Tensor) -> torch.Tensor:
        return lanes.mean(dim=(-1, -2))

    def step(self, hidden, state, index):
        return hidden, state, {"index": index}


class _FakeCore(nn.Module):
    def __init__(self, *, vocab: int = 13, width: int = 8, block_size: int = 8):
        super().__init__()
        self.config = SimpleNamespace(
            d_model=width,
            block_size=block_size,
            route_mode="off",
        )
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

    def forward(
        self,
        token_ids: torch.Tensor,
        *,
        return_diagnostics: bool = False,
        return_aux: bool = False,
    ):
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
                    [decoder(raw_lanes[:, :, index]) for index, decoder in enumerate(self.lane_decoders)],
                    dim=2,
                )
            }
        if return_diagnostics and return_aux:
            return logits, traces, aux
        if return_diagnostics:
            return logits, traces
        if return_aux:
            return logits, aux
        return logits


def _packet(
    mode: str = "canonical_six_view_reader",
    *,
    family: str = "family-a",
):
    pool = [_record("alpha", family), _record("beta", family)]
    return build_prime_token_batch(
        [pool],
        [[1, 3]],
        sequence_length=5,
        mode=mode,
        binding_pool=pool if mode == "shuffled_binding_reader" else None,
    )


def _example(
    packet=None,
    *,
    record_id: str = "train-1",
    split: str = "train",
    family: str = "family-a",
) -> PrimeTrainingExample:
    packet = packet or _packet(family=family)
    token_ids = torch.tensor([[1, 2, 3, 4, 5]], dtype=torch.long)
    targets = torch.tensor([[2, 3, 4, 5, 6]], dtype=torch.long)
    weights = torch.tensor([[0.0, 0.0, 0.0, 1.0, 1.0]])
    return PrimeTrainingExample(
        record_ids=(record_id,),
        splits=(split,),
        source_families=(family,),
        token_ids=token_ids,
        targets=targets,
        weights=weights,
        packet=packet,
        output_positions=((3, 4),),
        allowed_output_token_ids=(5, 6),
        exact_evaluator_receipt_sha256="e" * 64,
    )


def test_packet_is_deterministic_sealed_and_tamper_evident() -> None:
    first = _packet()
    second = _packet()
    assert first.seal_sha256 == second.seal_sha256
    assert torch.equal(first.features, second.features)
    first.validate()
    first.features[0, 1, 0] += 0.25
    with pytest.raises(ValueError, match="mutated"):
        first.validate()


def test_controls_keep_equal_width_and_reader_parameter_count() -> None:
    packets = {mode: _packet(mode) for mode in CONTROL_MODES}
    assert {packet.features.shape[-1] for packet in packets.values()} == {FEATURE_WIDTH}
    counts = {sum(parameter.numel() for parameter in PrimeTokenInputReader(8, 4).parameters()) for _ in CONTROL_MODES}
    assert len(counts) == 1
    lexical = packets["lexical_only_reader"]
    assert torch.count_nonzero(lexical.features[..., VIEW_WIDTH:]) == 0
    canonical = packets["canonical_six_view_reader"]
    random_fixed = packets["random_fixed_reader"]
    for position in (1, 3):
        canonical_norms = canonical.features[0, position].reshape(-1, VIEW_WIDTH).norm(dim=1)
        random_norms = random_fixed.features[0, position].reshape(-1, VIEW_WIDTH).norm(dim=1)
        assert torch.allclose(canonical_norms, random_norms)
    shuffled = packets["shuffled_binding_reader"]
    assert torch.equal(shuffled.features[0, 1], canonical.features[0, 3])
    assert torch.equal(shuffled.features[0, 3], canonical.features[0, 1])


def test_independent_reconstruction_matches_every_control() -> None:
    records = [[_record("alpha"), _record("beta")]]
    positions = [[1, 3]]
    for mode in CONTROL_MODES:
        binding_pool = records[0] if mode == "shuffled_binding_reader" else None
        producer = build_prime_token_batch(
            records,
            positions,
            sequence_length=5,
            mode=mode,
            binding_pool=binding_pool,
        )
        replay = reconstruct_packet_independently(
            records,
            positions,
            sequence_length=5,
            mode=mode,
            binding_pool=binding_pool,
        )
        assert replay.seal_sha256 == producer.seal_sha256
        assert torch.equal(replay.features, producer.features)
        assert torch.equal(replay.view_mask, producer.view_mask)


def test_shuffled_binding_requires_dataset_pool_and_true_vector_derangement() -> None:
    alpha = _record("alpha", "family-a")
    beta = _record("beta", "family-b")
    with pytest.raises(ValueError, match="dataset-wide pool"):
        build_prime_token_batch(
            [[alpha]],
            [[1]],
            sequence_length=3,
            mode="shuffled_binding_reader",
        )
    duplicate_vector = _record("alpha", "family-c")
    with pytest.raises(ValueError, match="vector derangement"):
        build_prime_token_batch(
            [[alpha]],
            [[1]],
            sequence_length=3,
            mode="shuffled_binding_reader",
            binding_pool=[alpha, duplicate_vector],
        )
    packet = build_prime_token_batch(
        [[alpha]],
        [[1]],
        sequence_length=3,
        mode="shuffled_binding_reader",
        binding_pool=[alpha, beta],
    )
    replay = reconstruct_packet_independently(
        [[alpha]],
        [[1]],
        sequence_length=3,
        mode="shuffled_binding_reader",
        binding_pool=[alpha, beta],
    )
    assert packet.binding_pool_sha256 == replay.binding_pool_sha256
    assert packet.binding_permutation_sha256 == replay.binding_permutation_sha256
    assert packet.seal_sha256 == replay.seal_sha256


def test_no_packet_path_is_bit_identical_and_reports_no_false_activation() -> None:
    core = _FakeCore()
    wrapped = FullSystemPrimeTokenInputAccessLM(core, reader_rank=4)
    token_ids = _example().token_ids
    expected = core(token_ids)
    observed = wrapped(token_ids)
    with_meta, meta = wrapped(token_ids, return_prime_meta=True)
    assert torch.equal(expected, observed)
    assert torch.equal(expected, with_meta)
    assert meta["prime_packet_used"] is False
    assert meta["false_activation"] is False


def test_owned_placeholder_is_masked_while_unowned_token_still_matters() -> None:
    wrapped = FullSystemPrimeTokenInputAccessLM(_FakeCore(), reader_rank=4)
    packet = _packet()
    baseline = _example().token_ids
    owned_changed = baseline.clone()
    owned_changed[0, 1] = 9
    unowned_changed = baseline.clone()
    unowned_changed[0, 0] = 9
    original = wrapped(baseline, prime_packet=packet)
    owned = wrapped(owned_changed, prime_packet=packet)
    unowned = wrapped(unowned_changed, prime_packet=packet)
    assert torch.equal(original, owned)
    assert not torch.equal(original[:, 0], unowned[:, 0])


def test_future_owned_record_cannot_change_earlier_logits() -> None:
    wrapped = FullSystemPrimeTokenInputAccessLM(_FakeCore(), reader_rank=4)
    packet_a = build_prime_token_batch(
        [[_record("alpha"), _record("beta")]],
        [[1, 3]],
        sequence_length=5,
        mode="canonical_six_view_reader",
    )
    packet_b = build_prime_token_batch(
        [[_record("alpha"), _record("gamma")]],
        [[1, 3]],
        sequence_length=5,
        mode="canonical_six_view_reader",
    )
    token_ids = _example().token_ids
    logits_a = wrapped(token_ids, prime_packet=packet_a)
    logits_b = wrapped(token_ids, prime_packet=packet_b)
    assert torch.equal(logits_a[:, :3], logits_b[:, :3])


def test_one_step_updates_reader_but_parent_is_bit_identical() -> None:
    model = FullSystemPrimeTokenInputAccessLM(_FakeCore(), reader_rank=4)
    parent_before = module_state_sha256(model.core)
    reader_before = deepcopy(model.adapter_state_dict())
    _, _, history = train_steps(
        model,
        [_example()],
        steps=1,
        learning_rate=0.01,
        seed=77,
        device=torch.device("cpu"),
    )
    assert module_state_sha256(model.core) == parent_before
    assert any(not torch.equal(reader_before[name], value) for name, value in model.adapter_state_dict().items())
    assert history[0]["parent_sha256"] == parent_before


def test_two_slot_resume_matches_uninterrupted_next_step(tmp_path: Path) -> None:
    torch.manual_seed(44)
    base = _FakeCore()
    uninterrupted = FullSystemPrimeTokenInputAccessLM(deepcopy(base), reader_rank=4)
    split = FullSystemPrimeTokenInputAccessLM(deepcopy(base), reader_rank=4)
    split.load_adapter_state_dict(uninterrupted.adapter_state_dict())
    identity = {"arm": "canonical_six_view_reader", "seed": "91", "parent": "fake"}
    example = _example()

    full_optimizer, full_sampler, _ = train_steps(
        uninterrupted,
        [example],
        steps=2,
        learning_rate=0.01,
        seed=91,
        device=torch.device("cpu"),
    )
    split_optimizer, split_sampler, _ = train_steps(
        split,
        [example],
        steps=1,
        learning_rate=0.01,
        seed=91,
        device=torch.device("cpu"),
    )
    save_adapter_checkpoint(
        tmp_path,
        model=split,
        optimizer=split_optimizer,
        sampler=split_sampler,
        step=1,
        save_every=1,
        identity=identity,
        metrics={"loss": 0.0},
    )
    resumed = FullSystemPrimeTokenInputAccessLM(deepcopy(base), reader_rank=4)
    resumed_optimizer, resumed_sampler = new_training_state(resumed, learning_rate=0.01, seed=91)
    payload, _ = load_adapter_checkpoint(
        tmp_path,
        model=resumed,
        optimizer=resumed_optimizer,
        sampler=resumed_sampler,
        expected_identity=identity,
    )
    train_steps(
        resumed,
        [example],
        steps=1,
        learning_rate=0.01,
        seed=91,
        device=torch.device("cpu"),
        optimizer=resumed_optimizer,
        sampler=resumed_sampler,
        start_step=int(payload["step"]),
    )
    assert all(
        torch.equal(value, resumed.adapter_state_dict()[name])
        for name, value in uninterrupted.adapter_state_dict().items()
    )
    assert full_optimizer.state_dict()["param_groups"] == resumed_optimizer.state_dict()["param_groups"]
    assert torch.equal(full_sampler.get_state(), resumed_sampler.get_state())


def test_material_launch_refuses_waiting_audit(tmp_path: Path) -> None:
    audit = tmp_path / "audit.json"
    audit.write_text(
        json.dumps(
            {
                "schema": "scbe.prime-token-frozen-input-access-release-audit.v1",
                "status": "WAITING_FOR_RELEASE_REQUIREMENTS",
                "error_count": 0,
                "blocker_count": 2,
                "contract_id": "contract-v1",
            }
        ),
        encoding="utf-8",
    )
    authorization = tmp_path / "authorization.json"
    authorization.write_text("{}", encoding="utf-8")
    with pytest.raises(MaterialReleaseError, match="not cleared"):
        admit_material_launch(audit, authorization)


def test_material_evaluator_requires_raw_tri_point_and_system_metrics() -> None:
    complete = {
        "evaluator_receipt_sha256": "e" * 64,
        "metrics": {
            "accuracy": 0.5,
            "relationship": 0.4,
            "function": 0.3,
            "ordinary_false_activation": 0.0,
            "frozen_parent_retention": 1.0,
            "throughput": 123.0,
            "peak_memory": 4096,
        },
        "per_example": [
            {
                "id": "held-1:3",
                "record_id": "held-1",
                "split": "final_test",
                "source_family": "family-held",
                "accuracy": True,
            }
        ],
    }
    assert (
        validate_evaluation_result(
            complete,
            train_examples=[_example()],
        )[
            "metrics"
        ]["function"]
        == 0.3
    )
    del complete["metrics"]["relationship"]
    with pytest.raises(ValueError, match="relationship"):
        validate_evaluation_result(complete)


def test_training_contract_rejects_noncausal_or_unbounded_supervision() -> None:
    example = _example()
    example.validate()
    with pytest.raises(ValueError, match="precedes"):
        replace(
            example,
            output_positions=((1,),),
            weights=torch.tensor([[0.0, 1.0, 0.0, 0.0, 0.0]]),
        ).validate()
    with pytest.raises(ValueError, match="outside the bounded output set"):
        replace(example, allowed_output_token_ids=(6,)).validate()
    with pytest.raises(ValueError, match="binary"):
        replace(
            example,
            weights=torch.tensor([[0.0, 0.0, 0.0, 0.5, 1.0]]),
        ).validate()
    with pytest.raises(ValueError, match="non-training split"):
        train_steps(
            FullSystemPrimeTokenInputAccessLM(_FakeCore(), reader_rank=4),
            [replace(example, splits=("final_test",))],
            steps=1,
            learning_rate=0.01,
            seed=7,
            device=torch.device("cpu"),
        )


def test_evaluator_rejects_training_source_family_overlap() -> None:
    value = {
        "evaluator_receipt_sha256": "e" * 64,
        "metrics": {
            "accuracy": 0.5,
            "relationship": 0.4,
            "function": 0.3,
            "ordinary_false_activation": 0.0,
            "frozen_parent_retention": 1.0,
            "throughput": 10.0,
            "peak_memory": 1000,
        },
        "per_example": [
            {
                "id": "held-1:3",
                "record_id": "held-1",
                "split": "final_test",
                "source_family": "family-a",
                "correct": True,
            }
        ],
    }
    with pytest.raises(ValueError, match="receipt differs"):
        validate_evaluation_result(
            {**value, "evaluator_receipt_sha256": "f" * 64},
            train_examples=[_example()],
        )
    with pytest.raises(ValueError, match="source families"):
        validate_evaluation_result(value, train_examples=[_example()])


def test_released_runner_writes_evaluation_and_checkpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    audit = tmp_path / "audit.json"
    audit.write_text(
        json.dumps(
            {
                "schema": "scbe.prime-token-frozen-input-access-release-audit.v1",
                "status": "READY_FOR_MANUAL_TRAINING_RELEASE_REVIEW",
                "error_count": 0,
                "blocker_count": 0,
                "contract_id": "contract-v1",
            }
        ),
        encoding="utf-8",
    )
    authorization = tmp_path / "authorization.json"
    authorization.write_text(
        json.dumps(
            {
                "schema": "scbe.prime-token-material-authorization.v1",
                "status": "AUTHORIZED_FOR_MATERIAL_TRAINING",
                "contract_id": "contract-v1",
                "audit_sha256": sha256_file(audit),
                "authorized_by": "test-human",
                "tool_dispatch": False,
                "partial_unfreeze": "NONE",
            }
        ),
        encoding="utf-8",
    )
    model = FullSystemPrimeTokenInputAccessLM(_FakeCore(), reader_rank=4)
    identity = {
        "arm": "canonical_six_view_reader",
        "seed": "18",
        "parent_sha256": module_state_sha256(model.core),
        "source_manifest_sha256": "a" * 64,
        "split_manifest_sha256": "b" * 64,
    }

    def evaluate(_model, _arm):
        return {
            "evaluator_receipt_sha256": "e" * 64,
            "metrics": {
                "accuracy": 0.5,
                "relationship": 0.4,
                "function": 0.3,
                "ordinary_false_activation": 0.0,
                "frozen_parent_retention": 1.0,
                "throughput": 10.0,
                "peak_memory": 1000,
            },
            "per_example": [
                {
                    "id": "held-1:3",
                    "record_id": "held-1",
                    "split": "final_test",
                    "source_family": "family-held",
                    "correct": True,
                }
            ],
        }

    payload = {
        "model": model,
        "train_examples": [_example()],
        "identity": identity,
        "evaluate": evaluate,
    }
    monkeypatch.setattr(material_runner, "_factory", lambda _spec: lambda _config: payload)
    runtime_config = tmp_path / "runtime.json"
    runtime_config.write_text("{}", encoding="utf-8")
    output = tmp_path / "lineage"
    result = material_runner.run(
        Namespace(
            audit=audit,
            authorization=authorization,
            runtime_factory="test:factory",
            runtime_config=runtime_config,
            output=output,
            arm="canonical_six_view_reader",
            seed=18,
            steps=1,
            save_every=1,
            learning_rate=0.01,
            device="cpu",
        )
    )
    assert result["status"] == "COMPLETE_NO_PROMOTION"
    assert result["evaluation"]["metrics"]["checkpoint_bytes"] > 0
    assert (output / "EVALUATION.json").is_file()
    assert (output / "LATEST.json").is_file()


def test_independent_replay_detects_checkpoint_and_ledger_tampering(
    tmp_path: Path,
) -> None:
    model = FullSystemPrimeTokenInputAccessLM(_FakeCore(), reader_rank=4)
    optimizer, sampler = new_training_state(model, learning_rate=0.01, seed=5)
    identity = {"arm": "canonical_six_view_reader", "seed": "5", "parent": "fake"}
    save_adapter_checkpoint(
        tmp_path,
        model=model,
        optimizer=optimizer,
        sampler=sampler,
        step=0,
        save_every=1,
        identity=identity,
        metrics={},
    )
    receipt = load_adapter_read_only(tmp_path, model=model, expected_identity=identity)
    assert receipt["producer_metrics_ignored"] is True
    held = _example(
        _packet(family="family-held"),
        record_id="held-1",
        split="final_test",
        family="family-held",
    )
    replay = replay_predictions(
        model,
        held.token_ids,
        held.targets,
        held.packet,
        record_ids=held.record_ids,
        splits=held.splits,
        source_families=held.source_families,
        output_positions=held.output_positions,
        allowed_output_token_ids=held.allowed_output_token_ids,
        exact_evaluator_receipt_sha256=held.exact_evaluator_receipt_sha256,
    )
    assert replay["example_count"] == 2
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps(replay), encoding="utf-8")
    verify_replay_ledger(ledger, replay)
    changed = json.loads(ledger.read_text(encoding="utf-8"))
    changed["correct_count"] += 1
    ledger.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(RuntimeError, match="correct_count"):
        verify_replay_ledger(ledger, replay)

    pointer = json.loads((tmp_path / "LATEST.json").read_text(encoding="utf-8"))
    checkpoint = tmp_path / pointer["file"]
    checkpoint.write_bytes(checkpoint.read_bytes() + b"tampered")
    assert sha256_file(checkpoint) != pointer["sha256"]
    with pytest.raises(RuntimeError, match="hash verification"):
        load_adapter_read_only(tmp_path, model=model, expected_identity=identity)


def test_no_intervention_replay_seals_parent_without_checkpoint() -> None:
    model = FullSystemPrimeTokenInputAccessLM(_FakeCore(), reader_rank=4)
    identity = {
        "arm": "no_intervention",
        "seed": "5",
        "parent_sha256": module_state_sha256(model.core),
        "source_manifest_sha256": "a" * 64,
        "split_manifest_sha256": "b" * 64,
    }
    receipt = verify_no_intervention_parent(model=model, expected_identity=identity)
    assert receipt["checkpoint"] is None
    assert receipt["checkpoint_free_baseline"] is True
    assert receipt["step"] == 0
    with pytest.raises(RuntimeError, match="parent differs"):
        verify_no_intervention_parent(
            model=model,
            expected_identity={**identity, "parent_sha256": "f" * 64},
        )
