from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
from pathlib import Path

import pytest
import torch

from python.scbe import clay_byte_embedding_thaw_replay as replay
from python.scbe import clay_frozen_multiview_replay as frozen_replay


def _vocab() -> list[str]:
    controls = [
        frozen_replay.PAD,
        frozen_replay.BOS,
        frozen_replay.SEP,
        frozen_replay.EOS,
        "K",
        " ",
        ":",
        "=",
        ">",
        "0",
    ]
    return controls + [chr(replay.BYTE_TOKEN_BASE + value) for value in range(256)]


def _states() -> tuple[list[str], dict[str, torch.Tensor], dict[str, torch.Tensor]]:
    vocab = _vocab()
    torch.manual_seed(71)
    parent_model = frozen_replay.ReplayFrozenActionModel(len(vocab))
    parent = {key: value.detach().clone() for key, value in parent_model.state_dict().items()}
    token_to_id = {token: index for index, token in enumerate(vocab)}
    byte_ids = [token_to_id[chr(replay.BYTE_TOKEN_BASE + value)] for value in range(256)]
    candidate = {key: value.detach().clone() for key, value in parent.items()}
    candidate["thawed_byte_rows"] = parent["e.weight"][byte_ids].detach().clone()
    return vocab, parent, candidate


def _row() -> frozen_replay.ReplayActionRow:
    body = "".join(chr(replay.BYTE_TOKEN_BASE + value) for value in range(148))
    prompt = f"K :{body} =>"
    payload = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return frozen_replay.ReplayActionRow(
        sample=frozen_replay.ReplaySample(
            sample_id="held-000001",
            payload_sha256=payload,
            concept_id="sector-2",
            variant_id="fixture",
            source_family=frozen_replay.HOLDOUT_SOURCE,
            split="holdout",
            operation_id="action-3",
            view_id="held-diagonal",
        ),
        prompt=prompt,
        target="3",
        label=3,
        sector=2,
    )


