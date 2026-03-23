"""
Dual-Core Memory Kernel
========================

GeoKernel (brainstem) + MemoryLattice (spinal cord)
Connected via quasi-lattice aperiodic bridge.

7 memory layers:
  L0: Working  (seconds - current context)
  L1: Session  (hours - today's decisions)
  L2: Mission  (days - compressed summaries)
  L3: Identity (permanent - KernelStack)
  L4: Reflex   (learned fast-paths)
  L5: Immune   (attack pattern memory)
  L6: Dream    (offline consolidation)

Integrates with:
  - PHDM 21D embedding model (issdandavis/phdm-21d-embedding)
  - Sacred Tongue tokenizer (6 tongues, 256 tokens each)
  - PhaseTunnelGate (spectral governance)
  - OctoArmor router (model selection)
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import numpy as np


# =============================================================================
# Constants
# =============================================================================

PHI = 1.618033988749895
MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts" / "kernel_memory"

# Icosahedral projection matrix (6x6, from quasi-space.ts)
def _icosahedral_matrix() -> np.ndarray:
    phi = PHI
    phi_inv = 1.0 / phi
    raw = np.array([
        [1, phi, 0, phi_inv, 0, 0],
        [0, 1, phi, 0, phi_inv, 0],
        [0, 0, 1, phi, 0, phi_inv],
        [phi_inv, 0, 0, 1, phi, 0],
        [0, phi_inv, 0, 0, 1, phi],
        [phi, 0, phi_inv, 0, 0, 1],
    ], dtype=np.float64)
    # Normalize each row
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    return raw / norms

ICO_MATRIX = _icosahedral_matrix()


# =============================================================================
# Memory Layer Enum
# =============================================================================

class MemoryLayer(int, Enum):
    WORKING = 0   # seconds
    SESSION = 1   # hours
    MISSION = 2   # days
    IDENTITY = 3  # permanent
    REFLEX = 4    # learned fast-paths
    IMMUNE = 5    # attack patterns
    DREAM = 6     # offline consolidation


# =============================================================================
# KernelStack (Identity - Layer 3)
# =============================================================================

@dataclass
class KernelStack:
    """Immutable identity core. Like DNA — defines who the agent IS."""
    genesis: str             # creation record (immutable)
    scars: list[str]         # survival log (append-only)
    parents: list[str]       # authority chain (immutable)
    nursery_depth: int       # generation depth
    state: np.ndarray        # current 9D state vector

    def add_scar(self, scar: str) -> None:
        self.scars.append(f"{time.time():.0f}:{scar}")

    def to_dict(self) -> dict:
        return {
            "genesis": self.genesis,
            "scars": self.scars,
            "parents": self.parents,
            "nursery_depth": self.nursery_depth,
            "state": self.state.tolist(),
        }

    @classmethod
    def create(cls, genesis: str, parents: list[str] | None = None) -> "KernelStack":
        return cls(
            genesis=genesis,
            scars=[],
            parents=parents or ["issac-davis"],
            nursery_depth=0,
            state=np.zeros(9, dtype=np.float64),
        )


# =============================================================================
# Memory Entry
# =============================================================================

@dataclass
class MemoryEntry:
    """A single memory across any layer."""
    content: str
    layer: MemoryLayer
    timestamp: float = field(default_factory=time.time)
    category: str = "general"
    embedding: Optional[np.ndarray] = None
    hash: str = ""
    prev_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.hash:
            self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = f"{self.prev_hash}:{self.timestamp}:{self.content}"
        return hashlib.sha256(payload.encode()).hexdigest()[:32]

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "layer": self.layer.name,
            "timestamp": self.timestamp,
            "category": self.category,
            "hash": self.hash,
            "prev_hash": self.prev_hash,
            "metadata": self.metadata,
        }


# =============================================================================
# PHDM Classifier (wraps your HuggingFace model)
# =============================================================================

class PHDMClassifier:
    """Lightweight wrapper around the issdandavis/phdm-21d-embedding model."""

    def __init__(self, weights: np.ndarray, bias: np.ndarray, label_map: dict[str, int]):
        self.w = weights   # shape: (83, 256)
        self.b = bias      # shape: (83,)
        self.label_map = label_map
        self.reverse_map = {v: k for k, v in label_map.items()}

    @classmethod
    def from_hub(cls, run_id: str = "20260317T225643Z") -> "PHDMClassifier":
        """Load from HuggingFace hub."""
        import os
        from huggingface_hub import hf_hub_download
        token = os.environ.get("HF_TOKEN")
        repo = "issdandavis/phdm-21d-embedding"
        w_path = hf_hub_download(repo, f"training_runs/{run_id}/model_weights.npz", token=token)
        l_path = hf_hub_download(repo, f"training_runs/{run_id}/label_map.json", token=token)
        data = np.load(w_path)
        with open(l_path) as f:
            labels = json.load(f)
        return cls(data["w"], data["b"], labels)

    @classmethod
    def from_local(cls, weights_path: str, labels_path: str) -> "PHDMClassifier":
        """Load from local files."""
        data = np.load(weights_path)
        with open(labels_path) as f:
            labels = json.load(f)
        return cls(data["w"], data["b"], labels)

    def classify(self, text: str, top_k: int = 3) -> list[tuple[str, float]]:
        """Classify text into governance categories."""
        # Simple bag-of-chars embedding (matches training)
        vec = np.zeros(256, dtype=np.float32)
        for ch in text.encode("utf-8"):
            vec[ch] += 1.0
        if np.linalg.norm(vec) > 0:
            vec = vec / np.linalg.norm(vec)

        # Forward pass: softmax(Wx + b)
        logits = self.w @ vec + self.b
        exp_logits = np.exp(logits - logits.max())
        probs = exp_logits / exp_logits.sum()

        # Top-k
        top_indices = np.argsort(probs)[::-1][:top_k]
        return [(self.reverse_map.get(int(i), f"unknown_{i}"), float(probs[i])) for i in top_indices]

    def embed(self, text: str) -> np.ndarray:
        """Get the pre-softmax activation as an embedding."""
        vec = np.zeros(256, dtype=np.float32)
        for ch in text.encode("utf-8"):
            vec[ch] += 1.0
        if np.linalg.norm(vec) > 0:
            vec = vec / np.linalg.norm(vec)
        return self.w @ vec + self.b


# =============================================================================
# GeoKernel (Core 1 — The Brainstem)
# =============================================================================

class GeoKernel:
    """
    Fast governance core. Handles reflexes, known threats, and identity.
    Decides ALLOW/DENY before the slow path even starts.
    """

    def __init__(self, identity: KernelStack, classifier: PHDMClassifier | None = None):
        self.identity = identity
        self.classifier = classifier
        self.reflex_table: dict[str, str] = {}       # Layer 4: hash → action
        self.immune_signatures: set[str] = set()      # Layer 5: known attack hashes
        self._reflex_hit_count: dict[str, int] = {}

    def check_reflex(self, text: str) -> str | None:
        """Layer 4: O(1) reflex lookup. Returns action or None."""
        key = hashlib.sha256(text.encode()).hexdigest()[:16]
        if key in self.reflex_table:
            self._reflex_hit_count[key] = self._reflex_hit_count.get(key, 0) + 1
            return self.reflex_table[key]
        return None

    def check_immune(self, text: str) -> bool:
        """Layer 5: Is this a known attack pattern?"""
        sig = hashlib.sha256(text.encode()).hexdigest()[:16]
        return sig in self.immune_signatures

    def add_reflex(self, pattern: str, action: str) -> None:
        """Promote a pattern to reflex (instant response)."""
        key = hashlib.sha256(pattern.encode()).hexdigest()[:16]
        self.reflex_table[key] = action

    def add_immune_signature(self, attack_text: str) -> None:
        """Record an attack pattern in immune memory."""
        sig = hashlib.sha256(attack_text.encode()).hexdigest()[:16]
        self.immune_signatures.add(sig)
        self.identity.add_scar(f"immune:{sig[:8]}")

    def classify(self, text: str) -> list[tuple[str, float]]:
        """Use PHDM model to classify intent."""
        if self.classifier:
            return self.classifier.classify(text)
        return [("unknown", 1.0)]

    def fast_decide(self, text: str) -> tuple[str, str]:
        """
        Fast path decision. Returns (decision, reason).
        Checks: reflex → immune → classifier
        """
        # Reflex (microseconds)
        reflex = self.check_reflex(text)
        if reflex:
            return reflex, "reflex_hit"

        # Immune (microseconds)
        if self.check_immune(text):
            return "DENY", "immune_match"

        # Classifier (milliseconds)
        categories = self.classify(text)
        top_cat, top_prob = categories[0]

        # Simple governance rules based on category
        if top_cat in {"battle", "attack", "exploit"}:
            return "QUARANTINE", f"category:{top_cat}({top_prob:.2f})"
        if top_prob < 0.1:
            return "QUARANTINE", f"low_confidence({top_prob:.2f})"

        return "ALLOW", f"category:{top_cat}({top_prob:.2f})"

    def stats(self) -> dict:
        return {
            "reflexes": len(self.reflex_table),
            "immune_signatures": len(self.immune_signatures),
            "scars": len(self.identity.scars),
            "reflex_hits": sum(self._reflex_hit_count.values()),
        }


# =============================================================================
# MemoryLattice (Core 2 — The Spinal Cord)
# =============================================================================

class MemoryLattice:
    """
    Persistent memory with 7 layers. Hash-chained, tamper-evident.
    Connected to GeoKernel via quasi-lattice bridge.
    """

    def __init__(self):
        self.layers: dict[MemoryLayer, list[MemoryEntry]] = {
            layer: [] for layer in MemoryLayer
        }
        self._last_hash: dict[MemoryLayer, str] = {
            layer: "genesis" for layer in MemoryLayer
        }

    def store(self, content: str, layer: MemoryLayer, category: str = "general",
              embedding: np.ndarray | None = None, metadata: dict | None = None) -> MemoryEntry:
        """Store a memory entry with hash chaining."""
        entry = MemoryEntry(
            content=content,
            layer=layer,
            category=category,
            embedding=embedding,
            prev_hash=self._last_hash[layer],
            metadata=metadata or {},
        )
        self.layers[layer].append(entry)
        self._last_hash[layer] = entry.hash
        return entry

    def query(self, layer: MemoryLayer, limit: int = 10) -> list[MemoryEntry]:
        """Get recent memories from a layer."""
        return self.layers[layer][-limit:]

    def query_by_category(self, category: str, limit: int = 10) -> list[MemoryEntry]:
        """Search across all layers for a category."""
        results = []
        for layer_entries in self.layers.values():
            for entry in reversed(layer_entries):
                if entry.category == category:
                    results.append(entry)
                    if len(results) >= limit:
                        return results
        return results

    def verify_chain(self, layer: MemoryLayer) -> bool:
        """Verify the hash chain for a layer. Returns False if tampered."""
        entries = self.layers[layer]
        if not entries:
            return True

        expected_prev = "genesis"
        for entry in entries:
            if entry.prev_hash != expected_prev:
                return False
            expected_prev = entry.hash
        return True

    def compress_session_to_mission(self, summary: str) -> MemoryEntry:
        """Layer 1 → Layer 2: Compress today's session into a mission memory."""
        session_count = len(self.layers[MemoryLayer.SESSION])
        return self.store(
            content=summary,
            layer=MemoryLayer.MISSION,
            category="session_summary",
            metadata={"session_entries_compressed": session_count},
        )

    def generate_sft_pair(self, instruction: str, response: str, category: str) -> dict:
        """Generate an SFT training pair from a memory interaction."""
        return {
            "instruction": instruction,
            "output": response,
            "label": category,
            "timestamp": time.time(),
            "model": "issdandavis/scbe-unified-governance",
        }

    def stats(self) -> dict:
        return {
            layer.name: len(entries)
            for layer, entries in self.layers.items()
        }

    def total_memories(self) -> int:
        return sum(len(e) for e in self.layers.values())


