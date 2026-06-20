"""Optional second-tier injection classifier (model-grade detection).

The pattern + structural screen in scbe.py is the fast, pure-python FIRST tier.
This adds a fine-tuned DeBERTa classifier as a SECOND tier — the layered design
every production guardrail uses (Meta LlamaFirewall = PromptGuard 2 classifier +
an LLM-judge; protectai/llm-guard and Rebuff = heuristics + a classifier).

Research caveats are deliberately baked into how this is used:
  * Fine-tuned DeBERTa injection classifiers (ProtectAI v2, Prompt Guard 2) get
    HIGH recall (~0.99) but imperfect precision (~10% false positives on
    out-of-distribution text) and are EVADABLE by character-injection. So the
    classifier is NOT a silver bullet: it complements the pattern prefilter
    (which catches the encoded/obfuscated cases the classifier misses), and the
    gate treats a model-only hit as ESCALATE (review), not a silent DENY, to
    absorb its false positives.

Default model: protectai/deberta-v3-base-prompt-injection-v2 (Apache-2.0, 0.2B,
CPU, ungated). Swap via env SCBE_INJECTION_MODEL. Everything degrades to None
when the deps/model are absent, so the default gate is unchanged and pure-python.
"""

from __future__ import annotations

import functools
import os
from typing import Optional

DEFAULT_MODEL = "protectai/deberta-v3-base-prompt-injection-v2"
# Label names (across models) that mean "attack"; the probability is summed over
# whichever of these the configured model exposes.
_INJECTION_LABELS = {"INJECTION", "JAILBREAK", "MALICIOUS", "UNSAFE", "LABEL_1"}


def configured_model() -> Optional[str]:
    """The model id to load, or None to keep the gate pure-python.

    Enabled only when SCBE_INJECTION_MODEL is set (to a HF id, or 1/on/default/true
    for the default model). Opt-in by design so the normal CLI stays fast and has
    no heavy dependency.
    """
    val = os.environ.get("SCBE_INJECTION_MODEL", "").strip()
    if not val:
        return None
    if val.lower() in {"1", "on", "true", "default", "yes"}:
        return DEFAULT_MODEL
    return val


@functools.lru_cache(maxsize=1)
def _backend():
    mid = configured_model()
    if not mid:
        return None
    # Preferred: ONNX via optimum (CPU, no torch) when a pre-exported ONNX repo is
    # configured — load only, never export (export needs torch).
    try:
        from optimum.onnxruntime import ORTModelForSequenceClassification  # type: ignore
        from transformers import AutoTokenizer  # type: ignore

        # ProtectAI (and most pre-exported repos) ship the ONNX weights + tokenizer in
        # an `onnx/` subfolder; load from there first (no torch export), then the root.
        for sub in ("onnx", ""):
            try:
                tok = AutoTokenizer.from_pretrained(mid, subfolder=sub)
                mdl = ORTModelForSequenceClassification.from_pretrained(mid, subfolder=sub)
                return ("onnx", tok, mdl)
            except Exception:
                continue
    except Exception:
        pass
    # Reliable fallback: a transformers text-classification pipeline (torch).
    try:
        from transformers import pipeline  # type: ignore

        clf = pipeline("text-classification", model=mid, top_k=None, truncation=True, max_length=512)
        return ("pipeline", clf, None)
    except Exception:
        return None


def is_available() -> bool:
    """True when a classifier is configured AND its dependencies/model loaded."""
    return _backend() is not None


def injection_prob(text: str) -> Optional[float]:
    """P(injection) in [0, 1] from the classifier, or None if unavailable.

    Never raises — any model/runtime error returns None so the caller falls back
    to the pure-python screen.
    """
    backend = _backend()
    if backend is None or not text:
        return None
    try:
        kind = backend[0]
        if kind == "pipeline":
            scores = backend[1](text[:4000])[0]  # list of {"label", "score"}
            inj = [s["score"] for s in scores if str(s["label"]).upper() in _INJECTION_LABELS]
            return float(min(1.0, sum(inj))) if inj else None
        # ONNX path
        import numpy as np  # local: only needed when the ONNX backend is active

        _, tok, mdl = backend
        enc = tok(text[:4000], return_tensors="np", truncation=True, max_length=512)
        logits = mdl(**enc).logits[0]
        ex = np.exp(logits - logits.max())
        probs = ex / ex.sum()
        id2label = getattr(mdl.config, "id2label", {}) or {}
        idxs = [int(i) for i, lab in id2label.items() if str(lab).upper() in _INJECTION_LABELS]
        if not idxs:
            idxs = [1] if len(probs) > 1 else [0]
        return float(min(1.0, sum(float(probs[i]) for i in idxs)))
    except Exception:
        return None
