"""GeoSeal Console harness bridge.

Small CORS-enabled FastAPI shim that runs paired coding agents on any
OpenAI-compatible chat-completions endpoint so the static GeoSeal Console
(loaded over ``python -m http.server`` or ``file://``) can dispatch
``ask`` / ``explain`` requests through a real model pair instead of
``window.claude.complete``.

Two zero-config backends are supported via ``HF_ROUTER_CHAT_URL``:

* **Local Ollama (default, free)** — point at
  ``http://127.0.0.1:11434/v1/chat/completions`` and use Ollama tags as
  model names (``scbe-geoseal-coder:q8``, ``smollm2:135m``, ...).
* **Hugging Face Inference Router (paid, Pro plan)** — point at
  ``https://router.huggingface.co/v1/chat/completions`` with ``HF_TOKEN``
  set, and use repo IDs of provider-hosted models. Personal fine-tunes on
  the Hub are NOT routable through the public router; deploy them as an
  HF Inference Endpoint, an Ollama Modelfile import, or a local vLLM
  server, and point this bridge at that URL.

Usage::

    # Free local pair (Ollama)
    HF_ROUTER_CHAT_URL=http://127.0.0.1:11434/v1/chat/completions \\
    GEOSEAL_PAIR_MODEL_A=scbe-geoseal-coder:q8 \\
    GEOSEAL_PAIR_MODEL_B=smollm2:135m \\
    HF_TOKEN=local-ollama-no-auth \\
    python -m uvicorn scripts.serve_geoseal_harness:app --host 127.0.0.1 --port 8766

    # HF Router pair (paid)
    export HF_TOKEN=hf_...
    python -m uvicorn scripts.serve_geoseal_harness:app --host 127.0.0.1 --port 8766

Endpoints:
    GET  /health           liveness + token-presence check
    POST /harness/pair     fan-out a single prompt to two models in parallel
    POST /harness/packet   compact AgentPacketV1 fan-out (token-cheap pair mode)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agent_comms import (
    AgentPacketV1,
    BudgetExceeded,
    MergeReport,
    PacketLedger,
    enforce_budget,
    compact_system_prompt,
    evaluate_lane_switch,
    packet_input_tokens,
    provider_registry,
    resolve_provider_model,
)
from src.coding_spine.deterministic_tongue_router import route_prompt

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKET_REF_EXCERPT_BYTES = int(os.getenv("GEOSEAL_PACKET_REF_EXCERPT_BYTES", "2048"))
PACKET_REF_MAX_BYTES = int(os.getenv("GEOSEAL_PACKET_REF_MAX_BYTES", "65536"))
PACKET_LEDGER_MAX = int(os.getenv("GEOSEAL_PACKET_LEDGER_MAX", "256"))
_LEDGER_PATH_ENV = os.getenv("GEOSEAL_PACKET_LEDGER_PATH")
_LEDGER = PacketLedger(
    max_entries=PACKET_LEDGER_MAX,
    path=Path(_LEDGER_PATH_ENV) if _LEDGER_PATH_ENV else None,
    promoted_only=True,
)


HF_ROUTER_URL = os.getenv(
    "HF_ROUTER_CHAT_URL",
    "http://127.0.0.1:11434/v1/chat/completions",
)

DEFAULT_MODEL_A = os.getenv(
    "GEOSEAL_PAIR_MODEL_A",
    "scbe-geoseal-coder:q8",
)
DEFAULT_MODEL_B = os.getenv(
    "GEOSEAL_PAIR_MODEL_B",
    "smollm2:135m",
)


class PairRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=32000)
    system: str | None = Field(default=None, max_length=8000)
    models: list[str] | None = Field(default=None, max_length=2)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    lane_signal: str | None = Field(default=None, max_length=512)


class ReasoningCodePacketRequest(BaseModel):
    intent: str = Field(..., min_length=1, max_length=12000)
    source: str = Field(default="", max_length=64000)
    source_name: str = Field(default="inline", max_length=512)
    language: str = Field(default="python", max_length=64)
    permission_mode: str = Field(default="observe", max_length=64)


def _hf_token() -> str:
    tok = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    if tok:
        return tok
    if any(host in HF_ROUTER_URL for host in ("127.0.0.1", "localhost", "0.0.0.0")):
        return "local-no-auth"
    raise HTTPException(
        status_code=400,
        detail="Hugging Face token not configured (set HF_TOKEN)",
    )


async def _call_hf(
    client: httpx.AsyncClient,
    model: str,
    prompt: str,
    system: str | None,
    temperature: float,
    max_tokens: int,
    token: str | None = None,
) -> dict[str, Any]:
    try:
        provider, resolved_model = resolve_provider_model(model)
    except ValueError as exc:
        return {
            "ok": False,
            "model": model,
            "provider": "unknown",
            "text": "",
            "error": str(exc),
            "latency_ms": 0,
        }
    resolved_token = token or provider.token()
    if not resolved_token:
        return {
            "ok": False,
            "model": resolved_model,
            "provider": provider.provider,
            "text": "",
            "error": f"missing token for provider {provider.provider}; set one of {','.join(provider.api_key_env)}",
            "latency_ms": 0,
        }
    payload = {
        "model": resolved_model,
        "messages": [
            {
                "role": "system",
                "content": system
                or "You are a paired coding agent in the GeoSeal Console. Be concise and emit valid JSON when asked.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {resolved_token}",
        "Content-Type": "application/json",
    }
    started = time.perf_counter()
    try:
        resp = await client.post(provider.chat_url, json=payload, headers=headers, timeout=60.0)
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "model": resolved_model,
            "provider": provider.provider,
            "text": "",
            "error": f"transport: {type(exc).__name__}: {exc}",
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    latency_ms = int((time.perf_counter() - started) * 1000)
    if resp.status_code >= 400:
        return {
            "ok": False,
            "model": resolved_model,
            "provider": provider.provider,
            "text": "",
            "error": f"hf_{resp.status_code}: {resp.text[:400]}",
            "latency_ms": latency_ms,
        }
    try:
        data = resp.json()
    except ValueError:
        return {
            "ok": False,
            "model": resolved_model,
            "provider": provider.provider,
            "text": "",
            "error": "non-json response from HF router",
            "latency_ms": latency_ms,
        }
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    text = (message.get("content") or "").strip()
    return {
        "ok": bool(text),
        "model": resolved_model,
        "provider": provider.provider,
        "provider_family": provider.family,
        "tool_adapter": provider.tool_adapter,
        "text": text,
        "finish_reason": choice.get("finish_reason"),
        "usage": data.get("usage") or {},
        "latency_ms": latency_ms,
    }


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def _normalize_json(text: str) -> str | None:
    try:
        return json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return None


def _agree(a: str, b: str) -> bool:
    """Loose agreement: identical JSON/text or one text contained in the other."""

    if not a or not b:
        return False
    ja, jb = _normalize_json(a), _normalize_json(b)
    if ja is not None and jb is not None:
        return ja == jb
    na, nb = _normalize(a), _normalize(b)
    if na == nb:
        return True
    short, long_ = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(short) >= 24 and short in long_:
        return True
    return False


app = FastAPI(title="GeoSeal Harness Bridge", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8765",
        "http://localhost:8765",
        "http://127.0.0.1:8766",
        "http://localhost:8766",
        "null",  # file:// origins
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "hf_token_present": bool(
            os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
        ),
        "default_pair": [DEFAULT_MODEL_A, DEFAULT_MODEL_B],
        "router": HF_ROUTER_URL,
        "providers": {name: provider.status() for name, provider in provider_registry().items()},
    }


@app.post("/harness/pair")
async def harness_pair(req: PairRequest) -> dict[str, Any]:
    pair = req.models or [DEFAULT_MODEL_A, DEFAULT_MODEL_B]
    if len(pair) == 1:
        pair = [pair[0], pair[0]]
    if len(pair) != 2:
        raise HTTPException(status_code=400, detail="exactly two models required")
    lane = evaluate_lane_switch(pair, signal=req.lane_signal)

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            _call_hf(client, pair[0], req.prompt, req.system, req.temperature, req.max_tokens, None),
            _call_hf(client, pair[1], req.prompt, req.system, req.temperature, req.max_tokens, None),
        )
    a, b = results
    return {
        "a": a,
        "b": b,
        "deterministic_route": route_prompt(req.prompt).as_json(),
        "lane_switch": lane.to_dict(),
        "agree": _agree(a.get("text", ""), b.get("text", "")),
        "both_ok": bool(a.get("ok") and b.get("ok")),
    }


@app.post("/harness/reasoning-code-packet")
async def harness_reasoning_code_packet(req: ReasoningCodePacketRequest) -> dict[str, Any]:
    from src.coding_spine.bijective_reasoning_code_packet import build_bijective_reasoning_code_packet

    packet = build_bijective_reasoning_code_packet(
        intent=req.intent,
        source=req.source,
        language=req.language,
        source_name=req.source_name,
        permission_mode=req.permission_mode,
    )
    return {"packet": packet}


class PacketRequest(BaseModel):
    """Compact pair-mode request keyed on AgentPacketV1.

    The packet's `request` is the only prose sent to the model pair;
    `context_refs` are dereferenced locally and summarized as short tags
    (kind, value, byte size) instead of being pasted in. An optional
    `include_excerpts` flag adds a small head-of-file excerpt per resolvable
    ref, capped by GEOSEAL_PACKET_REF_EXCERPT_BYTES.
    """

    packet: dict[str, Any] = Field(..., description="AgentPacketV1.to_dict()")
    models: list[str] | None = Field(default=None, max_length=2)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    include_excerpts: bool = Field(default=False)
    bypass_ledger: bool = Field(default=False, description="Skip dedup short-circuit and force a fresh fan-out")
    lane_signal: str | None = Field(default=None, max_length=512)


def _resolve_path_ref(value: str) -> Path | None:
    """Resolve a path ref to an absolute path inside REPO_ROOT, or None."""
    try:
        candidate = (REPO_ROOT / value).resolve()
    except (OSError, ValueError):
        return None
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


def _dereference_refs(packet: AgentPacketV1, include_excerpts: bool) -> tuple[list[dict[str, Any]], list[str]]:
    """Dereference packet.context_refs against the local repo.

    Returns (summaries, evidence_tags). Refs that don't resolve get
    {"resolved": False} entries; nothing is fetched over the network.
    """
    summaries: list[dict[str, Any]] = []
    evidence: list[str] = []
    total_bytes = 0
    for ref in packet.context_refs:
        entry: dict[str, Any] = {"kind": ref.kind, "value": ref.value, "resolved": False}
        path: Path | None = None
        if ref.kind == "path":
            path = _resolve_path_ref(ref.value)
        elif ref.kind == "manifest_id":
            candidate = REPO_ROOT / "training-data" / "manifests" / f"{ref.value}-manifest.json"
            if candidate.is_file():
                path = candidate
        if path is not None and total_bytes < PACKET_REF_MAX_BYTES:
            try:
                data = path.read_bytes()
            except OSError:
                summaries.append(entry)
                continue
            sha = hashlib.sha256(data).hexdigest()
            entry["resolved"] = True
            entry["bytes"] = len(data)
            entry["sha256"] = sha
            entry["path"] = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
            if ref.kind == "sha256" and ref.value != sha:
                evidence.append(f"hash:mismatch:{entry['path']}")
            elif ref.kind == "sha256":
                evidence.append(f"hash:matched:{entry['path']}")
            if include_excerpts:
                excerpt = data[:PACKET_REF_EXCERPT_BYTES].decode("utf-8", errors="replace")
                entry["excerpt"] = excerpt
            total_bytes += len(data)
        summaries.append(entry)
    return summaries, evidence


def _build_packet_prompt(packet: AgentPacketV1, ref_summaries: list[dict[str, Any]]) -> str:
    """Build the compact prompt sent to each model.

    Only the packet.request prose travels over the wire as instruction; refs
    appear as short tagged lines, not pasted content (unless excerpts opt-in).
    """
    lines: list[str] = []
    lines.append(f"task_id: {packet.task_id}")
    lines.append(f"phase: {packet.phase}")
    lines.append(
        f"route: tongue={packet.route.tongue} domain={packet.route.domain} " f"permission={packet.route.permission}"
    )
    lines.append(f"state_hash: {packet.state_hash}")
    lines.append(f"expected_output: {packet.expected_output}")
    if ref_summaries:
        lines.append("context_refs:")
        for i, s in enumerate(ref_summaries):
            head = f"  [{i}] kind={s['kind']} value={s['value']}"
            if s.get("resolved"):
                head += f" path={s.get('path')} bytes={s.get('bytes')}"
            else:
                head += " unresolved=true"
            lines.append(head)
            if s.get("excerpt"):
                lines.append("    excerpt:")
                for line in s["excerpt"].splitlines()[:40]:
                    lines.append(f"    | {line}")
    lines.append("")
    lines.append(f"request: {packet.request}")
    return "\n".join(lines)


def _decide(both_ok: bool, agree: bool) -> str:
    if both_ok and agree:
        return "promote"
    if both_ok or agree:
        return "hold"
    return "reject"


@app.post("/harness/packet")
async def harness_packet(req: PacketRequest) -> dict[str, Any]:
    """Token-cheap counterpart to /harness/pair.

    Accepts an AgentPacketV1 dict, validates + budget-checks it, derefs
    context_refs locally, fans the compressed prompt to the model pair, and
    returns a MergeReport-shaped verdict.
    """
    try:
        packet = AgentPacketV1.from_dict(req.packet)
        packet.validate()
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid packet: {exc}") from exc

    try:
        enforce_budget(packet)
    except BudgetExceeded as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    ref_summaries, hash_evidence = _dereference_refs(packet, req.include_excerpts)
    estimated_input_tokens = packet_input_tokens(packet)

    if not req.bypass_ledger:
        cached = _LEDGER.seen(packet)
        if cached is not None:
            cached_dict = cached.to_dict()
            cached_evidence = list(cached_dict.get("evidence", []))
            if "ledger:hit" not in cached_evidence:
                cached_evidence.append("ledger:hit")
            cached_dict["evidence"] = cached_evidence
            cached_dict["task_id"] = packet.task_id
            cached_delta = dict(cached_dict.get("delta", {}))
            cached_delta["cached"] = True
            cached_delta["estimated_input_tokens"] = estimated_input_tokens
            cached_dict["delta"] = cached_delta
            return {
                "task_id": packet.task_id,
                "route": {
                    "tongue": packet.route.tongue,
                    "domain": packet.route.domain,
                    "permission": packet.route.permission,
                },
                "deterministic_route": route_prompt(packet.request).as_json(),
                "ref_summaries": ref_summaries,
                "merge_report": cached_dict,
                "a": {"ok": True, "model": "ledger", "text": "", "latency_ms": 0},
                "b": {"ok": True, "model": "ledger", "text": "", "latency_ms": 0},
                "cached": True,
            }

    prompt = _build_packet_prompt(packet, ref_summaries)
    pair = req.models or [DEFAULT_MODEL_A, DEFAULT_MODEL_B]
    if len(pair) == 1:
        pair = [pair[0], pair[0]]
    if len(pair) != 2:
        raise HTTPException(status_code=400, detail="exactly two models required")
    lane = evaluate_lane_switch(pair, signal=req.lane_signal)

    first_provider, _ = resolve_provider_model(pair[0])
    system_msg = compact_system_prompt(
        phase=packet.phase,
        tongue=packet.route.tongue,
        domain=packet.route.domain,
        expected_output=packet.expected_output,
        adapter=first_provider.tool_adapter,
    )

    async with httpx.AsyncClient() as client:
        a, b = await asyncio.gather(
            _call_hf(client, pair[0], prompt, system_msg, req.temperature, req.max_tokens, None),
            _call_hf(client, pair[1], prompt, system_msg, req.temperature, req.max_tokens, None),
        )

    text_a = a.get("text", "")
    text_b = b.get("text", "")
    both_ok = bool(a.get("ok") and b.get("ok"))
    agree = _agree(text_a, text_b)
    decision = _decide(both_ok, agree)
    if decision == "promote" and not lane.ok:
        decision = "hold"

    evidence: list[str] = []
    evidence.append(f"models:{pair[0]}|{pair[1]}")
    evidence.append(f"providers:{a.get('provider')}|{b.get('provider')}")
    evidence.append(f"tool_adapters:{a.get('tool_adapter')}|{b.get('tool_adapter')}")
    evidence.append(f"lane_switch:{'ok' if lane.ok else 'flagged'}")
    evidence.append(f"lane_cost:{lane.cost}")
    evidence.append(f"lane_reason:{lane.reason}")
    evidence.append(f"both_ok:{str(both_ok).lower()}")
    evidence.append(f"agree:{str(agree).lower()}")
    evidence.extend(hash_evidence)
    contact_points: list[str] = [
        f"hard:harness_pair",
        f"near:{packet.route.domain}",
        f"phase:{packet.phase}",
    ]
    delta: dict[str, Any] = {
        "estimated_input_tokens": estimated_input_tokens,
        "latency_ms_a": a.get("latency_ms"),
        "latency_ms_b": b.get("latency_ms"),
        "refs_resolved": sum(1 for s in ref_summaries if s.get("resolved")),
        "refs_total": len(ref_summaries),
        "lane_switch": lane.to_dict(),
    }

    report = MergeReport(
        claim=f"packet {packet.task_id} {packet.phase}/{packet.expected_output}",
        delta=delta,
        evidence=evidence,
        contact_points=contact_points,
        decision=decision,
        task_id=packet.task_id,
    )
    report.validate()

    if not req.bypass_ledger:
        _LEDGER.record(packet, report)

    return {
        "task_id": packet.task_id,
        "route": {
            "tongue": packet.route.tongue,
            "domain": packet.route.domain,
            "permission": packet.route.permission,
        },
        "deterministic_route": route_prompt(packet.request).as_json(),
        "ref_summaries": ref_summaries,
        "lane_switch": lane.to_dict(),
        "merge_report": report.to_dict(),
        "a": {
            "ok": a.get("ok"),
            "provider": a.get("provider"),
            "model": a.get("model"),
            "tool_adapter": a.get("tool_adapter"),
            "text": text_a,
            "latency_ms": a.get("latency_ms"),
        },
        "b": {
            "ok": b.get("ok"),
            "provider": b.get("provider"),
            "model": b.get("model"),
            "tool_adapter": b.get("tool_adapter"),
            "text": text_b,
            "latency_ms": b.get("latency_ms"),
        },
    }