def test_replay_source_does_not_import_thaw_producer_or_model() -> None:
    source = Path(replay.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any(name.endswith("clay_byte_embedding_thaw") for name in imported)
    assert not any(name.endswith("clay_byte_embedding_thaw_campaign") for name in imported)


def test_independent_model_uses_shadow_rows_only_on_action_path() -> None:
    vocab, _, candidate = _states()
    model = replay.ReplayByteThawModel(vocab)
    model.load_state_dict(candidate, strict=True)
    stoi = {token: index for index, token in enumerate(vocab)}
    byte_token = stoi[chr(replay.BYTE_TOKEN_BASE + 7)]
    inputs = torch.tensor([[stoi[frozen_replay.BOS], byte_token]])
    count_before = model._embed(inputs, head="count").detach().clone()
    action_before = model._embed(inputs, head="action").detach().clone()
    with torch.no_grad():
        model.thawed_byte_rows[7].add_(2.0)
    count_after = model._embed(inputs, head="count").detach()
    action_after = model._embed(inputs, head="action").detach()
    assert torch.equal(count_before, count_after)
    assert torch.equal(count_before, action_before)
    assert not torch.equal(action_before[:, 1], action_after[:, 1])
    assert torch.equal(action_before[:, 0], action_after[:, 0])


def test_shuffle_is_replayable_bijective_and_sample_local() -> None:
    row = _row()
    first = replay.sample_local_byte_shuffle(row, seed=20261115)
    same = replay.sample_local_byte_shuffle(row, seed=20261115)
    other_seed = replay.sample_local_byte_shuffle(row, seed=20261116)
    other_sample = replay.sample_local_byte_shuffle(
        replace(row, sample=replace(row.sample, sample_id="held-000002")),
        seed=20261115,
    )
    assert first.prompt == same.prompt
    assert first.prompt != row.prompt
    assert first.prompt != other_seed.prompt
    assert first.prompt != other_sample.prompt
    original_values = [ord(token) - replay.BYTE_TOKEN_BASE for token in row.prompt[3:-3]]
    shuffled_values = [ord(token) - replay.BYTE_TOKEN_BASE for token in first.prompt[3:-3]]
    assert len(set(original_values)) == len(set(shuffled_values))


def test_state_audit_catches_frozen_and_state_key_tampering() -> None:
    vocab, parent, candidate = _states()
    candidate["thawed_byte_rows"][9].add_(1.0)
    clean = replay.audit_thaw_state(parent, candidate, vocab)
    assert clean["state_keys_exact"] is True
    assert clean["frozen_tensors_bit_identical"] is True
    assert clean["changed_byte_rows"] == 1
    assert clean["weight_effect"]["scalar_count"] == clean["trainable_parameters"]

    frozen_tamper = {key: value.clone() for key, value in candidate.items()}
    frozen_tamper["g.weight_ih_l0"][0, 0].add_(1.0)
    assert replay.audit_thaw_state(parent, frozen_tamper, vocab)["frozen_tensors_bit_identical"] is False
    key_tamper = {**candidate, "unexpected.weight": torch.zeros(1)}
    assert replay.audit_thaw_state(parent, key_tamper, vocab)["state_keys_exact"] is False


def test_atomic_ledger_is_canonical_unique_and_no_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    rows = [
        {"arm": "z", "seed": 2, "sample_id": "b", "prediction": 1},
        {"arm": "a", "seed": 1, "sample_id": "a", "prediction": 0},
    ]
    receipt = replay.atomic_jsonl(path, rows)
    assert receipt["rows"] == 2
    assert receipt["unique_keys"] == 2
    lines = path.read_text(encoding="utf-8").splitlines()
    assert '"arm":"a"' in lines[0]
    assert receipt["sha256"] == replay.file_sha256(path)
    with pytest.raises(FileExistsError):
        replay.atomic_jsonl(path, rows)
    with pytest.raises(RuntimeError, match="duplicate"):
        replay.canonical_ledger_rows([rows[0], rows[0]])


def test_replayed_gate_requires_both_controls_and_finite_uncertainty() -> None:
    comparisons = {}
    paired = {}
    for control in replay.GATE_CONTROLS:
        name = f"{replay.PRIMARY}_vs_{control}"
        comparisons[name] = {
            "accuracy": {"clears_positive_gate": True},
            "macro_f1": {"clears_positive_gate": True},
        }
        paired[name] = {"clears_finite_uncertainty_gate": True}
    assert replay.replayed_gate(
        comparisons=comparisons,
        paired=paired,
        parameter_counts={10},
        retained=True,
        rows_changed=True,
    )
    paired[f"{replay.PRIMARY}_vs_{replay.SHUFFLED}"]["clears_finite_uncertainty_gate"] = False
    assert not replay.replayed_gate(
        comparisons=comparisons,
        paired=paired,
        parameter_counts={10},
        retained=True,
        rows_changed=True,
    )


def test_baseline_replay_binding_rejects_stale_verifier(tmp_path: Path) -> None:
    result = tmp_path / "RESULT.json"
    result.write_text("{}", encoding="utf-8")
    receipt = {
        "status": "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION",
        "errors": [],
        "producer_result_sha256": replay.file_sha256(result),
        "independent_dataset_builder_sha256": replay.file_sha256(Path(frozen_replay.__file__).resolve(strict=True)),
        "promotion": "NONE",
        "partial_unfreeze_authorized": False,
    }
    assert replay._baseline_replay_errors(result, receipt) == []
    receipt["independent_dataset_builder_sha256"] = "0" * 64
    assert "verifier binding is stale" in " ".join(replay._baseline_replay_errors(result, receipt))


def test_baseline_watch_binding_matches_real_receipt_schema(tmp_path: Path) -> None:
    replay_path = tmp_path / "INDEPENDENT_REPLAY.json"
    replay_path.write_text("{}", encoding="utf-8")
    source_adapter_sha256 = "a" * 64
    replay_receipt = {
        "status": "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION",
        "errors": [],
        "producer_result_sha256": "b" * 64,
        "independent_dataset_builder_sha256": "c" * 64,
        "verifier_contract_sha256": "d" * 64,
        "verifier_contract": {
            "files": {
                "source_adapter": {"sha256": source_adapter_sha256},
            }
        },
    }
    watch_receipt = {
        "status": "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION",
        "producer_result_sha256": replay_receipt["producer_result_sha256"],
        "replay_receipt_sha256": replay.file_sha256(replay_path),
        "replay_status": replay_receipt["status"],
        "replay_error_count": 0,
        "verifier_sha256": replay_receipt["independent_dataset_builder_sha256"],
        "verifier_contract_sha256": replay_receipt["verifier_contract_sha256"],
        "source_adapter_sha256": source_adapter_sha256,
        "verifier_contract_binding_matches": True,
        "verifier_contract_stable_during_replay": True,
        "authority_boundary_passed": True,
    }
    assert (
        replay._baseline_watch_errors(
            replay_path,
            replay_receipt,
            watch_receipt,
        )
        == []
    )

    stale = {**watch_receipt, "producer_result_sha256": "0" * 64}
    assert "producer result" in " ".join(replay._baseline_watch_errors(replay_path, replay_receipt, stale))

    unstable = {
        **watch_receipt,
        "verifier_contract_stable_during_replay": False,
    }
    assert "verifier contract changed" in " ".join(replay._baseline_watch_errors(replay_path, replay_receipt, unstable))
