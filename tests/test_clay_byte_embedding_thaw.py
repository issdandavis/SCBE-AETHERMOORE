from __future__ import annotations

import hashlib
from pathlib import Path

import torch

from python.scbe.clay_byte_embedding_thaw import (
    ActionGatedByteEmbeddingThaw,
    sample_local_byte_shuffle,
)
from python.scbe.clay_frozen_multiview_adapter import (
    BOS,
    EOS,
    PAD,
    SEP,
    FrozenActionModel,
    counting_accuracy,
    counting_rows,
    set_trainable,
    vocab_of,
)
from python.scbe.clay_frozen_multiview_data import (
    ActionTextRow,
    BYTE_TOKEN_BASE,
    FrozenMultiviewDataset,
    action_prompt,
)
from python.scbe.clay_byte_embedding_thaw_campaign import (
    ThawCampaignConfig,
    train_arm,
)
from python.scbe.concept_exposure_ledger import ExposureSample


def _vocab() -> list[str]:
    controls = [PAD, BOS, SEP, EOS, "K", " ", ":", "=", ">", "0"]
    return controls + [chr(BYTE_TOKEN_BASE + value) for value in range(256)]


def _model() -> ActionGatedByteEmbeddingThaw:
    vocab = _vocab()
    torch.manual_seed(11)
    parent = FrozenActionModel(len(vocab))
    model = ActionGatedByteEmbeddingThaw(vocab)
    model.load_parent_state(parent.state_dict())
    return model


def test_action_thaw_changes_input_carrier_but_not_count_path() -> None:
    model = _model()
    vocab = _vocab()
    stoi = {token: index for index, token in enumerate(vocab)}
    token = stoi[chr(BYTE_TOKEN_BASE + 7)]
    inputs = torch.tensor([[stoi[BOS], token, stoi[SEP]]])
    count_before, _ = model(inputs, "count")
    action_before = model._embed(inputs, "action").detach().clone()
    with torch.no_grad():
        model.thawed_byte_rows[7].add_(3.0)
    count_after, _ = model(inputs, "count")
    action_after = model._embed(inputs, "action").detach()
    assert torch.equal(count_before, count_after)
    assert not torch.equal(action_before[:, 1], action_after[:, 1])
    assert torch.equal(action_before[:, 0], action_after[:, 0])


def test_trainable_surface_is_byte_rows_plus_action_adapter_only() -> None:
    model = _model()
    selected = set_trainable(model, "byte_thaw_multiview")
    assert any(parameter is model.thawed_byte_rows for parameter in selected)
    assert model.thawed_byte_rows.requires_grad
    assert not model.e.weight.requires_grad
    assert all(not parameter.requires_grad for parameter in model.g.parameters())
    assert all(parameter.requires_grad for parameter in model.adapter.parameters())
    assert all(parameter.requires_grad for parameter in model.adapter_head.parameters())


def test_action_step_moves_thaw_rows_and_preserves_parent_tensors() -> None:
    model = _model()
    vocab = _vocab()
    stoi = {token: index for index, token in enumerate(vocab)}
    selected = set_trainable(model, "byte_thaw_multiview")
    base_before = {
        name: value.detach().clone()
        for name, value in model.state_dict().items()
        if name.startswith(("e.", "g.", "count_head."))
    }
    thaw_before = model.thawed_byte_rows.detach().clone()
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
    optimizer = torch.optim.Adam(selected, lr=0.01)
    logits, _ = model(inputs, "action")
    loss = torch.nn.functional.cross_entropy(logits[:, -1], torch.tensor([stoi["0"]]))
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    assert not torch.equal(thaw_before, model.thawed_byte_rows)
    for name, before in base_before.items():
        assert torch.equal(before, model.state_dict()[name])


