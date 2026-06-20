"""
Contact Lattice Layer — Multi-Planar Dual Nodal Attention substrate.

Each token embedding is projected into 6 typed semantic planes (one per Sacred Tongue).
Per-plane Poincaré-ball representations are inserted into a shared signed octree.
Contact nodes form where 2+ planes co-locate in the same Morton-addressed cell.
Attention routes through surviving contacts, weighted by harmonic survival scores.

  c_{t,p,q} = f(h_t^{(p)}, h_t^{(q)})    [contact at token t, planes p and q]
  H(d_H, pd) = 1 / (1 + φ·d_H + 2·pd)     [harmonic survival gate — L12]

Contact cell ("slice") = octree cell at depth 6, identified by top-18 bits of Morton code.
Dual lattice = face-plane adjacency between contact cells (8 octants + 6 faces = 14 surfaces).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from hydra.color_dimension import PHI, TONGUE_WEIGHTS
from hydra.octree_sphere_grid import SphereGrid, morton_decode_3d, morton_encode_3d

TONGUES: Tuple[str, ...] = tuple(TONGUE_WEIGHTS.keys())  # KO AV RU CA UM DR, phi-ordered

# Contact detection resolution: octree depth 6 → 64³ cell grid
_CONTACT_DEPTH: int = 6
_CONTACT_SHIFT: int = 30 - 3 * _CONTACT_DEPTH  # 12 bits stripped from full Morton code


# ---------------------------------------------------------------------------
#  Data structures
# ---------------------------------------------------------------------------


@dataclass
class ContactNode:
    """A node in the contact lattice: 2+ tongue planes co-located in the same cell."""

    cell_code: int
    tongues: List[str]
    positions: List[Tuple[float, float, float]]  # Poincaré ball coords per tongue
    survival_score: float = 0.0
    sphere_grid: SphereGrid = field(default_factory=SphereGrid.create_default)


@dataclass
class ContactLatticeOutput:
    """Return type for one ContactLatticeLayer forward pass."""

    enriched: np.ndarray  # (seq_len, 3) contact-weighted embeddings
    contacts: List[List[ContactNode]]  # per-token contact node lists
    plane_embeddings: Dict[str, np.ndarray]  # {tongue: (seq_len, 3)}
    contact_counts: List[int]  # surviving contacts per token


# ---------------------------------------------------------------------------
#  Per-tongue projection into Poincaré ball
# ---------------------------------------------------------------------------


class TonguePlaneProjector:
    """
    Projects token embeddings (seq_len, d_model) into 6 per-tongue 3D Poincaré-ball vectors.

    Projection matrices W_l ∈ ℝ^{d_model × 3} are initialized as orthonormal columns,
    then scaled by φ^k where k is the tongue's position in the Sacred Tongue sequence.
    The tanh compression ensures all outputs satisfy ||h|| < 1 (open Poincaré ball).
    """

    def __init__(self, d_model: int, seed: int = 42):
        rng = np.random.default_rng(seed)
        self._W: Dict[str, np.ndarray] = {}
        for k, tongue in enumerate(TONGUES):
            raw = rng.standard_normal((d_model, 3))
            Q, _ = np.linalg.qr(raw)  # (d_model, 3) orthonormal columns
            self._W[tongue] = Q * (PHI**k)

    def project(self, embeddings: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Args:
            embeddings: (seq_len, d_model)
        Returns:
            {tongue: (seq_len, 3)}, all within ||.|| < 1
        """
        result: Dict[str, np.ndarray] = {}
        for tongue, W in self._W.items():
            h = embeddings @ W  # (seq_len, 3)
            norms = np.linalg.norm(h, axis=-1, keepdims=True) + 1e-8
            result[tongue] = (h / norms) * np.tanh(norms * 0.5)  # smooth ball compression
        return result


# ---------------------------------------------------------------------------
#  Contact Lattice Layer
# ---------------------------------------------------------------------------


