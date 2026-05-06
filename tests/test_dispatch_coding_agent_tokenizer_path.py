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
    """The resize guard must always be present so a profile that points
    at an extended tokenizer does not need a flag day to opt in — the
    code does the right thing automatically when vocab mismatches."""

    profile = _baseline_profile()
    script = dispatcher.render_uv_training_script(profile)
    assert "model.resize_token_embeddings(extended_vocab)" in script
    assert '"event": "resize_token_embeddings"' in script
    assert "extended_vocab != base_vocab" in script


def test_render_auto_sets_modules_to_save_when_vocab_mismatches():
    """When tokenizer extends vocab, embed_tokens + lm_head must be
    trainable so the new rows learn — LoRA alone freezes them."""

    profile = _baseline_profile()
    script = dispatcher.render_uv_training_script(profile)
    assert 'modules_to_save = ["embed_tokens", "lm_head"]' in script
    assert "modules_to_save=modules_to_save" in script


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
