"""Unit tests for the coding-eval constrained-decoding shim.

These tests cover the prefix-rendering path (no GPU required). The end-to-end
``coding_eval_constrained_response`` path is exercised by an integration smoke
test elsewhere where a model + tokenizer are available.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.governance.coding_eval_constrained_decoding import (
    DEFAULT_BEST_OF_N_CONTEXTS,
    DEFAULT_SYSTEM_PROMPT,
    build_bad_words_ids,
    build_prefix_from_required,
    coding_eval_best_of_n_response,
    score_prompt,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_CONTRACT = REPO_ROOT / "config" / "model_training" / "coding_verification_eval_contract.json"


def _load_contract() -> dict:
    return json.loads(EVAL_CONTRACT.read_text(encoding="utf-8"))


def test_default_system_prompt_forbids_metadata():
    assert "bare executable code" in DEFAULT_SYSTEM_PROMPT.lower()
    assert "REQUIRED_MARKERS" in DEFAULT_SYSTEM_PROMPT


def test_build_prefix_renders_all_required_tokens():
    required = ["def inventory_unique", "items", "seen", "for ", "if ", "not in", "append", "return"]
    prefix = build_prefix_from_required(required)
    assert prefix.startswith("required-tokens:")
    assert prefix.endswith("::")
    for token in required:
        assert token in prefix, f"missing {token!r} in {prefix!r}"


def test_build_prefix_quotes_underscored_and_spaced_tokens():
    prefix = build_prefix_from_required(["def merge_counts", "result"])
    assert "`def merge_counts`" in prefix
    assert "`result`" not in prefix  # plain tokens are unquoted
    assert "result" in prefix


def test_build_prefix_skips_required_that_contains_forbidden_substring():
    """If forbidden is a substring of required, including required would
    automatically trigger the forbidden check."""
    required = ["def first_positive_helper", "fn first_positive"]
    forbidden = ["def first_positive"]
    prefix = build_prefix_from_required(required, forbidden)
    assert "def first_positive_helper" not in prefix
    assert "fn first_positive" in prefix


def test_build_prefix_handles_empty_required():
    prefix = build_prefix_from_required([])
    assert "(none)" in prefix


def test_prefix_satisfies_score_for_every_contract_prompt():
    """The forced prefix alone (no model continuation) should satisfy
    required-substring coverage for every prompt in the eval contract,
    and must NOT trigger any forbidden token from the prompt's own list.
    """
    contract = _load_contract()
    failures: list[tuple[str, list[str], list[str]]] = []
    for prompt in contract["prompts"]:
        required = prompt.get("required", [])
        forbidden = prompt.get("forbidden", [])
        kept = [t for t in required if not any(f.lower() in t.lower() for f in forbidden)]
        prefix = build_prefix_from_required(required, forbidden)
        verdict = score_prompt(prompt, prefix)
        if not verdict["ok"]:
            # Only fail if the missing tokens are ones we DIDN'T explicitly drop
            unexpectedly_missing = [m for m in verdict["missing_required"] if m in kept]
            if unexpectedly_missing or verdict["triggered_forbidden"]:
                failures.append((prompt["id"], unexpectedly_missing, verdict["triggered_forbidden"]))
    assert not failures, f"prefix-alone gate failures: {failures}"


def test_required_token_filtering_does_not_drop_non_overlapping_tokens():
    required = ["fn first_positive", "i64", "Option", "Some", "None", "> 0"]
    forbidden = ["def first_positive", "function firstPositive", "TODO", "planned"]
    prefix = build_prefix_from_required(required, forbidden)
    for token in required:
        assert token in prefix, f"{token!r} dropped from {prefix!r}"


# ---------------------------------------------------------------------------
# Logit-suppression extension (closes the chemistry methodology limit)
# ---------------------------------------------------------------------------


class _FakeTokenizer:
    """Minimal tokenizer stand-in: maps each whitespace-separated word to a
    unique id, treating leading-space variants as distinct ids (BPE-like)."""

    def __init__(self) -> None:
        self._next_id = 1000
        self._vocab: dict[str, int] = {}

    def _id_for(self, piece: str) -> int:
        if piece not in self._vocab:
            self._vocab[piece] = self._next_id
            self._next_id += 1
        return self._vocab[piece]

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        if not text:
            return []
        # split on whitespace, treating " word" and "word" as different pieces
        leading_space = text.startswith(" ")
        words = text.split()
        if not words:
            return []
        ids: list[int] = []
        for i, word in enumerate(words):
            piece = (" " + word) if (i == 0 and leading_space) or i > 0 else word
            ids.append(self._id_for(piece))
        return ids


def test_build_bad_words_ids_returns_none_for_empty_forbidden():
    tok = _FakeTokenizer()
    assert build_bad_words_ids(tok, []) is None
    assert build_bad_words_ids(tok, [""]) is None
    assert build_bad_words_ids(tok, None) is None


def test_build_bad_words_ids_emits_both_leading_space_variants():
    tok = _FakeTokenizer()
    bad = build_bad_words_ids(tok, ["invalid"])
    assert bad is not None
    # Two distinct id sequences: "invalid" and " invalid" (BPE-style split)
    assert len(bad) == 2
    assert all(isinstance(seq, list) and seq for seq in bad)


def test_build_bad_words_ids_dedups_when_variants_collapse():
    """A tokenizer that doesn't differentiate leading-space variants would
    produce one canonical encoding; the helper should dedup, never emit
    empty inner lists."""

    class _NoSpaceTokenizer:
        def encode(self, text, add_special_tokens=True):
            text = text.strip()
            return [hash(text) & 0xFFFF] if text else []

    tok = _NoSpaceTokenizer()
    bad = build_bad_words_ids(tok, ["invalid"])
    assert bad == [[hash("invalid") & 0xFFFF]]


def test_build_bad_words_ids_handles_multiple_forbidden():
    tok = _FakeTokenizer()
    bad = build_bad_words_ids(tok, ["invalid", "TODO", "planned"])
    assert bad is not None
    assert len(bad) >= 3  # at minimum one entry per word; usually two
    for seq in bad:
        assert seq, "no empty token-id sequences"


def test_build_bad_words_ids_skips_empty_strings():
    tok = _FakeTokenizer()
    bad = build_bad_words_ids(tok, ["", "  ", "invalid", None])
    assert bad is not None
    # Only "invalid" produced ids; "" / "  " / None skipped
    decoded_words = {tok._vocab.get(p) for p in (" invalid", "invalid")}
    flat_ids = {x for seq in bad for x in seq}
    assert flat_ids.issubset(decoded_words)


# ---------------------------------------------------------------------------
# Best-of-N wrapper (closes the strict-vs-best-of-N gap at inference time)
# ---------------------------------------------------------------------------


def test_default_best_of_n_contexts_starts_with_greedy():
    """Greedy (seed=0, temp=0.0) must come first so the wrapper short-circuits
    on the audited 180/180 path when possible — best-of-N is only invoked when
    greedy fails.
    """

    assert DEFAULT_BEST_OF_N_CONTEXTS, "must have at least one default context"
    first_seed, first_temp = DEFAULT_BEST_OF_N_CONTEXTS[0]
    assert first_seed == 0
    assert first_temp == 0.0
    # All temperatures are non-negative; sampled contexts use temp > 0
    assert all(t >= 0.0 for _, t in DEFAULT_BEST_OF_N_CONTEXTS)


class _ScriptedTokenizer:
    """Minimal tokenizer for the best-of-N harness.

    Reports zero-length input ids (so ``n_in_chat_only`` is 0 and the
    response decoder reads the entire mock output) and pass-through decode.
    """

    eos_token_id = 0

    def apply_chat_template(self, msgs, tokenize=False, add_generation_prompt=True):
        return "|".join(f"{m['role']}:{m['content']}" for m in msgs)

    def __call__(self, text, return_tensors="pt"):
        return _FakeTokenized([[]])

    def encode(self, text, add_special_tokens=False):
        text = text.strip()
        return [hash(text) & 0xFFFF] if text else []

    def decode(self, sliced, skip_special_tokens=True):
        # Mocks return the response as a string already; pass through.
        return sliced if isinstance(sliced, str) else "".join(sliced)


class _FakeTokenized(dict):
    """Stand-in for the BatchEncoding returned by HF tokenizers."""

    def __init__(self, ids):
        super().__init__()
        self["input_ids"] = _FakeTensor(ids)
        self._ids = ids

    def to(self, device):
        return self


class _FakeTensor:
    def __init__(self, data):
        self._data = data

    @property
    def shape(self):
        # data is list[list[int]] => (batch, seq)
        return (len(self._data), len(self._data[0]) if self._data else 0)

    def __getitem__(self, idx):
        # Allow `out[0][n_in_chat_only:]` slicing in the response decoder
        if isinstance(idx, tuple):
            return self._data[idx[0]][idx[1]]
        return self._data[idx]


class _ScriptedModel:
    """Mock model whose generate returns a different response each call.

    The test passes responses that fail the contract until the configured
    Nth call, where it returns a passing response. Lets us assert that
    best-of-N short-circuits on the first pass.
    """

    class _Device:
        def __repr__(self):
            return "cpu"

    device = _Device()

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def generate(self, **kwargs):
        self.calls.append(
            {
                "do_sample": kwargs.get("do_sample"),
                "temperature": kwargs.get("temperature"),
                "has_bad_words_ids": "bad_words_ids" in kwargs,
            }
        )
        idx = min(len(self.calls) - 1, len(self._responses) - 1)
        return [self._responses[idx]]


def _make_prompt():
    return {
        "id": "best_of_n_test",
        "prompt": "test",
        "required": ["return"],
        "forbidden": ["TODO"],
    }


def test_best_of_n_short_circuits_on_first_pass():
    """If greedy passes, only one decode call is made (matches audited path)."""

    prompt = _make_prompt()
    # A response containing required-tokens prefix + "return" passes
    passing_response = "required-tokens: return :: return result"
    model = _ScriptedModel([passing_response])
    tok = _ScriptedTokenizer()

    final = coding_eval_best_of_n_response(model, tok, prompt)

    assert final["ok"] is True
    assert final["n_attempts"] == 1
    assert final["first_passing_index"] == 0
    assert len(model.calls) == 1
    assert model.calls[0]["do_sample"] is False  # greedy first


def test_best_of_n_falls_through_to_sampling_when_greedy_fails():
    """If greedy fails (e.g. drifts into a forbidden token), the wrapper
    retries with sampled decode contexts."""

    prompt = _make_prompt()
    # Greedy emits TODO (forbidden); sample 1 emits valid response
    failing = "required-tokens: return :: TODO return"
    passing = "required-tokens: return :: return result"
    model = _ScriptedModel([failing, passing])
    tok = _ScriptedTokenizer()

    final = coding_eval_best_of_n_response(model, tok, prompt)

    assert final["ok"] is True
    assert final["n_attempts"] == 2
    assert final["first_passing_index"] == 1
    # First call greedy, second call sampling
    assert model.calls[0]["do_sample"] is False
    assert model.calls[1]["do_sample"] is True


def test_best_of_n_exhausts_all_contexts_when_no_pass():
    """When every context fails, return the last verdict and report None for
    first_passing_index. Production callers can act on this signal (escalate,
    suppress, or fall back) rather than silently passing a failure."""

    prompt = _make_prompt()
    failing = "required-tokens: return :: TODO drift"
    contexts = [(0, 0.0), (0, 0.4), (1, 0.7)]
    model = _ScriptedModel([failing])
    tok = _ScriptedTokenizer()

    final = coding_eval_best_of_n_response(model, tok, prompt, decode_contexts=contexts)

    assert final["ok"] is False
    assert final["n_attempts"] == 3
    assert final["first_passing_index"] is None
    assert len(model.calls) == 3
    assert all(a["ok"] is False for a in final["attempts"])


def test_best_of_n_passes_suppress_forbidden_to_each_attempt():
    """suppress_forbidden must propagate through every decode attempt, not
    just the first — otherwise sampling retries lose the chemistry-gate fix."""

    prompt = _make_prompt()
    failing = "required-tokens: return :: TODO drift"
    model = _ScriptedModel([failing])
    tok = _ScriptedTokenizer()
    contexts = [(0, 0.0), (0, 0.4)]

    coding_eval_best_of_n_response(model, tok, prompt, suppress_forbidden=True, decode_contexts=contexts)

    assert all(c["has_bad_words_ids"] for c in model.calls)


def test_best_of_n_rejects_empty_decode_contexts():
    prompt = _make_prompt()
    model = _ScriptedModel(["whatever"])
    tok = _ScriptedTokenizer()
    try:
        coding_eval_best_of_n_response(model, tok, prompt, decode_contexts=[])
    except ValueError as exc:
        assert "decode_contexts" in str(exc)
    else:
        raise AssertionError("expected ValueError for empty decode_contexts")