class ContactLatticeLayer:
    """
    Multi-Planar Dual Nodal Attention substrate.

    Pipeline per token:
      1. Project embedding into 6 Poincaré-ball planes (TonguePlaneProjector).
      2. Compute Morton contact cell for each plane position (octree address at contact_depth).
      3. Group planes by cell; cells with 2+ planes yield candidate contact nodes.
      4. Score each candidate with the L12 harmonic wall; keep score >= threshold.
      5. Output = softmax(scores) · contact centroids; fallback = plane centroid.

    contact_depth controls the spatial resolution of co-location detection:
      depth=6 (default): 64³ grid, ~0.03 cell width — sparse, production precision
      depth=3:           8³ grid,  ~0.25 cell width — denser, good for low-d probing

    Dual lattice:
      Call dual_lattice_edges(contacts) to get face-plane adjacency between contact cells.
      Two cells are face-adjacent when their Morton-decoded coords differ by 1 on one axis
      (matching the 6-face-plane attachment geometry of SignedOctree.auto_cross_branches).
    """

    def __init__(
        self,
        d_model: int,
        contact_threshold: float = 0.3,
        contact_depth: int = 6,
    ):
        self.d_model = d_model
        self.contact_threshold = contact_threshold
        self.contact_depth = contact_depth
        self._contact_shift = 30 - 3 * contact_depth
        self.projector = TonguePlaneProjector(d_model)

    # ------------------------------------------------------------------
    #  Forward pass
    # ------------------------------------------------------------------

    def forward(self, embeddings: np.ndarray) -> ContactLatticeOutput:
        """
        Args:
            embeddings: (seq_len, d_model)
        Returns:
            ContactLatticeOutput
        """
        seq_len = embeddings.shape[0]
        plane_embeddings = self.projector.project(embeddings)

        all_contacts: List[List[ContactNode]] = []
        enriched = np.zeros((seq_len, 3), dtype=np.float64)
        contact_counts: List[int] = []

        for t in range(seq_len):
            positions: Dict[str, np.ndarray] = {tongue: plane_embeddings[tongue][t] for tongue in TONGUES}

            # Group tongues by contact cell (same Morton prefix)
            cell_groups: Dict[int, List[str]] = {}
            for tongue, pos in positions.items():
                cell = self._cell_code(pos)
                cell_groups.setdefault(cell, []).append(tongue)

            token_contacts: List[ContactNode] = []
            for cell_code, tongues_here in cell_groups.items():
                if len(tongues_here) < 2:
                    continue
                pos_here = [positions[tg] for tg in tongues_here]
                score = self._harmonic_score(pos_here)
                if score >= self.contact_threshold:
                    token_contacts.append(
                        ContactNode(
                            cell_code=cell_code,
                            tongues=list(tongues_here),
                            positions=[(float(p[0]), float(p[1]), float(p[2])) for p in pos_here],
                            survival_score=score,
                        )
                    )

            all_contacts.append(token_contacts)
            contact_counts.append(len(token_contacts))
            enriched[t] = self._contact_attention(token_contacts, positions)

        return ContactLatticeOutput(
            enriched=enriched,
            contacts=all_contacts,
            plane_embeddings=plane_embeddings,
            contact_counts=contact_counts,
        )

    # ------------------------------------------------------------------
    #  Dual lattice
    # ------------------------------------------------------------------

    def dual_lattice_edges(
        self,
        contacts: List[ContactNode],
    ) -> List[Tuple[ContactNode, ContactNode, str]]:
        """
        Build the dual lattice over a token's contact nodes.

        Returns edges (a, b, face_plane) for every pair of contact nodes whose
        cells are face-adjacent (differ by 1 in exactly one Morton axis).
        Face plane labels: "xy", "xz", "yz" — matching SignedOctree.FACE_PLANES geometry.

        With N contact nodes this is O(N²); N ≤ 6 in practice (at most 6 tongue planes).
        """
        edges: List[Tuple[ContactNode, ContactNode, str]] = []
        for i, a in enumerate(contacts):
            for b in contacts[i + 1 :]:
                plane = self._shared_face_plane(a.cell_code, b.cell_code)
                if plane is not None:
                    edges.append((a, b, plane))
        return edges

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _cell_code(self, pos: np.ndarray) -> int:
        """Map a Poincaré ball position to a depth-contact_depth octree cell code."""
        res = 1024
        mx = int(np.clip((float(pos[0]) + 1.0) / 2.0 * (res - 1), 0, res - 1))
        my = int(np.clip((float(pos[1]) + 1.0) / 2.0 * (res - 1), 0, res - 1))
        mz = int(np.clip((float(pos[2]) + 1.0) / 2.0 * (res - 1), 0, res - 1))
        return morton_encode_3d(mx, my, mz) >> self._contact_shift

    def _hyperbolic_dist(self, a: np.ndarray, b: np.ndarray) -> float:
        """Poincaré ball distance: arcosh(1 + 2||u-v||²/((1-||u||²)(1-||v||²)))."""
        na2 = float(np.dot(a, a))
        nb2 = float(np.dot(b, b))
        if na2 >= 1.0 or nb2 >= 1.0:
            return 10.0  # clamp at boundary (should not occur after tanh compression)
        diff = a - b
        num = float(np.dot(diff, diff))
        denom = (1.0 - na2) * (1.0 - nb2)
        if denom < 1e-10:
            return 10.0
        return math.acosh(max(1.0, 1.0 + 2.0 * num / denom))

    def _harmonic_score(self, positions: List[np.ndarray]) -> float:
        """
        L12 harmonic wall applied to a contact node.

        H(d_H, pd) = 1 / (1 + φ·d_H + 2·pd)

        d_H = average pairwise hyperbolic distance between co-located planes.
        pd  = plane coverage deficiency: 0 when all 6 planes present, 5/6 when only 2.
              Lower pd rewards broad multi-plane agreement; higher d_H penalizes spread.
        """
        if len(positions) < 2:
            return 0.0
        total_d = 0.0
        pairs = 0
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                total_d += self._hyperbolic_dist(positions[i], positions[j])
                pairs += 1
        d_H = total_d / pairs
        pd = max(0.0, 1.0 - len(positions) / 6.0)
        return 1.0 / (1.0 + PHI * d_H + 2.0 * pd)

    def _contact_attention(
        self,
        contacts: List[ContactNode],
        positions: Dict[str, np.ndarray],
    ) -> np.ndarray:
        """Softmax over survival scores, weighted sum of contact centroids."""
        if not contacts:
            return np.mean([positions[tongue] for tongue in TONGUES], axis=0)
        scores = np.array([c.survival_score for c in contacts])
        scores = scores / (scores.sum() + 1e-8)
        values = np.array([np.mean(c.positions, axis=0) for c in contacts])
        return scores @ values

    def _shared_face_plane(self, code_a: int, code_b: int) -> Optional[str]:
        """Return face-plane name if two contact cells are adjacent; None otherwise."""
        ax, ay, az = morton_decode_3d(code_a)
        bx, by, bz = morton_decode_3d(code_b)
        dx, dy, dz = abs(ax - bx), abs(ay - by), abs(az - bz)
        if dx == 1 and dy == 0 and dz == 0:
            return "yz"
        if dx == 0 and dy == 1 and dz == 0:
            return "xz"
        if dx == 0 and dy == 0 and dz == 1:
            return "xy"
        return None


