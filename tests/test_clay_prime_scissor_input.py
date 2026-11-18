from __future__ import annotations

import hashlib

import torch

from python.scbe.clay_frozen_multiview_adapter import (
    BOS,
    EOS,
    PAD,
    SEP,
    FrozenActionModel,
    set_trainable,
)
from python.scbe.clay_frozen_multiview_data import ActionTextRow, BYTE_TOKEN_BASE
from python.scbe.clay_prime_scissor_input import (
    ARMS,
    ActionGatedPrimeScissorInput,
    build_feature_tables,
    build_occurrence_derangement,
)
from python.scbe.concept_exposure_ledger import ExposureSample


def _vocab() -> list[str]:
    controls = [PAD, BOS, SEP, EOS, "K", " ", ":", "=", ">", "0"]
    return controls + [chr(BYTE_TOKEN_BASE + value) for value in range(256)]


def _row(sample_index: int, payload: bytes) -> ActionTextRow:
    sample_id = f"sample-{sample_index}"
    return ActionTextRow(
        sample=ExposureSample(
            sample_id=sample_id,
            payload_sha256=hashlib.sha256(payload).hexdigest(),
            concept_id=f"sector-{sample_index}",
            variant_id=f"variant-{sample_index}",
            source_family=f"source-{sample_index}",
            split="train" if sample_index < 3 else "holdout",
            operation_id=f"action-{sample_index % 5}",
            view_id=f"view-{sample_index}",
        ),
        prompt="K :" + "".join(chr(BYTE_TOKEN_BASE + value) for value in payload) + " =>",
        target=str(sample_index % 5),
        label=sample_index % 5,
        sector=sample_index,
    )


def _rows(width: int = 16) -> tuple[ActionTextRow, ...]:
    return tuple(_row(row, bytes((row * width + offset) % 256 for offset in range(width))) for row in range(16))


def _model(arm: str) -> ActionGatedPrimeScissorInput:
    vocab = _vocab()
    torch.manual_seed(71)
    parent = FrozenActionModel(len(vocab))
    model = ActionGatedPrimeScissorInput(vocab, arm=arm, tables=build_feature_tables())
    model.load_parent_state(parent.state_dict())
    return model


def test_exact_dynamic_anchor_table_round_trips_and_has_measured_capacity() -> None:
    tables = build_feature_tables()
    receipt = tables.receipt
    assert tuple(receipt["raw"]) == ("next-cyclic", "previous-cyclic")
    assert receipt["raw"]["next-cyclic"]["anchor_policy"] == "next-cyclic"
    assert receipt["raw"]["previous-cyclic"]["anchor_policy"] == "previous-cyclic"
    assert receipt["raw_block_width"] == 456
    assert receipt["combined_raw_width"] == 912
    assert receipt["pivot_modulus"] == 1_000_003
    assert receipt["pivot_count"] == 205
    assert receipt["affine_rank"] == 205
    assert receipt["linear_rank_with_constant"] == 206
    assert receipt["feature_width"] == 206
    assert receipt["unique_rows"] == {
        "prime_scissor": 256,
        "canonical_onehot_matched": 256,
        "deterministic_random_matched": 256,
    }


def test_controls_match_declared_global_spectrum_or_per_token_leverage() -> None:
    tables = build_feature_tables().tables
    names = (
        "prime_scissor",
        "canonical_onehot_matched",
        "deterministic_random_matched",
    )
    reference = tables[names[0]].double()
    reference_spectrum = torch.linalg.svdvals(reference)
    for name in names:
        value = tables[name].double()
        assert tuple(value.shape) == (256, 206)
        assert torch.linalg.matrix_rank(value, atol=1e-7, rtol=0.0).item() == 206
        assert torch.allclose(torch.linalg.vector_norm(value), torch.tensor(206.0**0.5, dtype=value.dtype))
    canonical = tables["canonical_onehot_matched"].double()
    assert torch.allclose(torch.linalg.svdvals(canonical), reference_spectrum, atol=2e-5, rtol=2e-6)
    assert torch.allclose(
        canonical.T @ canonical,
        reference.T @ reference,
        atol=5e-5,
        rtol=2e-5,
    )
    random_control = tables["deterministic_random_matched"].double()
    assert torch.allclose(
        torch.linalg.vector_norm(random_control, dim=1),
        torch.linalg.vector_norm(reference, dim=1),
        atol=2e-6,
        rtol=2e-6,
    )
    assert torch.count_nonzero(tables["no_intervention"]).item() == 0


def test_split_local_occurrence_derangement_is_one_to_one_randomized_and_replayable() -> None:
    rows = _rows()
    binding = build_occurrence_derangement(rows, seed=771, split_name="preflight")
    original = torch.tensor(
        [[ord(token) - BYTE_TOKEN_BASE for token in row.prompt[3:-3]] for row in rows],
        dtype=torch.uint8,
    )
    assert binding.metadata()["occurrence_count"] == original.numel()
    assert binding.metadata()["same_value_fixed_points"] == 0
    assert binding.metadata()["split_name"] == "preflight"
    assert not binding.metadata()["association"]["gate_evaluated"]
    assert not bool(torch.any(original == binding.mapped_values))
    assert torch.equal(
        torch.bincount(original.flatten().long(), minlength=256),
        torch.bincount(binding.mapped_values.flatten().long(), minlength=256),
    )
    assert build_occurrence_derangement(rows, seed=771, split_name="preflight").seal_sha256 == binding.seal_sha256
    assert build_occurrence_derangement(rows, seed=772, split_name="preflight").seal_sha256 != binding.seal_sha256


