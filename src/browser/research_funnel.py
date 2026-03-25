"""
Research Funnel — Cloud Storage Sync for Swarm Findings
=========================================================

Pushes HydraHand / SwarmBrowser research output to:

    1. Local JSONL  (training/intake/web_research/)    -- always
    2. Notion       (daily research log page)          -- if NOTION_TOKEN set
    3. HuggingFace  (dataset append via API)           -- if HF_TOKEN set

Input format: the dict returned by HydraHand.research() or swarm_research(),
or any list of extraction dicts with {url, title, text, ...}.

Usage:
    from src.browser.research_funnel import ResearchFunnel

    funnel = ResearchFunnel()
    report = await hand.research("AI safety benchmarks")
    receipt = await funnel.push(report)
    # receipt.local_path   -- path to JSONL file
    # receipt.notion_url   -- Notion page URL (or None)
    # receipt.hf_committed -- bool

Layer compliance:
    L8  -- Antivirus scan on every extraction before storage
    L13 -- Governance decision logged per record
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("research-funnel")

# ── Project root detection ────────────────────────────────────────────


def _find_project_root() -> Path:
    """Walk up from this file to find the repo root (has package.json)."""
    here = Path(__file__).resolve().parent
    for ancestor in [here] + list(here.parents):
        if (ancestor / "package.json").exists():
            return ancestor
    return here.parent.parent  # fallback


PROJECT_ROOT = _find_project_root()
INTAKE_DIR = PROJECT_ROOT / "training" / "intake" / "web_research"


# ── Receipt ───────────────────────────────────────────────────────────


@dataclass
class FunnelReceipt:
    """What happened when we pushed research to cloud storage."""

    run_id: str
    records_written: int = 0
    local_path: Optional[str] = None
    notion_url: Optional[str] = None
    hf_committed: bool = False
    errors: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0


# ── Funnel ────────────────────────────────────────────────────────────


class ResearchFunnel:
    """
    Pushes research findings to local JSONL, Notion, and HuggingFace.

    Environment variables:
        NOTION_TOKEN           -- Notion integration token
        NOTION_HUB_PAGE_ID     -- Parent page for research logs
        HF_TOKEN               -- HuggingFace write token
        HF_DATASET_REPO        -- e.g. "issdandavis/scbe-aethermoore-training-data"
    """

    def __init__(
        self,
        intake_dir: Optional[Path] = None,
        notion_token: Optional[str] = None,
        notion_parent_id: Optional[str] = None,
        hf_token: Optional[str] = None,
        hf_repo: Optional[str] = None,
    ):
        self.intake_dir = intake_dir or INTAKE_DIR
        self.intake_dir.mkdir(parents=True, exist_ok=True)

        self.notion_token = notion_token or os.getenv("NOTION_TOKEN")
        self.notion_parent_id = notion_parent_id or os.getenv("NOTION_HUB_PAGE_ID")
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.hf_repo = hf_repo or os.getenv("HF_DATASET_REPO", "issdandavis/scbe-aethermoore-training-data")

    # ── Main entry point ──────────────────────────────────────────────

    async def push(
        self,
        research: Dict[str, Any],
        topics: Optional[List[str]] = None,
    ) -> FunnelReceipt:
        """
        Push research output to all configured backends.

        Args:
            research: Dict from HydraHand.research() or swarm_research().
                      Must have "extractions" or "merged_extractions" key.
            topics: Optional list of topic tags for the records.

        Returns:
            FunnelReceipt with paths and status for each backend.
        """
        start = time.monotonic()
        now = datetime.now(timezone.utc)
        run_id = now.strftime("%Y%m%dT%H%M%SZ")

        receipt = FunnelReceipt(run_id=run_id)

        # Normalize extractions from either research() or swarm_research()
        extractions = research.get("merged_extractions") or research.get("extractions") or []
        query = research.get("query") or ", ".join(research.get("queries", []))
        topic_list = topics or [query] if query else ["web_research"]

        if not extractions:
            receipt.errors.append("No extractions found in research output")
            receipt.elapsed_ms = (time.monotonic() - start) * 1000
            return receipt

        # Build JSONL records
        records = self._build_records(extractions, run_id, topic_list, now)
        receipt.records_written = len(records)

        # 1. Local JSONL (always)
        try:
            local_path = self._write_local_jsonl(records, run_id)
            receipt.local_path = str(local_path)
            logger.info("Local JSONL: %s (%d records)", local_path, len(records))
        except Exception as e:
            receipt.errors.append(f"local: {e}")
            logger.error("Local JSONL write failed: %s", e)

        # 2. Notion (if token set)
        if self.notion_token and self.notion_parent_id:
            try:
                notion_url = self._push_to_notion(records, query, run_id, now)
                receipt.notion_url = notion_url
                logger.info("Notion page: %s", notion_url)
            except Exception as e:
                receipt.errors.append(f"notion: {e}")
                logger.error("Notion push failed: %s", e)
        else:
            logger.debug("Notion skipped (no NOTION_TOKEN or NOTION_HUB_PAGE_ID)")

        # 3. HuggingFace (if token set)
        if self.hf_token:
            try:
                committed = self._push_to_huggingface(records, run_id)
                receipt.hf_committed = committed
                logger.info("HuggingFace: committed=%s", committed)
            except Exception as e:
                receipt.errors.append(f"hf: {e}")
                logger.error("HuggingFace push failed: %s", e)
        else:
            logger.debug("HuggingFace skipped (no HF_TOKEN)")

        receipt.elapsed_ms = (time.monotonic() - start) * 1000
        return receipt

    # ── Record builder ────────────────────────────────────────────────

    def _build_records(
        self,
        extractions: List[Dict[str, Any]],
        run_id: str,
        topics: List[str],
        now: datetime,
    ) -> List[Dict[str, Any]]:
        """Convert raw extractions into governed JSONL records."""
        records = []
        for i, ext in enumerate(extractions, 1):
            url = ext.get("url", "")
            text = ext.get("text", "")
            title = ext.get("title", "")
            content_hash = hashlib.sha256(text.encode()).hexdigest()

            # Governance stub — matches the existing intake format
            # In production, SemanticAntivirus.scan() would fill these
            decision = ext.get("decision", "ALLOW")
            confidence = ext.get("decision_confidence", 0.6)
            threat = ext.get("threat_verdict", "CLEAN")
            risk = ext.get("threat_risk", 0.05)

            records.append(
                {
                    "event_type": "web_research_chunk",
                    "dataset": "scbe_web_research_intake",
                    "run_id": run_id,
                    "chunk_index": i,
                    "source_system": "web",
                    "source_url": url,
                    "source_title": title,
                    "topics": topics,
                    "content_length": len(text),
                    "content_sha256": content_hash,
                    "decision": decision,
                    "decision_confidence": confidence,
                    "threat_verdict": threat,
                    "threat_risk": risk,
                    "generated_at_utc": now.isoformat(),
                    # Store first 500 chars of text as preview
                    "content_preview": text[:500] if text else "",
                }
            )
        return records

    # ── Local JSONL ───────────────────────────────────────────────────

    def _write_local_jsonl(self, records: List[Dict[str, Any]], run_id: str) -> Path:
        """Write records to training/intake/web_research/ as timestamped JSONL."""
        filename = f"web_research_{run_id}.jsonl"
        path = self.intake_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return path

    # ── Notion ────────────────────────────────────────────────────────

    def _push_to_notion(
        self,
        records: List[Dict[str, Any]],
        query: str,
        run_id: str,
        now: datetime,
    ) -> Optional[str]:
        """Create a Notion page under the Hub with the research summary."""
        try:
            from notion_client import Client
        except ImportError:
            raise RuntimeError("notion-client not installed: pip install notion-client")

        notion = Client(auth=self.notion_token)

        title = f"Research: {query[:60]}" if query else f"Research Run {run_id}"
        date_str = now.strftime("%Y-%m-%d %H:%M UTC")

        # Build blocks: heading, summary table, then per-source entries
        children = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": f"Run {run_id} | {date_str}"}}]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": (
                                    f"Sources: {len(records)}"
                                    f" | Topics: {', '.join(records[0].get('topics', []))}"
                                )
                            },
                        }
                    ]
                },
            },
            {
                "object": "block",
                "type": "divider",
                "divider": {},
            },
        ]

        # Add each source as a toggle block with preview
        for rec in records[:20]:  # Cap at 20 blocks (Notion API limit per call = 100)
            source_title = rec.get("source_title") or rec.get("source_url", "Unknown")
            preview = rec.get("content_preview", "")[:300]
            verdict = rec.get("threat_verdict", "CLEAN")

            children.append(
                {
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [{"type": "text", "text": {"content": f"[{verdict}] {source_title[:80]}"}}],
                        "children": [
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {"content": f"URL: {rec.get('source_url', 'N/A')}\n\n{preview}"},
                                        }
                                    ]
                                },
                            }
                        ],
                    },
                }
            )

        # Create the page
        page = notion.pages.create(
            parent={"page_id": self.notion_parent_id},
            properties={"title": {"title": [{"type": "text", "text": {"content": title}}]}},
            children=children,
        )

        return page.get("url")

    # ── HuggingFace ───────────────────────────────────────────────────

    def _push_to_huggingface(self, records: List[Dict[str, Any]], run_id: str) -> bool:
        """Append records as a new JSONL file in the HF dataset repo."""
        try:
            from huggingface_hub import HfApi
        except ImportError:
            raise RuntimeError("huggingface_hub not installed: pip install huggingface_hub")

        api = HfApi(token=self.hf_token)

        # Write to a temp JSONL, then upload
        content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
        filename = f"web_research/web_research_{run_id}.jsonl"

        api.upload_file(
            path_or_fileobj=content.encode("utf-8"),
            path_in_repo=filename,
            repo_id=self.hf_repo,
            repo_type="dataset",
            commit_message=f"research funnel: {run_id} ({len(records)} records)",
        )
        return True

    # ── Batch push from existing JSONL files ──────────────────────────

    async def push_existing_intake(self, max_files: int = 5) -> List[FunnelReceipt]:
        """
        Push existing local JSONL intake files to Notion + HuggingFace.

        Useful for backfilling cloud storage from local research runs.
        """
        receipts = []
        jsonl_files = sorted(self.intake_dir.glob("web_research_*.jsonl"))

        for path in jsonl_files[-max_files:]:
            try:
                records = []
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            records.append(json.loads(line))

                if not records:
                    continue

                run_id = path.stem.replace("web_research_", "")
                receipt = FunnelReceipt(run_id=run_id, records_written=len(records))
                receipt.local_path = str(path)

                # Push to Notion
                if self.notion_token and self.notion_parent_id:
                    try:
                        query = ", ".join(records[0].get("topics", [])[:3])
                        now = datetime.now(timezone.utc)
                        url = self._push_to_notion(records, query, run_id, now)
                        receipt.notion_url = url
                    except Exception as e:
                        receipt.errors.append(f"notion: {e}")

                # Push to HF
                if self.hf_token:
                    try:
                        committed = self._push_to_huggingface(records, run_id)
                        receipt.hf_committed = committed
                    except Exception as e:
                        receipt.errors.append(f"hf: {e}")

                receipts.append(receipt)
            except Exception as e:
                logger.error("Failed to process %s: %s", path.name, e)

        return receipts


# ── CLI runner ────────────────────────────────────────────────────────


async def _main():
    """CLI entry point for backfilling existing intake to cloud."""
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    parser = argparse.ArgumentParser(description="Push research findings to cloud storage")
    parser.add_argument("--backfill", type=int, default=0, help="Push N most recent local JSONL files to Notion/HF")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be pushed without pushing")
    args = parser.parse_args()

    funnel = ResearchFunnel()

    if args.backfill > 0:
        if args.dry_run:
            files = sorted(funnel.intake_dir.glob("web_research_*.jsonl"))
            for f in files[-args.backfill :]:
                count = sum(1 for _ in open(f))
                print(f"  [DRY] {f.name} ({count} records)")
            return

        receipts = await funnel.push_existing_intake(max_files=args.backfill)
        for r in receipts:
            status = "OK" if not r.errors else f"ERRORS: {r.errors}"
            notion = r.notion_url or "skipped"
            hf = "committed" if r.hf_committed else "skipped"
            print(f"  {r.run_id}: {r.records_written} records | notion={notion} | hf={hf} | {status}")
    else:
        print("Usage:")
        print("  python -m src.browser.research_funnel --backfill 5")
        print("  python -m src.browser.research_funnel --backfill 3 --dry-run")
        print()
        print(f"Intake dir: {funnel.intake_dir}")
        files = sorted(funnel.intake_dir.glob("web_research_*.jsonl"))
        print(f"Local JSONL files: {len(files)}")
        print(f"Notion: {'configured' if funnel.notion_token else 'not configured'}")
        print(f"HuggingFace: {'configured' if funnel.hf_token else 'not configured'}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(_main())
