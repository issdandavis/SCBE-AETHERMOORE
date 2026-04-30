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

import json
import os
import re
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Repo root — used to locate local merged model
_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOCAL_MODEL_PATH = _REPO_ROOT / "artifacts" / "merged" / "polly-r8-merged-1.5b"
_HF_MODEL_ID = "issdandavis/polly-r8-merged-qwen-1.5b"
_CLAUDE_MODEL = "claude-sonnet-4-6"

# Ollama defaults — override via OLLAMA_HOST / OLLAMA_MODEL env vars
_OLLAMA_HOST_DEFAULT = "http://localhost:11434"
_OLLAMA_MODEL_DEFAULT = "qwen2.5-coder:1.5b"
_OLLAMA_HEALTH_TIMEOUT = 1.5  # seconds — short so chain advances fast when down

# Ordered list of provider tiers (cheapest/safest first).
PROVIDER_TIERS = ("local", "ollama", "hf", "claude")

# Governance tiers in ascending severity (lower index = more permissive).
_GOVERNANCE_TIERS = ("ALLOW", "QUARANTINE", "ESCALATE", "DENY")

# System prompt template — filled with tongue/language at call time
_SYSTEM_TEMPLATE = textwrap.dedent("""\
    You are Polly, an expert {language} code generation assistant.
    You operate under the SCBE governance framework using the {tongue_name} Sacred Tongue.

    Rules:
    - Output ONLY the requested code — no explanations, no markdown fences unless
      the user explicitly asked for them.
    - Write idiomatic, production-quality {language}.
    - Include only necessary imports/use declarations.
    - Never add placeholder comments like "# TODO" unless they were in the task.
    """)

# Strip markdown code fences from model output
_FENCE_RE = re.compile(r"```[a-zA-Z0-9_+-]*\n?(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class BackendDescriptor:
    provider: str
    model: str
    supports_lanes: tuple[str, ...]
    local_only: bool = False

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "supports_lanes": list(self.supports_lanes),
            "local_only": self.local_only,
        }


@dataclass
class GenerateResult:
    code: str  # Extracted code (fences stripped)
    raw: str  # Full model output
    provider: str  # "local", "ollama", "hf", "claude", "none"
    model: str  # Model ID / path used
    language: str
    tongue: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: Optional[str] = None
    extra: dict = field(default_factory=dict)
    # Ordered ledger of provider attempts (success or failure). Each entry:
    # {provider, model, duration_ms, prompt_tokens, completion_tokens,
    #  error (str|None), success (bool), skipped_reason (str|None)}
    attempted_providers: list[dict] = field(default_factory=list)


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
    prompt_str = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    prompt_ids = tok(prompt_str, return_tensors="pt").input_ids
    prompt_len = prompt_ids.shape[-1]

    pipe = pipeline(
        "text-generation",
        model=model_path,
        tokenizer=tok,
        device_map="auto",
        max_new_tokens=max_new_tokens,
        do_sample=False,  # deterministic
        temperature=None,
        top_p=None,
    )
    out = pipe(prompt_str)[0]["generated_text"]
    # Strip the prompt prefix
    if out.startswith(prompt_str):
        out = out[len(prompt_str) :]
    completion_len = len(tok(out).input_ids)
    return out.strip(), prompt_len, completion_len


# ---------------------------------------------------------------------------
# Provider 2 — Ollama (local HTTP, zero-cost)
# ---------------------------------------------------------------------------


def _ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", _OLLAMA_HOST_DEFAULT).rstrip("/")


def _ollama_model() -> str:
    return os.environ.get("OLLAMA_MODEL", _OLLAMA_MODEL_DEFAULT)


