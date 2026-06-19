"""A free, stdlib-only code generator for the verify loop -- backed by ANY
OpenAI-compatible endpoint: Ollama (local, $0 forever), Groq, Gemini, etc.

No `openai` package needed (uses urllib). Default target = local Ollama. Override via env:
  SCBE_LLM_BASE   (default http://localhost:11434/v1)   # Ollama; Groq: https://api.groq.com/openai/v1
  SCBE_LLM_KEY    (default "ollama")                     # any string for Ollama; real key for cloud
  SCBE_LLM_MODEL  (default qwen2.5-coder:7b)             # Groq e.g. llama-3.3-70b-versatile

The model only PROPOSES; public_bench / score_solutions DECIDES (runs the code, checks the
hidden tests, flags overfit). So a free/weaker model is safe -- nothing reaches the user unless
it actually ran and passed tests it never saw. On any failure this emits a stub that FAILS
verification rather than returning confident-but-wrong code.

    from python.helm.free_generator import make_generator
    from python.helm.public_bench import run_public_bench
    run_public_bench(problems, generator=make_generator(), public_k=1)
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any, Callable, Dict, Optional

DEFAULT_BASE = "http://localhost:11434/v1"  # Ollama's OpenAI-compatible endpoint
DEFAULT_MODEL = "qwen2.5-coder:7b"


def _chat(messages, *, base: str, key: str, model: str, timeout: int = 120) -> str:
    """POST to an OpenAI-compatible /chat/completions endpoint; return the message text."""
    body = json.dumps({"model": model, "messages": messages, "temperature": 0}).encode("utf-8")
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=body,
        headers={"content-type": "application/json", "authorization": f"Bearer {key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - user-configured LLM endpoint
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def strip_to_code(text: str) -> str:
    """Pull the code out of a model reply (handles ```python fences or bare code)."""
    m = re.search(r"```(?:python)?\s*(.*?)```", text or "", re.S)
    return (m.group(1) if m else (text or "")).strip()


def make_generator(
    base: Optional[str] = None,
    key: Optional[str] = None,
    model: Optional[str] = None,
    public_k: int = 1,
) -> Callable[[Dict[str, Any]], str]:
    """Build a generator(problem) -> source backed by a free OpenAI-compatible model."""
    base = base or os.environ.get("SCBE_LLM_BASE", DEFAULT_BASE)
    key = key or os.environ.get("SCBE_LLM_KEY", "ollama")
    model = model or os.environ.get("SCBE_LLM_MODEL", DEFAULT_MODEL)

    def generator(problem: Dict[str, Any]) -> str:
        public = "\n".join(list(problem.get("test_list", []))[:public_k])
        prompt = (
            (problem.get("prompt") or problem.get("text") or "").strip()
            + "\n\nWrite a complete Python solution. It must make this example pass:\n"
            + public
            + "\nReturn ONLY the code."
        )
        try:
            return strip_to_code(_chat([{"role": "user", "content": prompt}], base=base, key=key, model=model))
        except Exception as exc:  # fail closed: emit code that FAILS the tests, never confident-wrong code
            return f"# generation failed ({type(exc).__name__}: {exc})\ndef _failed(*a, **k):\n    return None\n"

    generator.__name__ = "free_llm(%s)" % model
    return generator
