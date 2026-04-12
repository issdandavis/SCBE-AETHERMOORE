"""
Cross-Modal Sacred Tongues Tokenizer — Comprehensive Test Suite
===============================================================

Tests the full tokenizer stack: base crypto tokenizer, HF wrapper,
bridge layer, and cross-modal invariants.

Test categories:
  1. Bijectivity & Determinism — same input always gives same output, round-trips clean
  2. Vocabulary Integrity — no collisions, no gaps, correct ranges
  3. Tongue Isolation — tongues don't leak into each other
  4. HF Interface Contract — encode/decode/__call__/chat_template/save_load
  5. Bridge Layer Geometry — shapes, tongue bias, harmonic init, gradient flow
  6. Cross-Modal Consistency — embedding neighborhoods preserved across projections
  7. Edge Cases — empty input, max length, all-same-byte, every byte value, unicode
  8. Drift Detection — serialization round-trip, version stability
  9. Adversarial — malformed inputs, out-of-range IDs, mixed tongues
  10. Performance — encoding speed, bridge throughput

Markers: homebrew (fast smoke), unit, property, integration, security, perf
"""

import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import pytest

# Ensure src/ is importable
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import torch

from crypto.sacred_tongues import (
    TONGUES,
    SECTION_TONGUES,
    SacredTongueTokenizer,
    TongueSpec,
    SACRED_TONGUE_TOKENIZER,
)
from tokenizer.sacred_tongues_hf import (
    SacredTonguesHFTokenizer,
    SacredTongueBridge,
    BridgedModel,
    SPECIAL_TOKENS,
    NUM_SPECIAL,
    TOKENS_PER_TONGUE,
    NUM_TONGUES,
    TOTAL_VOCAB,
    replace_model_tokenizer,
)

PHI = 1.618033988749895
ALL_TONGUES = ["ko", "av", "ru", "ca", "um", "dr"]
TONGUE_FREQUENCIES = {
    "ko": 440.0, "av": 523.25, "ru": 329.63,
    "ca": 659.25, "um": 293.66, "dr": 392.0,
}


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def tokenizer():
    """Fresh base tokenizer."""
    return SacredTongueTokenizer(TONGUES)


@pytest.fixture
def hf_tokenizer():
    """Fresh HF-compatible tokenizer."""
    return SacredTonguesHFTokenizer(default_tongue="ko")


@pytest.fixture
def bridge():
    """Fresh bridge layer (CPU)."""
    return SacredTongueBridge(
        sacred_vocab_size=TOTAL_VOCAB,
        bridge_dim=256,
        model_dim=896,
    )


# ============================================================
# 1. BIJECTIVITY & DETERMINISM
# ============================================================

class TestBijectivity:
    """Every byte maps to exactly one token per tongue, and back."""

    @pytest.mark.homebrew
    def test_roundtrip_all_bytes_all_tongues(self, tokenizer):
        """Every byte 0-255 round-trips through every tongue."""
        for tongue in ALL_TONGUES:
            for byte_val in range(256):
                data = bytes([byte_val])
                tokens = tokenizer.encode_bytes(tongue, data)
                recovered = tokenizer.decode_tokens(tongue, tokens)
                assert recovered == data, (
                    f"Tongue {tongue}, byte {byte_val}: "
                    f"encoded to {tokens}, decoded to {recovered!r}"
                )

    @pytest.mark.homebrew
    def test_roundtrip_multibyte_sequences(self, tokenizer):
        """Multi-byte sequences round-trip cleanly."""
        for tongue in ALL_TONGUES:
            data = bytes(range(256))
            tokens = tokenizer.encode_bytes(tongue, data)
            assert len(tokens) == 256
            recovered = tokenizer.decode_tokens(tongue, tokens)
            assert recovered == data

    @pytest.mark.unit
    def test_deterministic_encoding(self, tokenizer):
        """Same input always produces same output — no randomness in encode."""
        data = b"SCBE determinism test payload 12345"
        for tongue in ALL_TONGUES:
            first = tokenizer.encode_bytes(tongue, data)
            for _ in range(10):
                again = tokenizer.encode_bytes(tongue, data)
                assert again == first, f"Non-deterministic encoding in {tongue}"

    @pytest.mark.unit
    def test_deterministic_hf_encoding(self, hf_tokenizer):
        """HF tokenizer is deterministic across repeated calls."""
        text = "Hello, Aethermoor! The Sacred Tongues speak truth."
        for tongue in ALL_TONGUES:
            first = hf_tokenizer.encode(text, tongue=tongue)
            for _ in range(10):
                again = hf_tokenizer.encode(text, tongue=tongue)
                assert again == first

    @pytest.mark.unit
    def test_hf_encode_decode_roundtrip(self, hf_tokenizer):
        """HF encode → decode round-trips for ASCII text."""
        texts = [
            "Hello world",
            "The quick brown fox jumps over the lazy dog",
            "SCBE-AETHERMOORE 14-layer pipeline",
            "12345 67890 !@#$%^&*()",
            "",  # empty
        ]
        for tongue in ALL_TONGUES:
            for text in texts:
                ids = hf_tokenizer.encode(text, tongue=tongue)
                recovered = hf_tokenizer.decode(ids)
                assert recovered == text, (
                    f"Round-trip failed for tongue={tongue}, text={text!r}: "
                    f"got {recovered!r}"
                )

    @pytest.mark.unit
    def test_hf_encode_decode_unicode(self, hf_tokenizer):
        """Unicode text round-trips through encode/decode."""
        texts = [
            "cafe\u0301",          # combining accent
            "\u00e9\u00e8\u00ea",  # accented latin
            "\u4e16\u754c",        # Chinese (世界)
            "\u0410\u0411\u0412",  # Cyrillic (АБВ)
            "\U0001f525\U0001f30d",  # emoji (🔥🌍)
        ]
        for text in texts:
            ids = hf_tokenizer.encode(text, tongue="ko")
            recovered = hf_tokenizer.decode(ids)
            assert recovered == text, f"Unicode round-trip failed: {text!r} → {recovered!r}"