def test_sample_local_shuffle_is_replayable_and_changes_byte_identity() -> None:
    body = "".join(chr(BYTE_TOKEN_BASE + value) for value in range(148))
    row = ActionTextRow(
        sample=ExposureSample(
            sample_id="sample-1",
            payload_sha256="0" * 64,
            concept_id="sector-1",
            variant_id="variant",
            source_family="source",
            split="train",
            operation_id="action-0",
            view_id="view",
        ),
        prompt=f"K :{body} =>",
        target="0",
        label=0,
        sector=1,
    )
    first = sample_local_byte_shuffle(row, seed=17)
    replay = sample_local_byte_shuffle(row, seed=17)
    alternate = sample_local_byte_shuffle(row, seed=18)
    assert first.prompt == replay.prompt
    assert first.prompt != row.prompt
    assert first.prompt != alternate.prompt
    assert len(first.prompt) == len(row.prompt)


def _tiny_rows(prefix: str) -> tuple[ActionTextRow, ...]:
    rows = []
    for label in range(5):
        torch.manual_seed(100 + label)
        prompt = action_prompt(torch.randn(37, dtype=torch.float32))
        payload = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        rows.append(
            ActionTextRow(
                sample=ExposureSample(
                    sample_id=f"{prefix}-sample-{label}",
                    payload_sha256=payload,
                    concept_id=f"sector-{label}",
                    variant_id=f"variant-{label}",
                    source_family=f"tiny-{prefix}-source",
                    split=prefix,
                    operation_id=f"action-{label}",
                    view_id="tiny-view",
                ),
                prompt=prompt,
                target=str(label),
                label=label,
                sector=label,
            )
        )
    return tuple(rows)


def test_one_step_campaign_horse_changes_rows_without_changing_parent(
    tmp_path: Path,
) -> None:
    rows = _tiny_rows("train")
    holdout = _tiny_rows("holdout")
    count_train = counting_rows(False)
    count_holdout = counting_rows(True)
    vocab, stoi = vocab_of(
        count_train,
        count_holdout,
        tuple(row.pair() for row in rows),
    )
    for value in range(256):
        token = chr(BYTE_TOKEN_BASE + value)
        if token not in stoi:
            stoi[token] = len(vocab)
            vocab.append(token)
    itos = {index: token for token, index in stoi.items()}
    torch.manual_seed(211)
    parent_model = FrozenActionModel(len(vocab))
    parent_counting = counting_accuracy(
        parent_model,
        rows=count_holdout,
        stoi=stoi,
        itos=itos,
        device="cpu",
    )
    parent = {"model_state": parent_model.state_dict(), "vocab": vocab}
    parent_result = {
        "parent_sha256": "synthetic-parent",
        "counting_accuracy": parent_counting,
    }
    dataset = FrozenMultiviewDataset(
        static_rows=rows,
        multiview_rows=rows,
        holdout_rows=holdout,
        manifest={"manifest_sha256": "synthetic-dataset"},
    )
    campaign = ThawCampaignConfig(
        baseline_run="synthetic",
        baseline_manifest_sha256="synthetic",
        baseline_result_sha256="synthetic",
        dataset_manifest_sha256="synthetic-dataset",
        seeds=(1, 2, 3),
        grow_steps=1,
        checkpoint_every=1,
        batch_size=5,
        learning_rate=0.002,
        threads=1,
        device="cpu",
        source_dir="synthetic",
        source_hashes={"synthetic": "source"},
    )
    baseline_manifest = {
        "config": {
            "data_seed": 1,
            "rows_per_view": 5,
            "holdout_rows": 5,
            "count_steps": 1,
        }
    }
    result = train_arm(
        arm="byte_thaw_multiview",
        seed=1,
        output=tmp_path,
        campaign=campaign,
        baseline_manifest=baseline_manifest,
        parent=parent,
        parent_result=parent_result,
        dataset=dataset,
        config_hash="synthetic-config",
    )
    assert result["status"] == "COMPLETE"
    assert result["base_parent_bit_identical"] is True
    assert result["counting_accuracy"] == parent_counting
    assert result["thaw_receipt"]["changed_byte_rows"] > 0
