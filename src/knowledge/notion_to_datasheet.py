"""
Notion-to-Datasheet Funnel — pulls all SCBE Notion pages into a structured
datasheet (CSV + JSON) that lives in the repo and can be opened in any
spreadsheet tool or linked from the browser.

Usage:
    python -m src.knowledge.notion_to_datasheet                  # Full pull
    python -m src.knowledge.notion_to_datasheet --query "GeoSeed" # Specific query
    python -m src.knowledge.notion_to_datasheet --format csv     # CSV only
    python -m src.knowledge.notion_to_datasheet --push-airtable  # Also push to Airtable
"""

import os
import csv
import json
import argparse
import datetime
from pathlib import Path

import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.knowledge.funnel import KnowledgeFunnel, BASIN_ROOT
from src.knowledge.scrapers.notion_scraper import scrape_workspace, categorize_page
from src.knowledge.tokenizer_graph.memory_chain import TokenizerGraph

DATASHEET_DIR = PROJECT_ROOT / "training-data" / "datasheets"
DATASHEET_DIR.mkdir(parents=True, exist_ok=True)


def pull_notion_to_datasheet(
    queries: list[str] = None,
    fetch_content: bool = True,
    output_format: str = "both",
    push_airtable: bool = False,
) -> dict:
    """
    Pull Notion workspace into a structured datasheet.

    Returns dict with paths and stats.
    """
    print("=" * 60)
    print("Notion -> Datasheet Funnel")
    print(f"Time: {datetime.datetime.utcnow().isoformat()}")
    print("=" * 60)

    # 1. Scrape Notion
    chunks = scrape_workspace(queries=queries, fetch_content=fetch_content)
    if not chunks:
        print("No chunks returned from Notion. Check NOTION_TOKEN.")
        return {"status": "error", "reason": "no_chunks"}

    print(f"\nPulled {len(chunks)} pages from Notion")

    # 2. Run through funnel (antivirus + chain)
    funnel = KnowledgeFunnel()
    graph = TokenizerGraph()
    allowed = []

    for chunk in chunks:
        result = funnel.ingest(chunk)
        if result["decision"] == "ALLOW":
            graph.add_chunk(
                chunk.id, chunk.title, chunk.category, chunk.content,
                chunk.source, chunk.chain_hash, chunk.parent_hash,
            )
            allowed.append(chunk)

    print(f"Allowed: {len(allowed)} / {len(chunks)}")

    # 3. Build datasheet rows
    rows = []
    for chunk in allowed:
        node = graph.nodes.get(chunk.id)
        coords = node.coords if node else [0.0] * 6
        edge_count = len(node.edges) if node else 0

        rows.append({
            "id": chunk.id,
            "title": chunk.title,
            "category": chunk.category,
            "source": chunk.source,
            "url": chunk.url,
            "timestamp": chunk.timestamp,
            "trust_score": chunk.trust_score,
            "governance_zone": chunk.governance_zone,
            "chain_hash": chunk.chain_hash[:12],
            "content_length": len(chunk.content),
            "content_preview": chunk.content[:200].replace("\n", " "),
            "tongue_KO": round(coords[0], 4),
            "tongue_AV": round(coords[1], 4),
            "tongue_RU": round(coords[2], 4),
            "tongue_CA": round(coords[3], 4),
            "tongue_UM": round(coords[4], 4),
            "tongue_DR": round(coords[5], 4),
            "edge_count": edge_count,
            "notion_id": chunk.metadata.get("notion_id", ""),
        })

    # 4. Export
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M")
    paths = {}

    if output_format in ("csv", "both"):
        csv_path = DATASHEET_DIR / f"notion_datasheet_{timestamp}.csv"
        _write_csv(rows, csv_path)
        paths["csv"] = str(csv_path)
        print(f"\nCSV: {csv_path}")

    if output_format in ("json", "both"):
        json_path = DATASHEET_DIR / f"notion_datasheet_{timestamp}.json"
        json_path.write_text(json.dumps(rows, indent=2))
        paths["json"] = str(json_path)
        print(f"JSON: {json_path}")

    # Also write a "latest" symlink-style file
    latest_csv = DATASHEET_DIR / "notion_datasheet_latest.csv"
    latest_json = DATASHEET_DIR / "notion_datasheet_latest.json"
    _write_csv(rows, latest_csv)
    latest_json.write_text(json.dumps(rows, indent=2))
    paths["latest_csv"] = str(latest_csv)
    paths["latest_json"] = str(latest_json)

    # 5. Export memory graph
    graph_path = str(DATASHEET_DIR / f"notion_memory_graph_{timestamp}.json")
    graph.export_graph(graph_path)
    paths["memory_graph"] = graph_path
    print(f"Memory Graph: {graph_path}")

    # 6. Optionally push to Airtable
    if push_airtable:
        _push_to_airtable(rows)

    # 7. Stats
    stats = funnel.get_stats()
    stats["graph_nodes"] = len(graph.nodes)
    stats["graph_cords"] = len(graph.cords)
    stats["datasheet_rows"] = len(rows)

    print(f"\n{'=' * 60}")
    print(f"DATASHEET STATS:")
    print(f"  Rows:        {len(rows)}")
    print(f"  Categories:  {len(set(r['category'] for r in rows))}")
    print(f"  Graph nodes: {stats['graph_nodes']}")
    print(f"  Graph cords: {stats['graph_cords']}")
    print(f"{'=' * 60}")

    return {"status": "ok", "paths": paths, "stats": stats, "row_count": len(rows)}


