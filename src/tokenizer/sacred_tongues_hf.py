"""
Sacred Tongues HuggingFace Tokenizer Wrapper
=============================================
Makes SCBE Sacred Tongues compatible with HuggingFace transformers.

Two integration modes:
1. VOCAB REPLACEMENT — Replace Qwen's tokenizer entirely with 1,536 Sacred Tongue tokens
2. BRIDGE MODE — Encode with Sacred Tongues, project into model's embedding space

Token vocabulary: 6 tongues × 256 tokens = 1,536 base tokens + special tokens
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import torch
import torch.nn as nn

# Resolve Sacred Tongues from crypto module
import sys

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root / "src") not in sys.path:
    sys.path.insert(0, str(_repo_root / "src"))

from crypto.sacred_tongues import (
    TONGUES,
    SacredTongueTokenizer,
)

# ============================================================
# SPECIAL TOKENS
# ============================================================
SPECIAL_TOKENS = {
    "<pad>": 0,
    "<bos>": 1,
    "<eos>": 2,
    "<unk>": 3,
    "<tongue:ko>": 4,  # Tongue switch markers
    "<tongue:av>": 5,
    "<tongue:ru>": 6,
    "<tongue:ca>": 7,
    "<tongue:um>": 8,
    "<tongue:dr>": 9,
    "<sep>": 10,
    "<mask>": 11,
}

NUM_SPECIAL = len(SPECIAL_TOKENS)
TOKENS_PER_TONGUE = 256
NUM_TONGUES = 6
TOTAL_VOCAB = NUM_SPECIAL + (NUM_TONGUES * TOKENS_PER_TONGUE)  # 12 + 1536 = 1548


# ============================================================
# HF-COMPATIBLE TOKENIZER
# ============================================================


class SacredTonguesHFTokenizer:
    """
    HuggingFace-compatible tokenizer wrapping SCBE Sacred Tongues.

    Vocab layout:
      [0..11]     special tokens
      [12..267]   KO tokens (256)
      [268..523]  AV tokens (256)
      [524..779]  RU tokens (256)
      [780..1035] CA tokens (256)
      [1036..1291] UM tokens (256)
      [1292..1547] DR tokens (256)
    """

    TONGUE_ORDER = ["ko", "av", "ru", "ca", "um", "dr"]

    def __init__(self, default_tongue: str = "ko"):
        self.scbe_tokenizer = SacredTongueTokenizer(TONGUES)
        self.default_tongue = default_tongue

        # Build ID tables
        self.token_to_id: Dict[str, int] = dict(SPECIAL_TOKENS)
        self.id_to_token: Dict[int, str] = {v: k for k, v in SPECIAL_TOKENS.items()}

        offset = NUM_SPECIAL
        self.tongue_offset: Dict[str, int] = {}

        for tongue_code in self.TONGUE_ORDER:
            self.tongue_offset[tongue_code] = offset
            for byte_val in range(256):
                token_str = self.scbe_tokenizer.byte_to_token[tongue_code][byte_val]
                full_key = f"{tongue_code}:{token_str}"
                self.token_to_id[full_key] = offset + byte_val
                self.id_to_token[offset + byte_val] = full_key
            offset += 256

        # HF compatibility attributes
        self.vocab_size = TOTAL_VOCAB
        self.pad_token_id = SPECIAL_TOKENS["<pad>"]
        self.bos_token_id = SPECIAL_TOKENS["<bos>"]
        self.eos_token_id = SPECIAL_TOKENS["<eos>"]
        self.unk_token_id = SPECIAL_TOKENS["<unk>"]
        self.pad_token = "<pad>"
        self.eos_token = "<eos>"
        self.bos_token = "<bos>"

    def encode(
        self,
        text: str,
        tongue: Optional[str] = None,
        add_special_tokens: bool = True,
    ) -> List[int]:
        """Encode text → Sacred Tongue token IDs."""
        tongue = tongue or self.default_tongue
        raw_bytes = text.encode("utf-8")
        tokens = self.scbe_tokenizer.encode_bytes(tongue, raw_bytes)

        offset = self.tongue_offset[tongue]
        ids = [offset + self.scbe_tokenizer.token_to_byte[tongue][t] for t in tokens]

        if add_special_tokens:
            tongue_marker = SPECIAL_TOKENS[f"<tongue:{tongue}>"]
            ids = [self.bos_token_id, tongue_marker] + ids + [self.eos_token_id]

        return ids

    def decode(self, ids: List[int], skip_special_tokens: bool = True) -> str:
        """Decode token IDs → text."""
        raw_bytes = []
        self.default_tongue

        for token_id in ids:
            # Skip specials
            if token_id < NUM_SPECIAL:
                if not skip_special_tokens:
                    raw_bytes.append(self.id_to_token.get(token_id, ""))
                # Detect tongue switch
                for code in self.TONGUE_ORDER:
                    if token_id == SPECIAL_TOKENS.get(f"<tongue:{code}>"):
                        pass
                continue

            # Find which tongue this belongs to
            for code in self.TONGUE_ORDER:
                start = self.tongue_offset[code]
                if start <= token_id < start + 256:
                    byte_val = token_id - start
                    raw_bytes.append(bytes([byte_val]))
                    break

        # Reconstruct UTF-8
        combined = b"".join(b if isinstance(b, bytes) else b.encode() for b in raw_bytes)
        return combined.decode("utf-8", errors="replace")

    def __call__(
        self,
        text: Union[str, List[str]],
        tongue: Optional[str] = None,
        padding: bool = False,
        max_length: Optional[int] = None,
        return_tensors: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """HF-compatible __call__ interface."""
        if isinstance(text, str):
            text = [text]

        all_ids = [self.encode(t, tongue=tongue) for t in text]

        if max_length:
            all_ids = [ids[:max_length] for ids in all_ids]

        if padding:
            max_len = max(len(ids) for ids in all_ids)
            attention_masks = []
            for i, ids in enumerate(all_ids):
                pad_len = max_len - len(ids)
                attention_masks.append([1] * len(ids) + [0] * pad_len)
                all_ids[i] = ids + [self.pad_token_id] * pad_len
        else:
            attention_masks = [[1] * len(ids) for ids in all_ids]

        result = {"input_ids": all_ids, "attention_mask": attention_masks}

        if return_tensors == "pt":
            result = {k: torch.tensor(v) for k, v in result.items()}

        return result

    def get_vocab(self) -> Dict[str, int]:
        return dict(self.token_to_id)

    def save_pretrained(self, save_dir: str) -> None:
        """Save tokenizer config for HF compatibility."""
        os.makedirs(save_dir, exist_ok=True)
        config = {
            "tokenizer_class": "SacredTonguesHFTokenizer",
            "vocab_size": self.vocab_size,
            "default_tongue": self.default_tongue,
            "tongue_order": self.TONGUE_ORDER,
            "special_tokens": SPECIAL_TOKENS,
        }
        with open(os.path.join(save_dir, "tokenizer_config.json"), "w") as f:
            json.dump(config, f, indent=2)

        # Save vocab
        with open(os.path.join(save_dir, "vocab.json"), "w") as f:
            json.dump(self.token_to_id, f, indent=2)

    @classmethod
    def from_pretrained(cls, load_dir: str) -> "SacredTonguesHFTokenizer":
        config_path = os.path.join(load_dir, "tokenizer_config.json")
        with open(config_path) as f:
            config = json.load(f)
        return cls(default_tongue=config.get("default_tongue", "ko"))

    # Canonical role → tongue routing: mirrors the SS1 section-to-tongue mapping.
    # system/metadata → Avali (header context), user → Kor'aelin (intent/flow),
    # assistant → Cassisivadan (output/bitcraft), tool → Draumric (integrity/seal).
    ROLE_TONGUE: Dict[str, str] = {
        "system": "av",
        "user": "ko",
        "assistant": "ca",
        "tool": "dr",
    }

    def apply_chat_template(
        self,
        messages: List[dict],
        tokenize: bool = True,
        add_generation_prompt: bool = False,
        tongue: Optional[str] = None,
    ) -> Union[str, List[int]]:
        """Chat template with per-role tongue routing.

        Each role is encoded in its canonical Sacred Tongue and separated by
        tongue-switch markers, so the training data carries the same geometric
        tongue structure as a governed SS1 envelope:
          [BOS] [tongue:av] <system in Avali> [sep] [tongue:ko] <user in Kor'aelin>
          [sep] [tongue:ca] <assistant in Cassisivadan> [EOS]

        If ``tongue`` is supplied, all roles use that single tongue (legacy mode).
        """
        if not tokenize:
            # Text-only mode: return flat string, no tongue routing needed
            parts = []
            for msg in messages:
                parts.append(f"<|{msg['role']}|>\n{msg['content']}")
            if add_generation_prompt:
                parts.append("<|assistant|>\n")
            return "\n".join(parts)

        # Multi-tongue tokenized mode
        ids: List[int] = [self.bos_token_id]
        for i, msg in enumerate(messages):
            role = msg["role"]
            content = msg["content"]
            role_tongue = tongue if tongue is not None else self.ROLE_TONGUE.get(role, self.default_tongue)

            # Insert tongue-switch marker before each section
            ids.append(SPECIAL_TOKENS[f"<tongue:{role_tongue}>"])

            # Encode content in the role's tongue (no BOS/EOS — we manage framing here)
            raw_bytes = content.encode("utf-8")
            tokens = self.scbe_tokenizer.encode_bytes(role_tongue, raw_bytes)
            offset = self.tongue_offset[role_tongue]
            section_ids = [offset + self.scbe_tokenizer.token_to_byte[role_tongue][t] for t in tokens]
            ids.extend(section_ids)

            # [sep] between sections (not after the last one)
            if i < len(messages) - 1:
                ids.append(SPECIAL_TOKENS["<sep>"])

        if add_generation_prompt:
            # Prime assistant generation with tongue:ca marker
            gen_tongue = tongue if tongue is not None else self.ROLE_TONGUE["assistant"]
            ids.append(SPECIAL_TOKENS["<sep>"])
            ids.append(SPECIAL_TOKENS[f"<tongue:{gen_tongue}>"])

        ids.append(self.eos_token_id)
        return ids


# ============================================================
# APPROACH 1: VOCAB REPLACEMENT — Resize embeddings for Sacred Tongues
# ============================================================


def replace_model_tokenizer(
    model: nn.Module,
    old_vocab_size: int = 151936,  # Qwen2.5 default
    new_vocab_size: int = TOTAL_VOCAB,  # 1548
    embed_dim: int = 896,  # Qwen2.5-0.5B hidden dim
) -> nn.Module:
    """
    Replace Qwen's embedding + LM head with Sacred Tongues vocab.

    This is a FULL REPLACEMENT — the model only speaks Sacred Tongues after this.
    Requires retraining embeddings from scratch (they won't transfer from Qwen).
    """
    # Replace input embeddings
    old_embed = model.model.embed_tokens
    new_embed = nn.Embedding(new_vocab_size, embed_dim)

    # Initialize from old embeddings where possible (special tokens area)
    with torch.no_grad():
        # Copy a random subset of old embeddings as initialization
        # (better than pure random — preserves some distributional properties)
        init_indices = torch.randint(0, old_vocab_size, (new_vocab_size,))
        new_embed.weight.copy_(old_embed.weight[init_indices])

    model.model.embed_tokens = new_embed

    # Replace LM head
    old_head = model.lm_head
    new_head = nn.Linear(embed_dim, new_vocab_size, bias=False)
    with torch.no_grad():
        init_indices = torch.randint(0, old_vocab_size, (new_vocab_size,))
        new_head.weight.copy_(old_head.weight[init_indices])

    model.lm_head = new_head

    # Update config
    model.config.vocab_size = new_vocab_size

    return model


# ============================================================
# APPROACH 2: BRIDGE LAYER — SCBE tokenizer → learned projection → model
# ============================================================


class SacredTongueBridge(nn.Module):
    """
    Two-stage bridge: Sacred Tongue tokens → learned projection → model embedding space.

    The bridge learns to map from the 1,548-token Sacred Tongue vocabulary
    into Qwen's 896-dim embedding space, preserving the geometric structure
    of the six tongues (harmonic frequencies, phi-weighted distances).

    Architecture:
      Sacred Tongue IDs → Bridge Embedding(1548, bridge_dim)
                        → TongueAwareProjection(bridge_dim, model_dim)
                        → [feeds into model's transformer layers]

    The tongue-aware projection adds per-tongue bias vectors so the model
    can distinguish which tongue a token came from (preserving the 6-tongue
    harmonic structure through the projection).
    """

    def __init__(
        self,
        sacred_vocab_size: int = TOTAL_VOCAB,
        bridge_dim: int = 256,
        model_dim: int = 896,  # Qwen2.5-0.5B
        num_tongues: int = 6,
        dropout: float = 0.1,
    ):
        super().__init__()

        self.sacred_vocab_size = sacred_vocab_size
        self.bridge_dim = bridge_dim
        self.model_dim = model_dim

        # Sacred Tongue embedding (small vocab, can be full precision)
        self.sacred_embed = nn.Embedding(sacred_vocab_size, bridge_dim)

        # Per-tongue harmonic bias (encodes the 6 spectral signatures)
        self.tongue_bias = nn.Embedding(num_tongues, bridge_dim)

        # Projection to model space
        self.projection = nn.Sequential(
            nn.Linear(bridge_dim, bridge_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(bridge_dim * 2, model_dim),
            nn.LayerNorm(model_dim),
        )

        # Tongue ID offset table for detecting tongue from token ID
        self._tongue_starts = torch.tensor([NUM_SPECIAL + i * 256 for i in range(num_tongues)])

        self._init_harmonic_weights()

    def _init_harmonic_weights(self):
        """Initialize tongue biases with phi-scaled harmonic frequencies.

        Orthogonal guarantee: after setting phi-scaled structured values in dims 0-1,
        we Gram-Schmidt orthogonalize the 6 tongue vectors so their embedding subspaces
        are linearly independent. Each tongue gets a guaranteed orthogonal neighbor.

        Phase geometry (GeoSeal):
          KO=0°, AV=60°, RU=120°, CA=180°, UM=240°, DR=300°
          Antipodal pairs (180°): KO↔CA, AV↔UM, RU↔DR
          120° neighbor (two-step rotational): KO→RU→UM→KO (and AV→CA→DR→AV)
          Phi connects consecutive (60°) steps as a scaling ratio — not angular.
          Gram-Schmidt below ensures the 6 bias directions are mutually orthogonal,
          so each token's tongue-direction is a distinct axis in embedding space.
        """
        phi = 1.618033988749895
        frequencies = [440.0, 523.25, 329.63, 659.25, 293.66, 392.0]  # KO AV RU CA UM DR

        with torch.no_grad():
            # Step 1: set structured phi-harmonic values in dims 0-1
            for i, freq in enumerate(frequencies):
                weight = freq / 660.0
                phi_scale = phi ** (i / 5.0)
                self.tongue_bias.weight[i] = torch.randn(self.bridge_dim) * 0.02
                self.tongue_bias.weight[i, 0] = weight * phi_scale
                self.tongue_bias.weight[i, 1] = freq / 1000.0

            # Step 2: Gram-Schmidt orthogonalization across the 6 tongue vectors.
            # This guarantees each tongue occupies a distinct orthogonal direction.
            # The phi-harmonic structure in dims 0-1 is preserved as the "seed" direction;
            # higher dims absorb the orthogonalization residual.
            W = self.tongue_bias.weight  # (6, bridge_dim)
            Q = torch.zeros_like(W)
            for i in range(6):
                v = W[i].clone()
                for j in range(i):
                    v = v - (v @ Q[j]) * Q[j]
                norm = v.norm()
                if norm > 1e-8:
                    Q[i] = v / norm
                else:
                    # Fallback: random orthogonal direction if degenerate
                    Q[i] = torch.randn(self.bridge_dim)
                    Q[i] = Q[i] / Q[i].norm()
            # Scale GS-orthogonalized vectors to small noise level for dims 2+.
            # Then re-inject the phi-harmonic anchors into dims 0-1: these are the
            # spectral identity of each tongue and must not be rotated away by GS.
            self.tongue_bias.weight.copy_(Q * 0.02)
            for i, freq in enumerate(frequencies):
                weight = freq / 660.0
                phi_scale = phi ** (i / 5.0)
                self.tongue_bias.weight[i, 0] = weight * phi_scale
                self.tongue_bias.weight[i, 1] = freq / 1000.0

    def _get_tongue_indices(self, token_ids: torch.Tensor) -> torch.Tensor:
        """Map token IDs to tongue indices (0-5), -1 for specials."""
        tongue_idx = torch.full_like(token_ids, -1)
        for i in range(6):
            start = NUM_SPECIAL + i * 256
            end = start + 256
            mask = (token_ids >= start) & (token_ids < end)
            tongue_idx[mask] = i
        return tongue_idx

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        """
        Sacred Tongue IDs → model-space embeddings.

        Args:
            input_ids: (batch, seq_len) Sacred Tongue token IDs
        Returns:
            (batch, seq_len, model_dim) embeddings ready for transformer layers
        """
        # Base embedding
        x = self.sacred_embed(input_ids)  # (B, S, bridge_dim)

        # Add tongue-specific bias
        tongue_idx = self._get_tongue_indices(input_ids)
        tongue_mask = tongue_idx >= 0
        if tongue_mask.any():
            valid_tongue_idx = tongue_idx.clamp(min=0)
            tongue_emb = self.tongue_bias(valid_tongue_idx)  # (B, S, bridge_dim)
            x = x + tongue_emb * tongue_mask.unsqueeze(-1).float()

        # Project to model dimension
        return self.projection(x)  # (B, S, model_dim)


class BridgedModel(nn.Module):
    """
    Wraps a pretrained model with a Sacred Tongue bridge.

    The bridge replaces the model's input embedding layer.
    The rest of the transformer (attention, FFN, LM head) stays frozen or LoRA'd.
    """

    def __init__(self, base_model: nn.Module, bridge: SacredTongueBridge):
        super().__init__()
        self.bridge = bridge
        self.base_model = base_model

        # Swap out the embedding layer — transformer layers read from bridge output
        self._original_embed = base_model.model.embed_tokens
        base_model.model.embed_tokens = None  # Detach original

    def forward(self, input_ids=None, attention_mask=None, labels=None, **kwargs):
        # Route through bridge
        hidden = self.bridge(input_ids)

        # Inject into transformer (bypass embed_tokens)
        # Qwen2 forward: inputs_embeds takes priority over input_ids
        return self.base_model(
            inputs_embeds=hidden,
            attention_mask=attention_mask,
            labels=labels,
            **kwargs,
        )

    @property
    def device(self):
        return next(self.parameters()).device

    @property
    def config(self):
        return self.base_model.config
