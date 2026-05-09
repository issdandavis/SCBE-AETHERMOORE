"""External worker / integration surfaces for Polly.

Single place to wire third-party datasets, models, and call services into
Polly's runtime. All integrations are **opt-in via environment variables** —
the module never throws when credentials are missing; it returns a structured
``WorkerStatus`` so callers can degrade gracefully.

Currently wired:

- **Ollama** (local LLM) — already used by ``polly_routes._free_llm_chat``.
  Status only here.

- **Hugging Face** (Inference API + datasets) — chat already used by
  ``polly_routes._free_llm_chat``. This module adds dataset push/pull for
  the live training corpus.

- **Kaggle** (datasets) — pull public CSV/JSON datasets for model
  enrichment. Push training corpus snapshots if Kaggle credentials are
  configured.

- **Twilio** (voice calls) — stub for an inbound AI customer-call service.
  When ``TWILIO_ACCOUNT_SID`` + ``TWILIO_AUTH_TOKEN`` + ``TWILIO_PHONE_NUMBER``
  are set, the ``call_service_status()`` reports as ``configured``; the
  TwiML endpoint is intentionally a thin stub so the prod deploy can wire
  to a real LLM voice service (Vapi, Bland, Retell, etc.) without changing
  this module's contract.

Design constraints:
- Never raise — degraded status, never crash.
- Never log secrets — only log "configured" / "missing" booleans.
- Pure stdlib for stub paths; optional packages (``kaggle``, ``twilio``,
  ``huggingface_hub``) are imported lazily only when the integration is
  actually invoked.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("scbe.api.polly.workers")


# ---------------------------------------------------------------------------
# Status reporting
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkerStatus:
    """Per-integration health and configuration report."""

    name: str
    configured: bool
    detail: str = ""


def ollama_status() -> WorkerStatus:
    """Ollama is local; we treat it as 'configured' if the env hint is set
    OR the default URL is reachable. We don't probe the network here — that
    belongs in a healthcheck endpoint.
    """
    base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip()
    model = os.environ.get("OLLAMA_MODEL", "llama3.2").strip()
    return WorkerStatus(
        name="ollama",
        configured=bool(base),
        detail=f"base_url={base or '(unset)'} model={model}",
    )


def hf_status() -> WorkerStatus:
    """Hugging Face is configured when ``HF_TOKEN`` is set."""
    token = os.environ.get("HF_TOKEN", "").strip()
    model = os.environ.get("HF_MODEL", "Qwen/Qwen2.5-72B-Instruct").strip()
    dataset_repo = os.environ.get("POLLY_TRAIN_HF_REPO", "issdandavis/polly-chat-live").strip()
    return WorkerStatus(
        name="huggingface",
        configured=bool(token),
        detail=f"model={model} dataset_repo={dataset_repo}",
    )


def kaggle_status() -> WorkerStatus:
    """Kaggle is configured when ``KAGGLE_USERNAME`` + ``KAGGLE_KEY`` are set,
    or when ``~/.kaggle/kaggle.json`` exists.
    """
    username = os.environ.get("KAGGLE_USERNAME", "").strip()
    key = os.environ.get("KAGGLE_KEY", "").strip()
    json_path = Path.home() / ".kaggle" / "kaggle.json"
    configured = bool(username and key) or json_path.is_file()
    detail = []
    if username:
        detail.append(f"user={username}")
    if json_path.is_file():
        detail.append(f"kaggle.json present")
    return WorkerStatus(
        name="kaggle",
        configured=configured,
        detail=" ".join(detail) or "no credentials",
    )


def call_service_status() -> WorkerStatus:
    """Twilio voice / AI-call service status."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    number = os.environ.get("TWILIO_PHONE_NUMBER", "").strip()
    bridge = os.environ.get("POLLY_VOICE_AGENT_URL", "").strip()
    configured = bool(sid and token and number)
    detail_parts: List[str] = []
    if number:
        detail_parts.append(f"number={number}")
    if bridge:
        detail_parts.append(f"voice_agent={bridge}")
    if not detail_parts:
        detail_parts.append("not configured")
    return WorkerStatus(
        name="twilio_voice",
        configured=configured,
        detail=" ".join(detail_parts),
    )


def all_statuses() -> List[WorkerStatus]:
    """Return health for every wired integration."""
    return [
        ollama_status(),
        hf_status(),
        kaggle_status(),
        call_service_status(),
    ]


# ---------------------------------------------------------------------------
# Hugging Face — push live training corpus snapshot.
# ---------------------------------------------------------------------------


