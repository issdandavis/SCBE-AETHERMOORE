#!/usr/bin/env python3
"""ArXiv monetization spine runner.

Pipeline:
1) Route arXiv research task through Browser Chain (UM lane).
2) Pull and score arXiv papers for monetization fit.
3) Generate actionable offers and execution plan per lead.
4) Route top leads into n8n and Zapier when configured.
5) Persist JSON + Markdown artifacts and emit cross-talk packet.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from scripts.system.browser_chain_dispatcher import BrowserChainDispatcher, build_default_fleet
from src.aaoe.research_hub import ArxivPaper, ResearchHub
from src.fleet.connector_bridge import ConnectorBridge, ConnectorResult

try:
    from src.aethercode.gateway import CrossTalkRequest, _write_crosstalk_packet

    CROSSTALK_AVAILABLE = True
except Exception:
    CROSSTALK_AVAILABLE = False


@dataclass(frozen=True)
class OfferPattern:
    offer_id: str
    label: str
    buyers: str
    delivery: str
    price_min_usd: int
    price_max_usd: int
    keywords: Tuple[str, ...]
    value_angle: str


DEFAULT_QUERIES: Tuple[str, ...] = (
    "ai agent workflow automation",
    "llm evaluation safety governance",
    "browser automation multi agent systems",
    "retrieval augmented generation enterprise",
    "ai compliance monitoring",
)


OFFER_PATTERNS: Tuple[OfferPattern, ...] = (
    OfferPattern(
        offer_id="governance_audit_sprint",
        label="AI Governance Audit Sprint",
        buyers="SaaS teams shipping LLM features",
        delivery="2-week policy + safety + gating implementation sprint",
        price_min_usd=3500,
        price_max_usd=12000,
        keywords=(
            "safety",
            "alignment",
            "governance",
            "verification",
            "constraint",
            "audit",
            "trust",
            "policy",
        ),
        value_angle="Reduces compliance and model-risk incidents before launch.",
    ),
    OfferPattern(
        offer_id="agent_ops_automation_pack",
        label="Agent Ops Automation Pack",
        buyers="Ops-heavy teams automating repetitive web workflows",
        delivery="Multi-agent task router + monitored browser workflow deployment",
        price_min_usd=2500,
        price_max_usd=9000,
        keywords=(
            "agent",
            "workflow",
            "multi-agent",
            "automation",
            "orchestration",
            "task",
            "pipeline",
            "execution",
        ),
        value_angle="Converts manual operations into repeatable automated lanes.",
    ),
    OfferPattern(
        offer_id="rag_research_stack",
        label="RAG Research Intelligence Stack",
        buyers="Research, legal, and strategy teams",
        delivery="Search + ingest + synthesis stack with evidence logging",
        price_min_usd=3000,
        price_max_usd=10000,
        keywords=(
            "retrieval",
            "rag",
            "knowledge",
            "search",
            "embedding",
            "summarization",
            "dataset",
            "corpus",
        ),
        value_angle="Cuts research cycle time while preserving traceable sources.",
    ),
    OfferPattern(
        offer_id="model_eval_benchmark_service",
        label="Model Eval + Benchmark Service",
        buyers="AI product teams comparing providers/models",
        delivery="Custom eval harness + regression checks + score dashboards",
        price_min_usd=2000,
        price_max_usd=7500,
        keywords=(
            "benchmark",
            "evaluation",
            "robustness",
            "adversarial",
            "performance",
            "accuracy",
            "reliability",
        ),
        value_angle="Improves model selection decisions with measurable quality gates.",
    ),
    OfferPattern(
        offer_id="commerce_conversion_ai",
        label="Ecommerce Conversion AI Ops",
        buyers="Shopify stores and digital-product businesses",
        delivery="Offer/pricing optimization + automated follow-up funnel",
        price_min_usd=1500,
        price_max_usd=6000,
        keywords=(
            "commerce",
            "recommendation",
            "conversion",
            "customer",
            "pricing",
            "personalization",
            "shop",
        ),
        value_angle="Directly targets conversion rate and average order value lift.",
    ),
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_branch(default: str = "local") -> str:
    try:
        out = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or default
    except Exception:
        return default


def _parse_queries(raw: Sequence[str]) -> List[str]:
    if not raw:
        return list(DEFAULT_QUERIES)

    out: List[str] = []
    for chunk in raw:
        for token in str(chunk).split(","):
            q = token.strip()
            if q:
                out.append(q)

    return out or list(DEFAULT_QUERIES)


def _published_recency_score(published: str) -> float:
    raw = (published or "").strip()
    if not raw:
        return 0.25
    dt: Optional[datetime] = None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        return 0.25
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    age_days = max(0, int((_utc_now() - dt.astimezone(timezone.utc)).days))
    if age_days <= 30:
        return 1.0
    if age_days <= 120:
        return 0.85
    if age_days <= 365:
        return 0.65
    if age_days <= 730:
        return 0.45
    return 0.25


def _score_offer_fit(text: str, offer: OfferPattern) -> Tuple[int, List[str]]:
    hits: List[str] = []
    lowered = text.lower()
    for keyword in offer.keywords:
        if keyword in lowered:
            hits.append(keyword)
    return len(hits), hits


def _select_offer(paper: ArxivPaper) -> Tuple[OfferPattern, int, List[str]]:
    text = f"{paper.title} {paper.summary} {' '.join(paper.categories)}".lower()
    best_offer = OFFER_PATTERNS[0]
    best_score = -1
    best_hits: List[str] = []

    for offer in OFFER_PATTERNS:
        score, hits = _score_offer_fit(text, offer)
        if score > best_score:
            best_score = score
            best_offer = offer
            best_hits = hits

    return best_offer, max(best_score, 0), best_hits


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _build_leads(papers: List[ArxivPaper], top_n: int) -> List[Dict[str, Any]]:
    leads: List[Dict[str, Any]] = []

    for paper in papers:
        offer, keyword_hits, hit_terms = _select_offer(paper)
        recency = _published_recency_score(paper.published)
        keyword_bonus = min(keyword_hits / 8.0, 1.0)

        money_score = _clamp01(
            (0.30 * float(paper.training_value))
            + (0.25 * float(paper.relevance_score))
            + (0.20 * float(paper.governance_score))
            + (0.15 * recency)
            + (0.10 * keyword_bonus)
        )

        lead = {
            "arxiv_id": paper.arxiv_id,
            "title": paper.title,
            "published": paper.published,
            "categories": paper.categories,
            "paper_url": paper.abs_url or f"https://arxiv.org/abs/{paper.arxiv_id}",
            "authors": paper.authors[:8],
            "abstract_excerpt": (paper.summary or "")[:520],
            "offer": {
                "offer_id": offer.offer_id,
                "label": offer.label,
                "buyers": offer.buyers,
                "delivery": offer.delivery,
                "price_min_usd": offer.price_min_usd,
                "price_max_usd": offer.price_max_usd,
                "value_angle": offer.value_angle,
            },
            "signals": {
                "keyword_hits": keyword_hits,
                "hit_terms": hit_terms,
                "governance_score": round(float(paper.governance_score), 4),
                "relevance_score": round(float(paper.relevance_score), 4),
                "training_value": round(float(paper.training_value), 4),
                "recency_score": round(recency, 4),
            },
            "money_score": round(money_score, 4),
            "execution_steps": [
                f"Draft offer brief using paper {paper.arxiv_id} as technical proof.",
                f"Build a 7-day pilot around '{offer.label}' with measurable ROI metric.",
                "Route prospect and proposal through n8n/Zapier follow-up automation.",
            ],
        }
        leads.append(lead)

    leads.sort(key=lambda item: float(item.get("money_score", 0.0)), reverse=True)

    trimmed = leads[: max(1, top_n)]
    for idx, row in enumerate(trimmed, start=1):
        row["rank"] = idx
    return trimmed


def _build_markdown_report(
    *,
    run_id: str,
    queries: Sequence[str],
    papers_count: int,
    leads: Sequence[Dict[str, Any]],
    lane_assignment: Dict[str, Any],
    route_results: Dict[str, Any],
) -> str:
    lines: List[str] = []
    lines.append("# ArXiv Monetization Spine")
    lines.append("")
    lines.append(f"Generated: {_utc_iso()}")
    lines.append(f"Run ID: {run_id}")
    lines.append("")
    lines.append("## Queries")
    for query in queries:
        lines.append(f"- {query}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Papers analyzed: {papers_count}")
    lines.append(f"- Leads generated: {len(leads)}")
    lines.append(f"- Lane: {lane_assignment.get('tentacle_id', 'n/a')} via {lane_assignment.get('execution_engine', 'n/a')}")

    n8n_status = str((route_results.get("n8n") or {}).get("status", "skipped"))
    zapier_status = str((route_results.get("zapier") or {}).get("status", "skipped"))
    lines.append(f"- n8n route: {n8n_status}")
    lines.append(f"- Zapier route: {zapier_status}")
    lines.append("")

    lines.append("## Top Leads")
    lines.append("| Rank | Score | Offer | Price Range | Paper |")
    lines.append("|---|---:|---|---|---|")
    for lead in leads:
        offer = lead.get("offer", {})
        price_range = f"${offer.get('price_min_usd', 0):,} - ${offer.get('price_max_usd', 0):,}"
        title = str(lead.get("title", "")).replace("|", " ")
        lines.append(
            f"| {lead.get('rank', '-') } | {lead.get('money_score', 0):.4f} | {offer.get('label', '')} | {price_range} | {title} |"
        )

    lines.append("")
    lines.append("## Immediate Action")
    lines.append("1. Pick top 3 leads and generate offer pages + checkout links.")
    lines.append("2. Launch outbound to 20 high-intent prospects per lead.")
    lines.append("3. Track close-rate and CAC in n8n/Zapier loop, then prune low-converting offers.")
    lines.append("")
    return "\n".join(lines)


def _result_to_dict(result: ConnectorResult) -> Dict[str, Any]:
    return {
        "status": "sent" if result.success else "failed",
        "success": bool(result.success),
        "platform": result.platform,
        "elapsed_ms": result.elapsed_ms,
        "credits_earned": result.credits_earned,
        "error": result.error,
        "data": result.data,
    }


async def _route_to_connectors(
    *,
    route_payload: Dict[str, Any],
    route_n8n: bool,
    route_zapier: bool,
    dry_run: bool,
) -> Dict[str, Any]:
    bridge = ConnectorBridge()
    out: Dict[str, Any] = {
        "n8n": {"status": "skipped", "reason": "disabled"},
        "zapier": {"status": "skipped", "reason": "disabled"},
    }

    if route_n8n:
        if not bridge.is_configured("n8n"):
            out["n8n"] = {"status": "skipped", "reason": "not_configured"}
        elif dry_run:
            out["n8n"] = {"status": "dry_run", "reason": "dry_run_enabled"}
        else:
            res = await bridge.execute("n8n", "trigger", route_payload)
            out["n8n"] = _result_to_dict(res)

    if route_zapier:
        if not bridge.is_configured("zapier"):
            out["zapier"] = {"status": "skipped", "reason": "not_configured"}
        elif dry_run:
            out["zapier"] = {"status": "dry_run", "reason": "dry_run_enabled"}
        else:
            res = await bridge.execute("zapier", "trigger", route_payload)
            out["zapier"] = _result_to_dict(res)

    return out


def _emit_crosstalk(
    *,
    summary: str,
    sender: str,
    recipient: str,
    task_id: str,
    next_action: str,
    session_id: str,
    codename: str,
    repo: str,
    branch: str,
    proof: Sequence[str],
) -> Dict[str, Any]:
    if not CROSSTALK_AVAILABLE:
        return {
            "ok": False,
            "reason": "gateway_crosstalk_unavailable",
        }

    packet = CrossTalkRequest(
        summary=summary,
        recipient=recipient,
        sender=sender,
        intent="asset_drop",
        status="done",
        task_id=task_id,
        next_action=next_action,
        risk="low",
        repo=repo,
        branch=branch,
        proof=list(proof),
        session_id=session_id,
        codename=codename,
        where="scripts/system/arxiv_monetization_spine.py",
        why="Monetization lead generation from current research",
        how="arXiv scan -> lead scoring -> connector routing -> artifact capture",
    )
    result = _write_crosstalk_packet(packet)
    return {
        "ok": True,
        "packet_id": result.get("packet", {}).get("packet_id", ""),
        "packet_path": str(result.get("packet_path", "")),
    }


def _dispatch_lane(engine: str) -> Dict[str, Any]:
    dispatcher = BrowserChainDispatcher()
    for tentacle in build_default_fleet():
        dispatcher.register_tentacle(tentacle)
    return dispatcher.assign_task(
        domain="arxiv.org",
        task_type="research",
        payload={"engine": engine},
    )


def _collect_papers(
    *,
    queries: Sequence[str],
    max_per_query: int,
    category: str,
) -> List[ArxivPaper]:
    hub = ResearchHub()
    seen: set[str] = set()
    papers: List[ArxivPaper] = []

    for query in queries:
        batch = hub.search(
            query=query,
            max_results=max_per_query,
            category=category or None,
            auto_analyze=True,
        )
        for paper in batch:
            key = paper.arxiv_id.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            papers.append(paper)

    papers.sort(key=lambda p: float(p.training_value), reverse=True)
    return papers


def _call_dispatch_monetization_swarm(codename: str, sender: str, branch: str) -> Dict[str, Any]:
    script = REPO_ROOT / "scripts" / "system" / "dispatch_monetization_swarm.py"
    if not script.exists():
        return {"ok": False, "reason": "dispatch_script_missing"}

    cmd = [
        sys.executable,
        str(script),
        "--codename",
        codename,
        "--sender",
        sender,
        "--branch",
        branch,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(REPO_ROOT))
    payload: Dict[str, Any] = {
        "ok": proc.returncode == 0,
        "returncode": int(proc.returncode),
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }
    if proc.returncode == 0:
        try:
            payload["json"] = json.loads(payload["stdout"])
        except Exception:
            pass
    return payload


def _capture_playwriter_evidence(session_id: str) -> Dict[str, Any]:
    runner = REPO_ROOT / "scripts" / "system" / "playwriter_lane_runner.py"
    if not runner.exists():
        return {"ok": False, "reason": "runner_missing"}

    tasks = ("title", "snapshot")
    outputs: Dict[str, Any] = {}
    overall_ok = True
    for task in tasks:
        cmd = [
            sys.executable,
            str(runner),
            "--session",
            str(session_id),
            "--task",
            task,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(REPO_ROOT))
        item: Dict[str, Any] = {
            "ok": proc.returncode == 0,
            "returncode": int(proc.returncode),
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
        }
        if proc.returncode == 0:
            try:
                item["json"] = json.loads(item["stdout"])
            except Exception:
                pass
        else:
            overall_ok = False
        outputs[task] = item

    return {
        "ok": overall_ok,
        "session_id": str(session_id),
        "tasks": outputs,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run arXiv monetization spine and route top leads to connectors.")
    parser.add_argument("--query", action="append", default=[], help="Query text (repeatable or comma-separated).")
    parser.add_argument("--max-per-query", type=int, default=5)
    parser.add_argument("--top-leads", type=int, default=10)
    parser.add_argument("--category", default="")
    parser.add_argument("--engine", choices=["playwriter", "playwright"], default="playwriter")
    parser.add_argument("--output-dir", default="artifacts/monetization")

    parser.add_argument("--route-n8n", dest="route_n8n", action="store_true")
    parser.add_argument("--no-route-n8n", dest="route_n8n", action="store_false")
    parser.set_defaults(route_n8n=True)

    parser.add_argument("--route-zapier", dest="route_zapier", action="store_true")
    parser.add_argument("--no-route-zapier", dest="route_zapier", action="store_false")
    parser.set_defaults(route_zapier=True)

    parser.add_argument("--dry-run-routing", action="store_true")
    parser.add_argument("--skip-lane-dispatch", action="store_true")
    parser.add_argument("--dispatch-monetization-swarm", action="store_true")
    parser.add_argument("--capture-playwriter-evidence", action="store_true")
    parser.add_argument("--playwriter-session", default="1")

    parser.add_argument("--sender", default="agent.codex")
    parser.add_argument("--recipient", default="agent.claude")
    parser.add_argument("--repo", default="SCBE-AETHERMOORE")
    parser.add_argument("--branch", default="")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--codename", default="RevenueSpine-Arxiv")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    branch = args.branch.strip() or _git_branch("local")
    queries = _parse_queries(args.query)
    now = _utc_now()
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    day = now.strftime("%Y%m%d")
    run_id = f"arxiv-monetization-{stamp}"

    lane_assignment: Dict[str, Any]
    if args.skip_lane_dispatch:
        lane_assignment = {"ok": True, "skipped": True, "reason": "skip_lane_dispatch"}
    else:
        lane_assignment = _dispatch_lane(args.engine)

    papers = _collect_papers(
        queries=queries,
        max_per_query=max(1, int(args.max_per_query)),
        category=args.category.strip(),
    )
    leads = _build_leads(papers, top_n=max(1, int(args.top_leads)))

    route_payload: Dict[str, Any] = {
        "event": "arxiv_monetization_spine",
        "run_id": run_id,
        "generated_at": _utc_iso(),
        "queries": queries,
        "paper_count": len(papers),
        "top_lead_count": len(leads),
        "top_leads": leads,
    }
    route_results = asyncio.run(
        _route_to_connectors(
            route_payload=route_payload,
            route_n8n=bool(args.route_n8n),
            route_zapier=bool(args.route_zapier),
            dry_run=bool(args.dry_run_routing),
        )
    )

    out_dir = (REPO_ROOT / args.output_dir / day).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{run_id}.json"
    md_path = out_dir / f"{run_id}.md"

    markdown_report = _build_markdown_report(
        run_id=run_id,
        queries=queries,
        papers_count=len(papers),
        leads=leads,
        lane_assignment=lane_assignment,
        route_results=route_results,
    )

    dispatch_result: Dict[str, Any] = {"ok": False, "reason": "not_requested"}
    if args.dispatch_monetization_swarm:
        dispatch_result = _call_dispatch_monetization_swarm(
            codename=f"{args.codename}-{day}",
            sender=args.sender,
            branch=branch,
        )

    playwriter_evidence: Dict[str, Any] = {"ok": False, "reason": "not_requested"}
    if args.capture_playwriter_evidence:
        playwriter_evidence = _capture_playwriter_evidence(str(args.playwriter_session))

    artifact = {
        "ok": True,
        "run_id": run_id,
        "generated_at": _utc_iso(),
        "queries": queries,
        "lane_assignment": lane_assignment,
        "papers_count": len(papers),
        "leads_count": len(leads),
        "route_results": route_results,
        "dispatch_monetization_swarm": dispatch_result,
        "playwriter_evidence": playwriter_evidence,
        "top_leads": leads,
        "report_markdown_path": str(md_path),
    }

    json_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    md_path.write_text(markdown_report, encoding="utf-8")

    crosstalk = _emit_crosstalk(
        summary=(
            f"ArXiv monetization run {run_id} generated {len(leads)} leads from {len(papers)} papers. "
            f"n8n={route_results.get('n8n', {}).get('status', 'skipped')} "
            f"zapier={route_results.get('zapier', {}).get('status', 'skipped')}"
        ),
        sender=args.sender,
        recipient=args.recipient,
        task_id="MONETIZE-ARXIV-SPINE",
        next_action="Pick top 3 leads and launch offer pages + outbound automation.",
        session_id=(args.session_id.strip() or f"sess-{day}-monetize"),
        codename=args.codename,
        repo=args.repo,
        branch=branch,
        proof=[str(json_path), str(md_path)],
    )

    output = {
        "ok": True,
        "run_id": run_id,
        "papers_count": len(papers),
        "leads_count": len(leads),
        "json_path": str(json_path),
        "report_path": str(md_path),
        "route_results": route_results,
        "crosstalk": crosstalk,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
