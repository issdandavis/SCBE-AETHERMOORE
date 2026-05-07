"""Custom tokenizer-path rendering tests for dispatch_coding_agent_hf_job.py.

Verifies that:
1. A profile without ``hub.tokenizer_path`` renders unchanged (back-compat).
2. A profile WITH ``hub.tokenizer_path`` renders the extended-tokenizer
   path through to AutoTokenizer.from_pretrained.
3. The render unconditionally emits a ``resize_token_embeddings`` guard
   so the embedding matrix grows when len(tokenizer) > base_vocab.
4. ``modules_to_save = ['embed_tokens', 'lm_head']`` is auto-set when
   the tokenizer was extended (vocab mismatch), so the new embedding
   rows actually train rather than staying at mean-init.
5. An explicit ``training.modules_to_save`` profile entry overrides the
   automatic default.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts.system import dispatch_coding_agent_hf_job as dispatcher

REPO_ROOT = Path(__file__).resolve().parents[1]


def _baseline_profile() -> dict:
    return json.loads(
        (REPO_ROOT / "config" / "model_training" / "scbe-coding-primary-7b-qlora-v6f.json").read_text(
            encoding="utf-8"
        )
    )


def test_render_without_tokenizer_path_is_valid_python():
    profile = _baseline_profile()
    profile.setdefault("hub", {}).pop("tokenizer_path", None)
    script = dispatcher.render_uv_training_script(profile)
    ast.parse(script)
    # tokenizer_path field is read with a fallback to base_model
    assert 'hub_cfg.get("tokenizer_path")' in script


def test_render_with_tokenizer_path_inlines_path_lookup():
    profile = _baseline_profile()
    profile.setdefault("hub", {})["tokenizer_path"] = "issdandavis/extended-tokenizer-test"
    script = dispatcher.render_uv_training_script(profile)
    ast.parse(script)
    # Path is read at runtime (not baked) so dispatch is profile-driven
    assert "tokenizer_path = str(hub_cfg.get(" in script
    assert "AutoTokenizer.from_pretrained(tokenizer_path" in script


def test_render_emits_resize_guard():
    """The resize guard must be present and gated on extended_vocab >
    base_vocab. Many models (Qwen2.5) pad model.config.vocab_size beyond
    the tokenizer's actual vocab — resizing down would crash. Use
    strictly-greater to detect a real extension."""

    profile = _baseline_profile()
    script = dispatcher.render_uv_training_script(profile)
    assert "model.resize_token_embeddings(extended_vocab)" in script
    assert '"event": "resize_token_embeddings"' in script
    assert "extended_vocab > base_vocab" in script
    # Negative: the buggy != check that shrunk Qwen embeddings 152064->151665
    # (job 69fbd7c6, 2026-05-06) must be gone.
    assert "extended_vocab != base_vocab" not in script


def test_render_auto_sets_modules_to_save_when_tokenizer_was_extended():
    """When tokenizer was extended (extended_vocab > base_vocab),
    embed_tokens + lm_head must be trainable so the new rows learn —
    LoRA alone freezes them. This must NOT fire when the tokenizer was
    not extended (false positive on padded model.config.vocab_size
    blew up v6g with 1.1B trainable params + OOM)."""

    profile = _baseline_profile()
    script = dispatcher.render_uv_training_script(profile)
    assert 'modules_to_save = ["embed_tokens", "lm_head"]' in script
    assert "modules_to_save=modules_to_save" in script
    # Gate must be 'tokenizer_was_extended' (boolean derived from > comparison),
    # not the buggy != comparison that fired on Qwen's padded vocab.
    assert "tokenizer_was_extended" in script


def test_render_does_not_resize_when_tokenizer_smaller_than_model_vocab():
    """Regression for v6g failure (job 69fbd7c6). Qwen2.5-Coder-7B has
    model.config.vocab_size=152064 but the base tokenizer is 151665. The
    earlier render did `if extended_vocab != base_vocab: resize` which
    SHRUNK the embedding 152064->151665, dropped 399 rows, and crashed
    training. The fixed render must use strictly-greater so this case
    is a no-op."""

    profile = _baseline_profile()
    # No tokenizer_path -> base tokenizer -> common case where Qwen pads model
    profile.setdefault("hub", {}).pop("tokenizer_path", None)
    script = dispatcher.render_uv_training_script(profile)
    # The condition must be the strictly-greater form; the runtime decides
    # but the rendered code can never call resize on shrink.
    idx = script.index("if tokenizer_was_extended:")
    block = script[idx : idx + 300]
    assert "model.resize_token_embeddings" in block


def test_render_honors_explicit_modules_to_save_override():
    """If a profile explicitly sets training.modules_to_save, the
    rendered script must read that field with priority over the
    auto-default."""

    profile = _baseline_profile()
    profile.setdefault("training", {})["modules_to_save"] = ["embed_tokens"]
    script = dispatcher.render_uv_training_script(profile)
    ast.parse(script)
    # Both branches present — runtime decides which wins
    assert 'train_cfg.get("modules_to_save")' in script


def test_lora_target_modules_unchanged():
    """Backward compat: target_modules default and override path is
    unchanged by the tokenizer wiring."""

    profile = _baseline_profile()
    script = dispatcher.render_uv_training_script(profile)
    assert 'target_modules=list(train_cfg.get("target_modules")' in script
    assert '["q_proj", "k_proj", "v_proj", "o_proj"]' in script
