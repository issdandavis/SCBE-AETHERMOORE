#!/usr/bin/env python3
"""
Real-time HuggingFace Training Thread for the Aethermoor RPG
=============================================================

Runs a background daemon thread that collects game training events
(SFT pairs) from player choices, battles, evolutions, NPC dialogues,
and tower floor clears.  Events are batched, optionally validated
through the SCBE governance pipeline (L7/L9/L12/L14), written to
local JSONL files, and pushed to HuggingFace Hub when credentials
are available.

The module works fully without huggingface_hub installed (local JSONL
only mode).  Thread safety is ensured via queue.Queue.

Usage inside the game loop::

    from demo.hf_trainer import RealTimeHFTrainer, load_dotenv

    load_dotenv()
    trainer = RealTimeHFTrainer()
    trainer.start()

    # During gameplay:
    trainer.record_choice(
        context="Starter Village crossroads",
        choice="Take the mountain path",
        alternatives=["Follow the river", "Enter the cave"],
        outcome="Encountered a wild Golem",
        tongue="KO",
        layers=[5, 12],
    )

    trainer.record_battle(
        attacker="Izack",
        defender="Shadow Golem",
        action="Flame Cipher",
        damage=42,
        tongue="DR",
        effectiveness="super_effective",
    )

    # On shutdown:
    trainer.stop()
"""

from __future__ import annotations

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

# ---------------------------------------------------------------------------
# .env loader
# ---------------------------------------------------------------------------

def load_dotenv() -> None:
    """Try to load HF_TOKEN and GOOGLE_AI_KEY from a .env file.

    Searches for .env in the project root (two levels up from this file),
    then falls back to the current working directory.  Uses python-dotenv
    if available, otherwise does a minimal manual parse.
    """
    candidates = [
        Path(__file__).resolve().parent.parent / ".env",
        Path.cwd() / ".env",
    ]

    # Try python-dotenv first
    try:
        from dotenv import load_dotenv as _load  # type: ignore[import-untyped]
        for path in candidates:
            if path.is_file():
                _load(dotenv_path=path, override=False)
                logger.debug("Loaded .env via python-dotenv: %s", path)
                return
    except ImportError:
        pass

    # Manual fallback: KEY=VALUE lines, no interpolation
    for path in candidates:
        if not path.is_file():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    if key and key not in os.environ:
                        os.environ[key] = value
            logger.debug("Loaded .env manually: %s", path)
            return
        except OSError:
            continue


# ---------------------------------------------------------------------------
# TrainingEvent
# ---------------------------------------------------------------------------

@dataclass
class TrainingEvent:
    """A single game event destined for the training pipeline.

    Attributes:
        event_type: One of "choice", "battle", "evolution", "dialogue",
                    "tower_floor".
        prompt:     The instruction / context half of the SFT pair.
        response:   The completion / outcome half.
        metadata:   Arbitrary extra data (tongue, layers, damage, etc.).
        timestamp:  Unix epoch seconds (auto-filled).
    """
    event_type: str
    prompt: str
    response: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# RealTimeHFTrainer
# ---------------------------------------------------------------------------

