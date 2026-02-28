"""Batch research pull from Perplexity — cache critical intelligence.

Run this while the API key is active to stockpile research data.
Results are saved as JSONL to training/intake/perplexity_research/.

Usage:
    python scripts/perplexity_research_batch.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.obsidian_researcher.sources.perplexity_source import PerplexitySource

OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "training", "intake", "perplexity_research"
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Research queries organized by strategic priority
RESEARCH_QUERIES = [
    # Market intelligence
    {
        "method": "market_research",
        "args": ["AI safety and governance tools market 2025-2026"],
        "filename": "market_ai_safety.jsonl",
    },
    {
        "method": "market_research",
        "args": ["AI agent orchestration platforms market size and players"],
        "filename": "market_ai_agents.jsonl",
    },
    # Competitive analysis
    {
        "method": "competitive_analysis",
        "args": ["OpenClaw open source AI agent framework"],
        "filename": "competitive_openclaw.jsonl",
    },
    {
        "method": "competitive_analysis",
        "args": ["LangChain LangGraph AI agent framework"],
        "filename": "competitive_langchain.jsonl",
    },
    {
        "method": "competitive_analysis",
        "args": ["CrewAI multi-agent framework"],
        "filename": "competitive_crewai.jsonl",
    },
    # Patent landscape
    {
        "method": "patent_landscape",
        "args": ["AI safety governance mathematical cost models hyperbolic geometry"],
        "filename": "patents_ai_safety_geometry.jsonl",
    },
    {
        "method": "patent_landscape",
        "args": ["post-quantum cryptography AI agent authentication"],
        "filename": "patents_pqc_ai_auth.jsonl",
    },
    # Core technology research
    {
        "method": "research",
        "args": ["hyperbolic geometry Poincare ball model applications in AI safety and trust"],
        "kwargs": {"depth": "standard", "focus": "academic"},
        "filename": "research_hyperbolic_ai_safety.jsonl",
    },
    {
        "method": "research",
        "args": ["post-quantum cryptography ML-KEM ML-DSA NIST standards 2025 2026"],
        "kwargs": {"depth": "standard", "focus": "cryptography"},
        "filename": "research_pqc_standards.jsonl",
    },
    {
        "method": "research",
        "args": ["multi-agent AI systems governance frameworks exponential cost barriers"],
        "kwargs": {"depth": "standard", "focus": "AI governance"},
        "filename": "research_multi_agent_governance.jsonl",
    },
    {
        "method": "research",
        "args": ["AI training data quality pipelines governance automated curation"],
        "kwargs": {"depth": "standard", "focus": "data engineering"},
        "filename": "research_training_data_quality.jsonl",
    },
    {
        "method": "research",
        "args": ["federated learning geometric deep learning sphere grid neural networks"],
        "kwargs": {"depth": "standard", "focus": "machine learning architectures"},
        "filename": "research_geometric_dl.jsonl",
    },
    # Business intelligence
    {
        "method": "research",
        "args": ["how to monetize open source AI framework SaaS consulting licensing"],
        "kwargs": {"depth": "standard", "focus": "business strategy"},
        "filename": "biz_monetize_oss_ai.jsonl",
    },
    {
        "method": "research",
        "args": ["AI safety startup funding landscape 2025 2026 investors VCs"],
        "kwargs": {"depth": "standard", "focus": "fundraising"},
        "filename": "biz_ai_safety_funding.jsonl",
    },
    {
        "method": "research",
        "args": ["SBDC small business grants for AI technology startups Washington state"],
        "kwargs": {"depth": "standard", "focus": "grants"},
        "filename": "biz_sbdc_grants.jsonl",
    },
]


def run_batch():
    """Execute all research queries and save results."""
    source = PerplexitySource()
    if not source._api_key:
        print("ERROR: PERPLEXITY_API_KEY not set in environment")
        sys.exit(1)

    print(f"Starting batch research — {len(RESEARCH_QUERIES)} queries")
    print(f"Output: {OUTPUT_DIR}\n")

    results_summary = []

    for i, query in enumerate(RESEARCH_QUERIES, 1):
        method = query["method"]
        args = query["args"]
        kwargs = query.get("kwargs", {})
        filename = query["filename"]

        print(f"[{i}/{len(RESEARCH_QUERIES)}] {method}: {args[0][:60]}...")

        try:
            func = getattr(source, method)
            result = func(*args, **kwargs)

            if result:
                filepath = os.path.join(OUTPUT_DIR, filename)
                entry = {
                    "title": result.title,
                    "content": result.raw_content,
                    "summary": result.summary,
                    "tags": result.tags,
                    "metadata": result.metadata,
                    "timestamp": result.timestamp,
                    "url": result.url,
                    "identifiers": result.identifiers,
                    "batch_query": args[0],
                    "batch_method": method,
                }
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

                citations = result.metadata.get("citations", [])
                tokens = result.metadata.get("usage", {}).get("total_tokens", 0)
                print(f"  OK — {len(result.raw_content)} chars, {len(citations)} citations, {tokens} tokens")
                results_summary.append({
                    "query": args[0][:60],
                    "status": "ok",
                    "chars": len(result.raw_content),
                    "citations": len(citations),
                    "file": filename,
                })
            else:
                print(f"  EMPTY — no result returned")
                results_summary.append({
                    "query": args[0][:60],
                    "status": "empty",
                })
        except Exception as exc:
            print(f"  ERROR — {exc}")
            results_summary.append({
                "query": args[0][:60],
                "status": "error",
                "error": str(exc),
            })

        # Rate limit: ~1 req/sec for sonar
        time.sleep(2)

    # Save summary
    summary_path = os.path.join(OUTPUT_DIR, "_batch_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_queries": len(RESEARCH_QUERIES),
            "successful": sum(1 for r in results_summary if r["status"] == "ok"),
            "failed": sum(1 for r in results_summary if r["status"] != "ok"),
            "results": results_summary,
        }, f, indent=2)

    ok = sum(1 for r in results_summary if r["status"] == "ok")
    print(f"\nDone! {ok}/{len(RESEARCH_QUERIES)} successful. Summary: {summary_path}")


if __name__ == "__main__":
    run_batch()
