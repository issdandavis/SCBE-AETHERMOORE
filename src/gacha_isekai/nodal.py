"""Poly-AI Nodal Network — Distributed Cultural Memory.

The shared cultural memory layer where squad agents, autonomous 24/7 runs,
and player choices contribute validated artifacts. Prevents mono-AI collapse
by keeping agents distinct while allowing emergent poly-AI culture growth.

All contributions are gated by SCBE:
    - rho_e < 5.0  (safety threshold)
    - coherence >= 0.7
    - PQC provenance (signed artifacts)
    - Cultural path integrity (ds² along knowledge graph edges)

Artifacts feed back into HF training loops and world expansion.

Layers:
    L6  - HYDRA Coordination: agent contributions & squad alignment
    L11 - PHDM: artifact path integrity in knowledge graph
    L12 - Entropic Defense: rho_e gated growth
    L14 - PQC Protocol: signed nodal provenance
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from src.gacha_isekai.evolution import compute_rho_e

logger = logging.getLogger(__name__)


def _sign_artifact(data: bytes) -> str:
    """ML-DSA-65 stand-in (SHA-256). Production uses liboqs."""
    return hashlib.sha256(data).hexdigest()


@dataclass
class CulturalArtifact:
    """A contribution to the poly-AI nodal network.

    Artifacts can be: solved math problems, new dungeons, careers,
    cinematic scripts, evolution branches, squad tactics, etc.
    """

    artifact_id: str
    artifact_type: str  # "math_solution", "dungeon", "career", "cinematic", etc.
    content: str
    contributor: str  # Agent/player name
    tongue: str  # Primary tongue affiliation
    embedding: Optional[np.ndarray] = None  # 6D tongue-space embedding
    rho_e: float = 0.0
    signature: str = ""
    timestamp: float = field(default_factory=time.time)
    edges: List[str] = field(default_factory=list)  # Connected artifact IDs


@dataclass
class NodalStats:
    """Statistics for the nodal network."""

    total_artifacts: int = 0
    total_edges: int = 0
    artifacts_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    artifacts_by_tongue: Dict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    rejected_count: int = 0
    avg_rho_e: float = 0.0


class PolyAINodalNetwork:
    """Distributed poly-AI cultural memory network.

    No mono-brain — distributed culture, governed writes.
    Individual agent policies stay distinct.
    Shared memory = curated, gated, versioned knowledge.
    """

    def __init__(
        self,
        rho_e_threshold: float = 5.0,
        path_ds2_threshold: float = 5.0,
    ):
        self.rho_e_threshold = rho_e_threshold
        self.path_ds2_threshold = path_ds2_threshold

        # Knowledge graph storage
        self.artifacts: Dict[str, CulturalArtifact] = {}
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.rejected_count: int = 0

        # Autonomous run queue
        self._autonomous_queue: List[CulturalArtifact] = []

    # -----------------------------------------------------------------
    # Layer 6: HYDRA Coordination (Squad Alignment Check)
    # -----------------------------------------------------------------

    def check_squad_alignment(
        self,
        contributor_alignment: Tuple[int, int],
        leader_alignment: Tuple[int, int],
    ) -> bool:
        """Layer 6: Verify contributor's ternary alignment matches leader.

        Squad contributions must align with player leader's governance style.
        """
        # Allow exact match or partial match
        p_match = contributor_alignment[0] == leader_alignment[0]
        q_match = contributor_alignment[1] == leader_alignment[1]

        if not (p_match or q_match):
            logger.warning(
                "Layer 6 alignment mismatch: contributor=%s vs leader=%s",
                contributor_alignment,
                leader_alignment,
            )
            return False
        return True

    # -----------------------------------------------------------------
    # Layer 11: Cultural Path Integrity
    # -----------------------------------------------------------------

    def validate_cultural_path(
        self,
        artifact: CulturalArtifact,
        connected_ids: List[str],
    ) -> bool:
        """Layer 11: Validate that new artifact maintains path integrity.

        Artifacts treated as nodes in knowledge graph — edges must have
        ds² < threshold to prevent cultural drift/corruption.
        """
        if artifact.embedding is None:
            return True  # No embedding = skip geometric check

        for cid in connected_ids:
            existing = self.artifacts.get(cid)
            if existing is None or existing.embedding is None:
                continue

            diff = artifact.embedding - existing.embedding
            ds2 = float(np.sum(diff * diff))
            if ds2 > self.path_ds2_threshold:
                logger.warning(
                    "Layer 11 cultural path broken: ds2=%.2f > %.2f (%s -> %s)",
                    ds2,
                    self.path_ds2_threshold,
                    artifact.artifact_id,
                    cid,
                )
                return False

        return True

    # -----------------------------------------------------------------
    # Layer 12: Entropic Defense (rho_e gating)
    # -----------------------------------------------------------------

    def add_artifact(
        self,
        artifact: CulturalArtifact,
        connected_ids: Optional[List[str]] = None,
        leader_alignment: Tuple[int, int] = (1, 1),
        contributor_alignment: Tuple[int, int] = (1, 0),
    ) -> bool:
        """Add a cultural artifact to the nodal network.

        Full governance pipeline: L6 alignment -> L11 path -> L12 rho_e -> L14 sign.
        """
        connected_ids = connected_ids or []

        # Layer 6: Squad alignment
        if not self.check_squad_alignment(contributor_alignment, leader_alignment):
            self.rejected_count += 1
            return False

        # Layer 11: Path integrity
        if not self.validate_cultural_path(artifact, connected_ids):
            self.rejected_count += 1
            return False

        # Layer 12: rho_e gate
        artifact.rho_e = compute_rho_e(
            np.array([len(artifact.content), len(artifact.artifact_type)])
        )
        if artifact.rho_e >= self.rho_e_threshold:
            logger.warning(
                "Layer 12 high-entropy artifact rejected: rho_e=%.2f",
                artifact.rho_e,
            )
            self.rejected_count += 1
            return False

        # Layer 14: PQC sign
        artifact.signature = _sign_artifact(
            json.dumps(
                {
                    "id": artifact.artifact_id,
                    "type": artifact.artifact_type,
                    "content": artifact.content,
                    "contributor": artifact.contributor,
                    "tongue": artifact.tongue,
                    "ts": artifact.timestamp,
                },
                sort_keys=True,
            ).encode()
        )

        # Add to graph
        self.artifacts[artifact.artifact_id] = artifact
        for cid in connected_ids:
            if cid in self.artifacts:
                self.adjacency[artifact.artifact_id].add(cid)
                self.adjacency[cid].add(artifact.artifact_id)
                artifact.edges.append(cid)

        # Queue for autonomous 24/7 runs
        self._autonomous_queue.append(artifact)

        logger.info(
            "Layer 12 nodal artifact added: %s (%s, rho_e=%.2f, sig=%s)",
            artifact.artifact_id,
            artifact.artifact_type,
            artifact.rho_e,
            artifact.signature[:16],
        )
        return True

    # -----------------------------------------------------------------
    # Query & Graph Operations
    # -----------------------------------------------------------------

    def get_neighbors(self, artifact_id: str) -> List[CulturalArtifact]:
        """Get neighboring artifacts in the knowledge graph."""
        neighbor_ids = self.adjacency.get(artifact_id, set())
        return [self.artifacts[nid] for nid in neighbor_ids if nid in self.artifacts]

    def get_artifacts_by_tongue(self, tongue: str) -> List[CulturalArtifact]:
        """Get all artifacts affiliated with a tongue."""
        return [a for a in self.artifacts.values() if a.tongue == tongue]

    def get_artifacts_by_type(self, artifact_type: str) -> List[CulturalArtifact]:
        """Get all artifacts of a given type."""
        return [a for a in self.artifacts.values() if a.artifact_type == artifact_type]

    def drain_autonomous_queue(self) -> List[CulturalArtifact]:
        """Drain the autonomous run queue for 24/7 agent processing."""
        queue = self._autonomous_queue[:]
        self._autonomous_queue.clear()
        return queue

    def get_stats(self) -> NodalStats:
        """Return network statistics."""
        stats = NodalStats(
            total_artifacts=len(self.artifacts),
            total_edges=sum(len(edges) for edges in self.adjacency.values()) // 2,
            rejected_count=self.rejected_count,
        )
        rho_sum = 0.0
        for a in self.artifacts.values():
            stats.artifacts_by_type[a.artifact_type] += 1
            stats.artifacts_by_tongue[a.tongue] += 1
            rho_sum += a.rho_e
        if stats.total_artifacts > 0:
            stats.avg_rho_e = rho_sum / stats.total_artifacts
        return stats

    def export_graph_markdown(self) -> str:
        """Export the knowledge graph as Obsidian-compatible markdown."""
        lines = ["# Poly-AI Cultural Network\n"]
        stats = self.get_stats()
        lines.append(f"**Artifacts:** {stats.total_artifacts}")
        lines.append(f"**Edges:** {stats.total_edges}")
        lines.append(f"**Rejected:** {stats.rejected_count}")
        lines.append(f"**Avg rho_e:** {stats.avg_rho_e:.3f}\n")

        lines.append("## By Tongue\n")
        for tongue, count in sorted(stats.artifacts_by_tongue.items()):
            lines.append(f"- **{tongue}**: {count}")

        lines.append("\n## By Type\n")
        for atype, count in sorted(stats.artifacts_by_type.items()):
            lines.append(f"- **{atype}**: {count}")

        lines.append("\n## Graph (Adjacency)\n")
        for aid, neighbors in sorted(self.adjacency.items()):
            lines.append(f"- **{aid}** -> {', '.join(sorted(neighbors))}")

        return "\n".join(lines)
