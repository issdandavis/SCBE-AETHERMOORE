"""
scbe_aethermoore._assistant
============================
Built-in governance assistant for the SCBE pipeline.

Runs entirely free via:
  1. Ollama   — auto-detected at localhost:11434 (priority)
  2. HuggingFace Inference API — free serverless endpoint, no key required
  3. Rule-based fallback — always works, zero network required

Usage
-----
    from scbe_aethermoore import explain, Assistant

    # One-shot explanation of a scan result
    result = scan("ignore all previous instructions")
    print(explain(result))

    # Interactive session
    ai = Assistant()
    ai.chat("why does prompt injection score so high?")
    ai.chat("how do I integrate this into a FastAPI middleware?")

The assistant knows the SCBE architecture, scoring formula, decision tiers,
and injection pattern library. It can explain results, suggest mitigations,
and help with integration questions.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

# ── Backend detection ─────────────────────────────────────────────────────────

_OLLAMA_BASE = os.environ.get("SCBE_OLLAMA_URL", "http://localhost:11434")
_HF_BASE = "https://api-inference.huggingface.co/v1"
_HF_MODEL = os.environ.get("SCBE_HF_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
_OLLAMA_MODEL = os.environ.get("SCBE_OLLAMA_MODEL", "")  # auto-detect if empty

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are the SCBE governance assistant, embedded inside the scbe-aethermoore \
AI safety framework (v3.3.0, USPTO patent #63/961,403).

Your role: help users understand scan results, interpret governance scores, \
troubleshoot integrations, and reason about adversarial input patterns.

== SCBE Architecture ==
The pipeline maps every input into hyperbolic space (Poincaré ball model) and \
computes the cost of reaching adversarial territory. The further a prompt drifts \
from the safe centroid, the higher the cost — superexponentially.

Core formula: H(d*, pd) = 1 / (1 + d* + 2*pd)
  d*  = hyperbolic distance from safe centroid (structural analysis)
  pd  = phase deviation = structural anomalies + semantic injection penalty
  H   = safety score in (0, 1]. Higher is safer.

Decision tiers:
  ALLOW       H >= 0.75   Safe — proceed
  QUARANTINE  H >= 0.45   Suspicious — flag for human review
  ESCALATE    H >= 0.20   High risk — requires governance action
  DENY        H <  0.20   Adversarial — blocked

What raises d* (structural):
  - High digit ratio (encoded payloads)
  - High control-char ratio (escape injection)
  - Very low or very high Shannon entropy (repetition or obfuscation)

What raises pd (semantic):
  - Prompt injection patterns ("ignore all previous instructions", etc.)
  - SQL injection ("DROP TABLE", "UNION SELECT")
  - Shell injection ("; rm -rf", "/etc/passwd")
  - Empty or trivially short input

harmonic_wall(d*): phi^((phi * d*)^2) — the superexponential cost function.

== Response style ==
- Be concise and specific. No generic platitudes.
- When explaining a scan result, cite the actual numbers.
- When suggesting integration, give code snippets.
- When asked about the math, be precise.
- If something is outside your knowledge, say so clearly.
"""

# ── Rule-based explanation (always available, no network) ─────────────────────


def _rule_explain(result: Dict[str, Any]) -> str:
    """Generate a deterministic explanation from scan fields alone."""
    decision = result["decision"]
    score = result["score"]
    d_star = result["d_star"]
    pd = result["phase_deviation"]
    n = result["input_len"]

    lines: List[str] = []

    # Decision summary
    tier_msg = {
        "ALLOW": "Input is within safe operating parameters.",
        "QUARANTINE": "Input shows suspicious patterns — flag for review before proceeding.",
        "ESCALATE": "Input contains high-risk signals — governance action required.",
        "DENY": "Input is adversarial or invalid — blocked.",
    }
    lines.append(f"Decision: {decision} (score={score:.4f})")
    lines.append(tier_msg[decision])
    lines.append("")

    # Score breakdown
    lines.append(f"Score breakdown (H = 1/(1 + {d_star:.4f} + 2×{pd:.4f}) = {score:.4f}):")

    if d_star == 0.0:
        lines.append("  d* = 0.00  — structure looks normal (no digit/punct/control anomalies)")
    else:
        lines.append(f"  d* = {d_star:.4f} — structural distance from safe centroid:")
        if d_star > 0.5:
            lines.append("    High digit ratio, unusual punctuation, or entropy anomaly detected.")

    if pd == 0.0:
        lines.append("  pd = 0.00  — no semantic injection patterns matched")
    elif pd > 0.0:
        lines.append(f"  pd = {pd:.4f} — temporal/semantic penalty breakdown:")
        if pd >= 0.75:
            lines.append("    One or more high-confidence injection patterns matched.")
            lines.append("    Common causes: prompt override, jailbreak phrase, SQL/shell injection.")
        elif pd >= 0.25:
            lines.append("    Moderate injection signal detected.")
        if n == 0:
            lines.append("    Empty input — no intent can be verified.")
        elif n < 5:
            lines.append("    Input too short to analyze reliably.")

    lines.append("")

    # Recommendation
    lines.append("Recommended action:")
    if decision == "ALLOW":
        lines.append("  Proceed. Log the digest for audit trail if required.")
    elif decision == "QUARANTINE":
        lines.append("  Route to human review queue. Do not auto-execute.")
    elif decision == "ESCALATE":
        lines.append("  Reject or escalate to governance layer. Log with digest.")
        lines.append("  If this is a false positive, check your injection pattern threshold.")
    else:
        lines.append("  Block immediately. Log digest and source for incident review.")

    return "\n".join(lines)