def push_training_corpus_to_hf(
    *,
    corpus_dir: Path,
    repo_id: Optional[str] = None,
    private: bool = True,
) -> Dict[str, Any]:
    """Upload the live JSONL training corpus to Hugging Face Datasets.

    Returns ``{"ok": bool, "uploaded": [...], "error": Optional[str]}``.
    Never raises; on failure returns ``ok=False`` with a string ``error``.

    Requires ``HF_TOKEN`` and the optional ``huggingface_hub`` package.
    """
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        return {"ok": False, "uploaded": [], "error": "HF_TOKEN not set"}
    if not corpus_dir.exists():
        return {"ok": False, "uploaded": [], "error": f"corpus dir missing: {corpus_dir}"}

    target_repo = repo_id or os.environ.get("POLLY_TRAIN_HF_REPO", "issdandavis/polly-chat-live").strip()
    if not target_repo:
        return {"ok": False, "uploaded": [], "error": "no HF dataset repo configured"}

    try:
        from huggingface_hub import HfApi  # type: ignore[import-not-found]
    except ImportError:
        return {
            "ok": False,
            "uploaded": [],
            "error": "huggingface_hub package not installed",
        }

    api = HfApi(token=token)
    try:
        api.create_repo(
            repo_id=target_repo,
            repo_type="dataset",
            private=private,
            exist_ok=True,
        )
    except Exception as exc:
        logger.warning("HF create_repo failed: %s", exc)
        return {"ok": False, "uploaded": [], "error": f"create_repo: {exc}"}

    uploaded: List[str] = []
    errors: List[str] = []
    for shard in sorted(corpus_dir.glob("*.jsonl")):
        try:
            api.upload_file(
                path_or_fileobj=str(shard),
                path_in_repo=f"shards/{shard.name}",
                repo_id=target_repo,
                repo_type="dataset",
            )
            uploaded.append(shard.name)
        except Exception as exc:
            logger.warning("HF upload_file failed for %s: %s", shard.name, exc)
            errors.append(f"{shard.name}: {exc}")

    return {
        "ok": not errors,
        "uploaded": uploaded,
        "error": "; ".join(errors) if errors else None,
    }


# ---------------------------------------------------------------------------
# Kaggle — pull a public dataset for model enrichment.
# ---------------------------------------------------------------------------


def pull_kaggle_dataset(
    *,
    dataset_slug: str,
    target_dir: Path,
) -> Dict[str, Any]:
    """Download a Kaggle dataset to ``target_dir``.

    ``dataset_slug`` is the standard ``user/dataset-name`` form.
    Returns ``{"ok": bool, "files": [...], "error": Optional[str]}``.
    Never raises.

    Requires Kaggle credentials and the optional ``kaggle`` package.
    """
    if not kaggle_status().configured:
        return {"ok": False, "files": [], "error": "Kaggle credentials not configured"}
    if not isinstance(dataset_slug, str) or "/" not in dataset_slug:
        return {"ok": False, "files": [], "error": f"invalid slug: {dataset_slug!r}"}

    try:
        from kaggle import KaggleApi  # type: ignore[import-not-found]
    except ImportError:
        return {"ok": False, "files": [], "error": "kaggle package not installed"}

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(
            dataset_slug,
            path=str(target_dir),
            unzip=True,
            quiet=True,
        )
    except Exception as exc:
        logger.warning("Kaggle pull failed for %s: %s", dataset_slug, exc)
        return {"ok": False, "files": [], "error": str(exc)}

    files = [str(p.relative_to(target_dir)) for p in target_dir.rglob("*") if p.is_file()]
    return {"ok": True, "files": files, "error": None}


# ---------------------------------------------------------------------------
# Twilio AI-call service — stub TwiML response for inbound calls.
# ---------------------------------------------------------------------------


VOICE_GREETING_DEFAULT = (
    "Hi, you've reached Aethermoor. I'm Polly. "
    "Tell me briefly what brought you to call, "
    "and I'll either help directly or route you to Issac."
)


def voice_response_twiml(
    *,
    greeting: Optional[str] = None,
    voice_agent_url: Optional[str] = None,
) -> str:
    """Return a TwiML XML string for an inbound voice call.

    If ``voice_agent_url`` (or ``POLLY_VOICE_AGENT_URL`` env var) is set,
    the TwiML connects the call to that streaming voice-agent endpoint
    (Vapi, Bland, Retell, or any TwiML-Stream-compatible service).
    Otherwise it plays the greeting and records a short voicemail that
    can later be transcribed by Whisper for Polly to follow up.
    """
    spoken = (greeting or VOICE_GREETING_DEFAULT).replace("&", "&amp;").replace("<", "&lt;")
    bridge = (voice_agent_url or os.environ.get("POLLY_VOICE_AGENT_URL", "")).strip()

    if bridge:
        # Stream the call audio to the bridge agent. The bridge is responsible
        # for ASR + LLM + TTS round-trip; this module just hands it the pipe.
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<Response>\n"
            f'  <Say voice="alice">{spoken}</Say>\n'
            f'  <Connect><Stream url="{bridge}"/></Connect>\n'
            "</Response>"
        )

    # Fallback: greeting + voicemail recording.
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        f'  <Say voice="alice">{spoken}</Say>\n'
        '  <Record maxLength="120" playBeep="true" '
        'transcribe="true" '
        'transcribeCallback="/v1/polly/voicemail"/>\n'
        '  <Say voice="alice">Thanks. Issac will follow up by email. Goodbye.</Say>\n'
        "</Response>"
    )


__all__ = [
    "WorkerStatus",
    "ollama_status",
    "hf_status",
    "kaggle_status",
    "call_service_status",
    "all_statuses",
    "push_training_corpus_to_hf",
    "pull_kaggle_dataset",
    "voice_response_twiml",
    "VOICE_GREETING_DEFAULT",
]