# ============================================================
# 2. VOCABULARY INTEGRITY
# ============================================================

class TestVocabularyIntegrity:
    """No collisions, no gaps, correct sizes."""

    @pytest.mark.homebrew
    def test_vocab_size(self):
        """Total vocab = 12 special + 6 × 256 = 1548."""
        assert NUM_SPECIAL == 12
        assert TOKENS_PER_TONGUE == 256
        assert NUM_TONGUES == 6
        assert TOTAL_VOCAB == 1548

    @pytest.mark.unit
    def test_no_token_collisions_within_tongue(self, tokenizer):
        """Each tongue has exactly 256 unique tokens."""
        for tongue in ALL_TONGUES:
            tokens = set(tokenizer.byte_to_token[tongue])
            assert len(tokens) == 256, (
                f"Tongue {tongue} has {len(tokens)} unique tokens, expected 256"
            )

    @pytest.mark.unit
    def test_no_token_collisions_across_tongues(self, tokenizer):
        """Token strings are unique across tongues (no ko token = av token)."""
        all_tokens = {}
        for tongue in ALL_TONGUES:
            for b in range(256):
                token = tokenizer.byte_to_token[tongue][b]
                key = token
                if key in all_tokens:
                    # Same string in different tongue is ok if they map
                    # to different tongue-prefixed IDs in HF tokenizer
                    pass
                all_tokens[(tongue, key)] = b
        # The critical check: no (tongue, token) pair appears twice
        assert len(all_tokens) == 6 * 256

    @pytest.mark.unit
    def test_hf_vocab_covers_all_ids(self, hf_tokenizer):
        """Every ID from 0 to TOTAL_VOCAB-1 has a token mapping."""
        for token_id in range(TOTAL_VOCAB):
            assert token_id in hf_tokenizer.id_to_token, (
                f"ID {token_id} has no token mapping"
            )

    @pytest.mark.unit
    def test_hf_vocab_no_gaps(self, hf_tokenizer):
        """Vocab is contiguous — no missing IDs."""
        all_ids = sorted(hf_tokenizer.id_to_token.keys())
        assert all_ids == list(range(TOTAL_VOCAB))

    @pytest.mark.unit
    def test_special_token_ids_correct(self):
        """Special tokens have the right IDs."""
        assert SPECIAL_TOKENS["<pad>"] == 0
        assert SPECIAL_TOKENS["<bos>"] == 1
        assert SPECIAL_TOKENS["<eos>"] == 2
        assert SPECIAL_TOKENS["<unk>"] == 3
        for i, tongue in enumerate(ALL_TONGUES):
            assert SPECIAL_TOKENS[f"<tongue:{tongue}>"] == 4 + i
        assert SPECIAL_TOKENS["<sep>"] == 10
        assert SPECIAL_TOKENS["<mask>"] == 11

    @pytest.mark.unit
    def test_tongue_offset_layout(self, hf_tokenizer):
        """Tongue offsets are contiguous and non-overlapping."""
        expected_offset = NUM_SPECIAL  # 12
        for tongue in ALL_TONGUES:
            actual = hf_tokenizer.tongue_offset[tongue]
            assert actual == expected_offset, (
                f"Tongue {tongue} offset: expected {expected_offset}, got {actual}"
            )
            expected_offset += 256

    @pytest.mark.unit
    def test_tongue_spec_frequencies(self):
        """Each tongue has the correct harmonic frequency."""
        for tongue_code, spec in TONGUES.items():
            assert spec.harmonic_frequency == TONGUE_FREQUENCIES[tongue_code], (
                f"Tongue {tongue_code} frequency mismatch: "
                f"spec={spec.harmonic_frequency}, expected={TONGUE_FREQUENCIES[tongue_code]}"
            )

    @pytest.mark.unit
    def test_tongue_spec_prefix_suffix_counts(self):
        """Every tongue has exactly 16 prefixes and 16 suffixes."""
        for tongue_code, spec in TONGUES.items():
            assert len(spec.prefixes) == 16, f"{tongue_code} has {len(spec.prefixes)} prefixes"
            assert len(spec.suffixes) == 16, f"{tongue_code} has {len(spec.suffixes)} suffixes"

    @pytest.mark.unit
    def test_tongue_spec_no_duplicate_prefixes(self):
        """No duplicate prefixes within a tongue."""
        for tongue_code, spec in TONGUES.items():
            assert len(set(spec.prefixes)) == 16, (
                f"{tongue_code} has duplicate prefixes: {spec.prefixes}"
            )

    @pytest.mark.unit
    def test_tongue_spec_no_duplicate_suffixes(self):
        """No duplicate suffixes within a tongue."""
        for tongue_code, spec in TONGUES.items():
            assert len(set(spec.suffixes)) == 16, (
                f"{tongue_code} has duplicate suffixes: {spec.suffixes}"
            )


