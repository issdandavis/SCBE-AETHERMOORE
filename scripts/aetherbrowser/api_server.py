"""AetherBrowser API Server — Backend for the AetherBrowser Mobile PWA shell.

Serves the five tab surfaces (Browse, Chat, Rooms, Vault, Ops) as REST endpoints.

Start:
    python scripts/aetherbrowser/api_server.py
    # or
    python -m uvicorn scripts.aetherbrowser.api_server:app --host 0.0.0.0 --port 8100

Default port: 8100
"""

from __future__ import annotations

import asyncio
from collections import deque
import datetime
import json
import logging
import os
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
#  Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = ROOT / "config"
TRUSTED_SITES_PATH = CONFIG_DIR / "security" / "trusted_external_sites.json"
ENV_FILE = CONFIG_DIR / "connector_oauth" / ".env.connector.oauth"
WORKFLOWS_DIR = ROOT / "workflows" / "momentum"
MOMENTUM_RUNS_DIR = ROOT / "artifacts" / "momentum_trains"
CHESSBOARD_ARTIFACTS_DIR = ROOT / "artifacts" / "chessboard"
IDE_LOGS_DIR = ROOT / "artifacts" / "ai_ide_logs"
IDE_CHAT_LOG = IDE_LOGS_DIR / "chat.jsonl"
IDE_CLI_LOG = IDE_LOGS_DIR / "cli.jsonl"
KNOWLEDGE_SEARCH_ROOTS: tuple[Path, ...] = (ROOT / "notes", ROOT / "docs")
KNOWLEDGE_SUFFIXES = {".md", ".txt", ".html"}
DEFAULT_OLLAMA_MODEL = os.environ.get("AETHERBOT_OLLAMA_MODEL", "issdandavis7795/AetherBot").strip()
DEFAULT_HF_CHAT_MODEL = (
    os.environ.get("AETHERBOT_HF_MODEL", "").strip()
    or os.environ.get("HF_CHAT_MODEL", "").strip()
)
HF_CHAT_ROUTER_URL = os.environ.get("HF_CHAT_ROUTER_URL", "https://router.huggingface.co/v1/chat/completions").strip()
SAFE_VAULT_ROOT = (ROOT / "notes").resolve()

MOMENTUM_TRAIN_CONFIGS: dict[str, Path] = {
    "daily_ops": WORKFLOWS_DIR / "daily_ops_train.json",
    "chessboard_dev_stack": WORKFLOWS_DIR / "chessboard_dev_stack_train.json",
}

CLI_DOCS_REGISTRY: dict[str, Path] = {
    "fast-access": ROOT / "docs" / "FAST_ACCESS_GUIDE.md",
    "system-anatomy": ROOT / "docs" / "SYSTEM_ANATOMY.md",
    "docs-catalog": ROOT / "docs" / "DOCS_CATALOG.md",
    "aetherbrowser-config": ROOT / "docs" / "specs" / "AETHERBROWSER_CONFIG.md",
    "aetherbrowser-search-mesh": ROOT / "docs" / "specs" / "aetherbrowser_search_mesh.md",
    "aetherbrowser-first-runbook": ROOT / "docs" / "operations" / "aetherbrowser_browser_first_runbook.md",
}

# Add project root + src to path so we can import SCBE modules
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Lazy-load the runtime gate (best effort — works even if deps are missing)
# ---------------------------------------------------------------------------

_runtime_gate = None


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str) -> Optional[float]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        logger.warning("Ignoring invalid float env %s=%r", name, raw)
        return None


def _runtime_gate_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "coords_backend": os.environ.get("SCBE_COORDS_BACKEND", "semantic"),
    }
    if _env_flag("SCBE_USE_CLASSIFIER"):
        kwargs["use_classifier"] = True
    if _env_flag("SCBE_USE_TRICHROMATIC_GOVERNANCE"):
        kwargs["use_trichromatic_governance"] = True

    classifier_model_dir = os.environ.get("SCBE_CLASSIFIER_MODEL_DIR", "").strip()
    if classifier_model_dir:
        kwargs["classifier_model_dir"] = classifier_model_dir

    quarantine_threshold = _env_float("SCBE_CLASSIFIER_QUARANTINE_THRESHOLD")
    if quarantine_threshold is not None:
        kwargs["classifier_quarantine_threshold"] = quarantine_threshold

    deny_threshold = _env_float("SCBE_CLASSIFIER_DENY_THRESHOLD")
    if deny_threshold is not None:
        kwargs["classifier_deny_threshold"] = deny_threshold

    trichromatic_quarantine = _env_float("SCBE_TRICHROMATIC_QUARANTINE_THRESHOLD")
    if trichromatic_quarantine is not None:
        kwargs["trichromatic_quarantine_threshold"] = trichromatic_quarantine

    trichromatic_deny = _env_float("SCBE_TRICHROMATIC_DENY_THRESHOLD")
    if trichromatic_deny is not None:
        kwargs["trichromatic_deny_threshold"] = trichromatic_deny

    return kwargs


def _get_gate():
    """Return a shared RuntimeGate instance, initialised on first call."""
    global _runtime_gate
    if _runtime_gate is None:
        try:
            from governance.runtime_gate import RuntimeGate
            _runtime_gate = RuntimeGate(**_runtime_gate_kwargs())
        except Exception:
            try:
                from src.governance.runtime_gate import RuntimeGate
                _runtime_gate = RuntimeGate(**_runtime_gate_kwargs())
            except Exception:
                logger.debug("RuntimeGate unavailable, governance gating disabled")
                _runtime_gate = None
    return _runtime_gate


# ---------------------------------------------------------------------------
#  Load trusted sites registry
# ---------------------------------------------------------------------------