class RealTimeHFTrainer:
    """Background training-data collector for the Aethermoor RPG.

    Collects :class:`TrainingEvent` objects via a thread-safe queue,
    optionally validates them through the SCBE governance pipeline, and
    exports approved pairs as JSONL files -- locally and (if configured)
    to HuggingFace Hub.

    Parameters:
        hf_repo:    HuggingFace dataset repository id.
        local_dir:  Where JSONL batches are written.  Defaults to
                    ``training-data/game_sessions/`` relative to the
                    project root.
    """

    # Maximum events drained from the queue per iteration
    _DRAIN_LIMIT: int = 100
    # Batch size that triggers an export
    _BATCH_SIZE: int = 100
    # Seconds between worker iterations
    _POLL_INTERVAL: float = 2.0
    # Maximum errors retained
    _MAX_ERRORS: int = 5

    def __init__(
        self,
        hf_repo: str = "SCBE-AETHER/aethermoor-training-v1",
        local_dir: Optional[Path] = None,
    ) -> None:
        # Threading primitives
        self.queue: queue.Queue[TrainingEvent] = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self.running: bool = False
        self._stop_event = threading.Event()

        # HuggingFace
        self.hf_repo: str = hf_repo
        self.hf_available: bool = self._try_import_hf()

        # Local storage
        if local_dir is not None:
            self.local_dir: Path = Path(local_dir)
        else:
            self.local_dir = (
                Path(__file__).resolve().parent.parent
                / "training-data"
                / "game_sessions"
            )
        self.local_dir.mkdir(parents=True, exist_ok=True)

        # Counters (accessed from main + worker thread; Python GIL
        # guarantees atomic int reads/writes so a plain int is safe)
        self.approved_count: int = 0
        self.batch_count: int = 0
        self.pending_count: int = 0
        self.status: str = "idle"

        # Governance
        self.governance_loop: Optional[Any] = None
        self._try_import_governance()

        # Error log (bounded)
        self.errors: List[str] = []

        # Internal accumulator (only touched by worker thread)
        self._approved_pairs: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background daemon thread."""
        if self.running:
            logger.warning("RealTimeHFTrainer already running")
            return

        self.running = True
        self._stop_event.clear()
        self.status = "running"

        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            name="hf-trainer-worker",
            daemon=True,
        )
        self.worker_thread.start()
        logger.info(
            "HF trainer started (hf_available=%s, governance=%s)",
            self.hf_available,
            self.governance_loop is not None,
        )

    def stop(self) -> None:
        """Signal the worker to stop and wait for it to finish."""
        if not self.running:
            return

        self.running = False
        self._stop_event.set()
        self.status = "stopping"

        if self.worker_thread is not None:
            self.worker_thread.join(timeout=10.0)
            if self.worker_thread.is_alive():
                logger.warning("Worker thread did not exit within timeout")
            self.worker_thread = None

        self.status = "stopped"
        logger.info(
            "HF trainer stopped: %d approved, %d batches exported",
            self.approved_count,
            self.batch_count,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Return a snapshot of trainer stats for the dashboard."""
        return {
            "running": self.running,
            "approved": self.approved_count,
            "batches": self.batch_count,
            "queue_size": self.pending_count,
            "status": self.status,
            "hf_available": self.hf_available,
        }

    # ------------------------------------------------------------------
    # Event submission (main thread)
    # ------------------------------------------------------------------

    def put_event(self, event: TrainingEvent) -> None:
        """Enqueue a training event (non-blocking).

        Increments *pending_count* so the dashboard can reflect the
        backlog even before the worker drains the queue.
        """
        self.queue.put_nowait(event)
        self.pending_count += 1

    # ------------------------------------------------------------------
    # Convenience recorders
    # ------------------------------------------------------------------

    def record_choice(
        self,
        context: str,
        choice: str,
        alternatives: List[str],
        outcome: str,
        tongue: str = "KO",
        layers: Optional[List[int]] = None,
    ) -> None:
        """Record a player choice event."""
        prompt = (
            f"[{tongue}] Game context: {context}\n"
            f"Player chose: {choice}\n"
            f"Alternatives: {', '.join(alternatives)}"
        )
        response = outcome
        self.put_event(TrainingEvent(
            event_type="choice",
            prompt=prompt,
            response=response,
            metadata={
                "tongue": tongue,
                "alternatives": alternatives,
                "layers": layers or [],
            },
        ))

    def record_battle(
        self,
        attacker: str,
        defender: str,
        action: str,
        damage: float,
        tongue: str = "KO",
        effectiveness: str = "normal",
    ) -> None:
        """Record a battle action event."""
        prompt = (
            f"[{tongue}] Battle: {attacker} uses {action} on {defender}"
        )
        response = (
            f"Damage: {damage}, Effectiveness: {effectiveness}"
        )
        self.put_event(TrainingEvent(
            event_type="battle",
            prompt=prompt,
            response=response,
            metadata={
                "attacker": attacker,
                "defender": defender,
                "action": action,
                "damage": damage,
                "tongue": tongue,
                "effectiveness": effectiveness,
            },
        ))

    def record_evolution(
        self,
        character: str,
        from_stage: str,
        to_stage: str,
        tongues: List[str],
    ) -> None:
        """Record a character evolution event."""
        tongue_str = ", ".join(tongues) if tongues else "none"
        prompt = (
            f"[{tongue_str}] Evolution: {character} "
            f"evolves from {from_stage}"
        )
        response = (
            f"New stage: {to_stage}, Active tongues: {tongue_str}"
        )
        self.put_event(TrainingEvent(
            event_type="evolution",
            prompt=prompt,
            response=response,
            metadata={
                "character": character,
                "from_stage": from_stage,
                "to_stage": to_stage,
                "tongues": tongues,
            },
        ))

    def record_dialogue(
        self,
        npc_name: str,
        tongue: str,
        player_input: str,
        npc_response: str,
        topic: str = "",
    ) -> None:
        """Record an NPC dialogue event."""
        prompt = (
            f"[{tongue}] NPC '{npc_name}'"
            + (f" (topic: {topic})" if topic else "")
            + f": Player says: {player_input}"
        )
        response = npc_response
        self.put_event(TrainingEvent(
            event_type="dialogue",
            prompt=prompt,
            response=response,
            metadata={
                "npc_name": npc_name,
                "tongue": tongue,
                "player_input": player_input,
                "topic": topic,
            },
        ))

    def record_tower_floor(
        self,
        floor_num: int,
        monsters_killed: int,
        theme: str,
        is_boss: bool = False,
    ) -> None:
        """Record a tower floor completion event."""
        floor_label = f"Boss floor {floor_num}" if is_boss else f"Floor {floor_num}"
        prompt = f"Tower {floor_label}: Theme={theme}"
        response = (
            f"Cleared with {monsters_killed} monsters defeated. "
            f"Boss={'yes' if is_boss else 'no'}."
        )
        self.put_event(TrainingEvent(
            event_type="tower_floor",
            prompt=prompt,
            response=response,
            metadata={
                "floor_num": floor_num,
                "monsters_killed": monsters_killed,
                "theme": theme,
                "is_boss": is_boss,
            },
        ))

    # ------------------------------------------------------------------
    # Worker thread
    # ------------------------------------------------------------------

    def _worker_loop(self) -> None:
        """Background loop: drain queue -> governance gate -> batch export."""
        logger.debug("Worker loop started")

        while self.running:
            try:
                # -- 1. Drain up to _DRAIN_LIMIT events ----------------
                drained: List[TrainingEvent] = []
                for _ in range(self._DRAIN_LIMIT):
                    try:
                        event = self.queue.get_nowait()
                        drained.append(event)
                    except queue.Empty:
                        break

                if not drained:
                    # Nothing to process; wait before polling again
                    self._stop_event.wait(timeout=self._POLL_INTERVAL)
                    continue

                # -- 2. Governance validation --------------------------
                for event in drained:
                    approved = True

                    if self.governance_loop is not None:
                        try:
                            # Use the governance loop's record + validate
                            # pipeline: record_event -> validate_event
                            ge = self.governance_loop.record_event(
                                choice=event.prompt,
                                outcome=event.response,
                                arc_stage=event.metadata.get(
                                    "arc_stage", "youth"
                                ),
                                provenance=f"aethermoor_{event.event_type}",
                            )
                            approved = self.governance_loop.validate_event(ge)
                        except Exception as exc:
                            # Governance failure should not drop data;
                            # fall through to local-only.
                            self._record_error(
                                f"Governance validation error: {exc}"
                            )
                            approved = True

                    if approved:
                        pair: Dict[str, Any] = {
                            "prompt": event.prompt,
                            "response": event.response,
                            "event_type": event.event_type,
                            "metadata": event.metadata,
                            "timestamp": event.timestamp,
                        }
                        self._approved_pairs.append(pair)
                        self.approved_count += 1

                    # Decrement pending regardless of outcome
                    self.pending_count = max(0, self.pending_count - 1)

                # -- 3. Export if batch threshold met ------------------
                while len(self._approved_pairs) >= self._BATCH_SIZE:
                    batch = self._approved_pairs[: self._BATCH_SIZE]
                    self._approved_pairs = self._approved_pairs[self._BATCH_SIZE :]
                    self._export_batch(batch)

            except Exception as exc:
                self._record_error(f"Worker loop error: {exc}")

            # Avoid busy-spinning
            self._stop_event.wait(timeout=self._POLL_INTERVAL)

        # -- Flush remaining pairs on shutdown -------------------------
        if self._approved_pairs:
            self._export_batch(self._approved_pairs)
            self._approved_pairs = []

        logger.debug("Worker loop exited")

    # ------------------------------------------------------------------
    # Batch export
    # ------------------------------------------------------------------

    def _export_batch(self, pairs: List[Dict[str, Any]]) -> None:
        """Write a batch of approved pairs to JSONL (and optionally HF Hub).

        The local file is the source of truth.  HuggingFace upload is
        best-effort; failures are logged but do not discard data.
        """
        self.batch_count += 1
        ts = int(time.time())
        filename = f"batch_{self.batch_count}_{ts}.jsonl"
        filepath = self.local_dir / filename

        # -- Local JSONL -----------------------------------------------
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                for pair in pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
            logger.info(
                "Batch %d exported locally: %d pairs -> %s",
                self.batch_count,
                len(pairs),
                filepath,
            )
        except OSError as exc:
            self._record_error(f"Local write failed: {exc}")
            return

        # -- HuggingFace Hub (best-effort) -----------------------------
        if self.hf_available:
            try:
                from huggingface_hub import HfApi  # type: ignore[import-untyped]

                api = HfApi()
                api.upload_file(
                    path_or_fileobj=str(filepath),
                    path_in_repo=f"game_sessions/{filename}",
                    repo_id=self.hf_repo,
                    repo_type="dataset",
                )
                logger.info(
                    "Batch %d pushed to HF Hub: %s/%s",
                    self.batch_count,
                    self.hf_repo,
                    filename,
                )
            except Exception as exc:
                self._record_error(f"HF upload failed: {exc}")

        self.status = (
            f"batch {self.batch_count} exported "
            f"({self.approved_count} total approved)"
        )

    # ------------------------------------------------------------------
    # Import helpers
    # ------------------------------------------------------------------

    def _try_import_governance(self) -> None:
        """Attempt to import the SCBE governance training loop.

        Falls back silently if unavailable -- the trainer will still
        collect and export data without governance validation.
        """
        try:
            # Ensure project root is on sys.path so src.* imports resolve
            _project_root = str(Path(__file__).resolve().parent.parent)
            if _project_root not in sys.path:
                sys.path.insert(0, _project_root)
            from src.gacha_isekai.training import HFTrainingLoop  # type: ignore[import-untyped]

            self.governance_loop = HFTrainingLoop()
            logger.info("SCBE governance loop loaded")
        except Exception:
            self.governance_loop = None
            logger.debug(
                "SCBE governance loop not available; running ungoverned"
            )

    def _try_import_hf(self) -> bool:
        """Check whether HuggingFace Hub is usable.

        Returns True only when the ``huggingface_hub`` package is
        importable **and** the ``HF_TOKEN`` environment variable is set.
        """
        try:
            from huggingface_hub import HfApi  # noqa: F401  # type: ignore[import-untyped]

            token = os.environ.get("HF_TOKEN", "")
            return bool(token)
        except ImportError:
            return False

    # ------------------------------------------------------------------
    # Status / dashboard
    # ------------------------------------------------------------------

    def get_status_dict(self) -> Dict[str, Any]:
        """Return a snapshot dict for dashboard display.

        Keys:
            approved  -- total approved training pairs
            batches   -- total exported batches
            pending   -- events still in the queue
            status    -- human-readable status string
            hf        -- whether HF Hub uploads are active
            governed  -- whether governance validation is active
            errors    -- last few error messages
        """
        return {
            "approved": self.approved_count,
            "batches": self.batch_count,
            "pending": self.pending_count,
            "status": self.status,
            "hf": self.hf_available,
            "governed": self.governance_loop is not None,
            "errors": list(self.errors),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_error(self, message: str) -> None:
        """Log an error and keep only the last ``_MAX_ERRORS`` entries."""
        logger.error(message)
        self.errors.append(message)
        if len(self.errors) > self._MAX_ERRORS:
            self.errors = self.errors[-self._MAX_ERRORS :]


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick smoke test: start the trainer, push a handful of events,
    # then shut down and inspect the output.
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    load_dotenv()

    trainer = RealTimeHFTrainer()
    print(f"HF available : {trainer.hf_available}")
    print(f"Governed     : {trainer.governance_loop is not None}")
    print(f"Local dir    : {trainer.local_dir}")

    trainer.start()

    # Simulate game events
    for i in range(5):
        trainer.record_choice(
            context=f"Crossroads event #{i}",
            choice="Go north",
            alternatives=["Go south", "Stay"],
            outcome=f"Encountered monster #{i}",
            tongue="KO",
            layers=[5, 12],
        )
        trainer.record_battle(
            attacker="Izack",
            defender=f"Goblin_{i}",
            action="Flame Cipher",
            damage=10 + i * 5,
            tongue="DR",
            effectiveness="super_effective",
        )
        trainer.record_evolution(
            character="Clay",
            from_stage="Rookie",
            to_stage="Champion",
            tongues=["KO", "AV"],
        )
        trainer.record_dialogue(
            npc_name="Eldrin",
            tongue="RU",
            player_input="Where is my father?",
            npc_response=f"The map shows a path beyond the {i}th spiral...",
            topic="Marcus Chen quest",
        )
        trainer.record_tower_floor(
            floor_num=i + 1,
            monsters_killed=3 + i,
            theme="Shadow Realm",
            is_boss=(i == 4),
        )

    # Give the worker time to drain
    time.sleep(5)
    trainer.stop()

    status = trainer.get_status_dict()
    print("\n--- Final Status ---")
    for k, v in status.items():
        print(f"  {k}: {v}")