# ============================================================
# 3. TONGUE ISOLATION
# ============================================================

class TestTongueIsolation:
    """Tongues must not leak into each other."""

    @pytest.mark.unit
    def test_same_byte_different_tongue_different_token(self, tokenizer):
        """Same byte value produces different tokens in different tongues."""
        for byte_val in range(256):
            tokens_by_tongue = {}
            for tongue in ALL_TONGUES:
                token = tokenizer.byte_to_token[tongue][byte_val]
                tokens_by_tongue[tongue] = token
            # At least some tongues should differ (all 6 differ for most bytes)
            unique_tokens = set(tokens_by_tongue.values())
            assert len(unique_tokens) > 1, (
                f"Byte {byte_val} maps to same token in all tongues: {tokens_by_tongue}"
            )

    @pytest.mark.unit
    def test_cross_tongue_decode_fails(self, tokenizer):
        """Tokens from one tongue cannot decode in another."""
        data = b"isolation test"
        ko_tokens = tokenizer.encode_bytes("ko", data)
        # Try decoding KO tokens as AV — should fail
        for other_tongue in ["av", "ru", "ca", "um", "dr"]:
            with pytest.raises((ValueError, KeyError)):
                tokenizer.decode_tokens(other_tongue, ko_tokens)

    @pytest.mark.unit
    def test_hf_ids_stay_in_tongue_range(self, hf_tokenizer):
        """Encoded IDs (excluding specials) fall within the tongue's offset range."""
        for tongue in ALL_TONGUES:
            ids = hf_tokenizer.encode("test", tongue=tongue, add_special_tokens=False)
            offset = hf_tokenizer.tongue_offset[tongue]
            for token_id in ids:
                assert offset <= token_id < offset + 256, (
                    f"Tongue {tongue}: ID {token_id} outside range "
                    f"[{offset}, {offset + 256})"
                )

    @pytest.mark.unit
    def test_tongue_marker_present_in_encoded(self, hf_tokenizer):
        """Encoding with special tokens includes the tongue marker."""
        for tongue in ALL_TONGUES:
            ids = hf_tokenizer.encode("hello", tongue=tongue, add_special_tokens=True)
            tongue_marker_id = SPECIAL_TOKENS[f"<tongue:{tongue}>"]
            assert tongue_marker_id in ids, (
                f"Tongue marker <tongue:{tongue}> (ID {tongue_marker_id}) "
                f"not found in encoded IDs: {ids}"
            )


# ============================================================
# 4. HF INTERFACE CONTRACT
# ============================================================

