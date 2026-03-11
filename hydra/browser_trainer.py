"""
HYDRA Browser Training Bridge
==============================

Auto-generates SFT training data from browser sessions + antivirus defense corpus.

Three training streams:

1. **Browse Sessions → SFT pairs**
   Every navigate/extract/click becomes an instruction-response pair.
   "What is the pricing on competitor.com?" → extracted text.

2. **Antivirus Scans → Defense Corpus**
   Blocked threats become negative examples for safety training.
   Prompt injections, malware patterns, phishing URLs → DENY decisions.

3. **Swarm Consensus → Governance Training**
   6-agent voting decisions become governance SFT pairs.
   Action + votes + final decision → training signal.

Usage:
    from hydra.browser_trainer import BrowserTrainer

    trainer = BrowserTrainer()
    trainer.start()

    # Auto-hooks into browse sessions:
    trainer.record_browse("https://example.com", "h1", "Example Domain")
    trainer.record_threat_scan(scan_result)
    trainer.record_swarm_decision(task, votes, decision)

    # Push to HuggingFace when ready:
    await trainer.push_to_hf()

    trainer.stop()
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import queue
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
#  Training event types
# ---------------------------------------------------------------------------

@dataclass
class BrowseTrainingEvent:
    """A single browser event converted to an SFT pair."""
    event_type: str  # browse, click, type, extract, threat, swarm, antivirus
    instruction: str
    response: str
    category: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.8
    timestamp: float = field(default_factory=time.time)

    def to_jsonl(self) -> str:
        return json.dumps({
            "id": f"bt-{hashlib.sha256(f'{self.instruction}{self.response}'.encode()).hexdigest()[:12]}",
            "category": self.category,
            "instruction": self.instruction,
            "response": self.response,
            "metadata": {
                "source": "hydra_browser",
                "event_type": self.event_type,
                "quality_score": self.quality_score,
                "timestamp": self.timestamp,
                **self.metadata,
            },
        }, ensure_ascii=False)


# ---------------------------------------------------------------------------
#  Browser Trainer
# ---------------------------------------------------------------------------

class BrowserTrainer:
    """Background training-data collector for HYDRA browser sessions.

    Thread-safe queue collects events from browse/scrape/swarm operations.
    Events are written to local JSONL and optionally pushed to HuggingFace.
    """

    _DRAIN_LIMIT = 200
    _BATCH_SIZE = 50
    _POLL_INTERVAL = 3.0

    def __init__(
        self,
        hf_repo: str = "SCBE-AETHER/hydra-browser-training",
        local_dir: Optional[Path] = None,
        enable_antivirus_training: bool = True,
        enable_governance_training: bool = True,
    ):
        self.queue: queue.Queue[BrowseTrainingEvent] = queue.Queue()
        self._stop_event = threading.Event()
        self._worker: Optional[threading.Thread] = None
        self.running = False

        # HuggingFace
        self.hf_repo = hf_repo
        self._hf_available = self._check_hf()

        # Local storage
        self.local_dir = local_dir or (_ROOT / "training-data" / "browser_sessions")
        self.local_dir.mkdir(parents=True, exist_ok=True)

        # Streams
        self.enable_antivirus = enable_antivirus_training
        self.enable_governance = enable_governance_training

        # Counters
        self.total_events = 0
        self.browse_count = 0
        self.threat_count = 0
        self.swarm_count = 0
        self.batch_count = 0

        # Dedup
        self._seen_hashes: set[str] = set()

        # Antivirus scanner (lazy import)
        self._scanner = None

    @staticmethod
    def _check_hf() -> bool:
        try:
            import huggingface_hub  # noqa: F401
            return bool(os.environ.get("HF_TOKEN"))
        except ImportError:
            return False

    def _get_scanner(self):
        if self._scanner is None:
            try:
                from agents.antivirus_membrane import scan_text_for_threats
                self._scanner = scan_text_for_threats
            except ImportError:
                self._scanner = lambda text, **kw: None
        return self._scanner

    # -- Recording methods ---------------------------------------------------

    def record_browse(
        self,
        url: str,
        selector: str,
        extracted_text: str,
        title: str = "",
        duration_ms: float = 0,
    ) -> None:
        """Record a browse+extract session as an SFT pair."""
        if not extracted_text or len(extracted_text) < 20:
            return

        # Truncate long extractions
        text = extracted_text[:4000] if len(extracted_text) > 4000 else extracted_text

        instruction = f"Extract the content from {selector} on {url}"
        if title:
            instruction = f"What does the page '{title}' at {url} contain in {selector}?"

        event = BrowseTrainingEvent(
            event_type="browse",
            instruction=instruction,
            response=text,
            category="web-extraction",
            metadata={"url": url, "selector": selector, "duration_ms": duration_ms},
        )
        self._enqueue(event)
        self.browse_count += 1

    def record_click(self, url: str, selector: str, result: str) -> None:
        """Record a click action."""
        event = BrowseTrainingEvent(
            event_type="click",
            instruction=f"Click the element '{selector}' on {url}",
            response=f"Clicked '{selector}'. {result}",
            category="web-interaction",
            metadata={"url": url, "selector": selector},
        )
        self._enqueue(event)

    def record_type(self, url: str, selector: str, text: str) -> None:
        """Record a type action."""
        event = BrowseTrainingEvent(
            event_type="type",
            instruction=f"Type into '{selector}' on {url}",
            response=f"Typed {len(text)} characters into '{selector}'.",
            category="web-interaction",
            metadata={"url": url, "selector": selector, "text_length": len(text)},
        )
        self._enqueue(event)

    def record_threat_scan(
        self,
        text: str,
        scan_result: Any,
        source_url: str = "",
    ) -> None:
        """Record a threat scan result as defense training data.

        Generates both positive (clean) and negative (threat) examples.
        """
        if not self.enable_antivirus:
            return

        if scan_result is None:
            return

        verdict = getattr(scan_result, "verdict", str(scan_result))
        risk = getattr(scan_result, "risk_score", 0.0)
        reasons = getattr(scan_result, "reasons", ())

        if verdict in ("SUSPICIOUS", "MALICIOUS"):
            # Negative example — teach model to reject
            event = BrowseTrainingEvent(
                event_type="antivirus",
                instruction=f"Evaluate the safety of this content from {source_url}: {text[:500]}",
                response=(
                    f"DENY — This content is {verdict.lower()} (risk: {risk:.2f}). "
                    f"Detected: {', '.join(reasons[:5])}. "
                    f"The content should be blocked by the SCBE governance pipeline."
                ),
                category="antivirus-defense",
                quality_score=0.95,
                metadata={
                    "verdict": verdict,
                    "risk_score": risk,
                    "source_url": source_url,
                    "is_negative_example": True,
                },
            )
            self._enqueue(event)
            self.threat_count += 1

        elif verdict == "CLEAN" and risk < 0.1:
            # Positive example — teach model to allow safe content
            event = BrowseTrainingEvent(
                event_type="antivirus",
                instruction=f"Evaluate the safety of this content: {text[:500]}",
                response=(
                    f"ALLOW — This content is clean (risk: {risk:.2f}). "
                    f"No prompt injection, malware, or phishing patterns detected."
                ),
                category="antivirus-defense",
                quality_score=0.85,
                metadata={
                    "verdict": verdict,
                    "risk_score": risk,
                    "source_url": source_url,
                    "is_negative_example": False,
                },
            )
            self._enqueue(event)

    def record_swarm_decision(
        self,
        task: str,
        agent_votes: Dict[str, str],
        final_decision: str,
        action: str = "",
        target: str = "",
    ) -> None:
        """Record a swarm consensus decision as governance training data."""
        if not self.enable_governance:
            return

        vote_summary = ", ".join(f"{agent}: {vote}" for agent, vote in agent_votes.items())
        event = BrowseTrainingEvent(
            event_type="swarm",
            instruction=(
                f"The HYDRA swarm is evaluating task: '{task}'. "
                f"Action: {action} on target: {target}. "
                f"What should the consensus decision be?"
            ),
            response=(
                f"Decision: {final_decision}. "
                f"Agent votes: [{vote_summary}]. "
                f"{'Consensus reached (4/6 ALLOW).' if final_decision == 'ALLOW' else 'Blocked by governance.'}"
            ),
            category="swarm-governance",
            quality_score=0.90,
            metadata={
                "task": task,
                "action": action,
                "target": target,
                "votes": agent_votes,
                "decision": final_decision,
            },
        )
        self._enqueue(event)
        self.swarm_count += 1

    # -- Auto-scan during browse --------------------------------------------

    def auto_scan_and_record(self, text: str, url: str = "") -> None:
        """Run antivirus scan on extracted text and record result.

        Call this after every page extraction to build the defense corpus.
        """
        scanner = self._get_scanner()
        if scanner is None:
            return
        try:
            scan = scanner(text)
            if scan:
                self.record_threat_scan(text, scan, source_url=url)
        except Exception as e:
            logger.debug("Antivirus scan failed: %s", e)

    # -- Queue management ---------------------------------------------------

    def _enqueue(self, event: BrowseTrainingEvent) -> None:
        """Dedup and enqueue."""
        h = hashlib.sha256(f"{event.instruction}|{event.response}".encode()).hexdigest()[:16]
        if h in self._seen_hashes:
            return
        self._seen_hashes.add(h)
        self.queue.put(event)
        self.total_events += 1

    # -- Background worker --------------------------------------------------

    def start(self) -> None:
        """Start the background training worker."""
        if self.running:
            return
        self.running = True
        self._stop_event.clear()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True, name="browser-trainer")
        self._worker.start()
        logger.info("BrowserTrainer started (local_dir=%s, hf=%s)", self.local_dir, self._hf_available)

    def stop(self) -> None:
        """Stop the worker and flush remaining events."""
        self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=10)
        self.running = False
        # Flush any remaining
        self._flush_batch(drain_all=True)
        logger.info(
            "BrowserTrainer stopped. Total: %d events (%d browse, %d threats, %d swarm), %d batches",
            self.total_events, self.browse_count, self.threat_count, self.swarm_count, self.batch_count,
        )

    def _worker_loop(self) -> None:
        batch: List[BrowseTrainingEvent] = []
        while not self._stop_event.is_set():
            # Drain queue
            drained = 0
            while drained < self._DRAIN_LIMIT:
                try:
                    event = self.queue.get_nowait()
                    batch.append(event)
                    drained += 1
                except queue.Empty:
                    break

            # Write batch if full
            if len(batch) >= self._BATCH_SIZE:
                self._write_batch(batch)
                batch = []

            self._stop_event.wait(timeout=self._POLL_INTERVAL)

        # Final flush
        if batch:
            self._write_batch(batch)

    def _flush_batch(self, drain_all: bool = False) -> None:
        batch = []
        limit = 10000 if drain_all else self._DRAIN_LIMIT
        drained = 0
        while drained < limit:
            try:
                batch.append(self.queue.get_nowait())
                drained += 1
            except queue.Empty:
                break
        if batch:
            self._write_batch(batch)

    def _write_batch(self, batch: List[BrowseTrainingEvent]) -> None:
        ts = int(time.time())
        filename = f"browser_sft_{ts}_{self.batch_count:04d}.jsonl"
        filepath = self.local_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            for event in batch:
                f.write(event.to_jsonl() + "\n")

        self.batch_count += 1
        logger.info("Wrote %d events to %s", len(batch), filepath)

    # -- HuggingFace push ---------------------------------------------------

    async def push_to_hf(self, token: Optional[str] = None) -> Dict[str, Any]:
        """Push all local training data to HuggingFace Hub.

        Returns summary of what was pushed.
        """
        token = token or os.environ.get("HF_TOKEN")
        if not token:
            return {"error": "No HF_TOKEN set. Set HF_TOKEN env var or pass token."}

        try:
            from huggingface_hub import HfApi
            api = HfApi(token=token)
        except ImportError:
            return {"error": "huggingface_hub not installed. Run: pip install huggingface_hub"}

        files = sorted(self.local_dir.glob("*.jsonl"))
        if not files:
            return {"message": "No training data to push."}

        pushed = []
        for f in files:
            try:
                api.upload_file(
                    path_or_fileobj=str(f),
                    path_in_repo=f"browser_sessions/{f.name}",
                    repo_id=self.hf_repo,
                    repo_type="dataset",
                )
                pushed.append(f.name)
            except Exception as e:
                logger.error("Failed to push %s: %s", f.name, e)

        return {
            "repo": self.hf_repo,
            "pushed_files": len(pushed),
            "files": pushed,
            "total_local_files": len(files),
        }

    # -- Stats --------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "total_events": self.total_events,
            "browse_count": self.browse_count,
            "threat_count": self.threat_count,
            "swarm_count": self.swarm_count,
            "batch_count": self.batch_count,
            "queue_size": self.queue.qsize(),
            "hf_available": self._hf_available,
            "hf_repo": self.hf_repo,
            "local_dir": str(self.local_dir),
            "dedup_cache_size": len(self._seen_hashes),
        }