def _write_csv(rows: list[dict], path: Path):
    """Write rows to CSV."""
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _push_to_airtable(rows: list[dict]):
    """Push datasheet rows to Airtable Knowledge table."""
    from urllib.request import urlopen, Request

    token = os.environ.get("AIRTABLE_TOKEN", "")
    base_id = os.environ.get("AIRTABLE_BASE_ID", "appPef1ccaauFOimQ")
    table_name = "Knowledge"

    if not token:
        print("  AIRTABLE_TOKEN not set, skipping Airtable push")
        return

    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Airtable accepts max 10 records per batch
    for i in range(0, len(rows), 10):
        batch = rows[i:i+10]
        records = []
        for row in batch:
            records.append({
                "fields": {
                    "Title": row["title"][:256],
                    "Category": row["category"],
                    "Source": row["source"],
                    "URL": row["url"],
                    "Trust Score": row["trust_score"],
                    "Zone": row["governance_zone"],
                    "Content Length": row["content_length"],
                    "Tongue KO": row["tongue_KO"],
                    "Tongue AV": row["tongue_AV"],
                    "Tongue RU": row["tongue_RU"],
                    "Tongue CA": row["tongue_CA"],
                    "Tongue UM": row["tongue_UM"],
                    "Tongue DR": row["tongue_DR"],
                    "Edge Count": row["edge_count"],
                }
            })

        body = json.dumps({"records": records}).encode()
        req = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                created = len(result.get("records", []))
                print(f"  Airtable: pushed {created} records (batch {i//10 + 1})")
        except Exception as e:
            print(f"  Airtable push error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Notion -> Datasheet Funnel")
    parser.add_argument("--query", type=str, default=None, help="Specific Notion search query")
    parser.add_argument("--format", choices=["csv", "json", "both"], default="both")
    parser.add_argument("--no-content", action="store_true", help="Skip fetching page content (faster)")
    parser.add_argument("--push-airtable", action="store_true", help="Also push to Airtable")
    args = parser.parse_args()

    queries = [args.query] if args.query else None
    pull_notion_to_datasheet(
        queries=queries,
        fetch_content=not args.no_content,
        output_format=args.format,
        push_airtable=args.push_airtable,
    )


if __name__ == "__main__":
    main()