def _load_trusted_sites() -> dict:
    """Load the trusted external sites JSON, returning the parsed dict."""
    try:
        return json.loads(TRUSTED_SITES_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("Suppressed error", exc_info=True)
        return {}


def _load_env():
    """Load .env.connector.oauth into os.environ (best-effort)."""
    if ENV_FILE.exists():
        try:
            for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
        except Exception:
            logger.debug("Failed to load connector oauth env file", exc_info=True)


_load_env()

# ---------------------------------------------------------------------------
#  SCBE-AETHERMOORE Training Lab logging (Hugging Face training export lane)
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: list[re.Pattern[str]] = [
    # SSH public keys pasted into chat
    re.compile(r"\bssh-(rsa|ed25519)\s+[A-Za-z0-9+/=]{20,}\b"),
    # Generic KEY=... / TOKEN: ... etc
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*([^\s\"']{8,})"),
    # Common prefix-style keys
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    # Hugging Face tokens
    re.compile(r"\bhf_[A-Za-z0-9]{10,}\b"),
    # Bearer tokens
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
    # Long opaque tokens (avoid grabbing normal code identifiers by requiring mixed charset + length)
    re.compile(r"\b[A-Za-z0-9_-]{40,}\b"),
]


def _scrub_text(text: str) -> str:
    if not text:
        return text
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


def _scrub_obj(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, str):
        return _scrub_text(obj)
    if isinstance(obj, list):
        return [_scrub_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _scrub_obj(v) for k, v in obj.items()}
    return obj


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    try:
        IDE_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        safe = _scrub_obj(record)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(safe, ensure_ascii=True) + "\n")
    except Exception:
        # Logging must never break the API server.
        logger.debug("Failed to append JSONL record to %s", path, exc_info=True)


def _tail_jsonl(path: Path, n: int) -> list[dict[str, Any]]:
    try:
        if not path.exists():
            return []
        dq: deque[str] = deque(maxlen=max(1, n))
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    dq.append(line)
        out: list[dict[str, Any]] = []
        for line in dq:
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    out.append(item)
            except Exception:
                logger.debug("Suppressed error", exc_info=True)
                continue
        return out
    except Exception:
        logger.debug("Suppressed error", exc_info=True)
        return []


def _is_path_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except Exception:
        logger.debug("Suppressed error", exc_info=True)
        return False


def _safe_vault_root() -> Path:
    configured = Path(os.environ.get("OBSIDIAN_VAULT", str(SAFE_VAULT_ROOT)))
    resolved = configured.resolve(strict=False)
    if _is_path_within(resolved, SAFE_VAULT_ROOT):
        return resolved
    logger.warning("Rejected unsafe vault root outside allowed tree: %s", configured)
    return SAFE_VAULT_ROOT

# ---------------------------------------------------------------------------
#  FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AetherBrowser API",
    description="Backend for the AetherBrowser Mobile PWA shell — 5-tab surface (Browse, Chat, Rooms, Vault, Ops).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================== #
#  HEALTH CHECK
# =========================================================================== #


@app.get("/api/health")
async def health():
    gate = _get_gate()
    return {
        "status": "ok",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "runtime_gate": "loaded" if gate is not None else "unavailable",
        "trusted_sites": TRUSTED_SITES_PATH.exists(),
        "env_loaded": ENV_FILE.exists(),
    }


# =========================================================================== #
#  TAB 1: BROWSE — Trust Check
# =========================================================================== #


def _classify_url(url: str) -> Dict[str, Any]:
    """Classify a URL against the trusted_external_sites.json registry."""
    registry = _load_trusted_sites()
    tiers = registry.get("tiers", {})
    blocked = registry.get("BLOCKED", {})
    dark_web = registry.get("DARK_WEB", {})

    # Normalise
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    try:
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname or url
    except Exception:
        logger.debug("Suppressed error", exc_info=True)
        hostname = url
    domain = re.sub(r"^www\.", "", hostname)

    # Check blocked patterns
    for pattern in blocked.get("patterns", []):
        # Pattern can be *.tk or pastebin.com
        if fnmatch(domain, pattern) or domain == pattern:
            return {
                "url": url,
                "domain": domain,
                "tier": "BLOCKED",
                "trust_level": "BLOCKED",
                "governance_decision": "DENY",
                "color": "blocked",
            }

    # Check .onion
    if domain.endswith(".onion"):
        return {
            "url": url,
            "domain": domain,
            "tier": "DARK_WEB",
            "trust_level": dark_web.get("trust_level", "QUARANTINE"),
            "governance_decision": "ESCALATE",
            "color": "quarantine",
        }

    # Walk tiers — each has a trust_level and a domains list
    for tier_name, tier_data in tiers.items():
        trust = tier_data.get("trust_level", "UNKNOWN")
        for d in tier_data.get("domains", []):
            if domain == d or domain.endswith("." + d):
                gov = "ALLOW"
                color = "core"
                if trust == "TRUSTED":
                    color = "trusted"
                elif trust == "PROVISIONAL":
                    color = "provisional"
                    gov = "ALLOW"
                return {
                    "url": url,
                    "domain": domain,
                    "tier": tier_name,
                    "trust_level": trust,
                    "governance_decision": gov,
                    "color": color,
                }

    # Unknown
    return {
        "url": url,
        "domain": domain,
        "tier": "UNKNOWN",
        "trust_level": "UNKNOWN",
        "governance_decision": "QUARANTINE",
        "color": "unknown",
    }


@app.get("/api/trust-check")
async def trust_check(url: str = Query(..., description="URL to classify")):
    return _classify_url(url)


# =========================================================================== #
#  TAB 2: CHAT — Governance-scored chat
# =========================================================================== #

PHI = 1.618033988749895
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_WEIGHTS = [PHI ** k for k in range(6)]

# Lightweight heuristic tongue patterns (mirrors the PWA stub but returns float activations)
_TONGUE_PATTERNS = {
    "KO": re.compile(r"\b(what|how|why|do|run|make|build|tell|show|find|get|set|start|stop)\b", re.I),
    "AV": re.compile(r"\b(about|context|describe|explain|history|background|metadata|info)\b", re.I),
    "RU": re.compile(r"\b(prove|verify|confirm|sign|witness|attest|check|test|validate|assert)\b", re.I),
    "CA": re.compile(r"\b(encrypt|hash|calculate|compute|key|token|crypto|cipher|math|formula)\b", re.I),
    "UM": re.compile(r"\b(block|deny|redact|scan|quarantine|threat|secure|protect|guard|firewall)\b", re.I),
    "DR": re.compile(r"\b(schema|struct|format|template|define|type|interface|model|shape|layout)\b", re.I),
}

FIB_SEQUENCE = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
SEARCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "the",
    "this",
    "to",
    "we",
    "what",
    "when",
    "where",
    "which",
    "with",
    "you",
    "your",
}


class ChatRequest(BaseModel):
    message: str
    model: str = "claude"
    mode: Optional[str] = None
    hf_model: Optional[str] = None
    active_file_name: Optional[str] = None
    active_file_content: Optional[str] = None


def _classify_tongues(text: str) -> Dict[str, float]:
    """Return tongue activation scores (0.0-1.0) for each Sacred Tongue."""
    activations: Dict[str, float] = {}
    words = text.split()
    wc = max(len(words), 1)
    for tongue, pattern in _TONGUE_PATTERNS.items():
        hits = len(pattern.findall(text))
        activations[tongue] = round(min(1.0, hits / (wc * 0.3 + 1)), 4)
    # If nothing activated, default KO to 0.5
    if all(v == 0.0 for v in activations.values()):
        activations["KO"] = 0.5
    return activations


class FactCheckRequest(BaseModel):
    question: str
    provider: str = "grounded"
    mode: str = "fact-check"
    max_sources: int = 6
    hf_model: Optional[str] = None
    allow_web: bool = False


def _normalize_text_blob(text: str) -> str:
    if not text:
        return ""
    out = re.sub(r"<[^>]+>", " ", text)
    out = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", out)
    out = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", out)
    out = re.sub(r"\[\[([^\]]+)\]\]", r"\1", out)
    out = re.sub(r"`{1,3}", " ", out)
    out = re.sub(r"[#>*_~|-]", " ", out)
    out = re.sub(r"\s+", " ", out)
    return out.strip()