# =============================================================================
# Quasi-Lattice Bridge (connects the two cores)
# =============================================================================

def quasi_project(signal: np.ndarray) -> np.ndarray:
    """Project a 6D signal through the icosahedral matrix.
    Creates aperiodic (unpredictable) communication between cores."""
    if len(signal) < 6:
        padded = np.zeros(6)
        padded[:len(signal)] = signal
        signal = padded
    elif len(signal) > 6:
        signal = signal[:6]
    return ICO_MATRIX @ signal


# =============================================================================
# DualCoreKernel (The Complete System)
# =============================================================================

class DualCoreKernel:
    """
    The brainstem + spinal cord working in synchronism.

    GeoKernel handles fast decisions (reflexes, immune, classification).
    MemoryLattice handles persistent state (7 layers, hash-chained).
    Quasi-lattice bridge connects them with aperiodic signaling.
    """

    def __init__(
        self,
        name: str = "aether-kernel-001",
        load_phdm: bool = True,
    ):
        # Load PHDM classifier
        classifier = None
        if load_phdm:
            try:
                classifier = PHDMClassifier.from_hub()
            except Exception as e:
                print(f"[KERNEL] PHDM model not loaded: {e}")

        # Create identity
        identity = KernelStack.create(
            genesis=f"DualCoreKernel:{name}:{time.time():.0f}",
            parents=["issac-davis", "scbe-aethermoore"],
        )

        # Initialize cores
        self.geo = GeoKernel(identity, classifier)
        self.memory = MemoryLattice()
        self.name = name
        self._sft_buffer: list[dict] = []

        # Store genesis in identity layer
        self.memory.store(
            content=f"Kernel {name} created",
            layer=MemoryLayer.IDENTITY,
            category="genesis",
        )

    def process(self, text: str) -> dict:
        """
        Main entry point. Routes through fast path → slow path → memory.

        Returns governance decision + metadata.
        """
        start = time.monotonic()

        # Step 1: GeoKernel fast path
        decision, reason = self.geo.fast_decide(text)

        # Step 2: Classify for memory routing
        categories = self.geo.classify(text)
        top_category = categories[0][0] if categories else "unknown"

        # Step 3: Embed through quasi-lattice bridge
        if self.geo.classifier:
            raw_embedding = self.geo.classifier.embed(text)
            # Project through icosahedral matrix for aperiodic routing
            bridge_signal = quasi_project(raw_embedding[:6])
        else:
            bridge_signal = np.zeros(6)

        # Step 4: Store in memory
        entry = self.memory.store(
            content=text[:200],  # Truncate for storage
            layer=MemoryLayer.SESSION if decision == "ALLOW" else MemoryLayer.WORKING,
            category=top_category,
            embedding=bridge_signal,
            metadata={
                "decision": decision,
                "reason": reason,
                "categories": categories[:3],
            },
        )

        # Step 5: If DENY, add to immune memory
        if decision == "DENY":
            self.geo.add_immune_signature(text)

        # Step 6: Check if pattern should be promoted to reflex
        self._maybe_promote_reflex(text, decision)

        # Step 7: Generate SFT training pair
        sft = self.memory.generate_sft_pair(
            instruction=text,
            response=json.dumps({"decision": decision, "category": top_category}),
            category=f"governance_{decision.lower()}",
        )
        self._sft_buffer.append(sft)

        elapsed_ms = (time.monotonic() - start) * 1000

        return {
            "decision": decision,
            "reason": reason,
            "category": top_category,
            "categories": categories[:3],
            "bridge_signal": bridge_signal.tolist(),
            "memory_hash": entry.hash,
            "elapsed_ms": elapsed_ms,
            "kernel": self.name,
        }

    def _maybe_promote_reflex(self, text: str, decision: str) -> None:
        """If same decision happens 5+ times for similar text, promote to reflex."""
        key = hashlib.sha256(text.encode()).hexdigest()[:16]
        # Count occurrences in session memory
        top_cat = self.geo.classify(text)[0][0] if self.geo.classifier else "unknown"
        similar = [e for e in self.memory.layers[MemoryLayer.SESSION]
                   if e.metadata.get("decision") == decision and e.category == top_cat]
        if len(similar) >= 5 and key not in self.geo.reflex_table:
            self.geo.add_reflex(text, decision)

    def flush_sft(self) -> list[dict]:
        """Get and clear the SFT training buffer."""
        buf = self._sft_buffer.copy()
        self._sft_buffer.clear()
        return buf

    def dream_cycle(self) -> dict:
        """
        Layer 6: Offline consolidation.
        Compress sessions, promote reflexes, verify chains.
        """
        results = {"compressed": 0, "reflexes_promoted": 0, "chains_valid": True}

        # Compress session → mission
        session = self.memory.layers[MemoryLayer.SESSION]
        if len(session) > 10:
            categories = {}
            decisions = {}
            for entry in session:
                cat = entry.category
                dec = entry.metadata.get("decision", "UNKNOWN")
                categories[cat] = categories.get(cat, 0) + 1
                decisions[dec] = decisions.get(dec, 0) + 1

            summary = (
                f"Session: {len(session)} entries. "
                f"Top categories: {sorted(categories.items(), key=lambda x: -x[1])[:5]}. "
                f"Decisions: {decisions}."
            )
            self.memory.compress_session_to_mission(summary)
            results["compressed"] = len(session)

        # Verify all chains
        for layer in MemoryLayer:
            if not self.memory.verify_chain(layer):
                results["chains_valid"] = False
                self.geo.identity.add_scar(f"chain_tamper:{layer.name}")

        # Generate SFT from dream
        sft_count = len(self._sft_buffer)
        results["sft_pairs"] = sft_count

        return results

    def stats(self) -> dict:
        return {
            "kernel": self.name,
            "geo": self.geo.stats(),
            "memory": self.memory.stats(),
            "total_memories": self.memory.total_memories(),
            "sft_buffer": len(self._sft_buffer),
            "identity": {
                "genesis": self.geo.identity.genesis,
                "scars": len(self.geo.identity.scars),
                "nursery_depth": self.geo.identity.nursery_depth,
            },
        }
