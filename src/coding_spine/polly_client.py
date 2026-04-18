"""
Coding Spine — Polly Inference Client
======================================
Generates code from a natural language task.  Four-tier fallback:

  1. Local Polly  — transformers pipeline from artifacts/merged/polly-r8-merged-1.5b
  2. Ollama       — local Ollama server (default: qwen2.5-coder:1.5b), zero-cost
  3. HF Inference — issdandavis/polly-r8-merged-qwen-1.5b (InferenceClient)
  4. Claude API   — claude-sonnet-4-6 via anthropic SDK

The caller (router / geoseal_cli) picks a tongue; this module picks the
provider, formats the system prompt accordingly, and returns the result.

Usage:
    from src.coding_spine.polly_client import generate, GenerateResult
    result = generate("write a thread-safe queue", language="Rust", tongue="RU")
    print(result.code)
"""

from __future__ import annotations

import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Repo root — used to locate local merged model
_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOCAL_MODEL_PATH = _REPO_ROOT / "artifacts" / "merged" / "polly-r8-merged-1.5b"
_HF_MODEL_ID = "issdandavis/polly-r8-merged-qwen-1.5b"
_CLAUDE_MODEL = "claude-sonnet-4-6"

# System prompt template — filled with tongue/language at call time
_SYSTEM_TEMPLATE = textwrap.dedent(
    """\
    You are Polly, an expert {language} code generation assistant.
    You operate under the SCBE governance framework using the {tongue_name} Sacred Tongue.

    Rules:
    - Output ONLY the requested code — no explanations, no markdown fences unless
      the user explicitly asked for them.
    - Write idiomatic, production-quality {language}.
    - Include only necessary imports/use declarations.
    - Never add placeholder comments like "# TODO" unless they were in the task.
    """
)

# Strip markdown code fences from model output
_FENCE_RE = re.compile(r"```[a-zA-Z0-9_+-]*\n?(.*?)```", re.DOTALL)


@dataclass
class GenerateResult:
    code: str                          # Extracted code (fences stripped)
    raw: str                           # Full model output
    provider: str                      # "local", "hf", "claude"
    model: str                         # Model ID / path used
    language: str
    tongue: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: Optional[str] = None
    extra: dict = field(default_factory=dict)


def _strip_fences(text: str) -> str:
    """Extract code from inside ```...``` if present; otherwise return as-is."""
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def _build_system(language: str, tongue: str, tongue_name: str) -> str:
    return _SYSTEM_TEMPLATE.format(language=language, tongue=tongue, tongue_name=tongue_name)


# ---------------------------------------------------------------------------
# Provider 1 — Local Polly via transformers
# ---------------------------------------------------------------------------

def _generate_local(
    task: str,
    system: str,
    max_new_tokens: int = 1024,
) -> tuple[str, int, int]:
    """Returns (raw_output, prompt_tokens, completion_tokens)."""
    from transformers import pipeline, AutoTokenizer  # type: ignore

    model_path = str(_LOCAL_MODEL_PATH)
    tok = AutoTokenizer.from_pretrained(model_path)

    # Qwen chat format
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task},
    ]
    prompt_str = tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    prompt_ids = tok(prompt_str, return_tensors="pt").input_ids
    prompt_len = prompt_ids.shape[-1]

    pipe = pipeline(
        "text-generation",
        model=model_path,
        tokenizer=tok,
        device_map="auto",
        max_new_tokens=max_new_tokens,
        do_sample=False,            # deterministic
        temperature=None,
        top_p=None,
    )
    out = pipe(prompt_str)[0]["generated_text"]
    # Strip the prompt prefix
    if out.startswith(prompt_str):
        out = out[len(prompt_str):]
    completion_len = len(tok(out).input_ids)
    return out.strip(), prompt_len, completion_len


# ---------------------------------------------------------------------------
# Provider 2 — HF Inference API
# ---------------------------------------------------------------------------

