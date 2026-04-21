"""SCBE Polly chat proxy for Hugging Face Spaces.

Exposes two endpoints compatible with the on-site Polly widget
(`docs/static/polly-companion.js`):

- `GET  /v1/spaceport/status` -> shallow health + backend info
- `POST /v1/chat`             -> {message, tentacle, mode, context} -> {response, model, domain, sources}

OPSEC note (memory: feedback_opsec_no_secrets):
    The HF token MUST live in the Space's private secrets (env var `HF_TOKEN`).
    It is never echoed to the client, never logged verbatim, and never bundled
    into the public repo. If `HF_TOKEN` is missing the Space still serves
    an offline-style status so the client can fall back to its local corpus.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()
HF_MODEL = os.environ.get("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct").strip()
HF_API = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
REQUEST_TIMEOUT = float(os.environ.get("HF_TIMEOUT", "45"))
MAX_NEW_TOKENS = int(os.environ.get("HF_MAX_NEW_TOKENS", "512"))

ALLOWED_ORIGINS = [
    "https://aethermoore.com",
    "https://www.aethermoore.com",
    "https://issdandavis.github.io",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
]

SYSTEM_PROMPT = (
    "You are Polly, the archive keeper for AetherMoore / SCBE-AETHERMOORE.\n"
    "Three lanes:\n"
    "- Lore: canonical AetherMoore world, characters, Sacred Tongues.\n"
    "- Science: SCBE 14-layer pipeline, harmonic wall H(d,pd)=1/(1+phi*d_H+2*pd),\n"
    "  Poincare ball hyperbolic geometry, Quantum Axiom Mesh, governance tiers.\n"
    "- Coding: map human goals through one of six Sacred Tongues\n"
    "  (KO=Python, AV=JavaScript, RU=Rust, CA=Mathematica, UM=Haskell, DR=Markdown).\n"
    "Be precise, honest about what is unverified, and cite concrete filenames,\n"
    "section IDs, or commits when possible."
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    tentacle: str | None = "ollama"
    mode: str | None = "public-site"
    context: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    model: str
    domain: str = "science"
    tentacle: str = "hf-space"
    sources: list[dict[str, Any]] = Field(default_factory=list)


app = FastAPI(title="SCBE Polly Space", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def classify_domain(text: str) -> str:
    lower = text.lower()
    lore_hits = sum(
        t in lower
        for t in ("aethermoor", "polly", "lore", "story", "tongue", "avali", "kor'aelin", "pattern rune")
    )
    sci_hits = sum(
        t in lower
        for t in ("scbe", "harmonic", "pipeline", "poincare", "mathbac", "axiom", "governance", "hydra")
    )
    code_hits = sum(t in lower for t in ("python", "typescript", "rust", "function", "code", "compile"))
    if code_hits and (sci_hits or lore_hits):
        return "hybrid"
    if sci_hits >= lore_hits and sci_hits >= code_hits:
        return "science"
    if lore_hits > sci_hits:
        return "lore"
    return "science"


def build_prompt(req: ChatRequest) -> str:
    parts = [f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>"]
    for ctx in (req.context or []):
        role = ctx.role if ctx.role in {"system", "user", "assistant"} else "user"
        parts.append(f"<|im_start|>{role}\n{ctx.content}<|im_end|>")
    parts.append(f"<|im_start|>user\n{req.message}<|im_end|>")
    parts.append("<|im_start|>assistant\n")
    return "\n".join(parts)


async def hf_generate(prompt: str) -> str:
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN not configured on this Space")
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": MAX_NEW_TOKENS,
            "temperature": 0.4,
            "top_p": 0.9,
            "return_full_text": False,
        },
        "options": {"wait_for_model": True},
    }
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(HF_API, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return str(data[0].get("generated_text", "")).strip()
    if isinstance(data, dict) and "generated_text" in data:
        return str(data["generated_text"]).strip()
    return str(data).strip()


@app.get("/")
def root() -> dict[str, Any]:
    return {"service": "scbe-polly-space", "ok": True, "model": HF_MODEL}


@app.get("/v1/spaceport/status")
def status() -> dict[str, Any]:
    return {
        "ok": True,
        "mode": "hf-space",
        "model": HF_MODEL,
        "token_present": bool(HF_TOKEN),
        "ts": time.time(),
        "backends": {
            "rag": {"topics": [{"name": "lore"}, {"name": "science"}]},
        },
        "active_profiles": ["coding", "tokenizer", "geoseal"],
    }


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if not HF_TOKEN:
        return ChatResponse(
            response=(
                "This Space has no HF_TOKEN configured, so I cannot call the model. "
                "The on-site widget should fall back to the offline corpus."
            ),
            model="none",
            domain=classify_domain(req.message),
        )
    prompt = build_prompt(req)
    try:
        text = await hf_generate(prompt)
    except httpx.HTTPStatusError as err:
        code = err.response.status_code if err.response else -1
        return ChatResponse(
            response=f"Model backend returned HTTP {code}. Try again in a few seconds.",
            model=HF_MODEL,
            domain=classify_domain(req.message),
        )
    except Exception as err:  # noqa: BLE001
        return ChatResponse(
            response=f"Model backend error: {err.__class__.__name__}.",
            model=HF_MODEL,
            domain=classify_domain(req.message),
        )
    return ChatResponse(
        response=text or "No content.",
        model=HF_MODEL,
        domain=classify_domain(req.message),
    )