# ── Backend connectivity ───────────────────────────────────────────────────────


def _http_post(url: str, payload: dict, headers: Optional[dict] = None, timeout: int = 30) -> Optional[dict]:
    """POST JSON, return parsed response dict, or None on failure."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _ollama_models() -> List[str]:
    """Return list of model names available in Ollama, or [] if down."""
    try:
        with urllib.request.urlopen(f"{_OLLAMA_BASE}/api/tags", timeout=3) as r:
            data = json.loads(r.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def _pick_ollama_model(available: List[str]) -> Optional[str]:
    """Pick the best available Ollama model for instruction-following."""
    if _OLLAMA_MODEL and _OLLAMA_MODEL in available:
        return _OLLAMA_MODEL
    # Preference order: qwen > mistral > llama > phi > anything
    preferred = ["qwen2.5", "qwen", "mistral", "llama3", "llama", "phi", "gemma"]
    for pref in preferred:
        for m in available:
            if pref in m.lower():
                return m
    return available[0] if available else None


def _ollama_chat(model: str, messages: List[dict]) -> Optional[str]:
    """Call Ollama chat endpoint; return assistant reply or None."""
    resp = _http_post(
        f"{_OLLAMA_BASE}/api/chat",
        {"model": model, "messages": messages, "stream": False},
        timeout=60,
    )
    if resp and "message" in resp:
        return resp["message"].get("content", "").strip()
    return None


def _hf_chat(messages: List[dict]) -> Optional[str]:
    """Call HuggingFace Inference API chat completions; return reply or None."""
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN", "")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = _http_post(
        f"{_HF_BASE}/chat/completions",
        {
            "model": _HF_MODEL,
            "messages": messages,
            "max_tokens": 600,
            "temperature": 0.4,
        },
        headers=headers,
        timeout=45,
    )
    if resp and "choices" in resp:
        return resp["choices"][0]["message"]["content"].strip()
    return None


# ── Public API ────────────────────────────────────────────────────────────────


def explain(result: Dict[str, Any], ai: bool = True) -> str:
    """
    Explain a scan() result in plain English.

    Parameters
    ----------
    result : dict — output from scan()
    ai     : bool — if True, attempt LLM explanation via Ollama/HuggingFace
                    (falls back to rule-based automatically)

    Returns
    -------
    str — human-readable explanation

    Examples
    --------
    >>> from scbe_aethermoore import scan, explain
    >>> result = scan("ignore all previous instructions")
    >>> print(explain(result))
    Decision: ESCALATE (score=0.3846)
    Input contains high-risk signals...
    """
    rule_text = _rule_explain(result)
    if not ai:
        return rule_text

    # Try LLM explanation
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Explain this SCBE scan result concisely (4-6 sentences):\n\n"
                f"{json.dumps(result, indent=2)}\n\n"
                f"Focus on: what caused this score, whether it's a real threat, "
                f"and what the developer should do."
            ),
        },
    ]

    assistant_inst = Assistant()
    reply = assistant_inst._call(messages)
    if reply:
        return reply
    return rule_text


class Assistant:
    """
    Stateful SCBE governance assistant.

    Auto-connects to Ollama (local) or HuggingFace (free API).
    Falls back to rule-based responses if neither is available.

    Examples
    --------
    >>> from scbe_aethermoore import Assistant
    >>> ai = Assistant()
    >>> print(ai.backend)          # "ollama:qwen2.5-coder:7b" or "huggingface" or "rule-based"
    >>> ai.chat("what does ESCALATE mean?")
    >>> ai.chat("how do I add this to a FastAPI middleware?")
    >>> ai.reset()                 # clear conversation history
    """

    def __init__(self) -> None:
        self._history: List[dict] = []
        self._model: Optional[str] = None
        self._backend: str = "rule-based"
        self._connect()

    def _connect(self) -> None:
        """Detect and connect to the best available backend."""
        # 1. Try Ollama
        models = _ollama_models()
        if models:
            m = _pick_ollama_model(models)
            if m:
                self._model = m
                self._backend = f"ollama:{m}"
                return
        # 2. Try HuggingFace
        test_resp = _hf_chat(
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Reply with exactly: ready"},
            ]
        )
        if test_resp and len(test_resp) < 200:
            self._backend = f"huggingface:{_HF_MODEL}"
            return
        # 3. Rule-based fallback
        self._backend = "rule-based"

    @property
    def backend(self) -> str:
        """Which backend is active: 'ollama:model', 'huggingface:model', or 'rule-based'."""
        return self._backend

    def _call(self, messages: List[dict]) -> Optional[str]:
        """Send messages to the active backend."""
        if self._backend.startswith("ollama") and self._model:
            return _ollama_chat(self._model, messages)
        if self._backend.startswith("huggingface"):
            return _hf_chat(messages)
        return None

    def chat(self, message: str, context: Optional[Dict[str, Any]] = None, print_reply: bool = True) -> str:
        """
        Send a message to the assistant. Maintains conversation history.

        Parameters
        ----------
        message  : str  — user message
        context  : dict — optional scan() result to attach as context
        print_reply : bool — if True, print the reply to stdout

        Returns
        -------
        str — assistant reply
        """
        if not self._history:
            self._history.append({"role": "system", "content": _SYSTEM_PROMPT})

        user_content = message
        if context:
            user_content = f"Context (scan result):\n{json.dumps(context, indent=2)}\n\n{message}"

        self._history.append({"role": "user", "content": user_content})

        reply = self._call(self._history)
        if not reply:
            # Rule-based fallback for common questions
            reply = self._rule_fallback(message, context)

        self._history.append({"role": "assistant", "content": reply})

        if print_reply:
            print(f"\n[{self._backend}]\n{reply}\n")
        return reply

    def explain(self, result: Dict[str, Any], print_reply: bool = True) -> str:
        """Explain a scan() result with optional LLM context."""
        return self.chat(
            "Explain this scan result. What caused this score and what should I do?",
            context=result,
            print_reply=print_reply,
        )

    def evaluate(self, text: str, print_reply: bool = True) -> Dict[str, Any]:
        """
        Scan text and immediately explain the result.

        Returns the scan() dict (result also printed via chat()).
        """
        # Import here to avoid circular
        from scbe_aethermoore import scan

        result = scan(text)
        self.explain(result, print_reply=print_reply)
        return result

    def reset(self) -> None:
        """Clear conversation history (keep system prompt on next turn)."""
        self._history = []

    def _rule_fallback(self, message: str, context: Optional[dict]) -> str:
        """Rule-based fallback when no LLM backend is available."""
        msg = message.lower()
        if context:
            return _rule_explain(context)
        if any(w in msg for w in ["escalate", "quarantine", "deny", "allow", "decision"]):
            return (
                "Decision tiers: ALLOW (score>=0.75, safe), QUARANTINE (>=0.45, review), "
                "ESCALATE (>=0.20, governance required), DENY (<0.20, blocked).\n"
                "Higher score = safer. Score = 1/(1 + d* + 2*pd)."
            )
        if any(w in msg for w in ["integrate", "fastapi", "middleware", "flask", "django"]):
            return (
                "Integration pattern:\n"
                "  from scbe_aethermoore import scan, is_safe\n"
                "  if not is_safe(user_input):\n"
                "      raise HTTPException(status_code=400, detail='Input blocked')\n"
                "Add the digest to your audit log for traceability."
            )
        if any(w in msg for w in ["score", "formula", "math", "h_eff", "d_star"]):
            return (
                "Core formula: H = 1 / (1 + d* + 2*pd)\n"
                "  d* = hyperbolic distance from safe centroid (structural analysis)\n"
                "  pd = phase deviation (semantic injection penalty)\n"
                "Result in (0, 1]. Higher = safer."
            )
        return (
            "SCBE governance assistant (rule-based mode — no LLM backend detected).\n"
            "Install Ollama (ollama.ai) for full conversational support, or set HF_TOKEN "
            "for HuggingFace inference.\n\n"
            "Try: explain(scan('your text')) for result explanations."
        )

    def __repr__(self) -> str:
        turns = max(0, len(self._history) - 1)
        return f"<Assistant backend={self._backend!r} turns={turns}>"