def _generate_hf(
    task: str,
    system: str,
    max_new_tokens: int = 1024,
) -> tuple[str, int, int]:
    from huggingface_hub import InferenceClient  # type: ignore

    hf_token = os.environ.get("HF_TOKEN", "")
    client = InferenceClient(model=_HF_MODEL_ID, token=hf_token or None)

    # Try chat_completion first (deployed inference endpoints); fall back to
    # text_generation (works for any causal LM, including freshly pushed repos)
    prompt_str = f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{task}<|im_end|>\n<|im_start|>assistant\n"
    try:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": task},
        ]
        resp = client.chat_completion(
            messages=messages,
            max_tokens=max_new_tokens,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content or ""
        pt = getattr(resp.usage, "prompt_tokens", 0) if hasattr(resp, "usage") else 0
        ct = getattr(resp.usage, "completion_tokens", 0) if hasattr(resp, "usage") else 0
        return raw, pt, ct
    except Exception:
        pass

    # text_generation fallback
    resp = client.text_generation(
        prompt_str,
        max_new_tokens=max_new_tokens,
        temperature=0.1,
        do_sample=False,
    )
    raw = resp if isinstance(resp, str) else str(resp)
    # Strip prompt echo if present
    if raw.startswith(prompt_str):
        raw = raw[len(prompt_str):]
    # Strip stop token
    if "<|im_end|>" in raw:
        raw = raw[: raw.index("<|im_end|>")]
    return raw.strip(), 0, 0


# ---------------------------------------------------------------------------
# Provider 3 — Claude API fallback
# ---------------------------------------------------------------------------

def _generate_claude(
    task: str,
    system: str,
    max_tokens: int = 1024,
) -> tuple[str, int, int]:
    import anthropic  # type: ignore

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=_CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": task}],
    )
    raw = msg.content[0].text if msg.content else ""
    pt = msg.usage.input_tokens
    ct = msg.usage.output_tokens
    return raw, pt, ct


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate(
    task: str,
    *,
    language: str = "Python",
    tongue: str = "KO",
    tongue_name: str = "Kor'aelin",
    max_tokens: int = 1024,
    force_provider: Optional[str] = None,  # "local" | "hf" | "claude"
) -> GenerateResult:
    """
    Generate code for `task` in `language`.

    Provider priority: local → hf → claude (unless force_provider is set).
    Falls back automatically on ImportError or runtime error.
    """
    system = _build_system(language, tongue, tongue_name)
    errors: list[str] = []

    providers = (
        [force_provider] if force_provider
        else (
            ["local"] if _LOCAL_MODEL_PATH.exists() else []
        ) + ["hf", "claude"]
    )

    for provider in providers:
        try:
            if provider == "local":
                raw, pt, ct = _generate_local(task, system, max_new_tokens=max_tokens)
                return GenerateResult(
                    code=_strip_fences(raw),
                    raw=raw,
                    provider="local",
                    model=str(_LOCAL_MODEL_PATH),
                    language=language,
                    tongue=tongue,
                    prompt_tokens=pt,
                    completion_tokens=ct,
                )

            elif provider == "hf":
                raw, pt, ct = _generate_hf(task, system, max_new_tokens=max_tokens)
                return GenerateResult(
                    code=_strip_fences(raw),
                    raw=raw,
                    provider="hf",
                    model=_HF_MODEL_ID,
                    language=language,
                    tongue=tongue,
                    prompt_tokens=pt,
                    completion_tokens=ct,
                )

            elif provider == "claude":
                raw, pt, ct = _generate_claude(task, system, max_tokens=max_tokens)
                return GenerateResult(
                    code=_strip_fences(raw),
                    raw=raw,
                    provider="claude",
                    model=_CLAUDE_MODEL,
                    language=language,
                    tongue=tongue,
                    prompt_tokens=pt,
                    completion_tokens=ct,
                )

        except Exception as exc:
            errors.append(f"{provider}: {exc}")
            continue

    # All providers failed
    return GenerateResult(
        code="",
        raw="",
        provider="none",
        model="none",
        language=language,
        tongue=tongue,
        error="; ".join(errors),
    )


if __name__ == "__main__":
    # Quick smoke test
    r = generate(
        "write a function that returns the nth Fibonacci number using memoization",
        language="Python",
        tongue="KO",
        tongue_name="Kor'aelin",
    )
    print(f"provider={r.provider}  model={r.model}")
    print(f"prompt_tokens={r.prompt_tokens}  completion_tokens={r.completion_tokens}")
    if r.error:
        print(f"ERROR: {r.error}")
    else:
        print("--- code ---")
        print(r.code)