def test_all_arms_have_identical_trainable_topology_and_parameter_count() -> None:
    counts = {}
    names = {}
    for arm in ARMS:
        model = _model(arm)
        selected = set_trainable(model, arm)
        counts[arm] = sum(parameter.numel() for parameter in selected)
        names[arm] = tuple(name for name, parameter in model.named_parameters() if parameter.requires_grad)
        assert not model.e.weight.requires_grad
        assert all(not parameter.requires_grad for parameter in model.g.parameters())
    assert len(set(counts.values())) == 1
    assert len(set(names.values())) == 1


def test_candidate_projection_is_pre_gru_action_only_and_receives_nonzero_gradient() -> None:
    model = _model("prime_scissor_input")
    vocab = _vocab()
    stoi = {token: index for index, token in enumerate(vocab)}
    inputs = torch.tensor(
        [
            [
                stoi[BOS],
                stoi[chr(BYTE_TOKEN_BASE + 7)],
                stoi[chr(BYTE_TOKEN_BASE + 19)],
                stoi[SEP],
            ]
        ]
    )
    owner_mask = torch.tensor([[False, True, True, False]])
    count_before, _ = model(inputs, "count")
    parent_before = {
        name: value.detach().clone()
        for name, value in model.state_dict().items()
        if name.startswith(("e.", "g.", "count_head."))
    }
    selected = set_trainable(model, "prime_scissor_input")
    logits, _ = model(inputs, "action", feature_owner_mask=owner_mask)
    loss = torch.nn.functional.cross_entropy(logits[:, -1], torch.tensor([stoi["0"]]))
    loss.backward()
    assert model.feature_projection.weight.grad is not None
    assert torch.count_nonzero(model.feature_projection.weight.grad).item() > 0
    optimizer = torch.optim.Adam(selected, lr=0.01)
    optimizer.step()
    assert torch.count_nonzero(model.feature_projection.weight).item() > 0
    count_after, _ = model(inputs, "count")
    assert torch.equal(count_before, count_after)
    for name, before in parent_before.items():
        assert torch.equal(before, model.state_dict()[name])
    assert model.input_receipt()["placement"].endswith("before frozen GRU")


def test_feature_override_changes_logits_and_future_bytes_cannot_change_earlier_logits() -> None:
    model = _model("prime_scissor_input")
    vocab = _vocab()
    stoi = {token: index for index, token in enumerate(vocab)}
    with torch.no_grad():
        torch.manual_seed(44)
        model.feature_projection.weight.copy_(torch.randn_like(model.feature_projection.weight) * 0.05)
    first = torch.tensor(
        [
            [
                stoi[chr(BYTE_TOKEN_BASE + 11)],
                stoi[chr(BYTE_TOKEN_BASE + 12)],
                stoi[chr(BYTE_TOKEN_BASE + 13)],
            ]
        ]
    )
    future_changed = first.clone()
    future_changed[0, 2] = stoi[chr(BYTE_TOKEN_BASE + 211)]
    owner_mask = torch.ones_like(first, dtype=torch.bool)
    logits_a, _ = model(first, "action", feature_owner_mask=owner_mask)
    logits_b, _ = model(future_changed, "action", feature_owner_mask=owner_mask)
    assert torch.equal(logits_a[:, :2], logits_b[:, :2])
    assert not torch.equal(logits_a[:, 2], logits_b[:, 2])


def test_shuffled_model_reads_only_owned_positions_from_sealed_occurrence_plan() -> None:
    rows = _rows(width=4)
    binding = build_occurrence_derangement(rows, seed=773, split_name="preflight")
    model = _model("shuffled_binding_matched")
    vocab = _vocab()
    stoi = {token: index for index, token in enumerate(vocab)}
    row = rows[0]
    inputs = torch.tensor([[stoi[BOS], *(stoi[token] for token in row.prompt), stoi[SEP]]])
    owner_mask = torch.zeros_like(inputs, dtype=torch.bool)
    owner_mask[:, 4:8] = True
    identity = model.byte_lookup[inputs]
    bound = model._bound_feature_ids(
        inputs,
        feature_owner_mask=owner_mask,
        sample_ids=[row.sample.sample_id],
        binding=binding,
    )
    active = owner_mask
    assert int(active.sum()) == 4
    assert not torch.equal(identity[active], bound[active])
    assert bool(torch.all(bound[~active] == -1))


def test_generated_byte_continuation_is_explicitly_unowned() -> None:
    model = _model("shuffled_binding_matched")
    vocab = _vocab()
    stoi = {token: index for index, token in enumerate(vocab)}
    continuation = torch.tensor([[stoi[chr(BYTE_TOKEN_BASE + 19)]]])
    owner_mask = torch.zeros_like(continuation, dtype=torch.bool)
    bound = model._bound_feature_ids(
        continuation,
        feature_owner_mask=owner_mask,
        sample_ids=None,
        binding=None,
    )
    assert bound.item() == -1
    logits, _ = model(
        continuation,
        "action",
        feature_owner_mask=owner_mask,
    )
    assert torch.isfinite(logits).all()