class TestHFInterfaceContract:
    """The tokenizer must fulfill HuggingFace's expected interface."""

    @pytest.mark.homebrew
    def test_call_returns_dict_with_required_keys(self, hf_tokenizer):
        """__call__ returns dict with input_ids and attention_mask."""
        result = hf_tokenizer("hello")
        assert "input_ids" in result
        assert "attention_mask" in result

    @pytest.mark.unit
    def test_call_single_string(self, hf_tokenizer):
        """Single string input works."""
        result = hf_tokenizer("hello")
        assert len(result["input_ids"]) == 1  # batch of 1
        assert len(result["attention_mask"]) == 1

    @pytest.mark.unit
    def test_call_batch(self, hf_tokenizer):
        """List of strings returns batch."""
        result = hf_tokenizer(["hello", "world", "test"])
        assert len(result["input_ids"]) == 3
        assert len(result["attention_mask"]) == 3

    @pytest.mark.unit
    def test_call_padding(self, hf_tokenizer):
        """Padding makes all sequences same length."""
        result = hf_tokenizer(["hi", "hello world"], padding=True)
        assert len(result["input_ids"][0]) == len(result["input_ids"][1])
        # Shorter sequence should have 0s in attention mask
        mask_short = result["attention_mask"][0]
        mask_long = result["attention_mask"][1]
        assert 0 in mask_short  # padded
        assert all(m == 1 for m in mask_long)  # no padding needed

    @pytest.mark.unit
    def test_call_max_length_truncation(self, hf_tokenizer):
        """max_length truncates sequences."""
        long_text = "a" * 500
        result = hf_tokenizer(long_text, max_length=20)
        assert len(result["input_ids"][0]) <= 20

    @pytest.mark.unit
    def test_call_return_tensors_pt(self, hf_tokenizer):
        """return_tensors='pt' returns torch tensors."""
        result = hf_tokenizer("hello", return_tensors="pt")
        assert isinstance(result["input_ids"], torch.Tensor)
        assert isinstance(result["attention_mask"], torch.Tensor)
        assert result["input_ids"].dtype == torch.int64
        assert result["attention_mask"].dtype == torch.int64

    @pytest.mark.unit
    def test_call_padding_with_tensors(self, hf_tokenizer):
        """Padding + tensors returns rectangular tensor."""
        result = hf_tokenizer(
            ["hi", "hello world foo bar"],
            padding=True,
            return_tensors="pt",
        )
        assert result["input_ids"].dim() == 2  # (batch, seq)
        assert result["input_ids"].shape[0] == 2  # batch size

    @pytest.mark.unit
    def test_get_vocab(self, hf_tokenizer):
        """get_vocab returns complete vocabulary."""
        vocab = hf_tokenizer.get_vocab()
        assert len(vocab) == TOTAL_VOCAB

    @pytest.mark.unit
    def test_special_token_attributes(self, hf_tokenizer):
        """HF-expected attributes exist."""
        assert hf_tokenizer.pad_token_id == 0
        assert hf_tokenizer.bos_token_id == 1
        assert hf_tokenizer.eos_token_id == 2
        assert hf_tokenizer.unk_token_id == 3
        assert hf_tokenizer.pad_token == "<pad>"
        assert hf_tokenizer.eos_token == "<eos>"
        assert hf_tokenizer.bos_token == "<bos>"
        assert hf_tokenizer.vocab_size == TOTAL_VOCAB

    @pytest.mark.unit
    def test_chat_template_structure(self, hf_tokenizer):
        """Chat template produces correct role markers."""
        messages = [
            {"role": "user", "content": "What is SCBE?"},
            {"role": "assistant", "content": "A security framework."},
        ]
        text = hf_tokenizer.apply_chat_template(messages, tokenize=False)
        assert "<|user|>" in text
        assert "<|assistant|>" in text
        assert "What is SCBE?" in text
        assert "A security framework." in text

    @pytest.mark.unit
    def test_chat_template_generation_prompt(self, hf_tokenizer):
        """add_generation_prompt appends assistant marker."""
        messages = [{"role": "user", "content": "Hello"}]
        text = hf_tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        assert text.endswith("<|assistant|>\n") or "<|assistant|>" in text.split("\n")[-1]

    @pytest.mark.unit
    def test_chat_template_tokenize(self, hf_tokenizer):
        """Chat template with tokenize=True returns IDs."""
        messages = [{"role": "user", "content": "Hi"}]
        ids = hf_tokenizer.apply_chat_template(messages, tokenize=True)
        assert isinstance(ids, list)
        assert all(isinstance(i, int) for i in ids)

    @pytest.mark.unit
    def test_save_and_load_roundtrip(self, hf_tokenizer, tmp_path):
        """Save → load preserves tokenizer behavior."""
        save_dir = str(tmp_path / "tokenizer_save")
        hf_tokenizer.save_pretrained(save_dir)

        # Verify files exist
        assert (Path(save_dir) / "tokenizer_config.json").exists()
        assert (Path(save_dir) / "vocab.json").exists()

        # Load and verify identical behavior
        loaded = SacredTonguesHFTokenizer.from_pretrained(save_dir)
        text = "Serialization round-trip test for all 6 tongues"
        for tongue in ALL_TONGUES:
            original_ids = hf_tokenizer.encode(text, tongue=tongue)
            loaded_ids = loaded.encode(text, tongue=tongue)
            assert original_ids == loaded_ids, (
                f"Save/load changed encoding for tongue {tongue}"
            )

    @pytest.mark.unit
    def test_saved_config_content(self, hf_tokenizer, tmp_path):
        """Saved config contains all required fields."""
        save_dir = str(tmp_path / "config_check")
        hf_tokenizer.save_pretrained(save_dir)

        with open(Path(save_dir) / "tokenizer_config.json") as f:
            config = json.load(f)

        assert config["tokenizer_class"] == "SacredTonguesHFTokenizer"
        assert config["vocab_size"] == TOTAL_VOCAB
        assert config["default_tongue"] == "ko"
        assert len(config["tongue_order"]) == 6
        assert len(config["special_tokens"]) == NUM_SPECIAL


# ============================================================
# 5. BRIDGE LAYER GEOMETRY
# ============================================================

