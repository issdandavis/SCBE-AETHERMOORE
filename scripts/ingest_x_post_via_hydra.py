#!/usr/bin/env python3
"""
HYDRA X-post ingestion pipeline with safety membrane + hub writeback.

Flow:
1) Browser fetch (Playwright backend through HYDRA BrowserLimb)
2) Safety membrane scan (prompt injection / malware-style payloads)
3) Catalog into chunked JSONL training data
4) Optional HF feature extraction using user model
5) Write back to HYDRA hub (Switchboard channel + Librarian memory)
6) Optional upload to HF dataset repo
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests

from hydra.limbs import BrowserLimb
from hydra.switchboard import Switchboard
from hydra.ledger import Ledger
from hydra.librarian import Librarian
from agents.antivirus_membrane import scan_text_for_threats, turnstile_action

try:
    from huggingface_hub import HfApi, login
except Exception:  # noqa: BLE001
    HfApi = None
    login = None


PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"developer\s+mode",
    r"act\s+as\s+root",
    r"bypass\s+safety",
    r"execute\s+shell",
]

MALWARE_PATTERNS = [
    r"powershell\s+-enc",
    r"cmd\.exe",
    r"rm\s+-rf",
    r"curl\s+.*\|\s*sh",
    r"wget\s+.*\|\s*bash",
    r"javascript:",
    r"data:text/html",
]


@dataclass
class MembraneReport:
    verdict: str
    risk_score: float
    prompt_injection_hits: List[str]
    malware_hits: List[str]
    external_link_count: int
    reasons: List[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_post_id(url: str) -> str:
    m = re.search(r"/status/(\d+)", url)
    return m.group(1) if m else hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def html_to_text(raw_html: str) -> str:
    s = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw_html)
    s = re.sub(r"(?is)<style.*?>.*?</style>", " ", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def chunk_text(text: str, chunk_size: int = 1400, overlap: int = 250) -> List[str]:
    norm = " ".join(text.split())
    if not norm:
        return []
    step = max(1, chunk_size - overlap)
    out: List[str] = []
    for i in range(0, len(norm), step):
        c = norm[i : i + chunk_size].strip()
        if len(c) >= 40:
            out.append(c)
    return out


def scan_membrane(source_text: str, source_url: str) -> MembraneReport:
    scan = scan_text_for_threats(source_text)
    action = turnstile_action("browser", scan)
    verdict = "ALLOW"
    if action == "HONEYPOT":
        verdict = "HONEYPOT"
    elif action in {"HOLD", "ISOLATE"}:
        verdict = "QUARANTINE"
    return MembraneReport(
        verdict=verdict,
        risk_score=scan.risk_score,
        prompt_injection_hits=list(scan.prompt_hits),
        malware_hits=list(scan.malware_hits),
        external_link_count=scan.external_link_count,
        reasons=list(scan.reasons),
    )


def heuristic_summary(text: str, max_sentences: int = 6) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    picked = [s.strip() for s in sentences if len(s.strip()) > 20][:max_sentences]
    return " ".join(picked)[:2200]


def hf_feature_extract(model_id: str, token: str, chunks: List[str]) -> Dict[str, Any]:
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"inputs": chunks[:8]}
    r = requests.post(api_url, headers=headers, json=payload, timeout=120)
    if r.status_code >= 400:
        return {"ok": False, "status_code": r.status_code, "error": r.text[:500]}
    data = r.json()
    dims = None
    if isinstance(data, list) and data:
        if isinstance(data[0], list):
            dims = len(data[0])
        elif isinstance(data[0], dict) and "embedding" in data[0] and isinstance(data[0]["embedding"], list):
            dims = len(data[0]["embedding"])
    return {"ok": True, "embedding_dims": dims, "sample_count": len(chunks[:8])}


async def fetch_x_content(url: str, backend: str) -> Dict[str, Any]:
    limb = BrowserLimb(backend_type=backend)
    await limb.activate()
    if not getattr(limb, "_backend", None):
        raise RuntimeError("Browser backend unavailable (playwright/selenium not installed)")

    backend_obj = limb._backend
    try:
        nav = await backend_obj.navigate(url)
        await backend_obj.wait(2.0)
        for _ in range(2):
            await backend_obj.scroll("down", 450)
            await backend_obj.wait(0.5)

        page_title = ""
        try:
            page_title = await backend_obj.get_page_title()
        except Exception:  # noqa: BLE001
            pass

        article_text = await backend_obj.execute_script(
            """
            () => {
              const a = document.querySelector("article");
              if (a && a.innerText) return a.innerText;
              const main = document.querySelector("main");
              if (main && main.innerText) return main.innerText;
              return document.body ? document.body.innerText : "";
            }
            """
        )
        page_html = await backend_obj.get_page_content()
        current_url = await backend_obj.get_current_url()

        return {
            "nav": nav,
            "page_title": page_title,
            "article_text": (article_text or "").strip(),
            "page_html": page_html,
            "current_url": current_url,
        }
    finally:
        try:
            await backend_obj.close()
        except Exception:  # noqa: BLE001
            pass


def persist_run(
    run_dir: Path,
    source_url: str,
    post_id: str,
    fetched: Dict[str, Any],
    membrane: MembraneReport,
    chunks: List[str],
    summary: str,
    hf_info: Dict[str, Any],
) -> Dict[str, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)

    raw = {
        "source_url": source_url,
        "post_id": post_id,
        "fetched_at": utc_now(),
        "title": fetched.get("page_title", ""),
        "resolved_url": fetched.get("current_url", source_url),
        "article_text_preview": fetched.get("article_text", "")[:5000],
    }
    (run_dir / "raw_fetch.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")

    membrane_json = {
        "verdict": membrane.verdict,
        "risk_score": membrane.risk_score,
        "prompt_injection_hits": membrane.prompt_injection_hits,
        "malware_hits": membrane.malware_hits,
        "external_link_count": membrane.external_link_count,
        "reasons": membrane.reasons,
    }
    (run_dir / "membrane_report.json").write_text(json.dumps(membrane_json, indent=2), encoding="utf-8")

    catalog = {
        "source_url": source_url,
        "post_id": post_id,
        "ingested_at": utc_now(),
        "chunk_count": len(chunks),
        "summary": summary,
        "hf_feature_extract": hf_info,
        "verdict": membrane.verdict,
        "risk_score": membrane.risk_score,
    }
    (run_dir / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    jsonl_path = run_dir / "dataset.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for i, c in enumerate(chunks):
            row = {
                "event_type": "x_post_chunk",
                "dataset": "scbe_external_intel",
                "source_url": source_url,
                "post_id": post_id,
                "chunk_index": i,
                "membrane_verdict": membrane.verdict,
                "membrane_risk": membrane.risk_score,
                "source_text": c,
                "generated_at": utc_now(),
            }
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    return {
        "raw_fetch": run_dir / "raw_fetch.json",
        "membrane_report": run_dir / "membrane_report.json",
        "catalog": run_dir / "catalog.json",
        "dataset": jsonl_path,
    }


def push_to_hf_dataset(
    repo_id: str,
    token: str,
    files: Dict[str, Path],
    post_id: str,
) -> Dict[str, Any]:
    if HfApi is None or login is None:
        return {"ok": False, "reason": "huggingface_hub not installed"}
    login(token=token)
    api = HfApi(token=token)
    prefix = f"ingest/x/{post_id}"
    uploaded = []
    for name, path in files.items():
        api.upload_file(
            path_or_fileobj=str(path),
            path_in_repo=f"{prefix}/{path.name}",
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"Add X ingest artifact: {path.name}",
        )
        uploaded.append(f"{prefix}/{path.name}")
    return {"ok": True, "uploaded": uploaded, "repo_id": repo_id}


def write_back_to_hub(
    switchboard_db: str,
    ledger_db: str,
    channel: str,
    sender: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    board = Switchboard(switchboard_db)
    msg_id = board.post_role_message(channel, sender, payload)

    ledger = Ledger(db_path=ledger_db)
    librarian = Librarian(ledger)
    memory_key = f"x_ingest:{payload.get('post_id', 'unknown')}:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    librarian.remember(
        memory_key,
        payload,
        category="external_intel",
        importance=0.85,
        keywords=["x", "roadmap", "scbe", "aetherauth"],
    )
    return {"switchboard_message_id": msg_id, "memory_key": memory_key}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest X post via HYDRA + safety membrane")
    p.add_argument("--url", required=True, help="X/Twitter post URL")
    p.add_argument("--backend", default="playwright", choices=["playwright", "selenium", "cdp", "chrome_mcp"])
    p.add_argument("--switchboard-db", default="artifacts/hydra/switchboard.db")
    p.add_argument("--ledger-db", default="artifacts/hydra/ledger.db")
    p.add_argument("--channel", default="hub.intel")
    p.add_argument("--sender", default="x_ingest_agent")
    p.add_argument("--run-root", default="training/runs/x_ingest")
    p.add_argument("--chunk-size", type=int, default=1400)
    p.add_argument("--overlap", type=int, default=250)
    p.add_argument("--hf-model-id", default="issdandavis/phdm-21d-embedding")
    p.add_argument("--hf-dataset-repo", default="issdandavis/scbe-aethermoore-knowledge-base")
    p.add_argument("--push-to-hub", action="store_true")
    p.add_argument("--push-to-hf", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    post_id = extract_post_id(args.url)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(args.run_root) / f"{stamp}_{post_id}"

    fetched = asyncio.run(fetch_x_content(args.url, args.backend))
    article_text = fetched.get("article_text", "").strip()
    if len(article_text) < 120:
        article_text = html_to_text(fetched.get("page_html", ""))

    membrane = scan_membrane(article_text, args.url)
    chunks = chunk_text(article_text, args.chunk_size, args.overlap)
    summary = heuristic_summary(article_text)

    hf_info: Dict[str, Any] = {"ok": False, "reason": "HF token not provided"}
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if hf_token and chunks:
        try:
            hf_info = hf_feature_extract(args.hf_model_id, hf_token, chunks)
        except Exception as exc:  # noqa: BLE001
            hf_info = {"ok": False, "reason": str(exc)}

    files = persist_run(
        run_dir=run_dir,
        source_url=args.url,
        post_id=post_id,
        fetched=fetched,
        membrane=membrane,
        chunks=chunks,
        summary=summary,
        hf_info=hf_info,
    )

    hub_result: Dict[str, Any] = {"skipped": True}
    if args.push_to_hub:
        hub_payload = {
            "event": "x_ingest_complete",
            "post_id": post_id,
            "source_url": args.url,
            "run_dir": str(run_dir).replace("\\", "/"),
            "membrane_verdict": membrane.verdict,
            "membrane_risk": membrane.risk_score,
            "summary": summary[:1200],
            "chunk_count": len(chunks),
            "hf_feature_extract": hf_info,
            "timestamp": utc_now(),
        }
        hub_result = write_back_to_hub(
            switchboard_db=args.switchboard_db,
            ledger_db=args.ledger_db,
            channel=args.channel,
            sender=args.sender,
            payload=hub_payload,
        )

    hf_push_result: Dict[str, Any] = {"skipped": True}
    if args.push_to_hf:
        if not hf_token:
            hf_push_result = {"ok": False, "reason": "HF_TOKEN not set"}
        else:
            try:
                hf_push_result = push_to_hf_dataset(
                    repo_id=args.hf_dataset_repo,
                    token=hf_token,
                    files=files,
                    post_id=post_id,
                )
            except Exception as exc:  # noqa: BLE001
                hf_push_result = {"ok": False, "reason": str(exc)}

    result = {
        "ok": True,
        "source_url": args.url,
        "post_id": post_id,
        "run_dir": str(run_dir).replace("\\", "/"),
        "membrane": {
            "verdict": membrane.verdict,
            "risk_score": membrane.risk_score,
            "reasons": membrane.reasons,
        },
        "chunk_count": len(chunks),
        "hf_feature_extract": hf_info,
        "hub_result": hub_result,
        "hf_push_result": hf_push_result,
        "artifacts": {k: str(v).replace("\\", "/") for k, v in files.items()},
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
