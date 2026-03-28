"""
Knowledge Funnel Runner — pull from all sources, process, store, push to HF.

Usage:
    python -m src.knowledge.run_funnel                # Full run
    python -m src.knowledge.run_funnel --source arxiv  # Single source
    python -m src.knowledge.run_funnel --dry-run       # No writes
    python -m src.knowledge.run_funnel --push-hf       # Push to HuggingFace after
"""

import sys
import argparse
import datetime
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.knowledge.funnel import KnowledgeFunnel, BASIN_ROOT
from src.knowledge.tokenizer_graph.memory_chain import TokenizerGraph


def run_arxiv(funnel: KnowledgeFunnel, graph: TokenizerGraph):
    """Pull from arXiv."""
    print("\n=== arXiv Scraper ===")
    from src.knowledge.scrapers.arxiv_scraper import scrape_all_categories

    chunks = scrape_all_categories("hyperbolic geometry AI safety", max_per_cat=5)
    print(f"  Fetched {len(chunks)} papers")

    for chunk in chunks:
        result = funnel.ingest(chunk)
        if result["decision"] == "ALLOW":
            graph.add_chunk(
                chunk.id,
                chunk.title,
                chunk.category,
                chunk.content,
                chunk.source,
                chunk.chain_hash,
                chunk.parent_hash,
            )
    return len(chunks)


def run_semantic_scholar(funnel: KnowledgeFunnel, graph: TokenizerGraph):
    """Pull from Semantic Scholar."""
    print("\n=== Semantic Scholar Scraper ===")
    from src.knowledge.scrapers.semantic_scholar_scraper import scrape_all_queries

    chunks = scrape_all_queries(max_per_query=5)
    print(f"  Fetched {len(chunks)} papers")

    for chunk in chunks:
        result = funnel.ingest(chunk)
        if result["decision"] == "ALLOW":
            graph.add_chunk(
                chunk.id,
                chunk.title,
                chunk.category,
                chunk.content,
                chunk.source,
                chunk.chain_hash,
                chunk.parent_hash,
            )
    return len(chunks)


def run_notion(funnel: KnowledgeFunnel, graph: TokenizerGraph):
    """Pull from Notion workspace."""
    print("\n=== Notion Scraper ===")
    from src.knowledge.scrapers.notion_scraper import scrape_workspace

    chunks = scrape_workspace(fetch_content=True)
    print(f"  Fetched {len(chunks)} pages")

    for chunk in chunks:
        result = funnel.ingest(chunk)
        if result["decision"] == "ALLOW":
            graph.add_chunk(
                chunk.id,
                chunk.title,
                chunk.category,
                chunk.content,
                chunk.source,
                chunk.chain_hash,
                chunk.parent_hash,
            )
    return len(chunks)


def push_to_huggingface(funnel: KnowledgeFunnel, graph: TokenizerGraph):
    """Push the chain manifest and graph to HuggingFace."""
    print("\n=== Pushing to HuggingFace ===")
    import os

    hf_token = os.environ.get("HF_TOKEN", "")
    if not hf_token:
        print("  ERROR: HF_TOKEN not set, skipping push")
        return

    # Export files
    manifest_path = funnel.export_chain_manifest()
    graph_path = str(BASIN_ROOT / "memory_graph.json")
    graph.export_graph(graph_path)

    print(f"  Exported chain manifest: {manifest_path}")
    print(f"  Exported memory graph: {graph_path}")

    # Push via huggingface_hub if available
    try:
        from huggingface_hub import HfApi

        api = HfApi(token=hf_token)

        repo_id = "issdandavis/scbe-aethermoore-knowledge-base"
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M")

        api.upload_file(
            path_or_fileobj=manifest_path,
            path_in_repo=f"knowledge/chain_manifest_{timestamp}.jsonl",
            repo_id=repo_id,
            repo_type="dataset",
        )
        api.upload_file(
            path_or_fileobj=graph_path,
            path_in_repo=f"knowledge/memory_graph_{timestamp}.json",
            repo_id=repo_id,
            repo_type="dataset",
        )
        print(f"  Pushed to {repo_id}")
    except ImportError:
        print("  huggingface_hub not installed. Run: pip install huggingface_hub")
    except Exception as e:
        print(f"  HF push failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="SCBE Knowledge Funnel")
    parser.add_argument(
        "--source", choices=["arxiv", "s2", "notion", "all"], default="all"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--push-hf", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("SCBE Knowledge Funnel — All Rivers to the Basin")
    print(f"Time: {datetime.datetime.utcnow().isoformat()}")
    print("=" * 60)

    funnel = KnowledgeFunnel()
    graph = TokenizerGraph()

    total = 0
    runners = {
        "arxiv": run_arxiv,
        "s2": run_semantic_scholar,
        "notion": run_notion,
    }

    if args.source == "all":
        for name, runner in runners.items():
            try:
                total += runner(funnel, graph)
            except Exception as e:
                print(f"  ERROR in {name}: {e}")
    else:
        runner = runners.get(args.source)
        if runner:
            total += runner(funnel, graph)

    # Print stats
    stats = funnel.get_stats()
    print(f"\n{'=' * 60}")
    print("FUNNEL STATS:")
    print(f"  Total chunks processed: {stats['total']}")
    print(f"  Allowed:     {stats['allowed']}")
    print(f"  Quarantined: {stats['quarantined']}")
    print(f"  Denied:      {stats['denied']}")
    print(f"  Chain length: {stats['chain_length']}")
    print(f"  Graph nodes:  {len(graph.nodes)}")
    print(f"  Graph cords:  {len(graph.cords)}")

    # Export
    if not args.dry_run:
        manifest = funnel.export_chain_manifest()
        graph_out = str(BASIN_ROOT / "memory_graph.json")
        graph.export_graph(graph_out)
        print(f"\n  Chain manifest: {manifest}")
        print(f"  Memory graph:   {graph_out}")

    if args.push_hf and not args.dry_run:
        push_to_huggingface(funnel, graph)

    print(f"\n{'=' * 60}")
    print("Funnel complete.")


if __name__ == "__main__":
    main()