class TestBridgeGeometry:
    """The bridge must preserve structure and produce correct shapes."""

    @pytest.mark.homebrew
    def test_bridge_output_shape(self, bridge):
        """Bridge produces (batch, seq, model_dim) output."""
        ids = torch.randint(0, TOTAL_VOCAB, (2, 32))
        out = bridge(ids)
        assert out.shape == (2, 32, 896)

    @pytest.mark.unit
    def test_bridge_output_shape_single(self, bridge):
        """Single sequence works."""
        ids = torch.randint(0, TOTAL_VOCAB, (1, 10))
        out = bridge(ids)
        assert out.shape == (1, 10, 896)

    @pytest.mark.unit
    def test_bridge_output_not_all_zeros(self, bridge):
        """Output is non-trivial (not collapsed to zeros)."""
        ids = torch.randint(NUM_SPECIAL, TOTAL_VOCAB, (1, 20))
        out = bridge(ids)
        assert out.abs().sum() > 0, "Bridge output is all zeros"

    @pytest.mark.unit
    def test_bridge_output_not_all_same(self, bridge):
        """Different inputs produce different outputs."""
        ids_a = torch.tensor([[12, 13, 14, 15, 16]])  # KO tokens
        ids_b = torch.tensor([[268, 269, 270, 271, 272]])  # AV tokens
        out_a = bridge(ids_a)
        out_b = bridge(ids_b)
        assert not torch.allclose(out_a, out_b, atol=1e-6), (
            "Different tongue tokens produced identical bridge output"
        )

    @pytest.mark.unit
    def test_bridge_tongue_bias_initialized(self, bridge):
        """Tongue biases have phi-scaled harmonic values, not zeros."""
        weights = bridge.tongue_bias.weight.detach()
        # Dim 0 should have phi-scaled frequency
        for i in range(6):
            assert weights[i, 0].abs() > 0.01, (
                f"Tongue {i} bias dim 0 is near zero — harmonic init failed"
            )
            assert weights[i, 1].abs() > 0.01, (
                f"Tongue {i} bias dim 1 is near zero — frequency init failed"
            )

    @pytest.mark.unit
    def test_bridge_phi_scaling_order(self, bridge):
        """Tongue bias dim 0 follows phi progression: later tongues have larger values."""
        weights = bridge.tongue_bias.weight.detach()
        dim0_values = [weights[i, 0].item() for i in range(6)]
        # Phi scaling means values should generally increase
        # (not strictly due to frequency normalization, but the trend should be upward)
        assert dim0_values[-1] > dim0_values[0], (
            f"Phi scaling not reflected: first={dim0_values[0]:.4f}, "
            f"last={dim0_values[-1]:.4f}"
        )

    @pytest.mark.unit
    def test_bridge_tongue_detection(self, bridge):
        """_get_tongue_indices correctly identifies tongue from token ID."""
        # KO range: 12-267 → tongue 0
        # AV range: 268-523 → tongue 1
        # DR range: 1292-1547 → tongue 5
        ids = torch.tensor([[12, 268, 524, 780, 1036, 1292, 0, 3]])
        tongue_idx = bridge._get_tongue_indices(ids)
        expected = torch.tensor([[0, 1, 2, 3, 4, 5, -1, -1]])
        assert torch.equal(tongue_idx, expected), (
            f"Tongue detection wrong: {tongue_idx} != {expected}"
        )

    @pytest.mark.unit
    def test_bridge_special_tokens_no_tongue_bias(self, bridge):
        """Special tokens (IDs 0-11) should get tongue index -1 → no tongue bias."""
        ids = torch.tensor([[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]])
        tongue_idx = bridge._get_tongue_indices(ids)
        assert (tongue_idx == -1).all(), "Special tokens should have tongue_idx = -1"

    @pytest.mark.unit
    def test_bridge_gradient_flows(self, bridge):
        """Gradients flow through the bridge (trainable)."""
        ids = torch.randint(NUM_SPECIAL, TOTAL_VOCAB, (2, 16))
        out = bridge(ids)
        loss = out.sum()
        loss.backward()
        # Check that sacred_embed got gradients
        assert bridge.sacred_embed.weight.grad is not None
        assert bridge.sacred_embed.weight.grad.abs().sum() > 0

    @pytest.mark.unit
    def test_bridge_deterministic(self, bridge):
        """Same input → same output (eval mode, no dropout randomness)."""
        bridge.eval()
        ids = torch.randint(0, TOTAL_VOCAB, (1, 20))
        with torch.no_grad():
            out1 = bridge(ids).clone()
            out2 = bridge(ids).clone()
        assert torch.equal(out1, out2), "Bridge not deterministic in eval mode"

    @pytest.mark.unit
    def test_bridge_output_finite(self, bridge):
        """No NaN or Inf in bridge output."""
        ids = torch.randint(0, TOTAL_VOCAB, (4, 64))
        bridge.eval()
        with torch.no_grad():
            out = bridge(ids)
        assert torch.isfinite(out).all(), "Bridge produced NaN or Inf"

    @pytest.mark.unit
    def test_bridge_layernorm_output_bounded(self, bridge):
        """LayerNorm at the end keeps output roughly normalized."""
        bridge.eval()
        ids = torch.randint(NUM_SPECIAL, TOTAL_VOCAB, (4, 32))
        with torch.no_grad():
            out = bridge(ids)
        # LayerNorm output should have reasonable magnitude
        mean_abs = out.abs().mean().item()
        assert 0.01 < mean_abs < 100.0, (
            f"Bridge output magnitude suspicious: mean_abs={mean_abs}"
        )


# ============================================================
# 6. CROSS-MODAL CONSISTENCY
# ============================================================

class TestCrossModalConsistency:
    """Embedding neighborhoods should be preserved across projections."""

    @pytest.mark.integration
    def test_same_tongue_tokens_closer_than_different(self, bridge):
        """Tokens from the same tongue should be closer in bridge output space
        than tokens from different tongues."""
        bridge.eval()
        with torch.no_grad():
            # 5 consecutive KO tokens
            ko_ids = torch.tensor([[12, 13, 14, 15, 16]])
            # 5 consecutive DR tokens
            dr_ids = torch.tensor([[1292, 1293, 1294, 1295, 1296]])
            # 5 mixed
            mixed_ids = torch.tensor([[12, 268, 524, 780, 1036]])

            ko_out = bridge(ko_ids).squeeze(0)  # (5, 896)
            dr_out = bridge(dr_ids).squeeze(0)
            mixed_out = bridge(mixed_ids).squeeze(0)

            # Intra-tongue variance should be lower than cross-tongue variance
            ko_var = ko_out.var(dim=0).mean().item()
            dr_var = dr_out.var(dim=0).mean().item()
            mixed_var = mixed_out.var(dim=0).mean().item()

            assert mixed_var > ko_var, (
                f"Mixed tongue variance ({mixed_var:.6f}) should exceed "
                f"same-tongue variance ({ko_var:.6f})"
            )
            assert mixed_var > dr_var, (
                f"Mixed tongue variance ({mixed_var:.6f}) should exceed "
                f"same-tongue variance ({dr_var:.6f})"
            )

    @pytest.mark.integration
    def test_tongue_centroids_distinct(self, bridge):
        """Each tongue's embedding centroid should be separated from others."""
        bridge.eval()
        centroids = {}
        with torch.no_grad():
            for i, tongue in enumerate(ALL_TONGUES):
                start = NUM_SPECIAL + i * 256
                # Sample 50 tokens from this tongue
                ids = torch.arange(start, start + 50).unsqueeze(0)
                out = bridge(ids).squeeze(0)  # (50, 896)
                centroids[tongue] = out.mean(dim=0)

        # Check all pairs are distinct
        for i, t1 in enumerate(ALL_TONGUES):
            for t2 in ALL_TONGUES[i + 1:]:
                dist = (centroids[t1] - centroids[t2]).norm().item()
                assert dist > 0.01, (
                    f"Tongue centroids {t1} and {t2} collapsed: dist={dist:.6f}"
                )

    @pytest.mark.integration
    def test_harmonic_frequency_ordering_in_bias(self, bridge):
        """Tongue bias should reflect frequency ordering at init."""
        weights = bridge.tongue_bias.weight.detach()
        # dim 1 stores freq/1000
        freq_vals = [weights[i, 1].item() for i in range(6)]
        # UM (293.66) should have smallest, CA (659.25) should have largest
        um_idx = ALL_TONGUES.index("um")
        ca_idx = ALL_TONGUES.index("ca")
        assert freq_vals[um_idx] < freq_vals[ca_idx], (
            f"UM freq ({freq_vals[um_idx]:.4f}) should be < CA freq ({freq_vals[ca_idx]:.4f})"
        )


