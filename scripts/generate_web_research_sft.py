#!/usr/bin/env python3
"""Generate SFT training data from curated web research.

Pulls content from cybersecurity, science, and technical sources via
Firecrawl/web scraping, then converts to oriented SFT pairs using auto_marker.

Workflow:
  1. Claude fetches pages via Firecrawl → saves to training/intake/web_research/
  2. This script reads those markdown files and generates oriented SFT pairs
  3. Output goes to training-data/sft/web_research_harvested.jsonl

Can also accept markdown directly via stdin for piping.

Usage:
    # Process all staged docs
    python scripts/generate_web_research_sft.py

    # Process a specific file
    python scripts/generate_web_research_sft.py --input training/intake/web_research/owasp_top10.md

    # Pipe markdown directly
    cat some_page.md | python scripts/generate_web_research_sft.py --stdin --source "OWASP Top 10"

    # List curated source targets
    python scripts/generate_web_research_sft.py --list-targets
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from training.auto_marker import chunk_markdown_to_pairs, write_oriented_jsonl

INTAKE_DIR = PROJECT_ROOT / "training" / "intake" / "web_research"
OUTPUT_PATH = PROJECT_ROOT / "training-data" / "sft" / "web_research_harvested.jsonl"

# ---------------------------------------------------------------------------
# Curated source targets — organized by domain
# ---------------------------------------------------------------------------

TARGET_SOURCES = {
    # --- Cybersecurity ---
    "owasp_top10": {
        "url": "https://owasp.org/www-project-top-ten/",
        "query": "OWASP Top 10 web application security risks",
        "category": "cyber",
    },
    "owasp_api_security": {
        "url": "https://owasp.org/API-Security/",
        "query": "OWASP API security top 10 risks",
        "category": "cyber",
    },
    "cwe_top25": {
        "url": "https://cwe.mitre.org/top25/archive/2024/2024_cwe_top25.html",
        "query": "CWE Top 25 most dangerous software weaknesses",
        "category": "cyber",
    },
    "nist_csf": {
        "url": "https://www.nist.gov/cyberframework",
        "query": "NIST Cybersecurity Framework functions and categories",
        "category": "cyber",
    },
    "pqc_nist": {
        "url": "https://csrc.nist.gov/projects/post-quantum-cryptography",
        "query": "Post-quantum cryptography standards ML-KEM ML-DSA",
        "category": "cyber",
    },
    "mitre_attack": {
        "url": "https://attack.mitre.org/",
        "query": "MITRE ATT&CK framework tactics techniques procedures",
        "category": "cyber",
    },
    "zero_trust": {
        "url": "https://www.nist.gov/publications/zero-trust-architecture",
        "query": "Zero trust architecture principles and implementation",
        "category": "cyber",
    },

    # --- ML/AI Science ---
    "attention_paper": {
        "url": "https://arxiv.org/abs/1706.03762",
        "query": "Attention is all you need transformer architecture",
        "category": "science",
    },
    "lora_paper": {
        "url": "https://arxiv.org/abs/2106.09685",
        "query": "LoRA low-rank adaptation of large language models",
        "category": "science",
    },
    "dpo_paper": {
        "url": "https://arxiv.org/abs/2305.18290",
        "query": "Direct preference optimization DPO training",
        "category": "science",
    },
    "rlhf_overview": {
        "url": "https://huggingface.co/blog/rlhf",
        "query": "RLHF reinforcement learning from human feedback overview",
        "category": "science",
    },
    "constitutional_ai": {
        "url": "https://arxiv.org/abs/2212.08073",
        "query": "Constitutional AI harmlessness from AI feedback",
        "category": "science",
    },
    "moe_overview": {
        "url": "https://huggingface.co/blog/moe",
        "query": "Mixture of experts MoE routing architecture",
        "category": "science",
    },
    "hyperbolic_nn": {
        "url": "https://arxiv.org/abs/1805.09112",
        "query": "Hyperbolic neural networks Poincare embeddings",
        "category": "math",
    },

    # --- Infrastructure ---
    "12factor": {
        "url": "https://12factor.net/",
        "query": "Twelve-factor app methodology for SaaS",
        "category": "infra",
    },
    "opentelemetry": {
        "url": "https://opentelemetry.io/docs/",
        "query": "OpenTelemetry observability traces metrics logs",
        "category": "infra",
    },

    # --- Math ---
    "poincare_model": {
        "url": "https://en.wikipedia.org/wiki/Poincar%C3%A9_disk_model",
        "query": "Poincare disk model hyperbolic geometry",
        "category": "math",
    },
    "golden_ratio": {
        "url": "https://en.wikipedia.org/wiki/Golden_ratio",
        "query": "Golden ratio phi properties and applications",
        "category": "math",
    },
    "lyapunov_stability": {
        "url": "https://en.wikipedia.org/wiki/Lyapunov_stability",
        "query": "Lyapunov stability theory control systems",
        "category": "math",
    },
}


def process_staged_file(filepath: Path, source_name: str | None = None) -> list:
    """Process a single staged markdown file into oriented records."""
    name = source_name or filepath.stem
    text = filepath.read_text(encoding="utf-8", errors="ignore")

    if len(text.strip()) < 50:
        print(f"  SKIP (too short): {filepath.name}", file=sys.stderr)
        return []

    records = chunk_markdown_to_pairs(
        markdown=text,
        source_name=name,
        source_type="web_research",
    )
    return records


def process_all_staged() -> list:
    """Process all markdown files in the intake directory."""
    if not INTAKE_DIR.exists():
        INTAKE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Created intake dir: {INTAKE_DIR}", file=sys.stderr)
        print("No files to process. Fetch pages via Firecrawl first.", file=sys.stderr)
        return []

    all_records = []
    for md_file in sorted(INTAKE_DIR.glob("*.md")):
        records = process_staged_file(md_file)
        print(f"  {md_file.name}: {len(records)} pairs", file=sys.stderr)
        all_records.extend(records)

    return all_records


def process_stdin(source_name: str) -> list:
    """Process markdown from stdin."""
    text = sys.stdin.read()
    return chunk_markdown_to_pairs(
        markdown=text,
        source_name=source_name,
        source_type="web_research",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SFT from web research")
    parser.add_argument("--input", help="Process a specific markdown file")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--source", default="unknown", help="Source name (for stdin)")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output JSONL path")
    parser.add_argument("--append", action="store_true", help="Append to existing output")
    parser.add_argument("--list-targets", action="store_true", help="List target sources")
    args = parser.parse_args()

    if args.list_targets:
        print(f"{'Source':<25} {'Category':<12} URL")
        print("-" * 90)
        for name, cfg in TARGET_SOURCES.items():
            print(f"{name:<25} {cfg['category']:<12} {cfg['url'][:55]}")
        print(f"\nTotal: {len(TARGET_SOURCES)} sources")
        return

    if args.stdin:
        records = process_stdin(args.source)
    elif args.input:
        records = process_staged_file(Path(args.input))
    else:
        records = process_all_staged()

    if not records:
        print("No records generated.", file=sys.stderr)
        return

    written = write_oriented_jsonl(records, args.output, append=args.append)
    print(f"\nWrote {written} oriented records to {args.output}", file=sys.stderr)

    layers = Counter(r.layer for r in records)
    categories = Counter(r.category for r in records)
    tongues = Counter(r.dominant_tongue for r in records)

    print(f"\n--- Layer distribution ---", file=sys.stderr)
    for k, v in layers.most_common():
        print(f"  {k}: {v}", file=sys.stderr)
    print(f"\n--- Category distribution ---", file=sys.stderr)
    for k, v in categories.most_common():
        print(f"  {k}: {v}", file=sys.stderr)
    print(f"\n--- Dominant tongue distribution ---", file=sys.stderr)
    for k, v in tongues.most_common():
        print(f"  {k}: {v}", file=sys.stderr)


if __name__ == "__main__":
    main()
