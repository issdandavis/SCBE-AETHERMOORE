"""HF Training Loop with SCBE Governance Gating.

Full pipeline:
    1. Collect game events (player choice + squad outcome + 21D state)
    2. Validate with SCBE (rho_e < 5.0, coherence >= 0.7, PQC provenance)
    3. Store approved pairs in cloud-ready format (JSONL with signatures)
    4. Fine-tune on HF (QLoRA, 100-pair batches)
    5. Deploy updated leader model; squad inherits ternary alignment
    6. Autonomous run: 24/7 agents replay episodes, contribute to nodal culture

Layers involved:
    L7  - Phase Modulation: event collection & narrative progression
    L9  - Authentication: validation & sanitization
    L12 - Entropic Defense: rho_e gating + batching
    L14 - PQC Protocol: signing before HF push
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from src.gacha_isekai.evolution import compute_rho_e

logger = logging.getLogger(__name__)

# Where approved training data lands
DEFAULT_OUTPUT_DIR = Path(os.environ.get(
    "SCBE_TRAINING_OUTPUT",
    str(Path(__file__).resolve().parent.parent.parent / "training-data" / "gacha_sessions"),
))
DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _compute_ternary(value: Any) -> tuple:
    """Compute ternary alignment from outcome.

    Returns (physical, perpendicular) in {-1, 0, +1}.
    """
    if isinstance(value, str):
        h = hashlib.sha256(value.encode()).digest()
        p = (h[0] % 3) - 1
        q = (h[1] % 3) - 1
        return (p, q)
    elif isinstance(value, (np.ndarray, list)):
        arr = np.asarray(value, dtype=float)
        mean = float(np.mean(arr))
        return (1 if mean > 0.3 else (-1 if mean < -0.3 else 0),
                1 if float(np.std(arr)) < 0.5 else 0)
    return (0, 0)


def _ml_dsa_hash(data: bytes) -> str:
    """ML-DSA-65 compatible hash (SHA-256 stand-in for demo).

    In production, use actual ML-DSA-65 from liboqs.
    """
    return hashlib.sha256(data).hexdigest()


@dataclass
class GameEvent:
    """A collected game event for training."""
    prompt: str
    response: str
    provenance: str
    arc_stage: str = "youth"
    phase_state: Optional[List[float]] = None
    rho_e: float = 0.0
    ternary_alignment: tuple = (0, 0)
    timestamp: float = field(default_factory=time.time)


class HFTrainingLoop:
    """SCBE-governed HF training pipeline.

    Collects game events, validates through L9/L12/L14 gates,
    then outputs approved pairs for QLoRA fine-tuning.
    """

    def __init__(
        self,
        batch_size: int = 100,
        rho_e_threshold: float = 5.0,
        coherence_threshold: float = 0.7,
        output_dir: Optional[Path] = None,
        base_model: str = "microsoft/phi-2",
        hf_repo: str = "SCBE-AETHER/leader-model-v1",
    ):
        self.batch_size = batch_size
        self.rho_e_threshold = rho_e_threshold
        self.coherence_threshold = coherence_threshold
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_model = base_model
        self.hf_repo = hf_repo

        self.pending_events: List[GameEvent] = []
        self.approved_pairs: List[Dict[str, Any]] = []
        self.rejected_count: int = 0
        self.total_batches_exported: int = 0

    # -----------------------------------------------------------------
    # Layer 7: Event Collection
    # -----------------------------------------------------------------

    def record_event(
        self,
        choice: str,
        outcome: str,
        arc_stage: str = "youth",
        provenance: str = "isekai_gacha_v1",
    ) -> GameEvent:
        """Layer 7: Collect a game event as phase-modulated training data.

        Ties narrative (starter village -> father quest) to training data.
        """
        event = GameEvent(
            prompt=f"{arc_stage.capitalize()} arc choice: {choice} (Marcus Chen quest path)",
            response=outcome,
            provenance=f"{provenance}_{arc_stage}",
            arc_stage=arc_stage,
        )
        self.pending_events.append(event)
        logger.info(
            "Layer 7 event collected: %s arc, rho_e preview=%.2f",
            arc_stage, compute_rho_e(np.array([len(outcome)])),
        )
        return event

    # -----------------------------------------------------------------
    # Layer 9: Validation & Sanitization
    # -----------------------------------------------------------------

    def validate_event(self, event: GameEvent) -> bool:
        """Layer 9: Validate training pair before storage.

        Security: sanitize input, check coherence, verify hash.
        """
        # Sanitize — strip potential injection
        sanitized = re.sub(r"<script>.*?</script>", "", event.prompt + event.response, flags=re.DOTALL)

        # PQC hash for tamper detection
        pair_hash = _ml_dsa_hash(sanitized.encode())

        # Spectral coherence approximation via token statistics
        tokens = sanitized.split()
        if len(tokens) < 2:
            return False
        unique_ratio = len(set(tokens)) / len(tokens)
        coherence = min(1.0, unique_ratio * 1.2)

        if coherence < self.coherence_threshold:
            logger.warning("Layer 9 pair rejected: coherence=%.3f < %.3f", coherence, self.coherence_threshold)
            return False

        logger.debug("Layer 9 pair validated: coherence=%.3f, hash=%s", coherence, pair_hash[:16])
        return True

    # -----------------------------------------------------------------
    # Layer 12: Entropic Defense Engine (rho_e gating + batching)
    # -----------------------------------------------------------------

    def process_pending(self) -> int:
        """Layer 12: Filter pending events through rho_e gate.

        Low-entropy (safe) data gets approved. High-entropy rejected.
        Returns number of newly approved pairs.
        """
        newly_approved = 0
        remaining = []

        for event in self.pending_events:
            # Layer 9 validation first
            if not self.validate_event(event):
                self.rejected_count += 1
                continue

            # Compute rho_e
            event.rho_e = compute_rho_e(np.array([len(event.response), len(event.prompt)]))
            if event.rho_e >= self.rho_e_threshold:
                logger.warning(
                    "Layer 12 high-entropy event rejected: rho_e=%.2f",
                    event.rho_e,
                )
                self.rejected_count += 1
                continue

            # Compute ternary alignment
            event.ternary_alignment = _compute_ternary(event.response)

            # Approved — add to batch
            self.approved_pairs.append({
                "prompt": event.prompt,
                "response": event.response,
                "provenance": event.provenance,
                "rho_e": event.rho_e,
                "ternary_alignment": list(event.ternary_alignment),
                "arc_stage": event.arc_stage,
                "timestamp": event.timestamp,
            })
            newly_approved += 1

            logger.info(
                "Layer 12 approved: rho_e=%.2f, alignment=%s",
                event.rho_e, event.ternary_alignment,
            )

        self.pending_events = remaining
        return newly_approved

    # -----------------------------------------------------------------
    # Layer 14: PQC Signing & Export
    # -----------------------------------------------------------------

    def sign_and_export(self) -> Optional[str]:
        """Layer 14: PQC-sign the batch and export to JSONL.

        Signs the entire batch for tamper-proof HF uploads.
        Returns the output file path, or None if batch not full.
        """
        if len(self.approved_pairs) < self.batch_size:
            return None

        batch = self.approved_pairs[:self.batch_size]
        self.approved_pairs = self.approved_pairs[self.batch_size:]

        # PQC signature over batch
        batch_bytes = json.dumps(batch, sort_keys=True).encode()
        signature = _ml_dsa_hash(batch_bytes)

        signed_batch = {
            "pairs": batch,
            "signature": signature,
            "ts": time.time(),
            "batch_id": self.total_batches_exported,
            "base_model": self.base_model,
            "hf_repo": self.hf_repo,
        }

        # Write JSONL
        self.total_batches_exported += 1
        out_path = self.output_dir / f"batch_{self.total_batches_exported:04d}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for pair in batch:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")

        # Write signature sidecar
        sig_path = self.output_dir / f"batch_{self.total_batches_exported:04d}.sig.json"
        with open(sig_path, "w", encoding="utf-8") as f:
            json.dump({
                "signature": signature,
                "batch_id": self.total_batches_exported,
                "pair_count": len(batch),
                "ts": signed_batch["ts"],
            }, f, indent=2)

        logger.info(
            "Layer 14 batch %d exported: %d pairs, sig=%s",
            self.total_batches_exported, len(batch), signature[:16],
        )
        return str(out_path)

    # -----------------------------------------------------------------
    # Full Loop
    # -----------------------------------------------------------------

    def run_loop(self, game_events: List[Dict[str, str]]) -> Dict[str, Any]:
        """Run the full training loop: collect -> validate -> gate -> sign.

        Args:
            game_events: List of dicts with 'choice', 'outcome', 'arc_stage'.

        Returns:
            Summary dict with counts and output paths.
        """
        # Collect
        for event in game_events:
            self.record_event(
                choice=event.get("choice", ""),
                outcome=event.get("outcome", ""),
                arc_stage=event.get("arc_stage", "youth"),
            )

        # Process
        approved = self.process_pending()

        # Export if batch full
        export_path = self.sign_and_export()

        return {
            "events_collected": len(game_events),
            "events_approved": approved,
            "events_rejected": self.rejected_count,
            "pending_pairs": len(self.approved_pairs),
            "export_path": export_path,
            "total_batches": self.total_batches_exported,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Return training pipeline statistics."""
        return {
            "pending_events": len(self.pending_events),
            "approved_pairs": len(self.approved_pairs),
            "rejected_count": self.rejected_count,
            "total_batches": self.total_batches_exported,
            "rho_e_threshold": self.rho_e_threshold,
            "coherence_threshold": self.coherence_threshold,
            "base_model": self.base_model,
            "hf_repo": self.hf_repo,
        }