def _ollama_available(timeout: float = _OLLAMA_HEALTH_TIMEOUT) -> bool:
    """Return True if the Ollama server responds to GET /api/tags."""
    try:
        req = urllib.request.Request(_ollama_host() + "/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return False


def _generate_ollama(
    task: str,
    system: str,
    max_new_tokens: int = 1024,
    model: Optional[str] = None,
    timeout: float = 120.0,
) -> tuple[str, int, int]:
    """POST /api/chat to a local Ollama daemon. Returns (raw, prompt_tok, completion_tok)."""
    model = model or _ollama_model()
    body = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": task},
        ],
        "options": {
            "num_predict": max_new_tokens,
            "temperature": 0.1,
        },
    }
    req = urllib.request.Request(
        _ollama_host() + "/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    raw = (payload.get("message") or {}).get("content", "") or ""
    pt = int(payload.get("prompt_eval_count", 0) or 0)
    ct = int(payload.get("eval_count", 0) or 0)
    return raw.strip(), pt, ct


# ---------------------------------------------------------------------------
# Provider 3 — HF Inference API
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
        raw = raw[len(prompt_str) :]
    # Strip stop token
    if "<|im_end|>" in raw:
        raw = raw[: raw.index("<|im_end|>")]
    return raw.strip(), 0, 0


# ---------------------------------------------------------------------------
# Provider 4 — Claude API fallback
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


def _provider_model(provider: str) -> str:
    if provider == "local":
        return str(_LOCAL_MODEL_PATH)
    if provider == "ollama":
        return _ollama_model()
    if provider == "hf":
        return _HF_MODEL_ID
    if provider == "claude":
        return _CLAUDE_MODEL
    return provider


def get_backend_registry() -> list[BackendDescriptor]:
    """Inspectable provider capability table for CLI explain/history surfaces."""
    lanes = ("python", "typescript", "c", "rust", "binary")
    return [
        BackendDescriptor("local", str(_LOCAL_MODEL_PATH), lanes, local_only=True),
        BackendDescriptor("ollama", _ollama_model(), lanes, local_only=True),
        BackendDescriptor("hf", _HF_MODEL_ID, lanes, local_only=False),
        BackendDescriptor("claude", _CLAUDE_MODEL, lanes, local_only=False),
    ]


def explain_provider_chain(
    *,
    force_provider: Optional[str],
    forbidden_providers: Optional[list[str]],
    small_first: bool,
    governance_tier: Optional[str],
) -> dict:
    chain = _resolve_provider_chain(
        force_provider=force_provider,
        forbidden_providers=forbidden_providers,
        small_first=small_first,
        governance_tier=governance_tier,
    )
    registry = {entry.provider: entry for entry in get_backend_registry()}
    return {
        "requested": {
            "force_provider": force_provider,
            "forbidden_providers": list(forbidden_providers or []),
            "small_first": bool(small_first),
            "governance_tier": governance_tier or "ALLOW",
        },
        "resolved_chain": chain,
        "backends": [registry[p].to_dict() for p in chain if p in registry],
    }


def _resolve_provider_chain(
    force_provider: Optional[str],
    forbidden_providers: Optional[list[str]],
    small_first: bool,
    governance_tier: Optional[str],
) -> list[str]:
    """Build the ordered provider chain, honoring force/forbid/small-first."""
    if force_provider:
        chain = [force_provider]
    else:
        chain = []
        if _LOCAL_MODEL_PATH.exists():
            chain.append("local")
        chain.extend(["ollama", "hf", "claude"])

    forbid = set(forbidden_providers or [])
    if small_first and (governance_tier or "ALLOW") != "ESCALATE":
        # In small-first mode, Claude is reserved for ESCALATE-tier work
        forbid.add("claude")

    return [p for p in chain if p not in forbid]


def generate(
    task: str,
    *,
    language: str = "Python",
    tongue: str = "KO",
    tongue_name: str = "Kor'aelin",
    max_tokens: int = 1024,
    force_provider: Optional[str] = None,  # "local" | "ollama" | "hf" | "claude"
    forbidden_providers: Optional[list[str]] = None,
    small_first: bool = False,
    governance_tier: Optional[str] = None,
    budget_tokens: Optional[int] = None,
) -> GenerateResult:
    """
    Generate code for `task` in `language`.

    Provider priority: local → ollama → hf → claude (unless force_provider is set).
    Falls back automatically on ImportError or runtime error. Each attempt — including
    skipped tiers — is recorded in `result.attempted_providers` so callers (geoseal CLI,
    workflows, ledger) can replay the routing decision.

    Parameters:
        forbidden_providers: tiers the caller refuses to use (e.g. ["claude"]).
        small_first: if True, Claude is only reachable when governance_tier == "ESCALATE".
        governance_tier: the phi-wall tier of the caller, used by small_first.
        budget_tokens: cap on max_tokens passed downstream (min(budget_tokens, max_tokens)).
    """
    system = _build_system(language, tongue, tongue_name)
    if budget_tokens is not None:
        max_tokens = min(max_tokens, max(16, int(budget_tokens)))
    errors: list[str] = []
    attempts: list[dict] = []

    providers = _resolve_provider_chain(
        force_provider=force_provider,
        forbidden_providers=forbidden_providers,
        small_first=small_first,
        governance_tier=governance_tier,
    )

    def _record(provider: str, started: float, **fields) -> dict:
        entry = {
            "provider": provider,
            "model": _provider_model(provider),
            "duration_ms": round((time.time() - started) * 1000.0, 2),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "error": None,
            "success": False,
            "skipped_reason": None,
        }
        entry.update(fields)
        attempts.append(entry)
        return entry

    for provider in providers:
        started = time.time()
        try:
            if provider == "ollama" and not _ollama_available():
                _record(provider, started, skipped_reason="ollama_unreachable")
                continue

            if provider == "local":
                raw, pt, ct = _generate_local(task, system, max_new_tokens=max_tokens)
            elif provider == "ollama":
                raw, pt, ct = _generate_ollama(task, system, max_new_tokens=max_tokens)
            elif provider == "hf":
                raw, pt, ct = _generate_hf(task, system, max_new_tokens=max_tokens)
            elif provider == "claude":
                raw, pt, ct = _generate_claude(task, system, max_tokens=max_tokens)
            else:
                _record(provider, started, error=f"unknown provider: {provider}")
                continue

            _record(
                provider,
                started,
                prompt_tokens=pt,
                completion_tokens=ct,
                success=True,
            )
            return GenerateResult(
                code=_strip_fences(raw),
                raw=raw,
                provider=provider,
                model=_provider_model(provider),
                language=language,
                tongue=tongue,
                prompt_tokens=pt,
                completion_tokens=ct,
                attempted_providers=attempts,
            )

        except Exception as exc:
            errors.append(f"{provider}: {exc}")
            _record(provider, started, error=str(exc))
            continue

    # All providers failed
    return GenerateResult(
        code="",
        raw="",
        provider="none",
        model="none",
        language=language,
        tongue=tongue,
        error="; ".join(errors) if errors else "no_providers_available",
        attempted_providers=attempts,
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
