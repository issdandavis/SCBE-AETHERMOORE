"""Live OllamaAdapter smoke tests — auto-skip when Ollama isn't reachable.

These exercise the actual end-to-end path that mocked tests can't
verify: real httpx round-trip → real Qwen 1.5B inference → real JSON
parse → real LatticeRouter dispatch. If Ollama isn't running, every
test in this module skips so CI never breaks.

To enable:
  ollama pull qwen2.5:1.5b-instruct
  ollama serve
  pytest tests/cli/test_slm_router_live_ollama.py
"""

from __future__ import annotations

import os
from typing import Optional

import pytest


def _ollama_reachable(
    host: str = "http://localhost:11434", timeout: float = 1.0
) -> bool:
    try:
        import httpx  # noqa: PLC0415
    except ImportError:
        return False
    try:
        resp = httpx.get(f"{host}/api/tags", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def _model_available(
    model: str, host: str = "http://localhost:11434", timeout: float = 2.0
) -> bool:
    try:
        import httpx  # noqa: PLC0415

        resp = httpx.get(f"{host}/api/tags", timeout=timeout)
        if resp.status_code != 200:
            return False
        names = [m.get("name", "") for m in resp.json().get("models", [])]
        return any(model in n for n in names)
    except Exception:
        return False


_HOST = os.environ.get("SCBE_OLLAMA_HOST", "http://localhost:11434")
_MODEL_DEFAULT = os.environ.get("SCBE_OLLAMA_MODEL", "qwen2.5:1.5b-instruct-q4_K_M")
_REACHABLE = _ollama_reachable(_HOST)


# Minimum-capability instruct models that empirically clear the 4-way
# band classification gate at >=90% accuracy. Sub-1B models (e.g.
# qwen2.5-coder:0.5b) and code-completion models (non-instruct) drift
# enough to fail the test even with good prompts — that's not a bug,
# it's a genuine capability floor. The router still works; the live
# *test* just needs an adequate model to be a useful smoke check.
_QUALIFIED_MODELS = (
    "qwen2.5:1.5b",
    "qwen2.5:3b",
    "qwen2.5:7b",
    "llama3.2:1b",  # 1B but instruct-tuned and surprisingly capable
    "llama3.2:3b",
    "phi3:3.8b",
    "phi3:14b",
    "gemma2:2b",
    "gemma2:9b",
)


def _resolve_qualified_model() -> Optional[str]:
    """Return a model that meets the capability floor, or None to skip.

    We deliberately do NOT fall back to whatever's installed — picking a
    coder-only or sub-1B model gives misleading test failures. Better to
    skip with a clear 'pull qwen2.5:1.5b-instruct' message."""
    if _model_available(_MODEL_DEFAULT, _HOST):
        return _MODEL_DEFAULT
    try:
        import httpx  # noqa: PLC0415

        resp = httpx.get(f"{_HOST}/api/tags", timeout=2.0)
        names = [m.get("name", "") for m in resp.json().get("models", [])]
    except Exception:
        return None
    for needle in _QUALIFIED_MODELS:
        for n in names:
            if needle in n:
                return n
    return None


_QUALIFIED_MODEL = _resolve_qualified_model() if _REACHABLE else None


if not _REACHABLE:
    _SKIP_REASON = (
        f"Ollama not reachable at {_HOST}. "
        "Start with `ollama serve` to enable these tests."
    )
elif _QUALIFIED_MODEL is None:
    _SKIP_REASON = (
        f"No qualified instruct model installed at {_HOST}. "
        f"4-way band classification needs >=1B instruct-tuned model. "
        f"Pull one with: `ollama pull qwen2.5:1.5b-instruct` "
        f"(or any of: {list(_QUALIFIED_MODELS)})."
    )
else:
    _SKIP_REASON = ""

pytestmark = pytest.mark.skipif(bool(_SKIP_REASON), reason=_SKIP_REASON)


# ---------------------------------------------------------------------------
#  End-to-end: live model classifies into a real lattice op
# ---------------------------------------------------------------------------


def test_live_ollama_classifies_band_for_arithmetic_intent() -> None:
    """Smoke: the local SLM reliably tags 'add x and y' as ARITHMETIC.

    Uses the production `_band_prompt` builder so the test catches any
    regression in the prompt that goes back to bare 'which band?' (the
    bare prompt mis-classified 'add' as AGGREGATION on qwen2.5:1.5b)."""
    from src.cli.slm_router import (
        OllamaAdapter,
        _band_prompt,
        _band_choices,
    )  # noqa: PLC0415

    adapter = OllamaAdapter(model=_QUALIFIED_MODEL, host=_HOST)
    bands = _band_choices()
    chosen, conf = adapter.classify(_band_prompt("add x and y"), bands)
    assert chosen in bands, f"model returned out-of-set value: {chosen!r}"
    assert chosen == "ARITHMETIC", f"expected ARITHMETIC for 'add', got {chosen!r}"
    assert 0.0 <= conf <= 1.0, f"confidence out of [0, 1]: {conf}"


def test_live_ollama_classifies_op_within_arithmetic_band() -> None:
    from src.cli.slm_router import (
        OllamaAdapter,
        _op_prompt,
        _ops_in_band,
    )  # noqa: PLC0415

    adapter = OllamaAdapter(model=_QUALIFIED_MODEL, host=_HOST)
    arith_ops = _ops_in_band("ARITHMETIC")
    chosen, conf = adapter.classify(
        _op_prompt("add x and y", "ARITHMETIC", arith_ops), arith_ops
    )
    assert chosen in arith_ops, f"out-of-set: {chosen!r}"
    assert chosen == "add", f"expected 'add', got {chosen!r}"


def test_live_ollama_full_router_pipeline_emits_runnable_code() -> None:
    """The contract that actually matters: NL intent → live SLM →
    LatticeOp → emit_from_ir produces lexicon code in every tongue."""
    from src.cli.cross_build_ir import emit_from_ir  # noqa: PLC0415
    from src.cli.slm_router import LatticeRouter, OllamaAdapter  # noqa: PLC0415

    adapter = OllamaAdapter(model=_QUALIFIED_MODEL, host=_HOST)
    router = LatticeRouter(adapter, min_confidence=0.0, adapter_timeout=30.0)
    try:
        result = router.route(
            "Multiply x by y",
            args={"a": "x", "b": "y"},
            dst_tongue="RU",  # skip tongue-classification stage to keep the test tight
        )
    finally:
        router.close()

    assert result.op.op_name == "mul", f"expected mul, got {result.op.op_name}"
    assert result.dst_tongue == "RU"
    code = emit_from_ir(result.op, "RU")
    assert code == "x.wrapping_mul(y)"


def test_live_ollama_router_handles_timeout_gracefully() -> None:
    """Even a real adapter must respect the router's timeout. We use
    an absurdly short deadline so it almost certainly fires."""
    from src.cli.slm_router import (
        LatticeRouter,
        OllamaAdapter,
        ClassificationFailure,
    )  # noqa: PLC0415

    adapter = OllamaAdapter(model=_QUALIFIED_MODEL, host=_HOST)
    router = LatticeRouter(adapter, adapter_timeout=0.001)
    try:
        with pytest.raises(ClassificationFailure):
            router.route("anything", args={"a": "x", "b": "y"})
    finally:
        router.close()