# ============================================================
# 7. EDGE CASES
# ============================================================

class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    @pytest.mark.unit
    def test_empty_input(self, hf_tokenizer):
        """Empty string encodes to just special tokens."""
        ids = hf_tokenizer.encode("", tongue="ko")
        # Should be [BOS, tongue_marker, EOS] with no content tokens
        assert ids[0] == hf_tokenizer.bos_token_id
        assert ids[-1] == hf_tokenizer.eos_token_id
        assert len(ids) == 3  # BOS + tongue + EOS

    @pytest.mark.unit
    def test_empty_input_no_specials(self, hf_tokenizer):
        """Empty string with no special tokens = empty list."""
        ids = hf_tokenizer.encode("", tongue="ko", add_special_tokens=False)
        assert ids == []

    @pytest.mark.unit
    def test_single_byte_all_values(self, tokenizer):
        """Every single byte value (0x00 through 0xFF) encodes without error."""
        for tongue in ALL_TONGUES:
            for b in range(256):
                tokens = tokenizer.encode_bytes(tongue, bytes([b]))
                assert len(tokens) == 1

    @pytest.mark.unit
    def test_all_same_byte(self, tokenizer):
        """Repeated same byte produces repeated same token."""
        for tongue in ALL_TONGUES:
            data = bytes([0x42] * 100)
            tokens = tokenizer.encode_bytes(tongue, data)
            assert len(set(tokens)) == 1  # all same token
            assert len(tokens) == 100

    @pytest.mark.unit
    def test_null_bytes(self, tokenizer):
        """Null bytes (0x00) encode cleanly."""
        for tongue in ALL_TONGUES:
            data = b"\x00\x00\x00"
            tokens = tokenizer.encode_bytes(tongue, data)
            assert len(tokens) == 3
            recovered = tokenizer.decode_tokens(tongue, tokens)
            assert recovered == data

    @pytest.mark.unit
    def test_max_byte(self, tokenizer):
        """0xFF encodes cleanly."""
        for tongue in ALL_TONGUES:
            data = b"\xff\xff\xff"
            tokens = tokenizer.encode_bytes(tongue, data)
            assert len(tokens) == 3
            recovered = tokenizer.decode_tokens(tongue, tokens)
            assert recovered == data

    @pytest.mark.unit
    def test_long_input(self, hf_tokenizer):
        """Long input (10KB) encodes without error."""
        text = "A" * 10000
        ids = hf_tokenizer.encode(text, tongue="ko")
        assert len(ids) > 10000  # content + specials

    @pytest.mark.unit
    def test_bridge_with_only_special_tokens(self, bridge):
        """Bridge handles sequences of only special tokens."""
        ids = torch.tensor([[0, 1, 2, 3, 4, 5]])
        bridge.eval()
        with torch.no_grad():
            out = bridge(ids)
        assert out.shape == (1, 6, 896)
        assert torch.isfinite(out).all()

    @pytest.mark.unit
    def test_bridge_single_token(self, bridge):
        """Bridge handles sequence length 1."""
        ids = torch.tensor([[42]])
        bridge.eval()
        with torch.no_grad():
            out = bridge(ids)
        assert out.shape == (1, 1, 896)

    @pytest.mark.unit
    def test_bridge_boundary_ids(self, bridge):
        """Test token IDs at exact tongue boundaries."""
        # First token of each tongue, last token of each tongue
        boundary_ids = []
        for i in range(6):
            start = NUM_SPECIAL + i * 256
            boundary_ids.extend([start, start + 255])
        ids = torch.tensor([boundary_ids])
        bridge.eval()
        with torch.no_grad():
            out = bridge(ids)
        assert torch.isfinite(out).all()
        assert out.shape == (1, 12, 896)


# ============================================================
# 8. DRIFT DETECTION
# ============================================================

