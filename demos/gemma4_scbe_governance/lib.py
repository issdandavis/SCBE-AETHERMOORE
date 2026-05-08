"""SCBE-governed Gemma — pure logic module.

The contract is one function: `govern_and_generate(intent, args, *, router,
gemma_client)`. It runs the user's intent through the SCBE Layer-13
governance gate (LatticeRouter; band -> op -> tongue with the v3 NONE
escape hatch), and only forwards to Gemma when the gate produces an
ALLOW verdict. Any quarantine path returns a typed reason without
touching the LLM.

This module is intentionally I/O-free at import time. The Gemma HTTP
client lazy-imports `httpx` so tests that exercise the routing logic
with a stub adapter don't need an Ollama server or `httpx` installed.

Why this matters for the DEV demo
---------------------------------
LLMs ship without policy enforcement; the system prompt is not a wall.
SCBE puts a 14-layer governance pipeline IN FRONT of the LLM. Layer 13
maps free-form NL into a bounded action space (4 bands x 64 ops x 6
tongues, ~1500 paths) or refuses with a typed quarantine. Adversarial
prose that doesn't fit any code-routing band returns BandNotApplicable
and never reaches the LLM at all.

Petri benchmark (Anthropic, 173 adversarial seeds, 2026-05-08):
  baseline (no gate)  : N/A — every seed reaches the LLM
  v2 (no NONE)        : 11.0% false-allow
  v3 (with NONE)      : 4.6% false-allow  <-- shipped in this module
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Optional

from src.cli.slm_router import (
    BandNotApplicable,
    ClassificationFailure,
    LatticeRouter,
    LoopDetected,
    Mode,
    QuarantineError,
    RoutingResult,
)

# ---------------------------------------------------------------------------
#  Result types
# ---------------------------------------------------------------------------


@dataclass
class GovernedResponse:
    """One end-to-end record per prompt: governance verdict + LLM response.

    On QUARANTINE the gate refused before the LLM was called, so
    `gemma_response` is None and `gemma_model` reflects the model that
    *would* have been called. On ALLOW, `routing` is populated with the
    band/op/tongue selection and `gemma_response` carries the LLM's text.
    """

    intent: str
    verdict: str  # "ALLOW" | "QUARANTINE"
    routing: Optional[Dict[str, Any]] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    gemma_model: Optional[str] = None
    gemma_response: Optional[str] = None
    elapsed_s: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_json(self, *, indent: Optional[int] = 2) -> str:
        return json.dumps(asdict(self), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
#  Gemma HTTP client (Ollama /api/chat)
# ---------------------------------------------------------------------------


@dataclass
class GemmaClient:
    """Tiny wrapper around Ollama's /api/chat for any Gemma variant.

    Defaults aim at the smallest commonly available Gemma (gemma3:1b).
    The model name is passed through verbatim, so users can swap to
    gemma3, gemma3:4b, gemma2, or whatever Gemma 4 ships as the moment
    `ollama pull <name>` lands.
    """

    model: str = "gemma3:1b"
    host: str = "http://localhost:11434"
    request_timeout: float = 60.0
    system_prompt: str = (
        "You are a helpful coding assistant. Answer concisely. "
        "Refuse anything that would cause harm; you are operating under "
        "an external SCBE governance layer that has already classified "
        "this prompt as in-distribution for arithmetic / logic / "
        "comparison / aggregation work."
    )

    def chat(self, user_prompt: str) -> str:
        """Single-turn chat. Returns the model's text response.

        Raises RuntimeError on transport / parse failure so the caller
        can record `gemma_response=None` without conflating it with
        governance refusal.
        """
        try:
            import httpx  # noqa: PLC0415  - lazy so tests don't require it
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("GemmaClient requires `httpx`; install with `pip install httpx`") from exc

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        try:
            resp = httpx.post(f"{self.host}/api/chat", json=body, timeout=self.request_timeout)
            resp.raise_for_status()
        except Exception as exc:
            raise RuntimeError(f"Gemma chat HTTP failed: {type(exc).__name__}: {exc}") from exc
        try:
            payload = resp.json()
            return payload["message"]["content"]
        except Exception as exc:
            raise RuntimeError(f"malformed Gemma reply: {resp.text!r}") from exc


# ---------------------------------------------------------------------------
#  Governance + generation pipeline
# ---------------------------------------------------------------------------


def _routing_to_dict(result: RoutingResult) -> Dict[str, Any]:
    return {
        "op_name": result.op.op_name,
        "op_band": result.op.band,
        "dst_tongue": result.dst_tongue,
        "confidence": result.confidence,
        "reasoning": list(result.reasoning),
    }


def govern_and_generate(
    intent: str,
    args: Mapping[str, str],
    *,
    router: LatticeRouter,
    gemma_client: Optional[GemmaClient] = None,
    mode: Mode = Mode.AUTO,
) -> GovernedResponse:
    """Run intent through SCBE governance, then optionally call Gemma.

    Args:
        intent: free-form natural language prompt
        args: template-variable bindings the lexicon op will need (use
              an empty dict in MANUAL mode where the caller pins band/op)
        router: configured LatticeRouter (with OllamaAdapter for live
              demos, or StubSLMAdapter for tests)
        gemma_client: optional GemmaClient. If omitted, allowed prompts
              return verdict="ALLOW" with gemma_response=None — useful
              for measuring just the governance layer.
        mode: routing mode (AUTO uses SLM, MANUAL needs caller pins)

    Never raises QuarantineError — quarantines are surfaced in the
    result object. Other errors (HTTP, programmer error) still raise.
    """
    started = time.time()
    gemma_model = gemma_client.model if gemma_client is not None else None
    try:
        routing = router.route(intent=intent, args=dict(args), mode=mode)
    except BandNotApplicable as exc:
        return GovernedResponse(
            intent=intent,
            verdict="QUARANTINE",
            error_type="BandNotApplicable",
            error_message=str(exc),
            gemma_model=gemma_model,
            elapsed_s=time.time() - started,
        )
    except ClassificationFailure as exc:
        return GovernedResponse(
            intent=intent,
            verdict="QUARANTINE",
            error_type=type(exc).__name__,
            error_message=str(exc),
            gemma_model=gemma_model,
            elapsed_s=time.time() - started,
        )
    except LoopDetected as exc:
        return GovernedResponse(
            intent=intent,
            verdict="QUARANTINE",
            error_type="LoopDetected",
            error_message=str(exc),
            gemma_model=gemma_model,
            elapsed_s=time.time() - started,
        )
    except QuarantineError as exc:
        return GovernedResponse(
            intent=intent,
            verdict="QUARANTINE",
            error_type=type(exc).__name__,
            error_message=str(exc),
            gemma_model=gemma_model,
            elapsed_s=time.time() - started,
        )

    # ALLOW path — optionally call Gemma.
    response_text: Optional[str] = None
    extra: Dict[str, Any] = {}
    if gemma_client is not None:
        try:
            response_text = gemma_client.chat(intent)
        except RuntimeError as exc:
            extra["gemma_error"] = str(exc)
    return GovernedResponse(
        intent=intent,
        verdict="ALLOW",
        routing=_routing_to_dict(routing),
        gemma_model=gemma_model,
        gemma_response=response_text,
        elapsed_s=time.time() - started,
        extra=extra,
    )