# ---------------------------------------------------------------------------
#  Standalone demo (PYTHONPATH=. python src/harmonic/contact_lattice.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    np.random.seed(42)

    d_model = 128
    seq_len = 8

    layer = ContactLatticeLayer(d_model=d_model, contact_threshold=0.25, contact_depth=3)

    # Simulate normalized token embeddings
    embeddings = np.random.randn(seq_len, d_model).astype(np.float64)
    embeddings /= np.linalg.norm(embeddings, axis=-1, keepdims=True)

    output = layer.forward(embeddings)

    print("Contact Lattice Layer — demo")
    print(f"seq_len={seq_len}  d_model={d_model}  threshold={layer.contact_threshold}")
    print(f"Total contacts: {sum(output.contact_counts)}\n")

    for t in range(seq_len):
        contacts = output.contacts[t]
        print(f"token {t}: {len(contacts)} contact(s)")
        for c in contacts:
            print(f"  [{'+'.join(c.tongues)}]  score={c.survival_score:.4f}  cell={c.cell_code}")
        if contacts:
            edges = layer.dual_lattice_edges(contacts)
            if edges:
                for a, b, plane in edges:
                    tag_a = "+".join(a.tongues)
                    tag_b = "+".join(b.tongues)
                    print(f"  dual edge: {tag_a} <-{plane}-> {tag_b}")

    print(f"\nenriched shape: {output.enriched.shape}")
    print(f"sample output[0]: {output.enriched[0].round(5)}")