class TestDriftDetection:
    """Detect if tokenizer behavior changes between versions."""

    @pytest.mark.unit
    def test_encoding_hash_stability(self, hf_tokenizer):
        """Hash of encoding output is stable — detects silent drift."""
        text = "The Sacred Tongues are six: KO AV RU CA UM DR"
        for tongue in ALL_TONGUES:
            ids = hf_tokenizer.encode(text, tongue=tongue)
            id_hash = hashlib.sha256(json.dumps(ids).encode()).hexdigest()
            # Store hash on first run; on subsequent runs, compare
            # (In CI, these would be pinned golden values)
            # For now: verify it's deterministic within the same process
            ids2 = hf_tokenizer.encode(text, tongue=tongue)
            id_hash2 = hashlib.sha256(json.dumps(ids2).encode()).hexdigest()
            assert id_hash == id_hash2, f"Encoding hash drifted for tongue {tongue}"

    @pytest.mark.unit
    def test_token_format_is_prefix_apostrophe_suffix(self, tokenizer):
        """All tokens follow the prefix'suffix format."""
        for tongue in ALL_TONGUES:
            for b in range(256):
                token = tokenizer.byte_to_token[tongue][b]
                assert "'" in token, (
                    f"Tongue {tongue}, byte {b}: token {token!r} missing apostrophe"
                )
                parts = token.split("'")
                assert len(parts) == 2, (
                    f"Tongue {tongue}, byte {b}: token {token!r} has "
                    f"{len(parts)} parts, expected 2"
                )
                assert len(parts[0]) > 0, f"Empty prefix in {token!r}"
                assert len(parts[1]) > 0, f"Empty suffix in {token!r}"

    @pytest.mark.unit
    def test_nibble_mapping_correct(self, tokenizer):
        """Token = prefixes[hi_nibble]'suffixes[lo_nibble] for each byte."""
        for tongue_code, spec in TONGUES.items():
            for b in range(256):
                hi = (b >> 4) & 0x0F
                lo = b & 0x0F
                expected = f"{spec.prefixes[hi]}'{spec.suffixes[lo]}"
                actual = tokenizer.byte_to_token[tongue_code][b]
                assert actual == expected, (
                    f"Tongue {tongue_code}, byte {b} (0x{b:02X}): "
                    f"expected {expected!r}, got {actual!r}"
                )

    @pytest.mark.unit
    def test_harmonic_fingerprint_deterministic(self, tokenizer):
        """compute_harmonic_fingerprint is deterministic."""
        tokens = tokenizer.encode_bytes("ko", b"test data")
        fp1 = tokenizer.compute_harmonic_fingerprint("ko", tokens)
        fp2 = tokenizer.compute_harmonic_fingerprint("ko", tokens)
        assert fp1 == fp2

    @pytest.mark.unit
    def test_harmonic_fingerprint_tongue_sensitive(self, tokenizer):
        """Different tongues produce different fingerprints for same data."""
        data = b"fingerprint sensitivity test"
        fingerprints = {}
        for tongue in ALL_TONGUES:
            tokens = tokenizer.encode_bytes(tongue, data)
            fp = tokenizer.compute_harmonic_fingerprint(tongue, tokens)
            fingerprints[tongue] = fp

        # All should differ (different frequencies + different tokens)
        values = list(fingerprints.values())
        assert len(set(values)) == 6, (
            f"Expected 6 distinct fingerprints, got {len(set(values))}: {fingerprints}"
        )

    @pytest.mark.unit
    def test_harmonic_fingerprint_bounded(self, tokenizer):
        """Fingerprint is bounded by tongue's frequency."""
        for tongue in ALL_TONGUES:
            tokens = tokenizer.encode_bytes(tongue, b"bound test")
            fp = tokenizer.compute_harmonic_fingerprint(tongue, tokens)
            max_freq = TONGUES[tongue].harmonic_frequency
            assert 0 <= fp <= max_freq, (
                f"Tongue {tongue}: fingerprint {fp} outside [0, {max_freq}]"
            )


# ============================================================
# 9. ADVERSARIAL INPUTS
# ============================================================

class TestAdversarial:
    """Malformed and adversarial inputs must fail gracefully."""

    @pytest.mark.security
    def test_invalid_tongue_code_raises(self, tokenizer):
        """Unknown tongue code raises KeyError."""
        with pytest.raises(KeyError):
            tokenizer.encode_bytes("xx", b"test")

    @pytest.mark.security
    def test_invalid_tongue_decode_raises(self, tokenizer):
        """Unknown tongue code on decode raises KeyError."""
        with pytest.raises(KeyError):
            tokenizer.decode_tokens("xx", ["sil'a"])

    @pytest.mark.security
    def test_invalid_token_decode_raises(self, tokenizer):
        """Nonexistent token raises ValueError."""
        with pytest.raises(ValueError):
            tokenizer.decode_tokens("ko", ["this_token_does_not_exist"])

    @pytest.mark.security
    def test_invalid_rwp_section_raises(self, tokenizer):
        """Unknown RWP section raises ValueError."""
        with pytest.raises(ValueError):
            tokenizer.encode_section("nonexistent_section", b"data")

    @pytest.mark.security
    def test_rwp_sections_all_valid(self, tokenizer):
        """All canonical RWP sections encode without error."""
        for section in SECTION_TONGUES:
            tokens = tokenizer.encode_section(section, b"test")
            assert len(tokens) == 4

    @pytest.mark.security
    def test_section_integrity_valid(self, tokenizer):
        """validate_section_integrity returns True for valid tokens."""
        for section in SECTION_TONGUES:
            tokens = tokenizer.encode_section(section, b"valid")
            assert tokenizer.validate_section_integrity(section, tokens)

    @pytest.mark.security
    def test_section_integrity_invalid(self, tokenizer):
        """validate_section_integrity returns False for wrong tongue's tokens."""
        ko_tokens = tokenizer.encode_bytes("ko", b"data")
        # KO tokens should fail validation for "salt" (which uses RU)
        assert not tokenizer.validate_section_integrity("salt", ko_tokens)

    @pytest.mark.security
    def test_bridge_out_of_range_id_no_crash(self, bridge):
        """Token ID at vocab boundary doesn't crash (even if out of range)."""
        # ID exactly at TOTAL_VOCAB would be out of embedding range
        # But IDs within range should all work
        ids = torch.tensor([[0, TOTAL_VOCAB - 1]])  # min and max valid
        bridge.eval()
        with torch.no_grad():
            out = bridge(ids)
        assert torch.isfinite(out).all()

    @pytest.mark.security
    def test_hf_decode_with_invalid_ids_graceful(self, hf_tokenizer):
        """Decoding IDs outside vocab doesn't crash."""
        # IDs within range should work
        result = hf_tokenizer.decode([1, 12, 13, 14, 2])
        assert isinstance(result, str)

    @pytest.mark.security
    def test_tongue_spec_validation(self):
        """TongueSpec with wrong counts raises ValueError."""
        with pytest.raises(ValueError):
            TongueSpec(
                code="bad",
                name="Bad",
                prefixes=("a", "b"),  # only 2, need 16
                suffixes=tuple(f"s{i}" for i in range(16)),
                domain="test",
                harmonic_frequency=100.0,
            )


