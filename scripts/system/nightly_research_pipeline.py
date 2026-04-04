"""
SCBE Nightly Research Pipeline — Autonomous Research Agent

Runs on a schedule (default: 10PM-6AM local time)
Phases every 2 hours:

  10PM — Foreign news scan (Asia/Europe daytime news, emerging events)
  12AM — American news digest (what happened today, evening/night stories)
  2AM  — Category deep dives (AI safety, mechanistic interp, PQC, browser tech)
  4AM  — Research article search (arXiv, Semantic Scholar, HuggingFace papers)
  6AM  — Synthesis + SFT generation (spin data → training pairs)

Each phase:
  1. Searches relevant sources
  2. Extracts key findings
  3. Labels with semantic tags + Sacred Tongue dimension affinity
  4. Generates SFT training pairs (instruction/response)
  5. Appends to training corpus
  6. Writes summary to Obsidian vault

Output:
  - training/sft_records/nightly_{date}.jsonl — SFT pairs
  - notes/_inbox.md — cross-talk summary
  - artifacts/research/nightly/{date}/ — raw findings

Usage:
  python scripts/system/nightly_research_pipeline.py                    # full run
  python scripts/system/nightly_research_pipeline.py --phase foreign    # single phase
  python scripts/system/nightly_research_pipeline.py --phase american
  python scripts/system/nightly_research_pipeline.py --phase categories
  python scripts/system/nightly_research_pipeline.py --phase research
  python scripts/system/nightly_research_pipeline.py --phase synthesis
  python scripts/system/nightly_research_pipeline.py --dry-run          # print plan only
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

# Research categories with Sacred Tongue affinities
RESEARCH_CATEGORIES = {
    "ai_safety": {
        "queries": ["AI safety governance", "transformer interpretability", "alignment research"],
        "tongue": "KO",  # Intent
        "arxiv_categories": ["cs.AI", "cs.LG"],
    },
    "mechanistic_interp": {
        "queries": ["mechanistic interpretability", "attention head analysis", "circuit discovery transformers"],
        "tongue": "AV",  # Metadata
        "arxiv_categories": ["cs.LG", "cs.CL"],
    },
    "post_quantum_crypto": {
        "queries": ["post-quantum cryptography", "lattice-based signatures", "ML-KEM ML-DSA"],
        "tongue": "CA",  # Compute
        "arxiv_categories": ["cs.CR"],
    },
    "browser_agents": {
        "queries": ["autonomous browser agents", "web automation AI", "computer use agents"],
        "tongue": "RU",  # Binding
        "arxiv_categories": ["cs.AI", "cs.HC"],
    },
    "hyperbolic_geometry": {
        "queries": ["hyperbolic embeddings", "Poincare ball model ML", "non-euclidean deep learning"],
        "tongue": "UM",  # Security
        "arxiv_categories": ["cs.LG", "math.DG"],
    },
    "game_ai": {
        "queries": ["game AI NPC behavior", "procedural generation AI", "emergent gameplay"],
        "tongue": "DR",  # Structure
        "arxiv_categories": ["cs.AI", "cs.GR"],
    },
}

NEWS_SOURCES = {
    "foreign": {
        "description": "Asia/Europe daytime, emerging global events",
        "queries": [
            "breaking international news technology",
            "AI regulation policy global",
            "cybersecurity incidents today",
            "open source AI releases",
        ],
        "time_window": "last 12 hours",
    },
    "american": {
        "description": "US daily digest, evening/night stories",
        "queries": [
            "US technology news today",
            "AI industry announcements",
            "startup funding AI",
            "tech policy congress",
        ],
        "time_window": "last 24 hours",
    },
    "night_darker": {
        "description": "Emergency, security, breaking — night shift news",
        "queries": [
            "cybersecurity breach attack today",
            "AI incident misuse",
            "data leak exposed",
            "critical infrastructure cyber",
        ],
        "time_window": "last 6 hours",
    },
}

# Spin data semantic field dynamics
SEMANTIC_FIELD_CONFIG = {
    "adjacency_radius": 2,  # How many hops in the topic graph
    "time_decay": 0.85,  # How fast old topics fade (per hour)
    "cross_field_weight": 0.3,  # Weight for cross-discipline connections
    "min_relevance": 0.4,  # Minimum semantic similarity to include
}


def get_phase_for_time(hour):
    """Determine which research phase to run based on hour."""
    if hour >= 22 or hour < 0:
        return "foreign"
    elif 0 <= hour < 2:
        return "american"
    elif 2 <= hour < 4:
        return "categories"
    elif 4 <= hour < 6:
        return "research"
    elif 6 <= hour < 8:
        return "synthesis"
    else:
        return "daytime"  # Not a night phase


def generate_sft_pair(finding, category):
    """Generate an SFT training pair from a research finding."""
    return {
        "instruction": f"Summarize the key finding about {category} and explain its relevance to AI governance.",
        "response": finding.get("summary", ""),
        "category": category,
        "tongue_affinity": RESEARCH_CATEGORIES.get(category, {}).get("tongue", "KO"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": finding.get("source", "unknown"),
        "semantic_tags": finding.get("tags", []),
    }


def run_phase(phase_name, dry_run=False):
    """Execute a single research phase."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    output_dir = Path(f"artifacts/research/nightly/{date_str}")
    output_dir.mkdir(parents=True, exist_ok=True)

    sft_path = Path(f"training/sft_records/nightly_{date_str}.jsonl")
    sft_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  NIGHTLY RESEARCH PIPELINE — Phase: {phase_name.upper()}")
    print(f"  Time: {now.strftime('%Y-%m-%d %H:%M:%S')} Local")
    print(f"  Output: {output_dir}")
    print(f"{'='*60}")

    if phase_name in ("foreign", "american"):
        config = NEWS_SOURCES.get(phase_name, NEWS_SOURCES.get("night_darker"))
        print(f"\n  Source: {config['description']}")
        print(f"  Time window: {config['time_window']}")
        print(f"  Queries:")
        for q in config["queries"]:
            print(f"    - {q}")

        if dry_run:
            print("\n  [DRY RUN] Would search news sources and generate SFT pairs")
            return

        # TODO: Implement actual web search via firecrawl/WebSearch
        # For now, generate the search plan
        plan = {
            "phase": phase_name,
            "timestamp": now.isoformat(),
            "queries": config["queries"],
            "time_window": config["time_window"],
            "status": "planned",
        }
        plan_path = output_dir / f"{phase_name}_plan.json"
        plan_path.write_text(json.dumps(plan, indent=2))
        print(f"\n  Plan saved: {plan_path}")

    elif phase_name == "categories":
        print(f"\n  Categories: {len(RESEARCH_CATEGORIES)}")
        for cat, config in RESEARCH_CATEGORIES.items():
            print(f"    [{config['tongue']}] {cat}: {', '.join(config['queries'][:2])}")

        if dry_run:
            print("\n  [DRY RUN] Would deep-dive into each category")
            return

        plan = {
            "phase": "categories",
            "timestamp": now.isoformat(),
            "categories": {k: v["queries"] for k, v in RESEARCH_CATEGORIES.items()},
            "status": "planned",
        }
        plan_path = output_dir / "categories_plan.json"
        plan_path.write_text(json.dumps(plan, indent=2))
        print(f"\n  Plan saved: {plan_path}")

    elif phase_name == "research":
        print("\n  Searching academic sources:")
        print("    - arXiv (last 48 hours)")
        print("    - Semantic Scholar (trending)")
        print("    - HuggingFace papers (new)")

        if dry_run:
            print("\n  [DRY RUN] Would search arXiv, Semantic Scholar, HuggingFace")
            return

        plan = {
            "phase": "research",
            "timestamp": now.isoformat(),
            "sources": ["arXiv", "Semantic Scholar", "HuggingFace"],
            "arxiv_categories": list(
                set(cat for config in RESEARCH_CATEGORIES.values() for cat in config.get("arxiv_categories", []))
            ),
            "status": "planned",
        }
        plan_path = output_dir / "research_plan.json"
        plan_path.write_text(json.dumps(plan, indent=2))
        print(f"\n  Plan saved: {plan_path}")

    elif phase_name == "synthesis":
        print("\n  Synthesis phase:")
        print("    1. Aggregate all phase findings")
        print("    2. Label with semantic field dynamics")
        print("    3. Generate SFT training pairs")
        print("    4. Write Obsidian summary")
        print(f"\n  Semantic config: {SEMANTIC_FIELD_CONFIG}")

        if dry_run:
            print("\n  [DRY RUN] Would synthesize findings into training data")
            return

        # Check what phases ran tonight
        phase_files = list(output_dir.glob("*_plan.json"))
        print(f"\n  Found {len(phase_files)} phase plans to synthesize")

    print(f"\n  Phase {phase_name} complete.")


def main():
    parser = argparse.ArgumentParser(description="SCBE Nightly Research Pipeline")
    parser.add_argument(
        "--phase",
        choices=["foreign", "american", "categories", "research", "synthesis", "all"],
        default="all",
        help="Which phase to run",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    args = parser.parse_args()

    if args.phase == "all":
        phases = ["foreign", "american", "categories", "research", "synthesis"]
    else:
        phases = [args.phase]

    for phase in phases:
        run_phase(phase, dry_run=args.dry_run)

    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE — {len(phases)} phases")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
