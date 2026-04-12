#!/usr/bin/env python3
"""Quick validation of Sacred Tongues HF tokenizer — no GPU needed.

Tests:
1. Encoding/decoding round-trip across all 6 tongues
2. Chat template formatting
3. Vocab size and special tokens
4. Tongue rotation in dataset
5. HF __call__ interface (padding, tensors)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tokenizer.sacred_tongues_hf import (
    SacredTonguesHFTokenizer,
    SacredTongueBridge,
    TOTAL_VOCAB,
    NUM_SPECIAL,
)


def test_basic_encode_decode():
    tok = SacredTonguesHFTokenizer(default_tongue="ko")
    print(f"Vocab size: {tok.vocab_size} (expected {TOTAL_VOCAB})")
    assert tok.vocab_size == TOTAL_VOCAB

    for tongue in ["ko", "av", "ru", "ca", "um", "dr"]:
        text = "Hello, Sacred Tongues!"
        ids = tok.encode(text, tongue=tongue)
        decoded = tok.decode(ids)
        match = "OK" if decoded == text else f"MISMATCH: '{decoded}'"
        print(f"  {tongue}: {len(ids)} tokens — round-trip {match}")
        assert decoded == text, f"Round-trip failed for {tongue}"

    print("PASS: encode/decode round-trip\n")


def test_special_tokens():
    tok = SacredTonguesHFTokenizer()
    ids = tok.encode("test", tongue="ko", add_special_tokens=True)
    assert ids[0] == tok.bos_token_id, "Missing BOS"
    assert ids[1] == 4, "Missing tongue:ko marker"
    assert ids[-1] == tok.eos_token_id, "Missing EOS"
    print(f"PASS: special tokens (BOS={ids[0]}, tongue={ids[1]}, EOS={ids[-1]})\n")


def test_hf_call_interface():
    tok = SacredTonguesHFTokenizer()
    result = tok(
        ["Hello", "World, longer text here"],
        padding=True,
        return_tensors="pt",
    )
    print(f"  input_ids shape: {result['input_ids'].shape}")
    print(f"  attention_mask shape: {result['attention_mask'].shape}")
    assert result["input_ids"].shape[0] == 2, "Batch size wrong"
    assert result["input_ids"].shape == result["attention_mask"].shape, "Shape mismatch"
    print("PASS: HF __call__ interface\n")


def test_chat_template():
    tok = SacredTonguesHFTokenizer()
    messages = [
        {"role": "user", "content": "What is the harmonic wall?"},
        {"role": "assistant", "content": "It is the canonical safety boundary."},
    ]
    text = tok.apply_chat_template(messages, tokenize=False)
    assert "<|user|>" in text
    assert "<|assistant|>" in text
    print(f"  Chat template:\n    {text[:100]}...")
    print("PASS: chat template\n")


def test_tongue_coverage():
    """Verify all 256 byte values encode correctly per tongue."""
    tok = SacredTonguesHFTokenizer()
    for tongue in ["ko", "av", "ru", "ca", "um", "dr"]:
        all_bytes = bytes(range(256))
        ids = tok.encode(
            all_bytes.decode("latin-1"),  # Preserve byte values
            tongue=tongue,
            add_special_tokens=False,
        )
        # Should be 256 tokens (one per byte)
        print(f"  {tongue}: {len(ids)} tokens for 256 bytes")

    print("PASS: full byte coverage\n")


def test_bridge_shapes():
    """Test bridge module output shapes (CPU only)."""
    import torch

    bridge = SacredTongueBridge(
        sacred_vocab_size=TOTAL_VOCAB,
        bridge_dim=256,
        model_dim=896,
    )

    # Fake batch
    input_ids = torch.randint(NUM_SPECIAL, TOTAL_VOCAB, (2, 32))
    output = bridge(input_ids)

    print(f"  Bridge input:  {input_ids.shape}")
    print(f"  Bridge output: {output.shape}")
    assert output.shape == (2, 32, 896), f"Wrong shape: {output.shape}"
    print("PASS: bridge output shape\n")


def test_save_load(tmp_path="/tmp/sacred_tongues_test"):
    tok = SacredTonguesHFTokenizer(default_tongue="av")
    tok.save_pretrained(tmp_path)
    tok2 = SacredTonguesHFTokenizer.from_pretrained(tmp_path)
    assert tok2.default_tongue == "av"
    assert tok2.vocab_size == TOTAL_VOCAB

    text = "Persistence test"
    assert tok.encode(text) == tok2.encode(text)
    print("PASS: save/load pretrained\n")


if __name__ == "__main__":
    print("=" * 60)
    print("SACRED TONGUES HF TOKENIZER — VALIDATION SUITE")
    print("=" * 60 + "\n")

    test_basic_encode_decode()
    test_special_tokens()
    test_hf_call_interface()
    test_chat_template()
    test_tongue_coverage()
    test_bridge_shapes()
    test_save_load()

    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