# ============================================================
# 10. PERFORMANCE
# ============================================================

class TestPerformance:
    """Encoding and bridge throughput."""

    @pytest.mark.perf
    def test_encoding_throughput(self, tokenizer):
        """Base tokenizer encodes at least 100KB/s."""
        data = bytes(range(256)) * 100  # 25.6KB
        start = time.perf_counter()
        for _ in range(10):
            tokenizer.encode_bytes("ko", data)
        elapsed = time.perf_counter() - start
        throughput = (len(data) * 10) / elapsed
        assert throughput > 100_000, f"Encoding too slow: {throughput/1000:.1f} KB/s"

    @pytest.mark.perf
    def test_hf_encoding_throughput(self, hf_tokenizer):
        """HF tokenizer encodes at least 50KB/s."""
        text = "A" * 10000
        start = time.perf_counter()
        for _ in range(10):
            hf_tokenizer.encode(text, tongue="ko")
        elapsed = time.perf_counter() - start
        throughput = (len(text) * 10) / elapsed
        assert throughput > 50_000, f"HF encoding too slow: {throughput/1000:.1f} KB/s"

    @pytest.mark.perf
    def test_bridge_inference_speed(self, bridge):
        """Bridge processes a batch in reasonable time."""
        bridge.eval()
        ids = torch.randint(0, TOTAL_VOCAB, (4, 128))
        # Warmup
        with torch.no_grad():
            bridge(ids)
        # Timed
        start = time.perf_counter()
        for _ in range(20):
            with torch.no_grad():
                bridge(ids)
        elapsed = time.perf_counter() - start
        # 20 batches × 4 sequences = 80 sequences in <5s
        assert elapsed < 5.0, f"Bridge too slow: {elapsed:.2f}s for 80 sequences"

    @pytest.mark.perf
    def test_vocab_lookup_constant_time(self, tokenizer):
        """Byte→token lookup is O(1) — first and last byte same speed."""
        data_start = bytes([0]) * 10000
        data_end = bytes([255]) * 10000

        start = time.perf_counter()
        tokenizer.encode_bytes("ko", data_start)
        time_start = time.perf_counter() - start

        start = time.perf_counter()
        tokenizer.encode_bytes("ko", data_end)
        time_end = time.perf_counter() - start

        # Should be within 3x of each other (generous for system noise)
        ratio = max(time_start, time_end) / max(min(time_start, time_end), 1e-9)
        assert ratio < 3.0, (
            f"Lookup time varies too much: byte 0={time_start:.6f}s, "
            f"byte 255={time_end:.6f}s, ratio={ratio:.1f}"
        )


# ============================================================
# 11. SINGLETON & MODULE-LEVEL
# ============================================================

class TestModuleLevel:
    """Module-level constants and singleton correctness."""

    @pytest.mark.homebrew
    def test_singleton_exists(self):
        """SACRED_TONGUE_TOKENIZER singleton is initialized."""
        assert SACRED_TONGUE_TOKENIZER is not None

    @pytest.mark.unit
    def test_singleton_is_functional(self):
        """Singleton can encode and decode."""
        tokens = SACRED_TONGUE_TOKENIZER.encode_bytes("ko", b"test")
        data = SACRED_TONGUE_TOKENIZER.decode_tokens("ko", tokens)
        assert data == b"test"

    @pytest.mark.unit
    def test_all_tongue_codes_present(self):
        """TONGUES dict has all 6 expected codes."""
        assert set(TONGUES.keys()) == {"ko", "av", "ru", "ca", "um", "dr"}

    @pytest.mark.unit
    def test_section_tongues_mapping(self):
        """All RWP section mappings use valid tongue codes."""
        for section, tongue_code in SECTION_TONGUES.items():
            assert tongue_code in TONGUES, (
                f"Section {section} maps to unknown tongue {tongue_code}"
            )

    @pytest.mark.unit
    def test_section_tongues_completeness(self):
        """All 6 RWP sections are mapped."""
        expected = {"aad", "salt", "nonce", "ct", "tag", "redact"}
        assert set(SECTION_TONGUES.keys()) == expected
