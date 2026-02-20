#!/usr/bin/env python3
"""
HYDRA headless browser coordinator with Multi-Model Modal Matrix reduction.

Pipeline:
1) Headless browser fetch via HYDRA MultiTabBrowserLimb.
2) Threat scan via antivirus membrane.
3) Multi-model x multi-modality matrix ingestion.
4) Reliability-weighted reducer => ALLOW / QUARANTINE / DENY.

This is designed for rapid, parallel internet sweeps.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.antivirus_membrane import scan_text_for_threats
from agents.multi_model_modal_matrix import Decision, MultiModelModalMatrix
from hydra.limbs import MultiTabBrowserLimb


MODEL_WEIGHTS: dict[str, dict[str, float]] = {
    "ko_navigator": {"navigation": 0.60, "content": 0.20, "threat": 0.20},
    "ru_reader": {"navigation": 0.20, "content": 0.60, "threat": 0.20},
    "dr_guardian": {"navigation": 0.20, "content": 0.20, "threat": 0.60},
}


def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def _prediction_from_risk(risk: float) -> Decision:
    if risk >= 0.70:
        return "DENY"
    if risk >= 0.40:
        return "QUARANTINE"
    return "ALLOW"


def _keyword_hit_ratio(text: str, query: str) -> float:
    q = (query or "").strip().lower()
    if not q:
        return 0.5
    terms = [t for t in q.replace(",", " ").split() if t]
    if not terms:
        return 0.5
    low = (text or "").lower()
    hits = sum(1 for t in terms if t in low)
    return hits / len(terms)


def _build_matrix_for_url(
    *,
    query: str,
    nav_success: bool,
    nav_decision: str,
    nav_latency_ms: float,
    content_latency_ms: float,
    content_preview: str,
    content_length: int,
    threat_risk: float,
) -> tuple[MultiModelModalMatrix, dict[str, float]]:
    matrix = MultiModelModalMatrix()

    query_hits = _keyword_hit_ratio(content_preview, query)

    nav_risk = 0.18 if nav_success else 0.82
    if str(nav_decision).upper() in {"DENY", "ESCALATE"}:
        nav_risk = _clamp01(nav_risk + 0.18)

    # Content risk: low textual yield + poor query hit increases risk.
    content_risk = 0.18
    if content_length < 128:
        content_risk = 0.62
    elif content_length < 512:
        content_risk = 0.38
    content_risk = _clamp01(content_risk + (1.0 - query_hits) * 0.25)

    modality_risk = {
        "navigation": _clamp01(nav_risk),
        "content": _clamp01(content_risk),
        "threat": _clamp01(threat_risk),
    }

    latency_by_modality = {
        "navigation": max(0.0, nav_latency_ms),
        "content": max(0.0, content_latency_ms),
        "threat": max(0.0, (nav_latency_ms + content_latency_ms) * 0.5),
    }

    for model_id, mix in MODEL_WEIGHTS.items():
        for modality_id in ("navigation", "content", "threat"):
            m_risk = modality_risk[modality_id]
            # model-specific perspective
            perspective_risk = _clamp01(0.55 * m_risk + 0.45 * (1.0 - mix[modality_id]))
            prediction = _prediction_from_risk(perspective_risk)

            base_conf = _clamp01(1.0 - perspective_risk)
            if modality_id == "content":
                base_conf = _clamp01(base_conf * (0.75 + 0.25 * query_hits))

            matrix.ingest(
                model_id=model_id,
                modality_id=modality_id,
                prediction=prediction,
                confidence=base_conf,
                latency_ms=latency_by_modality[modality_id],
                risk=perspective_risk,
            )

    return matrix, modality_risk


def _load_urls(args: argparse.Namespace) -> list[str]:
    urls: list[str] = []
    if args.urls:
        urls.extend([u.strip() for u in args.urls if str(u).strip()])
    if args.urls_file:
        raw = Path(args.urls_file).read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                urls.extend([str(x).strip() for x in data if str(x).strip()])
            else:
                raise ValueError("urls-file JSON must be an array")
        except json.JSONDecodeError:
            urls.extend([line.strip() for line in raw.splitlines() if line.strip()])
    dedup: list[str] = []
    seen = set()
    for u in urls:
        if u not in seen:
            dedup.append(u)
            seen.add(u)
    return dedup


async def _process_url(
    *,
    limb: MultiTabBrowserLimb,
    tab_id: str,
    url: str,
    query: str,
    include_preview: bool,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    nav = await limb.execute("navigate", url, {"tab_id": tab_id, "domain_type": "browser"})
    t1 = time.perf_counter()
    content = await limb.execute("get_content", url, {"tab_id": tab_id, "domain_type": "browser"})
    t2 = time.perf_counter()

    nav_latency_ms = (t1 - t0) * 1000.0
    content_latency_ms = (t2 - t1) * 1000.0

    nav_success = bool(nav.get("success"))
    nav_decision = str(nav.get("decision", "ALLOW")).upper()

    data = content.get("data") if isinstance(content.get("data"), dict) else {}
    content_preview = str(data.get("preview", ""))
    content_length = int(data.get("length", 0) or 0)
    content_sha256 = str(data.get("sha256", ""))

    threat = scan_text_for_threats(f"{url}\n{content_preview}")
    threat_risk = float(threat.risk_score)

    matrix, modality_risk = _build_matrix_for_url(
        query=query,
        nav_success=nav_success,
        nav_decision=nav_decision,
        nav_latency_ms=nav_latency_ms,
        content_latency_ms=content_latency_ms,
        content_preview=content_preview,
        content_length=content_length,
        threat_risk=threat_risk,
    )
    reduced = matrix.reduce()

    return {
        "url": url,
        "tab_id": tab_id,
        "nav": {
            "success": nav_success,
            "decision": nav_decision,
            "latency_ms": round(nav_latency_ms, 3),
        },
        "content": {
            "length": content_length,
            "sha256": content_sha256,
            "latency_ms": round(content_latency_ms, 3),
            "preview": (content_preview if include_preview else content_preview[:256]),
        },
        "threat_scan": threat.to_dict(),
        "modality_risk": modality_risk,
        "matrix": {
            "cells": [c.to_dict() for c in matrix.cells],
            "decision": reduced.to_dict(),
        },
        "decision": reduced.decision,
        "decision_confidence": reduced.confidence,
    }


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    urls = _load_urls(args)
    if not urls:
        raise ValueError("no urls provided (use --urls or --urls-file)")

    tab_count = min(max(1, int(args.max_tabs)), len(urls))
    limb = MultiTabBrowserLimb(
        backend_type=args.backend,
        max_tabs=max(tab_count, int(args.max_tabs)),
        scbe_url=args.scbe_url,
    )
    await limb.activate()

    tab_ids: list[str] = []
    for i in range(tab_count):
        created = await limb.create_tab(f"tab-{i+1}")
        if created:
            tab_ids.append(created)
    if not tab_ids:
        raise RuntimeError("failed to create browser tabs")

    queue: asyncio.Queue[str] = asyncio.Queue()
    for u in urls:
        queue.put_nowait(u)

    results: list[dict[str, Any]] = []
    lock = asyncio.Lock()

    async def worker(tab_id: str) -> None:
        while True:
            try:
                url = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                row = await _process_url(
                    limb=limb,
                    tab_id=tab_id,
                    url=url,
                    query=args.query or "",
                    include_preview=args.include_preview,
                )
                async with lock:
                    results.append(row)
            finally:
                queue.task_done()

    try:
        await asyncio.gather(*(worker(t) for t in tab_ids))
    finally:
        # Best effort cleanup.
        for tab_id in list(tab_ids):
            try:
                await limb.execute("close_tab", tab_id, {"tab_id": tab_id})
            except Exception:
                pass
        await limb.deactivate()

    counts = {"ALLOW": 0, "QUARANTINE": 0, "DENY": 0}
    for r in results:
        d = str(r.get("decision", "QUARANTINE")).upper()
        if d in counts:
            counts[d] += 1

    summary = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "backend": args.backend,
        "scbe_url": args.scbe_url,
        "query": args.query,
        "urls_total": len(urls),
        "tabs_used": len(tab_ids),
        "decision_counts": counts,
    }

    return {"summary": summary, "results": sorted(results, key=lambda x: x["url"])}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="HYDRA headless MMX coordinator")
    p.add_argument("--urls", nargs="*", default=[], help="URLs to process")
    p.add_argument("--urls-file", default="", help="File with URLs (JSON list or newline list)")
    p.add_argument("--query", default="", help="Optional query terms for relevance bias")
    p.add_argument("--backend", default="playwright", choices=["playwright", "selenium", "chrome_mcp", "cdp"])
    p.add_argument("--max-tabs", type=int, default=6, help="Max concurrent tabs")
    p.add_argument("--scbe-url", default="http://127.0.0.1:8080")
    p.add_argument("--include-preview", action="store_true", help="Include full extracted preview text in output")
    p.add_argument("--output-json", default="", help="Optional path for JSON result output")
    return p


def main() -> int:
    args = _parser().parse_args()
    payload = asyncio.run(_run(args))
    text = json.dumps(payload, indent=2)
    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

