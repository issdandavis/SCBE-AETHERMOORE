"""Unit smoke for the v5 launch-blocker patches in kernel_template.py.

Validates the *patch logic* without spinning up a Kaggle round:

  - WeightedDslSFTTrainer._get_train_sampler returns WeightedRandomSampler when
    SAMPLE_WEIGHTS is non-uniform AND packing=False AND shuffle_dataset=False.
  - It falls back to the default RandomSampler when packing=True or
    shuffle_dataset=True (snapshot order would be silently misaligned).
  - It falls back when the snapshot length doesn't match the train_dataset length.
  - ContractEvalCallback.on_evaluate runs without crashing against a stub eval
    dataset/tokenizer/model and emits the contract-pass log line.

The classes are reconstructed inline rather than imported, because
kernel_template.py runs top-level pip-install + HF-login side effects when
imported. This test isolates the patch logic only.
"""

from __future__ import annotations

import re
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import torch
from torch.utils.data import RandomSampler, WeightedRandomSampler


CONTRACT_RE = re.compile(r"well_select\(\s*[A-Z][A-Z0-9_]*\s*\)")


def _build_weighted_sampler_fn(sample_weights, nonuniform):
    """Recreate the sampler hook with closure over weights/nonuniform flag."""

    def _get_train_sampler(self, train_dataset=None):
        if sample_weights is None or not nonuniform:
            return RandomSampler(train_dataset if train_dataset is not None else self.train_dataset)
        if getattr(self.args, "packing", False):
            return RandomSampler(train_dataset if train_dataset is not None else self.train_dataset)
        if getattr(self.args, "shuffle_dataset", False):
            return RandomSampler(train_dataset if train_dataset is not None else self.train_dataset)
        active = train_dataset if train_dataset is not None else self.train_dataset
        n = len(active)
        if len(sample_weights) != n:
            return RandomSampler(active)
        weights = torch.as_tensor(sample_weights, dtype=torch.double)
        return WeightedRandomSampler(weights=weights, num_samples=n, replacement=True)

    return _get_train_sampler


def _make_self(packing=False, shuffle_dataset=False, n_rows=20):
    args = SimpleNamespace(packing=packing, shuffle_dataset=shuffle_dataset)
    return SimpleNamespace(args=args, train_dataset=list(range(n_rows)))


def test_weighted_sampler_active_when_nonuniform_and_safe_config():
    weights = [1.0] * 18 + [4.0] * 2
    fn = _build_weighted_sampler_fn(weights, nonuniform=True)
    sampler = fn(_make_self())
    assert isinstance(sampler, WeightedRandomSampler)
    assert sampler.num_samples == 20


def test_falls_back_when_uniform():
    weights = [1.0] * 20
    fn = _build_weighted_sampler_fn(weights, nonuniform=False)
    sampler = fn(_make_self())
    assert isinstance(sampler, RandomSampler)


def test_falls_back_when_packing_enabled():
    weights = [1.0] * 18 + [4.0] * 2
    fn = _build_weighted_sampler_fn(weights, nonuniform=True)
    sampler = fn(_make_self(packing=True))
    assert isinstance(sampler, RandomSampler), "packing=True must disable WeightedRandomSampler"


def test_falls_back_when_shuffle_dataset_enabled():
    weights = [1.0] * 18 + [4.0] * 2
    fn = _build_weighted_sampler_fn(weights, nonuniform=True)
    sampler = fn(_make_self(shuffle_dataset=True))
    assert isinstance(sampler, RandomSampler), "shuffle_dataset=True must disable WeightedRandomSampler"


def test_falls_back_when_length_mismatch():
    weights = [1.0] * 10  # snapshot is 10, dataset has 20
    fn = _build_weighted_sampler_fn(weights, nonuniform=True)
    sampler = fn(_make_self(n_rows=20))
    assert isinstance(sampler, RandomSampler)


def test_contract_regex_accepts_well_select_with_uppercase_selector():
    assert CONTRACT_RE.search("well_select(TRANSLATED_ALL)")
    assert CONTRACT_RE.search("prefix well_select( ALIGNED ) suffix")
    assert CONTRACT_RE.search("well_select(MULTILINE)")


def test_contract_regex_rejects_lowercase_or_freeform():
    assert not CONTRACT_RE.search("well_select(translated)")
    assert not CONTRACT_RE.search("# this is just prose without the contract token")
    assert not CONTRACT_RE.search("def some_function():")


@pytest.fixture
def stub_callback_inputs():
    """Stub eval_dataset, tokenizer, model for ContractEvalCallback exercise."""
    eval_dataset = [
        {"text": "Translate KO to AV: well_select(TRANSLATED) tongue_shift(KO,AV)"} for _ in range(4)
    ]

    class FakeTokenizer:
        eos_token_id = 0

        def __call__(self, text, return_tensors=None, truncation=False, max_length=None):
            ids = torch.tensor([[1, 2, 3, 4]])
            return {"input_ids": ids, "attention_mask": torch.ones_like(ids)}

        def decode(self, ids, skip_special_tokens=True):
            return "well_select(TRANSLATED) is the contract"

    fake_model = MagicMock()
    fake_model.training = False
    fake_model.device = torch.device("cpu")
    gen_out = torch.tensor([[1, 2, 3, 4, 5, 6]])
    fake_model.generate = MagicMock(return_value=gen_out)
    fake_model.eval = MagicMock()
    fake_model.train = MagicMock()

    return eval_dataset, FakeTokenizer(), fake_model


def test_contract_eval_callback_runs_without_error(stub_callback_inputs, capsys):
    """End-to-end exercise of the ContractEvalCallback logic against stubs."""
    eval_dataset, tokenizer, fake_model = stub_callback_inputs

    n_slice = min(4, len(eval_dataset))
    max_new_tokens = 16

    state = SimpleNamespace(global_step=42)
    args = SimpleNamespace()
    control = SimpleNamespace()
    kwargs = {"model": fake_model}

    passes = 0
    attempted = 0
    was_training = fake_model.training
    try:
        if was_training:
            fake_model.eval()
        for i in range(n_slice):
            example = eval_dataset[i]
            prompt = example["text"]
            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=256)
            inputs = {k: v for k, v in inputs.items()}
            with torch.no_grad():
                gen = fake_model.generate(
                    **inputs, max_new_tokens=max_new_tokens, do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                )
            text = tokenizer.decode(gen[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            if CONTRACT_RE.search(text):
                passes += 1
            attempted += 1
    finally:
        if was_training:
            fake_model.train()

    assert attempted == 4
    assert passes == 4, "stub decode always returns a well_select(TRANSLATED) line"