def _query_terms(text: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", text.lower()):
        if token in SEARCH_STOPWORDS or token in seen:
            continue
        seen.add(token)
        terms.append(token)
    return terms[:12]


def _knowledge_files() -> list[Path]:
    files: list[Path] = []
    for root in KNOWLEDGE_SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in KNOWLEDGE_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 1_500_000:
                    continue
            except OSError:
                logger.debug("Suppressed error", exc_info=True)
                continue
            files.append(path)
    return files


def _public_source_url(path: Path) -> Optional[str]:
    try:
        relative = path.relative_to(ROOT / "docs")
    except ValueError:
        logger.debug("Suppressed error", exc_info=True)
        return None
    return "/" + str(relative).replace("\\", "/")


def _build_snippet(text: str, terms: list[str], max_chars: int = 320) -> str:
    if not text:
        return ""
    lower = text.lower()
    indices = [lower.find(term) for term in terms if lower.find(term) >= 0]
    anchor = min(indices) if indices else 0
    start = max(0, anchor - 110)
    end = min(len(text), anchor + max_chars)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def _search_local_knowledge(query: str, max_sources: int = 6) -> list[dict[str, Any]]:
    query_text = (query or "").strip()
    if not query_text:
        return []
    query_lower = query_text.lower()
    terms = _query_terms(query_text)
    results: list[dict[str, Any]] = []
    for path in _knowledge_files():
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            logger.debug("Suppressed error", exc_info=True)
            continue
        normalized = _normalize_text_blob(raw)
        if not normalized:
            continue
        haystack = normalized.lower()
        path_text = str(path.relative_to(ROOT)).replace("\\", "/").lower()
        score = 0
        if query_lower in haystack:
            score += 8
        if query_lower in path_text:
            score += 8
        for term in terms:
            if term in path_text:
                score += 4
            hits = haystack.count(term)
            if hits:
                score += min(hits, 5)
        if score <= 0:
            continue
        results.append(
            {
                "title": path.stem.replace("-", " ").replace("_", " "),
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "excerpt": _build_snippet(normalized, terms or [query_lower]),
                "score": score,
                "public_url": _public_source_url(path),
            }
        )
    results.sort(key=lambda item: (-int(item["score"]), item["path"]))
    return results[: max(1, min(int(max_sources), 8))]


def _mode_guidance(mode: str) -> str:
    mapping = {
        "fact-check": "Answer only from the evidence packet. Distinguish supported claims from gaps or uncertainty.",
        "research": "Synthesize the evidence packet into a readable research answer, but do not invent support that is not present.",
        "draft": "Use the evidence packet to draft a useful response. Label any sentence that extends beyond the evidence as a draft inference.",
        "code": "Answer like an implementation assistant grounded in the repo notes and docs. Prefer concrete steps, file paths, and constraints.",
        "math": "Answer like a math explainer grounded in the local SCBE corpus. Keep equations and assumptions explicit.",
        "skills": "Answer using the local skill vault and docs as the operating reference. Point to skill paths and likely invocation patterns.",
    }
    return mapping.get(mode, mapping["fact-check"])


def _grounding_prompt(question: str, mode: str, sources: list[dict[str, Any]]) -> str:
    evidence_lines: list[str] = []
    if sources:
        for index, source in enumerate(sources, start=1):
            evidence_lines.append(
                f"[S{index}] {source['path']}\nTitle: {source['title']}\nExcerpt: {source['excerpt']}"
            )
    else:
        evidence_lines.append("[S0] No matching local evidence was found in notes/ or docs/.")
    return (
        "You are AetherBot for the SCBE research surface.\n"
        f"Mode: {mode}\n"
        f"Instruction: {_mode_guidance(mode)}\n"
        "Rules:\n"
        "- Cite supporting claims inline as [S1], [S2], etc.\n"
        "- If the evidence packet is weak, say that directly.\n"
        "- Do not claim you accessed sources outside the provided packet.\n\n"
        "Evidence Packet:\n"
        f"{chr(10).join(evidence_lines)}\n\n"
        f"User question:\n{question}\n\n"
        "Answer:"
    )


def _grounded_fallback_answer(question: str, mode: str, sources: list[dict[str, Any]]) -> str:
    if not sources:
        return (
            "I could not find direct support for that question in the local SCBE notes/docs corpus. "
            "Use a narrower query or route this through a model provider after the retrieval layer is strengthened."
        )
    lines = [
        f"Grounded {mode} packet for: {question}",
        "",
        "Best local evidence:",
    ]
    for index, source in enumerate(sources[:4], start=1):
        lines.append(f"[S{index}] {source['title']} ({source['path']})")
        lines.append(source["excerpt"])
        lines.append("")
    lines.append("This answer is retrieval-only. It summarizes the local evidence packet without a model rewrite.")
    return "\n".join(lines).strip()


def _call_local_ollama(prompt: str, model_id: Optional[str] = None) -> dict[str, Any]:
    try:
        import requests as _req
    except Exception:
        logger.debug("Suppressed error", exc_info=True)
        return {"ok": False, "error": "requests is not available for Ollama calls"}
    chosen_model = (model_id or DEFAULT_OLLAMA_MODEL).strip()
    try:
        response = _req.post(
            "http://localhost:11434/api/generate",
            json={"model": chosen_model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        if response.status_code != 200:
            return {"ok": False, "error": f"Ollama error {response.status_code}", "model": chosen_model}
        payload = response.json() if response.content else {}
        return {"ok": True, "text": str(payload.get("response", "")).strip(), "model": chosen_model}
    except Exception as exc:
        logger.debug("Ollama call failed: %s", exc)
        return {"ok": False, "error": "Ollama unavailable", "model": chosen_model}


def _call_huggingface_chat(prompt: str, model_id: Optional[str] = None) -> dict[str, Any]:
    token = os.environ.get("HF_TOKEN", "").strip()
    chosen_model = (model_id or DEFAULT_HF_CHAT_MODEL).strip()
    if not token:
        return {"ok": False, "error": "HF_TOKEN is not configured", "model": chosen_model or None}
    if not chosen_model:
        return {"ok": False, "error": "No Hugging Face chat model is configured", "model": None}
    payload = {
        "model": chosen_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are AetherBot for SCBE-AETHERMOORE. "
                    "Answer from the supplied evidence packet, cite it as [S1], [S2], etc, and say when support is missing."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 900,
    }
    request = urllib.request.Request(
        HF_CHAT_ROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        logger.debug("Hugging Face HTTP error %s: %s", exc.code, exc.read().decode("utf-8", errors="ignore")[:240])
        return {"ok": False, "error": f"Hugging Face router error {exc.code}", "model": chosen_model}
    except Exception as exc:
        logger.debug("Hugging Face call failed: %s", exc)
        return {"ok": False, "error": "Hugging Face unavailable", "model": chosen_model}
    choice = body.get("choices", [{}])[0] if isinstance(body, dict) else {}
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    text = str(message.get("content", "")).strip()
    if not text:
        return {"ok": False, "error": "Hugging Face returned an empty response", "model": chosen_model}
    return {"ok": True, "text": text, "model": chosen_model}


def _provider_response(provider: str, prompt: str, hf_model: Optional[str] = None) -> dict[str, Any]:
    provider_key = (provider or "grounded").strip().lower()
    if provider_key == "local":
        return _call_local_ollama(prompt)
    if provider_key == "huggingface":
        return _call_huggingface_chat(prompt, model_id=hf_model)
    return {"ok": False, "error": f"Unknown provider: {provider_key}"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    tongues = _classify_tongues(req.message)

    # Run through governance gate if available
    gate = _get_gate()
    gate_result = None
    decision = "ALLOW"
    trust_level = "PROVISIONAL"
    fib_index = 1
    cost = 0.0

    if gate is not None:
        try:
            gr = gate.evaluate(req.message)
            decision = gr.decision.value
            trust_level = gr.trust_level
            fib_index = gr.trust_index
            cost = round(gr.cost, 4)
            gate_result = {
                "decision": decision,
                "cost": cost,
                "spin_magnitude": gr.spin_magnitude,
                "signals": gr.signals,
                "tongue_coords": [round(c, 4) for c in gr.tongue_coords],
            }
        except Exception:
            logger.exception("Runtime gate evaluation failed")
            gate_result = {"error": "runtime gate unavailable"}

    fibonacci_index = min(fib_index, len(FIB_SEQUENCE) - 1)
    fib_value = FIB_SEQUENCE[fibonacci_index]

    # Route to model — Ollama local for "local", stub for others
    response_text = ""
    if req.model in {"local", "huggingface"} and decision != "DENY":
        ctx_lines: list[str] = []
        if req.mode:
            ctx_lines.append(f"MODE: {req.mode}")
        if req.active_file_name:
            ctx_lines.append(f"ACTIVE_FILE: {req.active_file_name}")
        if req.active_file_content:
            content = req.active_file_content
            if len(content) > 12000:
                content = content[:12000] + "\n...[TRUNCATED]..."
            ctx_lines.append("ACTIVE_FILE_CONTENT:\n" + content)
        prompt = req.message
        if ctx_lines:
            prompt = "\n".join(ctx_lines) + "\n\nUSER:\n" + req.message + "\n\nASSISTANT:"
        model_result = await asyncio.to_thread(_provider_response, req.model, prompt, req.hf_model)
        if model_result.get("ok"):
            response_text = str(model_result.get("text", ""))
        else:
            response_text = f"[{req.model.capitalize()} unavailable: {model_result.get('error', 'unknown error')}]"
    elif decision == "DENY":
        response_text = f"[DENIED by governance gate. Cost: {cost}. Signals: {gate_result.get('signals', []) if gate_result else []}]"
    else:
        response_text = (
            f"[{req.model.capitalize()} model not wired yet. "
            f"Governance: {decision}. Trust: {trust_level} (FIB {fib_value}). "
            f"Select 'Local' to use AetherBot via Ollama.]"
        )

    _append_jsonl(
        IDE_CHAT_LOG,
        {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "kind": "chat",
            "request": {
                "message": req.message,
                "model": req.model,
                "mode": req.mode,
                "active_file_name": req.active_file_name,
                "active_file_content_preview": _scrub_text((req.active_file_content or "")[:4000]),
                "active_file_content_len": len(req.active_file_content or ""),
            },
            "response": {
                "text": response_text,
                "tongues": tongues,
                "governance_decision": decision,
                "trust_level": trust_level,
                "fibonacci_index": fibonacci_index,
                "fibonacci_value": fib_value,
                "cost": cost,
            },
        },
    )

    return {
        "response": response_text,
        "tongues": tongues,
        "trust_level": trust_level,
        "fibonacci_index": fibonacci_index,
        "fibonacci_value": fib_value,
        "governance_decision": decision,
        "cost": cost,
        "model": req.model,
        "gate": gate_result,
    }


@app.post("/api/fact-check")
async def fact_check(req: FactCheckRequest):
    question = (req.question or "").strip()
    if not question:
        return {"ok": False, "error": "Question is required"}

    mode = (req.mode or "fact-check").strip().lower()
    provider = (req.provider or "grounded").strip().lower()
    sources = await asyncio.to_thread(_search_local_knowledge, question, req.max_sources)
    grounding_prompt = _grounding_prompt(question, mode, sources)
    answer = _grounded_fallback_answer(question, mode, sources)
    provider_meta: dict[str, Any] = {"provider": provider, "status": "grounded-only"}

    gate = _get_gate()
    gate_result = None
    decision = "ALLOW"
    trust_level = "PROVISIONAL"
    cost = 0.0
    if gate is not None:
        try:
            gr = gate.evaluate(question)
            decision = gr.decision.value
            trust_level = gr.trust_level
            cost = round(gr.cost, 4)
            gate_result = {
                "decision": decision,
                "cost": cost,
                "spin_magnitude": gr.spin_magnitude,
                "signals": gr.signals,
                "tongue_coords": [round(c, 4) for c in gr.tongue_coords],
            }
        except Exception:
            logger.debug("Suppressed error", exc_info=True)
            gate_result = {"error": "Runtime gate evaluation failed"}

    if decision == "DENY":
        answer = "The governance gate denied this request before model routing. Narrow the question and retry."
        provider_meta = {"provider": provider, "status": "blocked-by-governance"}
    elif provider in {"local", "huggingface"}:
        model_result = await asyncio.to_thread(_provider_response, provider, grounding_prompt, req.hf_model)
        provider_meta = {
            "provider": provider,
            "status": "ok" if model_result.get("ok") else "fallback",
            "model": model_result.get("model"),
        }
        if model_result.get("ok"):
            answer = str(model_result.get("text", "")).strip()
        else:
            provider_meta["error"] = model_result.get("error")
            answer = (
                f"{answer}\n\nModel provider note: {model_result.get('error', 'provider unavailable')}."
            )

    _append_jsonl(
        IDE_CHAT_LOG,
        {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "kind": "fact_check",
            "request": {
                "question": question,
                "provider": provider,
                "mode": mode,
                "max_sources": req.max_sources,
                "allow_web": bool(req.allow_web),
            },
            "response": {
                "answer": answer,
                "source_count": len(sources),
                "governance_decision": decision,
                "trust_level": trust_level,
                "cost": cost,
                "provider_meta": provider_meta,
            },
        },
    )

    return {
        "ok": True,
        "question": question,
        "answer": answer,
        "mode": mode,
        "provider": provider,
        "provider_meta": provider_meta,
        "sources": sources,
        "source_count": len(sources),
        "governance_decision": decision,
        "trust_level": trust_level,
        "cost": cost,
        "gate": gate_result,
        "web_search": {
            "enabled": False,
            "requested": bool(req.allow_web),
            "status": "not-wired-yet",
        },
        "training_capture": {
            "logged": True,
            "log_path": str(IDE_CHAT_LOG),
        },
    }


# =========================================================================== #
#  TAB 3: ROOMS — Red Team Sandbox
# =========================================================================== #


class RedTeamRunRequest(BaseModel):
    suite: Optional[str] = None  # Optional: run a specific suite only


@app.post("/api/red-team/run")
async def red_team_run(req: RedTeamRunRequest = RedTeamRunRequest()):
    """Run the adversarial benchmark test suite via subprocess."""
    test_file = ROOT / "tests" / "adversarial" / "test_adversarial_benchmark.py"
    if not test_file.exists():
        return {"error": "Benchmark file not found", "path": str(test_file)}

    cmd = [
        sys.executable, "-m", "pytest",
        str(test_file),
        "-v", "--tb=short", "--no-header", "-q",
    ]

    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(ROOT),
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        # Parse pytest output
        passed = len(re.findall(r" PASSED", stdout))
        failed = len(re.findall(r" FAILED", stdout))
        errors = len(re.findall(r" ERROR", stdout))
        total = passed + failed + errors

        # Extract individual test results
        results = []
        for line in stdout.splitlines():
            if " PASSED" in line or " FAILED" in line or " ERROR" in line:
                status = "PASSED" if " PASSED" in line else ("FAILED" if " FAILED" in line else "ERROR")
                test_name = line.split("::")[1].split(" ")[0] if "::" in line else line.strip()
                results.append({"test": test_name, "status": status})

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "results": results,
            "exit_code": proc.returncode,
            "stdout_tail": stdout[-2000:] if len(stdout) > 2000 else stdout,
            "stderr_tail": stderr[-1000:] if len(stderr) > 1000 else stderr,
        }
    except subprocess.TimeoutExpired:
        logger.debug("Suppressed error", exc_info=True)
        return {"error": "Benchmark timed out (120s limit)", "total": 0, "passed": 0, "failed": 0, "results": []}
    except Exception:
        logger.exception("Red team benchmark execution failed")
        return {"error": "Benchmark execution failed", "total": 0, "passed": 0, "failed": 0, "results": []}


@app.get("/api/red-team/suites")
async def red_team_suites():
    """List available test suites with probe counts."""
    suites_dir = ROOT / "tests" / "adversarial"
    suites = []

    # Known suites from the HTML UI
    known = [
        {"id": "adversarial", "name": "Adversarial Benchmark", "file": "test_adversarial_benchmark.py", "probes": 12},
        {"id": "null-space", "name": "Null-Space Detection", "file": "test_null_space.py", "probes": 9},
        {"id": "hard-negatives", "name": "Hard-Negative Benign", "file": "test_hard_negatives.py", "probes": 11},
        {"id": "phi-poincare", "name": "Phi-Poincare Edge Cases", "file": "test_phi_poincare_edge.py", "probes": 35},
        {"id": "golden-vectors", "name": "Golden Vector Parity", "file": "test_golden_vector_parity.py", "probes": 48},
    ]

    for suite in known:
        path = suites_dir / suite["file"]
        suite["exists"] = path.exists()
        # If the file exists, try to count test functions
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                test_count = len(re.findall(r"^\s*def test_", content, re.MULTILINE))
                if test_count > 0:
                    suite["probes"] = test_count
            except Exception:
                logger.debug("Failed to inspect adversarial suite file %s", path, exc_info=True)
        suites.append(suite)

    return {"suites": suites, "total_probes": sum(s["probes"] for s in suites)}


# =========================================================================== #
#  TAB 4: VAULT — Obsidian Knowledge Graph
# =========================================================================== #


def _run_subprocess(cmd: List[str], timeout: int = 60) -> Dict[str, Any]:
    """Run a subprocess and return stdout/stderr/exit_code."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ROOT),
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        logger.debug("Suppressed error", exc_info=True)
        return {"stdout": "", "stderr": "timeout", "exit_code": -1}
    except Exception:
        logger.exception("Subprocess invocation failed")
        return {"stdout": "", "stderr": "subprocess failed", "exit_code": -1}


@app.get("/api/vault/stats")
async def vault_stats():
    """Scan the Obsidian vault and return stats."""
    vault_sync = ROOT / "scripts" / "apollo" / "obsidian_vault_sync.py"

    # Try running the scan command
    if vault_sync.exists():
        scan_result = await asyncio.to_thread(
            _run_subprocess,
            [sys.executable, str(vault_sync), "scan"],
            timeout=60,
        )
        graph_result = await asyncio.to_thread(
            _run_subprocess,
            [sys.executable, str(vault_sync), "graph"],
            timeout=60,
        )
        stdout = scan_result.get("stdout", "")

        # Try to parse structured output
        notes = 0
        edges = 0
        orphans = 0
        tongues_dist: Dict[str, int] = {}
        sft_pairs = 0

        # Parse lines for metrics
        for line in stdout.splitlines():
            if "notes" in line.lower() or "files" in line.lower():
                nums = re.findall(r"\d+", line)
                if nums:
                    notes = int(nums[0])
            if "edge" in line.lower() or "link" in line.lower():
                nums = re.findall(r"\d+", line)
                if nums:
                    edges = int(nums[0])
            if "orphan" in line.lower():
                nums = re.findall(r"\d+", line)
                if nums:
                    orphans = int(nums[0])

        # Check if the graph JSON exists for more accurate stats
        graph_file = ROOT / "artifacts" / "apollo" / "obsidian_graph.json"
        if graph_file.exists():
            try:
                graph = json.loads(graph_file.read_text(encoding="utf-8"))
                if "stats" in graph and isinstance(graph["stats"], dict):
                    stats = graph["stats"]
                    notes = int(stats.get("total_notes", notes))
                    edges = int(stats.get("total_links", edges))
                    orphans = int(stats.get("orphan_count", orphans))
                    tongues_dist = stats.get("tongues", tongues_dist) if isinstance(stats.get("tongues"), dict) else tongues_dist
                else:
                    if "nodes" in graph and isinstance(graph["nodes"], list):
                        notes = len(graph["nodes"])
                    if "edges" in graph and isinstance(graph["edges"], list):
                        edges = len(graph["edges"])
            except Exception:
                logger.debug("Suppressed error", exc_info=True)

        # Check SFT output
        sft_file = ROOT / "training-data" / "apollo" / "obsidian_vault_sft.jsonl"
        if sft_file.exists():
            try:
                sft_pairs = sum(1 for _ in sft_file.open(encoding="utf-8"))
            except Exception:
                logger.debug("Suppressed error", exc_info=True)

        return {
            "notes": notes,
            "edges": edges,
            "orphans": orphans,
            "tongues": tongues_dist,
            "sft_pairs": sft_pairs,
            "scan_output": stdout[:2000] if stdout else "scan completed",
            "graph_output": graph_result.get("stdout", "")[:1000],
            "exit_code": max(scan_result.get("exit_code", 0), graph_result.get("exit_code", 0)),
        }
    else:
        return {
            "notes": 0,
            "edges": 0,
            "orphans": 0,
            "tongues": {},
            "sft_pairs": 0,
            "scan_output": "vault sync script not found",
            "exit_code": -1,
        }


@app.get("/api/vault/search")
async def vault_search(q: str = Query(..., description="Search query")):
    """Search vault notes by keyword."""
    # Fallback: search the vault directory directly
    vault_path = _safe_vault_root()
    results: List[Dict[str, Any]] = []

    if vault_path.exists():
        try:
            query_lower = q.lower()
            for md_file in vault_path.rglob("*.md"):
                try:
                    resolved_file = md_file.resolve()
                    if md_file.is_symlink() or not _is_path_within(resolved_file, vault_path):
                        logger.warning("Skipping vault search file outside allowed root: %s", md_file)
                        continue
                    content = md_file.read_text(encoding="utf-8", errors="ignore")
                    if query_lower in content.lower() or query_lower in md_file.stem.lower():
                        # Extract first heading
                        heading_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                        title = heading_match.group(1) if heading_match else md_file.stem
                        # Extract snippet around match
                        idx = content.lower().find(query_lower)
                        snippet = content[max(0, idx - 50):idx + 100].replace("\n", " ").strip() if idx >= 0 else ""
                        results.append({
                            "title": title,
                            "path": str(md_file.relative_to(vault_path)),
                            "snippet": snippet[:200],
                            "size": md_file.stat().st_size,
                        })
                        if len(results) >= 20:
                            break
                except Exception:
                    logger.debug("Suppressed vault search read failure for %s", md_file, exc_info=True)
                    continue
        except Exception:
            logger.debug("Suppressed vault search traversal failure for %s", vault_path, exc_info=True)

    # If vault not accessible, try searching docs/ in the repo
    if not results:
        docs_path = ROOT / "docs"
        if docs_path.exists():
            query_lower = q.lower()
            for md_file in docs_path.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8", errors="ignore")
                    if query_lower in content.lower() or query_lower in md_file.stem.lower():
                        heading_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                        title = heading_match.group(1) if heading_match else md_file.stem
                        idx = content.lower().find(query_lower)
                        snippet = content[max(0, idx - 50):idx + 100].replace("\n", " ").strip() if idx >= 0 else ""
                        results.append({
                            "title": title,
                            "path": str(md_file.relative_to(ROOT)),
                            "snippet": snippet[:200],
                            "size": md_file.stat().st_size,
                        })
                        if len(results) >= 20:
                            break
                except Exception:
                    logger.debug("Suppressed docs search read failure for %s", md_file, exc_info=True)
                    continue

    return {"query": q, "count": len(results), "results": results}


@app.post("/api/vault/sync")
async def vault_sync():
    """Trigger vault sync + cloud push."""
    vault_sync_script = ROOT / "scripts" / "apollo" / "obsidian_vault_sync.py"
    if not vault_sync_script.exists():
        return {"error": "obsidian_vault_sync.py not found", "synced": False}

    # Run connect/apply, export SFT, graph build, then cloud sync
    connect_result = await asyncio.to_thread(
        _run_subprocess,
        [sys.executable, str(vault_sync_script), "connect", "--apply"],
        timeout=90,
    )
    export_result = await asyncio.to_thread(
        _run_subprocess,
        [sys.executable, str(vault_sync_script), "export-sft"],
        timeout=90,
    )
    graph_result = await asyncio.to_thread(
        _run_subprocess,
        [sys.executable, str(vault_sync_script), "graph"],
        timeout=60,
    )
    sync_result = await asyncio.to_thread(
        _run_subprocess,
        [sys.executable, str(vault_sync_script), "sync-cloud"],
        timeout=60,
    )

    # Return updated stats as well (used by the Ops tab).
    stats = {"notes": 0, "edges": 0, "orphans": 0, "tongues": {}, "sft_pairs": 0}
    graph_file = ROOT / "artifacts" / "apollo" / "obsidian_graph.json"
    if graph_file.exists():
        try:
            graph = json.loads(graph_file.read_text(encoding="utf-8"))
            if "stats" in graph and isinstance(graph["stats"], dict):
                s = graph["stats"]
                stats["notes"] = int(s.get("total_notes", 0))
                stats["edges"] = int(s.get("total_links", 0))
                stats["orphans"] = int(s.get("orphan_count", 0))
                stats["tongues"] = s.get("tongues", {}) if isinstance(s.get("tongues"), dict) else {}
        except Exception:
            logger.debug("Suppressed obsidian graph stats read failure", exc_info=True)
    sft_file = ROOT / "training-data" / "apollo" / "obsidian_vault_sft.jsonl"
    if sft_file.exists():
        try:
            stats["sft_pairs"] = sum(1 for _ in sft_file.open(encoding="utf-8"))
        except Exception:
            logger.debug("Suppressed obsidian SFT count failure", exc_info=True)

    return {
        "synced": sync_result.get("exit_code", -1) == 0,
        **stats,
        "connect_output": connect_result.get("stdout", "")[:1000],
        "export_output": export_result.get("stdout", "")[:1000],
        "graph_output": graph_result.get("stdout", "")[:1000],
        "sync_output": sync_result.get("stdout", "")[:1000],
        "errors": [
            e
            for e in [
                connect_result.get("stderr", ""),
                export_result.get("stderr", ""),
                graph_result.get("stderr", ""),
                sync_result.get("stderr", ""),
            ]
            if e and e != "timeout"
        ],
    }


# =========================================================================== #
#  TAB 5: OPS — Operational Commands
# =========================================================================== #


@app.post("/api/ops/check-email")
async def ops_check_email():
    """Run the Apollo email reader and return classified digests."""
    script = ROOT / "scripts" / "apollo" / "email_reader.py"
    if not script.exists():
        return {"error": "email_reader.py not found", "digests": []}

    result = await asyncio.to_thread(
        _run_subprocess,
        [sys.executable, str(script)],
        timeout=30,
    )
    return {
        "output": result.get("stdout", "")[:2000],
        "exit_code": result.get("exit_code", -1),
        "errors": result.get("stderr", "")[:500] if result.get("stderr") else None,
    }


@app.post("/api/ops/youtube-review")
async def ops_youtube_review():
    """Run video_review.py review-all."""
    script = ROOT / "scripts" / "apollo" / "video_review.py"
    if not script.exists():
        return {"error": "video_review.py not found"}

    result = await asyncio.to_thread(
        _run_subprocess,
        [sys.executable, str(script), "review-all"],
        timeout=60,
    )
    return {
        "output": result.get("stdout", "")[:2000],
        "exit_code": result.get("exit_code", -1),
        "errors": result.get("stderr", "")[:500] if result.get("stderr") else None,
    }


@app.post("/api/ops/tor-sweep")
async def ops_tor_sweep():
    """Run tor_sweeper.py sweep."""
    script = ROOT / "scripts" / "apollo" / "tor_sweeper.py"
    if not script.exists():
        return {"error": "tor_sweeper.py not found"}

    result = await asyncio.to_thread(
        _run_subprocess,
        [sys.executable, str(script), "sweep"],
        timeout=90,
    )
    return {
        "output": result.get("stdout", "")[:2000],
        "exit_code": result.get("exit_code", -1),
        "errors": result.get("stderr", "")[:500] if result.get("stderr") else None,
    }


@app.post("/api/ops/run-tests")
async def ops_run_tests():
    """Run pytest and return pass/fail summary."""
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-q", "--no-header"]

    result = await asyncio.to_thread(
        _run_subprocess,
        cmd,
        timeout=120,
    )
    stdout = result.get("stdout", "")
    passed = len(re.findall(r" PASSED", stdout))
    failed = len(re.findall(r" FAILED", stdout))
    errors = len(re.findall(r" ERROR", stdout))

    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "total": passed + failed + errors,
        "summary": f"{passed} passed, {failed} failed, {errors} errors",
        "exit_code": result.get("exit_code", -1),
        "output_tail": stdout[-2000:] if len(stdout) > 2000 else stdout,
    }


@app.get("/api/ops/git-status")
async def ops_git_status():
    """Return git status + recent log."""
    status_result = await asyncio.to_thread(
        _run_subprocess,
        ["git", "status", "--short"],
        timeout=10,
    )
    log_result = await asyncio.to_thread(
        _run_subprocess,
        ["git", "log", "--oneline", "-5"],
        timeout=10,
    )
    branch_result = await asyncio.to_thread(
        _run_subprocess,
        ["git", "branch", "--show-current"],
        timeout=10,
    )

    branch = branch_result.get("stdout", "").strip()
    status_lines = [l for l in status_result.get("stdout", "").splitlines() if l.strip()]
    log_lines = [l.strip() for l in log_result.get("stdout", "").splitlines() if l.strip()]

    modified = sum(1 for l in status_lines if l.startswith(" M") or l.startswith("M "))
    untracked = sum(1 for l in status_lines if l.startswith("??"))
    staged = sum(1 for l in status_lines if l[0] in "MADR" and l[0] != "?")

    return {
        "branch": branch,
        "modified": modified,
        "untracked": untracked,
        "staged": staged,
        "status": status_lines[:30],
        "recent_commits": log_lines,
    }


class MomentumRunRequest(BaseModel):
    train_id: str = "daily_ops"
    execute: bool = True
    flow: Optional[str] = None
    max_parallel: Optional[int] = None


def _parse_last_json(stdout: str) -> dict[str, Any] | None:
    for line in reversed((stdout or "").splitlines()):
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
            return payload if isinstance(payload, dict) else None
        except Exception:
            logger.debug("Suppressed error", exc_info=True)
            continue
    return None


@app.post("/api/ops/momentum/run")
async def ops_momentum_run(req: MomentumRunRequest = MomentumRunRequest()):
    """Run a configured Momentum Train by id (safe allowlist)."""
    cfg = MOMENTUM_TRAIN_CONFIGS.get(req.train_id)
    if not cfg or not cfg.exists():
        return {"error": f"Unknown or missing train_id: {req.train_id}", "ok": False}

    runner = ROOT / "scripts" / "system" / "momentum_train.py"
    if not runner.exists():
        return {"error": "momentum_train.py not found", "ok": False}

    cmd = [sys.executable, str(runner), "--config", str(cfg)]
    if req.flow:
        cmd += ["--flow", str(req.flow)]
    if req.execute:
        cmd += ["--execute"]
    if req.max_parallel:
        cmd += ["--max-parallel", str(int(req.max_parallel))]

    result = await asyncio.to_thread(_run_subprocess, cmd, timeout=600)
    parsed = _parse_last_json(result.get("stdout", ""))
    if parsed:
        return parsed
    return {
        "ok": result.get("exit_code", -1) == 0,
        "train_id": req.train_id,
        "stdout": result.get("stdout", "")[:2000],
        "stderr": result.get("stderr", "")[:800] if result.get("stderr") else None,
        "exit_code": result.get("exit_code", -1),
    }


@app.get("/api/ops/momentum/latest")
async def ops_momentum_latest(train_id: str = "daily_ops"):
    """Return the latest Momentum Train state.json summary (no execution)."""
    run_root = MOMENTUM_RUNS_DIR / train_id
    if not run_root.exists():
        return {"error": f"No runs found for train_id={train_id}", "ok": False}
    dirs = [p for p in run_root.iterdir() if p.is_dir()]
    if not dirs:
        return {"error": f"No runs found for train_id={train_id}", "ok": False}
    latest = sorted(dirs, key=lambda p: p.name)[-1]
    state_path = latest / "state.json"
    if not state_path.exists():
        return {"error": f"state.json missing for {latest.name}", "ok": False}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("Suppressed error", exc_info=True)
        return {"error": "Could not read momentum train state", "ok": False}

    stations = state.get("stations", {}) if isinstance(state, dict) else {}
    statuses: dict[str, str] = {}
    for key, node in stations.items():
        if isinstance(node, dict):
            statuses[key] = str(node.get("status", "unknown"))

    failed = sum(1 for v in statuses.values() if v == "failed")
    completed = sum(1 for v in statuses.values() if v == "completed")
    return {
        "ok": bool(state.get("ok", False)),
        "train_id": train_id,
        "run_dir": str(latest.relative_to(ROOT)),
        "finished_at": state.get("finished_at"),
        "station_count": len(statuses),
        "completed": completed,
        "failed": failed,
        "statuses": statuses,
    }


class ChessboardGenerateRequest(BaseModel):
    goal: str = "Improve SCBE long-running agentic workflows with governed momentum trains."


@app.post("/api/ops/chessboard/generate")
async def ops_chessboard_generate(req: ChessboardGenerateRequest = ChessboardGenerateRequest()):
    """Generate a chessboard dev-stack packet set for a given goal."""
    script = ROOT / "scripts" / "system" / "chessboard_dev_stack.py"
    if not script.exists():
        return {"error": "chessboard_dev_stack.py not found", "ok": False}
    result = await asyncio.to_thread(
        _run_subprocess,
        [sys.executable, str(script), "--goal", str(req.goal)],
        timeout=60,
    )
    parsed = _parse_last_json(result.get("stdout", ""))
    if parsed:
        return parsed
    return {
        "ok": result.get("exit_code", -1) == 0,
        "stdout": result.get("stdout", "")[:2000],
        "stderr": result.get("stderr", "")[:800] if result.get("stderr") else None,
        "exit_code": result.get("exit_code", -1),
    }


@app.get("/api/ops/chessboard/latest")
async def ops_chessboard_latest():
    """Return the latest generated chessboard packet set."""
    if not CHESSBOARD_ARTIFACTS_DIR.exists():
        return {"error": "No chessboard artifacts dir found", "ok": False}
    dirs = [p for p in CHESSBOARD_ARTIFACTS_DIR.iterdir() if p.is_dir()]
    if not dirs:
        return {"error": "No chessboard packet runs found", "ok": False}
    latest = sorted(dirs, key=lambda p: p.name)[-1]
    meta_path = latest / "meta.json"
    packets_path = latest / "packets.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        packets = json.loads(packets_path.read_text(encoding="utf-8")) if packets_path.exists() else {}
    except Exception:
        logger.debug("Suppressed error", exc_info=True)
        return {"error": "Could not read latest chessboard artifacts", "ok": False}
    return {
        "ok": True,
        "output_dir": str(latest.relative_to(ROOT)),
        "meta": meta,
        "packets": packets,
    }


# =========================================================================== #
#  CLI — Safe command interpreter (web-usable)
# =========================================================================== #


class CliRunRequest(BaseModel):
    command: str = "help"


def _cli_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _cli_truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n...(truncated)...\n"


def _cli_command_registry() -> list[dict[str, Any]]:
    """A small interoperability matrix for multi-lane ops."""
    return [
        {
            "cmd": "help",
            "lane": "offline",
            "interop": {"web": True, "python": True, "node": False, "connectors": False},
            "desc": "Show CLI help + examples.",
            "example": "help",
        },
        {
            "cmd": "matrix",
            "lane": "offline",
            "interop": {"web": True, "python": True, "node": False, "connectors": False},
            "desc": "Return the interoperability matrix for safe commands.",
            "example": "matrix",
        },
        {
            "cmd": "trust <url>",
            "lane": "browse",
            "interop": {"web": True, "python": True, "node": False, "connectors": False},
            "desc": "Classify a URL against trusted_external_sites.json (safe allowlist).",
            "example": "trust aethermoorgames.com",
        },
        {
            "cmd": "vault stats|search <q>|sync",
            "lane": "vault",
            "interop": {"web": True, "python": True, "node": False, "connectors": False},
            "desc": "Vault operations (local Obsidian vault).",
            "example": "vault search \"harmonic wall\"",
        },
        {
            "cmd": "ops email|youtube|tor|tests|git",
            "lane": "ops",
            "interop": {"web": True, "python": True, "node": False, "connectors": True},
            "desc": "Run operational tasks through the same endpoints used by the Ops tab buttons.",
            "example": "ops tests",
        },
        {
            "cmd": "momentum run <train_id> [--flow X] [--execute] [--max-parallel N]",
            "lane": "momentum",
            "interop": {"web": True, "python": True, "node": False, "connectors": False},
            "desc": "Run a Momentum Train (safe allowlist of configs).",
            "example": "momentum run daily_ops --execute --max-parallel 3",
        },
        {
            "cmd": "momentum latest [train_id]",
            "lane": "momentum",
            "interop": {"web": True, "python": True, "node": False, "connectors": False},
            "desc": "Show the latest Momentum Train summary (no execution).",
            "example": "momentum latest daily_ops",
        },
        {
            "cmd": "chessboard generate <goal...> | chessboard latest",
            "lane": "chessboard",
            "interop": {"web": True, "python": True, "node": False, "connectors": False},
            "desc": "Generate or view the latest chessboard dev-stack packet set.",
            "example": "chessboard generate \"Draft AetherBrowser Mobile V1 spec\"",
        },
        {
            "cmd": "docs list | docs show <key>",
            "lane": "docs",
            "interop": {"web": True, "python": True, "node": False, "connectors": False},
            "desc": "Show curated docs safely (registry, not arbitrary file reads).",
            "example": "docs show aetherbrowser-config",
        },
    ]


def _cli_help_text() -> str:
    lines = [
        "AetherBrowser CLI (SAFE MODE)",
        "",
        "This endpoint is a command interpreter for the AetherBrowser web UI and for AI callers.",
        "It is allowlist-only (no arbitrary shell).",
        "",
        "Core commands:",
        "  help",
        "  matrix",
        "  trust <url>",
        "  vault stats",
        "  vault search \"query\"",
        "  vault sync",
        "  ops email|youtube|tor|tests|git",
        "  momentum run <train_id> [--flow X] [--execute] [--max-parallel N]",
        "  momentum latest [train_id]",
        "  chessboard generate \"goal...\"",
        "  chessboard latest",
        "  docs list",
        "  docs show <key>",
        "",
        "Examples:",
        "  trust aethermoorgames.com",
        "  vault search \"phi poincare\"",
        "  ops tests",
        "  momentum run daily_ops --execute --max-parallel 3",
        "  chessboard generate \"Improve long-running agent workflows\"",
        "  docs show aetherbrowser-config",
    ]
    return "\n".join(lines)


def _cli_docs_list() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key, path in sorted(CLI_DOCS_REGISTRY.items(), key=lambda kv: kv[0]):
        items.append(
            {
                "key": key,
                "path": str(path.relative_to(ROOT)) if path.exists() else str(path),
                "exists": path.exists(),
            }
        )
    return items


def _cli_docs_show(key: str, max_chars: int = 9000) -> dict[str, Any]:
    path = CLI_DOCS_REGISTRY.get(key)
    if not path:
        return {"ok": False, "error": f"Unknown doc key: {key}", "docs": _cli_docs_list()}
    if not path.exists():
        return {"ok": False, "error": f"Doc missing: {path}", "key": key, "path": str(path)}
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        logger.exception("Failed to read CLI doc %s", path)
        return {"ok": False, "error": "Could not read document", "key": key, "path": str(path)}
    return {
        "ok": True,
        "key": key,
        "path": str(path.relative_to(ROOT)),
        "content": _cli_truncate(content, max_chars),
    }


def _cli_parse_flags(parts: list[str]) -> dict[str, Any]:
    """Very small flag parser for: --flow, --execute, --max-parallel."""
    out: dict[str, Any] = {"args": []}
    i = 0
    while i < len(parts):
        p = parts[i]
        if p == "--flow" and i + 1 < len(parts):
            out["flow"] = parts[i + 1]
            i += 2
            continue
        if p == "--execute":
            out["execute"] = True
            i += 1
            continue
        if p == "--max-parallel" and i + 1 < len(parts):
            try:
                out["max_parallel"] = int(parts[i + 1])
            except Exception:
                logger.debug("Suppressed error", exc_info=True)
                out["max_parallel"] = parts[i + 1]
            i += 2
            continue
        out["args"].append(p)
        i += 1
    return out


async def _cli_dispatch(parts: list[str]) -> dict[str, Any]:
    if not parts:
        return {"ok": True, "result": _cli_help_text()}

    cmd = parts[0].lower()
    rest = parts[1:]

    if cmd in {"help", "?"}:
        return {"ok": True, "result": _cli_help_text()}

    if cmd in {"matrix", "commands"}:
        return {"ok": True, "result": _cli_command_registry()}

    if cmd == "trust":
        if not rest:
            return {"ok": False, "error": "Usage: trust <url>"}
        return _classify_url(rest[0])

    if cmd == "health":
        return await health()

    if cmd == "vault":
        if not rest or rest[0].lower() == "stats":
            return await vault_stats()
        if rest[0].lower() == "sync":
            return await vault_sync()
        if rest[0].lower() == "search":
            q = " ".join(rest[1:]).strip().strip('"')
            if not q:
                return {"ok": False, "error": "Usage: vault search <query>"}
            return await vault_search(q=q)
        return {"ok": False, "error": "Unknown vault subcommand. Try: vault stats|search|sync"}

    if cmd == "ops":
        if not rest:
            return {"ok": False, "error": "Usage: ops email|youtube|tor|tests|git"}
        op = rest[0].lower()
        if op in {"email", "mail"}:
            return await ops_check_email()
        if op in {"youtube", "yt"}:
            return await ops_youtube_review()
        if op in {"tor", "onion"}:
            return await ops_tor_sweep()
        if op in {"tests", "test"}:
            return await ops_run_tests()
        if op in {"git", "status"}:
            return await ops_git_status()
        return {"ok": False, "error": f"Unknown ops subcommand: {op}"}

    if cmd == "momentum":
        if not rest:
            return {"ok": False, "error": "Usage: momentum run|latest ..."}
        sub = rest[0].lower()
        if sub == "latest":
            train_id = rest[1] if len(rest) >= 2 else "daily_ops"
            return await ops_momentum_latest(train_id=train_id)
        if sub == "run":
            if len(rest) < 2:
                return {"ok": False, "error": "Usage: momentum run <train_id> [--flow X] [--execute] [--max-parallel N]"}
            flags = _cli_parse_flags(rest[2:])
            req = MomentumRunRequest(
                train_id=rest[1],
                flow=flags.get("flow"),
                execute=bool(flags.get("execute", False)),
                max_parallel=flags.get("max_parallel"),
            )
            return await ops_momentum_run(req=req)
        return {"ok": False, "error": f"Unknown momentum subcommand: {sub}"}

    if cmd == "chessboard":
        if not rest:
            return {"ok": False, "error": "Usage: chessboard generate|latest ..."}
        sub = rest[0].lower()
        if sub == "latest":
            return await ops_chessboard_latest()
        if sub == "generate":
            goal = " ".join(rest[1:]).strip().strip('"')
            if not goal:
                return {"ok": False, "error": "Usage: chessboard generate <goal...>"}
            return await ops_chessboard_generate(req=ChessboardGenerateRequest(goal=goal))
        return {"ok": False, "error": f"Unknown chessboard subcommand: {sub}"}

    if cmd == "docs":
        if not rest or rest[0].lower() == "list":
            return {"ok": True, "result": _cli_docs_list()}
        if rest[0].lower() == "show":
            if len(rest) < 2:
                return {"ok": False, "error": "Usage: docs show <key>", "docs": _cli_docs_list()}
            return _cli_docs_show(rest[1])
        return {"ok": False, "error": "Unknown docs subcommand. Try: docs list | docs show <key>"}

    return {"ok": False, "error": f"Unknown command: {cmd}. Try: help"}


@app.get("/api/cli/commands")
async def cli_commands():
    return {"ok": True, "commands": _cli_command_registry(), "timestamp": _cli_now_iso()}


@app.post("/api/cli/run")
async def cli_run(req: CliRunRequest = CliRunRequest()):
    raw = (req.command or "").strip()
    if not raw:
        raw = "help"
    try:
        parts = shlex.split(raw, posix=True)
    except Exception as e:
        logger.debug("CLI parse error: %s", e)
        return {"ok": False, "command": raw, "error": "Invalid command syntax", "timestamp": _cli_now_iso()}

    result = await _cli_dispatch(parts)
    # Normalise to always include command + timestamp
    if isinstance(result, dict):
        out: dict[str, Any] = dict(result)
        out.setdefault("ok", True)
        out.setdefault("command", raw)
        out.setdefault("timestamp", _cli_now_iso())
    else:
        out = {"ok": True, "command": raw, "result": result, "timestamp": _cli_now_iso()}

    _append_jsonl(
        IDE_CLI_LOG,
        {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "kind": "cli",
            "command": raw,
            "result": out,
        },
    )
    return out


@app.post("/api/cli/job")
async def cli_job(req: CliRunRequest = CliRunRequest()):
    """Run a safe CLI command asynchronously and return a job_id."""
    raw = (req.command or "").strip() or "help"
    try:
        parts = shlex.split(raw, posix=True)
    except Exception as e:
        logger.debug("CLI job parse error: %s", e)
        return {"ok": False, "command": raw, "error": "Invalid command syntax", "timestamp": _cli_now_iso()}

    job_id = uuid.uuid4().hex
    started = _cli_now_iso()
    _cli_jobs[job_id] = {"ok": True, "job_id": job_id, "command": raw, "status": "running", "started_at": started}

    async def _runner():
        try:
            out = await _cli_dispatch(parts)
            _append_jsonl(
                IDE_CLI_LOG,
                _scrub_obj({
                    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "kind": "cli_job",
                    "job_id": job_id,
                    "command": raw,
                    "status": "completed",
                    "result": out,
                }),
            )
            _cli_jobs[job_id] = {
                "ok": True,
                "job_id": job_id,
                "command": raw,
                "status": "completed",
                "started_at": started,
                "finished_at": _cli_now_iso(),
                "result": out,
            }
        except Exception:
            safe_cmd = (raw[:40] + "..." if len(raw) > 40 else raw).replace("\n", " ").replace("\r", " ")
            logger.exception("CLI job failed for command: %s", safe_cmd)
            _append_jsonl(
                IDE_CLI_LOG,
                {
                    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "kind": "cli_job",
                    "job_id": job_id,
                    "command": raw,
                    "status": "failed",
                    "error": "CLI job failed",
                },
            )
            _cli_jobs[job_id] = {
                "ok": False,
                "job_id": job_id,
                "command": raw,
                "status": "failed",
                "started_at": started,
                "finished_at": _cli_now_iso(),
                "error": "CLI job failed",
            }

    asyncio.create_task(_runner())
    return {"ok": True, "job_id": job_id, "command": raw, "status": "running", "started_at": started}


@app.get("/api/cli/job/{job_id}")
async def cli_job_status(job_id: str):
    """Fetch a job result created by /api/cli/job."""
    job = _cli_jobs.get(job_id)
    if not job:
        return {"ok": False, "error": f"Unknown job_id: {job_id}", "job_id": job_id, "timestamp": _cli_now_iso()}
    out = dict(job)
    out.setdefault("timestamp", _cli_now_iso())
    return out


@app.get("/api/ide/logs/tail")
async def ide_logs_tail(kind: str = Query("chat"), n: int = Query(50, ge=1, le=500)):
    kind = (kind or "").strip().lower()
    if kind not in {"chat", "cli"}:
        return {"ok": False, "error": "kind must be 'chat' or 'cli'", "timestamp": _cli_now_iso()}
    path = IDE_CHAT_LOG if kind == "chat" else IDE_CLI_LOG
    entries = _tail_jsonl(path, n=int(n))
    return {
        "ok": True,
        "kind": kind,
        "requested": int(n),
        "returned": len(entries),
        "path": str(path),
        "entries": entries,
        "timestamp": _cli_now_iso(),
    }


# In-memory job store (safe commands only). Not persisted.
_cli_jobs: dict[str, dict[str, Any]] = {}


# =========================================================================== #
#  Entry point
# =========================================================================== #

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("AETHERBROWSER_PORT", "8100"))
    print(f"AetherBrowser API starting on http://localhost:{port}")
    print(f"  Root: {ROOT}")
    print(f"  Trusted sites: {TRUSTED_SITES_PATH}")
    print(f"  Env file: {ENV_FILE}")
    uvicorn.run(app, host="0.0.0.0", port=port)
