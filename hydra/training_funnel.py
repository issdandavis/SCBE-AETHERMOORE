"""
HYDRA Training Data Funnel
===========================

Collects data from all HYDRA services and structures it for AI training.

Sources:
  - Spiral search results -> SFT pairs
  - Browser swarm extractions -> SFT pairs
  - Obsidian notes -> knowledge base
  - Notion pages -> context data
  - Telegram conversations -> interaction logs
  - Self-healing events -> system behavior data
  - Decision traces -> governance training data

Sinks:
  - HuggingFace Hub datasets (push directly)
  - Local JSONL files (for review before push)
  - Colab notebooks (trigger training runs)

Usage:
    from hydra.training_funnel import TrainingFunnel

    funnel = TrainingFunnel()
    funnel.ingest_spiral_search(report)   # From spiral search results
    funnel.ingest_mesh_events(mesh)       # From self-healing mesh
    funnel.ingest_obsidian_notes()        # From Obsidian vault
    funnel.push_to_hf()                   # Push to HuggingFace
    funnel.trigger_colab_training()       # Start Colab training run
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
#  Training pair formats
# ---------------------------------------------------------------------------

@dataclass
class SFTPair:
    """Supervised fine-tuning pair."""
    instruction: str
    input: str
    output: str
    source: str  # spiral_search, browser, obsidian, notion, telegram, mesh, governance
    tongue: str = ""  # KO, AV, RU, CA, UM, DR
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    pair_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output,
            "source": self.source,
            "tongue": self.tongue,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "id": self.pair_id,
        }

    def to_chat_format(self) -> Dict[str, Any]:
        """Convert to chat format for HF datasets."""
        messages = []
        if self.instruction:
            messages.append({"role": "system", "content": self.instruction})
        if self.input:
            messages.append({"role": "user", "content": self.input})
        if self.output:
            messages.append({"role": "assistant", "content": self.output})
        return {"messages": messages, "source": self.source, "tongue": self.tongue}


@dataclass
class DPOTriple:
    """Direct Preference Optimization triple."""
    prompt: str
    chosen: str
    rejected: str
    source: str
    tongue: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "chosen": self.chosen,
            "rejected": self.rejected,
            "source": self.source,
            "tongue": self.tongue,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
#  Training Funnel
# ---------------------------------------------------------------------------

class TrainingFunnel:
    """Collects, structures, and pushes training data to HuggingFace."""

    def __init__(self, output_dir: str = "training-data/funnel"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sft_pairs: List[SFTPair] = []
        self.dpo_triples: List[DPOTriple] = []
        self.stats = {
            "spiral_search": 0,
            "browser": 0,
            "obsidian": 0,
            "notion": 0,
            "telegram": 0,
            "mesh": 0,
            "governance": 0,
        }

    # ------------------------------------------------------------------
    #  Ingest from Spiral Search
    # ------------------------------------------------------------------

    def ingest_spiral_search(self, report: Dict[str, Any]) -> int:
        """Convert spiral search results into SFT pairs.

        Each finding becomes:
          instruction: "Research and verify: [topic]"
          input: "What do we know about [finding]?"
          output: [verified answer with sources]
        """
        count = 0
        topic = report.get("topic", "unknown")
        findings = report.get("findings", [])

        for f in findings:
            pair = SFTPair(
                instruction=f"You are a research agent investigating: {topic}",
                input=f.get("question", f.get("finding", "")),
                output=f.get("answer", f.get("detail", "")),
                source="spiral_search",
                tongue=",".join(f.get("tongues", [])),
                confidence=f.get("confidence", 0.5),
            )
            if pair.input and pair.output:
                self.sft_pairs.append(pair)
                count += 1

        # Also create DPO from contradictions
        contradictions = report.get("contradictions", [])
        for c in contradictions:
            triple = DPOTriple(
                prompt=c.get("question", ""),
                chosen=c.get("verified_answer", ""),
                rejected=c.get("contradicted_claim", ""),
                source="spiral_search",
            )
            if triple.prompt and triple.chosen and triple.rejected:
                self.dpo_triples.append(triple)

        self.stats["spiral_search"] += count
        return count

    # ------------------------------------------------------------------
    #  Ingest from Browser Swarm
    # ------------------------------------------------------------------

    def ingest_browser_extraction(self, url: str, text: str, tongue: str = "") -> int:
        """Convert browser-extracted content into SFT pairs.

        Creates Q&A pairs from extracted text using simple heuristics.
        """
        count = 0
        # Split text into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]

        for i, para in enumerate(paragraphs[:10]):  # Max 10 pairs per page
            pair = SFTPair(
                instruction="Extract and summarize information from web content.",
                input=f"What does this passage from {url} say?\n\n{para[:500]}",
                output=para[:1000],
                source="browser",
                tongue=tongue,
            )
            self.sft_pairs.append(pair)
            count += 1

        self.stats["browser"] += count
        return count

    # ------------------------------------------------------------------
    #  Ingest from Obsidian Notes
    # ------------------------------------------------------------------

    def ingest_obsidian_notes(self, vault_path: str = None) -> int:
        """Scan Obsidian vault and create SFT pairs from notes."""
        if vault_path is None:
            vault_path = r"C:\Users\issda\OneDrive\Dropbox\Izack Realmforge"

        vault = Path(vault_path)
        count = 0

        # Scan key directories
        for subdir in ["SCBE Architecture", "AI Workspace", "Math Research", "Lore"]:
            dir_path = vault / subdir
            if not dir_path.exists():
                continue

            for md_file in dir_path.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8", errors="ignore")
                    if len(content) < 100:
                        continue

                    # Extract title from filename or first heading
                    title = md_file.stem.replace("_", " ").replace("-", " ")
                    lines = content.split("\n")
                    for line in lines[:5]:
                        if line.startswith("# "):
                            title = line[2:].strip()
                            break

                    pair = SFTPair(
                        instruction="You are an expert on the SCBE-AETHERMOORE system.",
                        input=f"Explain: {title}",
                        output=content[:2000],
                        source="obsidian",
                    )
                    self.sft_pairs.append(pair)
                    count += 1
                except Exception:
                    continue

        self.stats["obsidian"] += count
        return count

    # ------------------------------------------------------------------
    #  Ingest from Self-Healing Mesh Events
    # ------------------------------------------------------------------

    def ingest_mesh_events(self, mesh) -> int:
        """Convert self-healing mesh events into governance training data."""
        count = 0

        # Heal log entries -> SFT pairs about system healing
        for event in mesh.heal_log:
            pair = SFTPair(
                instruction="You are a HYDRA self-healing system operator.",
                input=f"Service '{event.get('service')}' is down with {event.get('failures', 0)} failures. What should we do?",
                output=f"Action: {event.get('action', 'heal_attempt')}. Resolution: {event.get('resolution', 'Alert sent.')}",
                source="mesh",
            )
            self.sft_pairs.append(pair)
            count += 1

        # Decision traces -> governance training data
        for trace in mesh.decision_traces:
            pair = SFTPair(
                instruction="You are a HYDRA governance decision engine.",
                input=f"Service '{trace.service}' needs action '{trace.action}'. Confidence: {trace.confidence:.2f}",
                output=f"Reasoning: {trace.reasoning}. Resolved to: {trace.resolved_to or 'pending'}. Alternatives: {', '.join(trace.alternatives) or 'none'}",
                source="governance",
                confidence=trace.confidence,
            )
            self.sft_pairs.append(pair)
            count += 1

        self.stats["mesh"] += count
        self.stats["governance"] += len(mesh.decision_traces)
        return count

    # ------------------------------------------------------------------
    #  Save locally
    # ------------------------------------------------------------------

    def save_local(self) -> Dict[str, str]:
        """Save all pairs to local JSONL files."""
        paths = {}

        # SFT pairs
        sft_path = self.output_dir / "sft_pairs.jsonl"
        with open(sft_path, "w", encoding="utf-8") as f:
            for pair in self.sft_pairs:
                f.write(json.dumps(pair.to_dict(), ensure_ascii=False) + "\n")
        paths["sft"] = str(sft_path)

        # Chat format (for HF)
        chat_path = self.output_dir / "chat_format.jsonl"
        with open(chat_path, "w", encoding="utf-8") as f:
            for pair in self.sft_pairs:
                f.write(json.dumps(pair.to_chat_format(), ensure_ascii=False) + "\n")
        paths["chat"] = str(chat_path)

        # DPO triples
        if self.dpo_triples:
            dpo_path = self.output_dir / "dpo_triples.jsonl"
            with open(dpo_path, "w", encoding="utf-8") as f:
                for triple in self.dpo_triples:
                    f.write(json.dumps(triple.to_dict(), ensure_ascii=False) + "\n")
            paths["dpo"] = str(dpo_path)

        # Stats
        stats_path = self.output_dir / "funnel_stats.json"
        with open(stats_path, "w") as f:
            json.dump({
                "total_sft": len(self.sft_pairs),
                "total_dpo": len(self.dpo_triples),
                "by_source": self.stats,
                "timestamp": time.time(),
            }, f, indent=2)
        paths["stats"] = str(stats_path)

        return paths

    # ------------------------------------------------------------------
    #  Push to HuggingFace
    # ------------------------------------------------------------------

    def push_to_hf(self, repo_id: str = "issdandavis/scbe-aethermoore-training-data",
                   split: str = "train") -> str:
        """Push training data to HuggingFace Hub."""
        token = os.environ.get("HF_TOKEN", "")
        if not token:
            return "ERROR: No HF_TOKEN set"

        # Save locally first
        paths = self.save_local()

        try:
            from huggingface_hub import HfApi
            api = HfApi(token=token)

            # Upload SFT pairs
            api.upload_file(
                path_or_fileobj=paths["sft"],
                path_in_repo=f"data/{split}/sft_pairs.jsonl",
                repo_id=repo_id,
                repo_type="dataset",
            )

            # Upload chat format
            api.upload_file(
                path_or_fileobj=paths["chat"],
                path_in_repo=f"data/{split}/chat_format.jsonl",
                repo_id=repo_id,
                repo_type="dataset",
            )

            # Upload DPO if exists
            if "dpo" in paths:
                api.upload_file(
                    path_or_fileobj=paths["dpo"],
                    path_in_repo=f"data/{split}/dpo_triples.jsonl",
                    repo_id=repo_id,
                    repo_type="dataset",
                )

            return f"Pushed {len(self.sft_pairs)} SFT + {len(self.dpo_triples)} DPO to {repo_id}"
        except Exception as e:
            return f"Push error: {e}"

    # ------------------------------------------------------------------
    #  Trigger Colab Training
    # ------------------------------------------------------------------

    def trigger_colab_training(self, tongue: str = "KO",
                                notebook_url: str = None) -> str:
        """Trigger a Colab training run.

        Colab can be triggered via:
        1. Colab API (if COLAB_API_URL is set)
        2. Google Drive -> Colab auto-open
        3. Manual: open the notebook URL

        For automated triggers, we push data to HF first, then
        the Colab notebook pulls from HF and trains.
        """
        if notebook_url is None:
            notebook_url = "https://colab.research.google.com/github/issdandavis/SCBE-AETHERMOORE/blob/main/notebooks/colab_qlora_training.ipynb"

        # Check if Colab API is available
        colab_url = os.environ.get("COLAB_API_URL", "")
        if colab_url:
            import urllib.request
            try:
                data = json.dumps({
                    "tongue": tongue,
                    "dataset": "issdandavis/scbe-aethermoore-training-data",
                    "action": "train",
                }).encode()
                req = urllib.request.Request(
                    colab_url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                )
                resp = urllib.request.urlopen(req, timeout=30)
                return f"Colab training triggered for {tongue}: {resp.status}"
            except Exception as e:
                return f"Colab API error: {e}. Manual URL: {notebook_url}"

        return f"No Colab API URL. Open manually: {notebook_url}"

    # ------------------------------------------------------------------
    #  Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Current funnel status."""
        return {
            "sft_pairs": len(self.sft_pairs),
            "dpo_triples": len(self.dpo_triples),
            "by_source": dict(self.stats),
            "output_dir": str(self.output_dir),
        }

    def status_text(self) -> str:
        s = self.status()
        lines = [
            "HYDRA Training Funnel",
            "=====================",
            f"SFT pairs: {s['sft_pairs']}",
            f"DPO triples: {s['dpo_triples']}",
            "",
            "By source:",
        ]
        for src, count in s["by_source"].items():
            lines.append(f"  {src:15s}: {count}")
        return "\n".join(lines)
