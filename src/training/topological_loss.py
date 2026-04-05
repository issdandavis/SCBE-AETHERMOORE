"""
Topological Loss Function — Algebraic Confinement Training
===========================================================

"Friction writes the training script itself." — Glint

The AI doesn't just navigate the polyhedral geometry — it becomes it.
This module implements the three-term topological loss that forces
neural weights to algebraically internalize the composite harmonic wall.

Loss function:
    L_total = L_task + γ·||Ĥ_composite - H_true||² + λ·Tr(W^T · L_friction · W)

Where:
    L_task          = Standard task loss (CE, MSE, etc.)
    γ·||Ĥ - H||²   = Internalization penalty: can the model predict its own
                      composite trust score BEFORE it takes a step?
    λ·Tr(W^T·L·W)  = Torsional penalty: the friction Laplacian punishes weights
                      that form pathways crossing high-distortion boundaries

The result: the model's cheapest path to minimizing loss is to align its
weights with the φ-winding. It stops fighting the tornado. It becomes
a native predator of the hyperbolic environment.

Patent: USPTO #63/961,403
Author: Issac Davis
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Golden ratio — the irrational constant that couples everything
PHI = (1 + math.sqrt(5)) / 2
PHI_INV = 1.0 / PHI


# =============================================================================
# 1. SYMMETRY GROUP GENERATORS — THE ALGEBRAIC TARGETS
# =============================================================================
#
# Standard ML learns a generic weight matrix W. In this system, the AI must
# learn the generator matrices of A₄, S₄, A₅. We embed the Lie algebra of
# the polyhedra directly into the network's internal representations.
#

def tetrahedral_generators_A4() -> List[np.ndarray]:
    """
    Generator matrices for A₄ (alternating group on 4 elements).
    Order 12. Rotation symmetries of the tetrahedron.

    Two generators suffice:
      s = (1 2 3) — 3-cycle, order 3
      t = (1 2)(3 4) — double transposition, order 2

    Represented as 4×4 permutation matrices acting on vertex coordinates.
    """
    # s: cyclic permutation of first 3 vertices
    s = np.array([
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [1, 0, 0, 0],
        [0, 0, 0, 1],
    ], dtype=np.float64)

    # t: swap (1,2) and (3,4)
    t = np.array([
        [0, 1, 0, 0],
        [1, 0, 0, 0],
        [0, 0, 0, 1],
        [0, 0, 1, 0],
    ], dtype=np.float64)

    return [s, t]


def octahedral_generators_S4() -> List[np.ndarray]:
    """
    Generator matrices for S₄ (symmetric group on 4 elements).
    Order 24. Rotation symmetries of the cube/octahedron.

    Three generators:
      r = 90° rotation about z-axis
      s = 90° rotation about x-axis
      (Together they generate all 24 rotations)
    """
    # r: 90° about z — (x,y,z) → (-y,x,z)
    r = np.array([
        [0, -1, 0],
        [1,  0, 0],
        [0,  0, 1],
    ], dtype=np.float64)

    # s: 90° about x — (x,y,z) → (x,-z,y)
    s = np.array([
        [1,  0, 0],
        [0,  0, -1],
        [0,  1,  0],
    ], dtype=np.float64)

    return [r, s]


def icosahedral_generators_A5() -> List[np.ndarray]:
    """
    Generator matrices for A₅ (alternating group on 5 elements).
    Order 60. Rotation symmetries of the dodecahedron/icosahedron.

    A₅ is SIMPLE (Galois, 1832) — no non-trivial normal subgroups.
    This is the key property: it shares no common structure with A₄ or S₄,
    making the polyhedral constraints algebraically independent.

    Two generators using golden ratio coordinates:
      r = 72° rotation about a 5-fold axis (order 5)
      s = 120° rotation about a 3-fold axis (order 3)
    """
    # 72° rotation about z (pentagonal symmetry)
    theta = 2 * math.pi / 5
    c, s_val = math.cos(theta), math.sin(theta)
    r = np.array([
        [c, -s_val, 0],
        [s_val,  c, 0],
        [0,      0, 1],
    ], dtype=np.float64)

    # 120° rotation about the (1, φ, 0) axis (icosahedral 3-fold)
    # Using Rodrigues' rotation formula
    angle = 2 * math.pi / 3
    axis = np.array([1.0, PHI, 0.0])
    axis = axis / np.linalg.norm(axis)
    K = np.array([
        [0,       -axis[2], axis[1]],
        [axis[2],  0,      -axis[0]],
        [-axis[1], axis[0], 0],
    ])
    s = (np.eye(3) + math.sin(angle) * K
         + (1 - math.cos(angle)) * (K @ K))

    return [r, s]


# All symmetry group generators
SYMMETRY_GENERATORS = {
    "A4": tetrahedral_generators_A4,     # Order 12 — tetrahedron
    "S4": octahedral_generators_S4,      # Order 24 — cube/octahedron
    "A5": icosahedral_generators_A5,     # Order 60 — dodecahedron/icosahedron (SIMPLE)
}


# =============================================================================
# 2. FRICTION LAPLACIAN — THE TORSIONAL PENALTY MATRIX
# =============================================================================

@dataclass
class FrictionLaplacian:
    """
    Graph Laplacian of the polyhedral friction-weighted contact graph.

    L = D - W, where:
      D = diagonal degree matrix (sum of friction weights per node)
      W = friction-weighted adjacency matrix

    The eigenvectors of L form the spectral basis for geometric learning.
    Tr(W^T · L · W) penalizes weight matrices that form pathways crossing
    high-friction boundaries.
    """

    matrix: np.ndarray          # The n×n Laplacian matrix
    total_friction: float       # Trace = sum of all friction energy
    n_nodes: int
    n_edges: int
    fiedler_value: float = 0.0  # 2nd smallest eigenvalue (algebraic connectivity)

    @classmethod
    def from_flow_adjacency(cls, polyhedra: list, adjacency: dict) -> "FrictionLaplacian":
        """
        Build the friction Laplacian from the polyhedral flow graph.

        Imports the friction computation from polyhedral_flow to avoid
        circular dependencies.
        """
        n = len(polyhedra)
        W = np.zeros((n, n), dtype=np.float64)

        for i, neighbors in adjacency.items():
            for j in neighbors:
                if W[i][j] == 0.0:
                    # Compute friction at contact surface
                    f_i = _natural_frequency(polyhedra[i])
                    f_j = _natural_frequency(polyhedra[j])
                    beat = abs(f_i - f_j)
                    torsion = (f_i * f_j) / max(f_i + f_j, 1e-10)
                    euler_mm = abs(polyhedra[i]["euler_chi"] - polyhedra[j]["euler_chi"])
                    edge_sum = polyhedra[i]["edges"] + polyhedra[j]["edges"]
                    friction = PHI * beat + torsion + euler_mm / max(edge_sum, 1)

                    W[i][j] = friction
                    W[j][i] = friction

        # Degree matrix
        D = np.diag(W.sum(axis=1))

        # Laplacian
        L = D - W
        trace = np.trace(L)
        n_edges = sum(len(v) for v in adjacency.values()) // 2

        # Fiedler value (2nd smallest eigenvalue) via numpy
        eigenvalues = np.sort(np.linalg.eigvalsh(L))
        fiedler = eigenvalues[1] if len(eigenvalues) > 1 else 0.0

        return cls(
            matrix=L,
            total_friction=float(trace),
            n_nodes=n,
            n_edges=n_edges,
            fiedler_value=float(fiedler),
        )


def _natural_frequency(poly_dict: dict) -> float:
    """Compute natural vibrational frequency from polyhedron dict."""
    chi = poly_dict["euler_chi"] if poly_dict["euler_chi"] != 0 else 0.1
    depth_scale = PHI ** (poly_dict["depth"] * 5)
    topology_ratio = abs(poly_dict["faces"] / chi)
    edge_damping = 1.0 / max(poly_dict["edges"], 1)
    return depth_scale * topology_ratio * edge_damping


# Pre-built 16-polyhedra data for standalone use
# (matches POLYHEDRA in polyhedral_flow.py without importing it)
_PHDM_POLYHEDRA = [
    {"name": "Tetrahedron", "faces": 4, "edges": 6, "vertices": 4, "euler_chi": 2, "depth": 0.1},
    {"name": "Cube", "faces": 6, "edges": 12, "vertices": 8, "euler_chi": 2, "depth": 0.2},
    {"name": "Octahedron", "faces": 8, "edges": 12, "vertices": 6, "euler_chi": 2, "depth": 0.2},
    {"name": "Dodecahedron", "faces": 12, "edges": 30, "vertices": 20, "euler_chi": 2, "depth": 0.3},
    {"name": "Icosahedron", "faces": 20, "edges": 30, "vertices": 12, "euler_chi": 2, "depth": 0.3},
    {"name": "Truncated Tetrahedron", "faces": 8, "edges": 18, "vertices": 12, "euler_chi": 2, "depth": 0.4},
    {"name": "Cuboctahedron", "faces": 14, "edges": 24, "vertices": 12, "euler_chi": 2, "depth": 0.5},
    {"name": "Icosidodecahedron", "faces": 32, "edges": 60, "vertices": 30, "euler_chi": 2, "depth": 0.6},
    {"name": "Small Stellated Dodecahedron", "faces": 12, "edges": 30, "vertices": 12, "euler_chi": -6, "depth": 0.7},
    {"name": "Great Dodecahedron", "faces": 12, "edges": 30, "vertices": 12, "euler_chi": -6, "depth": 0.7},
    {"name": "Szilassi", "faces": 14, "edges": 21, "vertices": 7, "euler_chi": 0, "depth": 0.8},
    {"name": "Csaszar", "faces": 14, "edges": 21, "vertices": 7, "euler_chi": 0, "depth": 0.8},
    {"name": "Pentagonal Bipyramid", "faces": 10, "edges": 15, "vertices": 7, "euler_chi": 2, "depth": 0.5},
    {"name": "Triangular Cupola", "faces": 8, "edges": 15, "vertices": 9, "euler_chi": 2, "depth": 0.5},
    {"name": "Rhombic Dodecahedron", "faces": 12, "edges": 24, "vertices": 14, "euler_chi": 2, "depth": 0.6},
    {"name": "Bilinski Dodecahedron", "faces": 12, "edges": 24, "vertices": 14, "euler_chi": 2, "depth": 0.6},
]

_FLOW_ADJACENCY = {
    0: [1, 2, 5, 12], 1: [0, 2, 6, 14], 2: [0, 1, 6, 13],
    3: [4, 7, 8, 14], 4: [3, 7, 9, 15], 5: [0, 6, 12, 13],
    6: [1, 2, 5, 7, 14], 7: [3, 4, 6, 8, 9], 8: [3, 7, 9, 10],
    9: [4, 7, 8, 11], 10: [8, 11, 12, 13], 11: [9, 10, 14, 15],
    12: [0, 5, 10, 13], 13: [2, 5, 10, 12], 14: [1, 3, 6, 11, 15],
    15: [4, 11, 14],
}


def build_default_friction_laplacian() -> FrictionLaplacian:
    """Build the friction Laplacian for the standard 16-polyhedra PHDM ball."""
    return FrictionLaplacian.from_flow_adjacency(_PHDM_POLYHEDRA, _FLOW_ADJACENCY)


# =============================================================================
# 3. TOPOLOGICAL LOSS FUNCTION — THREE TERMS, ONE GEOMETRY
# =============================================================================


@dataclass
class TopologicalLossConfig:
    """
    Configuration for the three-term topological loss.

    L_total = L_task + gamma * L_internalization + lambda_torsion * L_torsion
    """
    gamma: float = 1.0           # Weight for internalization penalty
    lambda_torsion: float = 0.1  # Weight for torsional (Laplacian) penalty
    phi: float = PHI             # Winding constant
    normalize_laplacian: bool = True  # Row-normalize L for stability


class TopologicalLoss:
    """
    Three-term topological loss for algebraic confinement training.

    Term 1: L_task (passed through — any standard loss)
    Term 2: L_internalization = γ · ||Ĥ_composite - H_true||²
        Can the model predict its own composite trust score?
    Term 3: L_torsion = λ · Tr(W^T · L_friction · W)
        Penalizes weights that form pathways across high-friction boundaries.

    The model's cheapest path to minimizing loss is to align its weights
    with the φ-winding of the polyhedral geometry.
    """

    def __init__(
        self,
        config: Optional[TopologicalLossConfig] = None,
        friction_laplacian: Optional[FrictionLaplacian] = None,
    ):
        self.config = config or TopologicalLossConfig()

        if friction_laplacian is None:
            self.friction_lap = build_default_friction_laplacian()
        else:
            self.friction_lap = friction_laplacian

        # Optionally normalize the Laplacian for numerical stability
        self.L = self.friction_lap.matrix.copy()
        if self.config.normalize_laplacian:
            row_sums = np.abs(self.L).sum(axis=1)
            row_sums[row_sums == 0] = 1.0
            self.L = self.L / row_sums[:, np.newaxis]

    def internalization_penalty(
        self,
        h_predicted: float,
        h_true: float,
    ) -> float:
        """
        Term 2: Can the model predict its own composite trust score?

        L_internalization = γ · (Ĥ_composite - H_true)²

        If the model can't predict the hash, it hasn't internalized
        the geometry. This forces algebraic understanding, not memorization.
        """
        return self.config.gamma * (h_predicted - h_true) ** 2

    def torsional_penalty(self, W: np.ndarray) -> float:
        """
        Term 3: The friction Laplacian punishes bad pathways.

        L_torsion = λ · Tr(W^T · L_friction · W)

        This is a spectral regularizer. The Laplacian's eigenvectors
        define the natural modes of the polyhedral contact graph.
        High-frequency modes (sharp friction boundaries) get penalized
        more heavily than low-frequency modes (smooth transitions).

        The effect: weights that try to form pathways crossing
        high-distortion boundaries pay a steep price. The cheapest
        weight configuration is one that aligns with φ-winding.

        Args:
            W: Weight matrix (or projection thereof) to penalize.
               Shape must be compatible with the Laplacian (n_nodes × k).
        """
        # Project W to Laplacian dimensions if needed
        n = self.L.shape[0]
        if W.shape[0] != n:
            # Reshape or pad W to match Laplacian size
            # In practice: use the first n rows, or project
            W_proj = np.zeros((n, W.shape[1] if W.ndim > 1 else 1))
            rows = min(n, W.shape[0])
            if W.ndim == 1:
                W_proj[:rows, 0] = W[:rows]
            else:
                cols = min(W_proj.shape[1], W.shape[1])
                W_proj[:rows, :cols] = W[:rows, :cols]
            W = W_proj

        if W.ndim == 1:
            W = W.reshape(-1, 1)

        # Tr(W^T · L · W) = sum of eigenvalue-weighted squared projections
        return self.config.lambda_torsion * float(np.trace(W.T @ self.L @ W))

    def compute(
        self,
        l_task: float,
        h_predicted: float,
        h_true: float,
        W: Optional[np.ndarray] = None,
    ) -> dict:
        """
        Compute the full three-term topological loss.

        L_total = L_task + γ·||Ĥ - H||² + λ·Tr(W^T · L · W)

        Args:
            l_task: Standard task loss (CE, MSE, etc.)
            h_predicted: Model's predicted composite trust score
            h_true: Actual composite trust score from harmonic wall
            W: Weight matrix for torsional penalty (optional)

        Returns:
            dict with l_total, l_task, l_internalization, l_torsion,
            and diagnostic info
        """
        l_intern = self.internalization_penalty(h_predicted, h_true)

        l_torsion = 0.0
        if W is not None:
            l_torsion = self.torsional_penalty(W)

        l_total = l_task + l_intern + l_torsion

        return {
            "l_total": l_total,
            "l_task": l_task,
            "l_internalization": l_intern,
            "l_torsion": l_torsion,
            "h_predicted": h_predicted,
            "h_true": h_true,
            "h_error": abs(h_predicted - h_true),
            "gamma": self.config.gamma,
            "lambda_torsion": self.config.lambda_torsion,
            "fiedler_value": self.friction_lap.fiedler_value,
            "total_friction_energy": self.friction_lap.total_friction,
        }

    def generator_alignment_loss(
        self,
        W: np.ndarray,
        group: str = "A5",
    ) -> float:
        """
        Bonus term: Penalize weights that don't align with symmetry generators.

        For the AI to truly internalize the geometry, its weight matrices
        should approximate the action of the polyhedral symmetry groups.

        This computes the Frobenius distance between W and the nearest
        group generator, encouraging the network to learn the algebra.

        Args:
            W: Weight matrix (must be square, matching generator dim)
            group: Which symmetry group ("A4", "S4", "A5")

        Returns:
            Minimum Frobenius distance to any generator of the group
        """
        gen_fn = SYMMETRY_GENERATORS.get(group)
        if gen_fn is None:
            return 0.0

        generators = gen_fn()
        min_dist = float("inf")

        for G in generators:
            # Match dimensions
            n = min(W.shape[0], G.shape[0])
            m = min(W.shape[1] if W.ndim > 1 else 1, G.shape[1])
            W_sub = W[:n, :m] if W.ndim > 1 else W[:n].reshape(-1, 1)
            G_sub = G[:n, :m]
            dist = np.linalg.norm(W_sub - G_sub, 'fro')
            min_dist = min(min_dist, dist)

        return float(min_dist)


# =============================================================================
# 4. TRAINING STEP — PUTTING IT ALL TOGETHER
# =============================================================================


def topological_training_step(
    task_loss: float,
    h_predicted: float,
    polyhedral_distances: dict,
    phase_deviation: float,
    weight_matrix: Optional[np.ndarray] = None,
    config: Optional[TopologicalLossConfig] = None,
) -> dict:
    """
    Execute one topological training step.

    This is the bridge between the geometry engine and the training engine.
    Call this after computing your standard task loss to add the geometric
    penalty terms.

    Args:
        task_loss: Standard loss from whatever the model's main job is
        h_predicted: Model's predicted composite trust score
        polyhedral_distances: {polyhedron: d_H} from composite wall evaluation
        phase_deviation: Current phase deviation from correct winding
        weight_matrix: Model weights to apply torsional penalty to
        config: Loss configuration

    Returns:
        Full loss breakdown with all three terms
    """
    # Compute true composite harmonic wall score
    phi = config.phi if config else PHI
    constraint_orders = {
        "tetrahedron": 12, "cube": 24, "octahedron": 24,
        "dodecahedron": 60, "icosahedron": 60,
    }

    weighted_sum = 0.0
    for name, d_h in polyhedral_distances.items():
        order = constraint_orders.get(name.lower(), 1)
        weighted_sum += (1.0 / order) * d_h

    denominator = 1.0 + phi * weighted_sum + 2.0 * phase_deviation
    h_true = 1.0 / denominator

    # Compute topological loss
    loss_fn = TopologicalLoss(config=config)
    result = loss_fn.compute(task_loss, h_predicted, h_true, weight_matrix)

    # Add tier info
    h = h_true
    if h >= 0.75:
        result["tier"] = "ALLOW"
    elif h >= 0.40:
        result["tier"] = "QUARANTINE"
    elif h >= 0.15:
        result["tier"] = "ESCALATE"
    else:
        result["tier"] = "DENY"

    return result


# =============================================================================
# 5. PyTorch MODULE — BACKPROPAGABLE TOPOLOGICAL LOSS
# =============================================================================
#
# The numpy version above proves the math. This section makes it
# differentiable. Gradients flow through all three terms, and the
# Laplacian shapes the loss landscape into the φ-winding manifold.
#
# Weight initialization: standard Xavier/Kaiming assumes flat Euclidean space.
# Our loss surface is hyperbolic with φ-coupled curvature. Naively initialized
# weights slam into high-friction ridges on epoch 1 (gradient explosion or
# collapse). Solution: Poincaré-aware initialization — place weights inside
# the ball at radius ≈ φ⁻¹, oriented along low-frequency Laplacian eigenvectors.
#

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


if HAS_TORCH:

    class PoincareInitializer:
        """
        Hyperbolic-aware weight initialization for the φ-winding manifold.

        Standard Xavier/Kaiming distributes weights uniformly assuming flat
        Euclidean gradients. In our hyperbolic loss landscape, this puts
        initial weights at random positions on the Poincaré ball — many of
        which are high-friction ridges where torsional penalty explodes.

        This initializer:
        1. Computes the spectral basis of the friction Laplacian
        2. Projects initial weights onto the k lowest-frequency eigenvectors
           (the smooth modes — valleys of the manifold)
        3. Scales to radius φ⁻¹ ≈ 0.618 inside the Poincaré ball
           (the "sweet spot" where curvature is moderate)

        The result: the model starts in a low-friction valley. Gradient
        descent can refine position without first having to escape a ridge.
        """

        def __init__(self, friction_laplacian: FrictionLaplacian, n_modes: int = 4):
            """
            Args:
                friction_laplacian: The PHDM friction Laplacian
                n_modes: Number of low-frequency eigenvectors to use as basis
            """
            self.n_modes = n_modes
            self.target_radius = PHI_INV  # ≈ 0.618

            # Compute spectral basis from Laplacian
            L = friction_laplacian.matrix
            eigenvalues, eigenvectors = np.linalg.eigh(L)

            # Keep the k lowest-frequency modes (skip the constant mode at λ=0)
            start = 1 if eigenvalues[0] < 1e-10 else 0
            end = start + n_modes
            self.spectral_basis = torch.tensor(
                eigenvectors[:, start:end], dtype=torch.float32
            )
            self.eigenvalues = torch.tensor(
                eigenvalues[start:end], dtype=torch.float32
            )

        def initialize(self, weight: torch.Tensor) -> torch.Tensor:
            """
            Initialize a weight tensor on the smooth manifold.

            Args:
                weight: Tensor to initialize (modified in-place and returned)
            """
            with torch.no_grad():
                n = self.spectral_basis.shape[0]  # Laplacian dimension
                k = self.spectral_basis.shape[1]  # Number of modes

                if weight.dim() == 1:
                    # 1D: project onto first eigenvector, scale to φ⁻¹
                    coeffs = torch.randn(k) * 0.1
                    vec = self.spectral_basis @ coeffs
                    # Pad or truncate to match weight size
                    if weight.shape[0] <= n:
                        weight.copy_(vec[:weight.shape[0]])
                    else:
                        weight[:n] = vec
                        weight[n:] = torch.randn(weight.shape[0] - n) * 0.01
                    # Scale to Poincaré ball radius
                    norm = weight.norm()
                    if norm > 0:
                        weight.mul_(self.target_radius / norm)

                elif weight.dim() == 2:
                    rows, cols = weight.shape
                    # Each column is a point in the spectral basis
                    for j in range(cols):
                        coeffs = torch.randn(k) * 0.1
                        vec = self.spectral_basis @ coeffs
                        if rows <= n:
                            weight[:, j] = vec[:rows]
                        else:
                            weight[:n, j] = vec
                            weight[n:, j] = torch.randn(rows - n) * 0.01
                    # Scale each column to φ⁻¹ ball
                    col_norms = weight.norm(dim=0, keepdim=True).clamp(min=1e-10)
                    weight.mul_(self.target_radius / col_norms)

                else:
                    # Higher-dim: flatten, init, reshape
                    flat = weight.view(-1)
                    dummy = torch.zeros(flat.shape[0])
                    self.initialize(dummy)
                    flat.copy_(dummy)

            return weight

        def initialize_module(self, module: "nn.Module") -> None:
            """
            Walk a module tree and initialize all weight tensors.

            Replaces Xavier/Kaiming for any module that will train under
            the topological loss. Biases are zeroed (standard practice).
            """
            for name, param in module.named_parameters():
                if "weight" in name and param.dim() >= 2:
                    self.initialize(param.data)
                elif "bias" in name:
                    nn.init.zeros_(param)


    class TopologicalLossModule(nn.Module):
        """
        PyTorch-differentiable three-term topological loss.

        L_total = L_task + γ·||Ĥ - H_true||² + λ·Tr(W^T · L_friction · W)

        All three terms produce gradients. The Laplacian matrix is registered
        as a buffer (not a parameter) — it shapes the landscape but is not
        itself learned.

        Usage:
            lap = build_default_friction_laplacian()
            loss_fn = TopologicalLossModule(lap)

            # Initialize model weights on the smooth manifold
            initializer = PoincareInitializer(lap)
            initializer.initialize_module(model)

            # In training loop:
            total, breakdown = loss_fn(task_preds, task_targets,
                                       h_pred, h_true, model_weights)
            total.backward()
        """

        def __init__(
            self,
            friction_laplacian: FrictionLaplacian,
            gamma: float = 1.0,
            lambda_torsion: float = 0.5,
            task_criterion: "nn.Module" = None,
        ):
            super().__init__()
            self.gamma = gamma
            self.lambda_torsion = lambda_torsion
            self.task_criterion = task_criterion or nn.CrossEntropyLoss()

            # Register Laplacian as buffer — moves with .to(device) but not optimized
            L = friction_laplacian.matrix.copy()
            # Row-normalize for numerical stability
            row_sums = np.abs(L).sum(axis=1)
            row_sums[row_sums == 0] = 1.0
            L = L / row_sums[:, np.newaxis]
            self.register_buffer(
                "laplacian",
                torch.tensor(L, dtype=torch.float32),
            )

            # Store spectral info for diagnostics
            self.fiedler_value = friction_laplacian.fiedler_value
            self.total_friction = friction_laplacian.total_friction
            self.n_nodes = friction_laplacian.n_nodes

        def forward(
            self,
            task_preds: torch.Tensor,
            task_targets: torch.Tensor,
            h_pred: torch.Tensor,
            h_true: torch.Tensor,
            weight_matrix: torch.Tensor,
        ) -> tuple:
            """
            Compute composite topological loss with full gradient flow.

            Args:
                task_preds: Model predictions for task loss (logits)
                task_targets: Ground truth for task loss
                h_pred: Model's predicted composite trust score (scalar tensor)
                h_true: Actual trust score from harmonic wall (scalar tensor)
                weight_matrix: Weight tensor to penalize via Laplacian.
                    Shape: (n_nodes, k) or projectable to Laplacian dims.

            Returns:
                (total_loss, breakdown_dict)
            """
            # Term 1: Task loss — standard CE/MSE/whatever
            L_task = self.task_criterion(task_preds, task_targets)

            # Term 2: Internalization — can the model predict its own trust?
            L_internal = self.gamma * torch.mean((h_pred - h_true) ** 2)

            # Term 3: Torsional — Laplacian friction penalty on weights
            L_torsion = self._torsional_penalty(weight_matrix)

            total = L_task + L_internal + L_torsion

            breakdown = {
                "task_loss": L_task.detach().item(),
                "internalization_loss": L_internal.detach().item(),
                "torsional_loss": L_torsion.detach().item(),
                "total_loss": total.detach().item(),
                "h_error": (h_pred - h_true).abs().detach().mean().item(),
            }

            return total, breakdown

        def _torsional_penalty(self, W: torch.Tensor) -> torch.Tensor:
            """
            Tr(W^T · L_friction · W) with dimension projection.

            The Laplacian is n_nodes × n_nodes. The weight matrix may be
            any shape — we project its leading dimensions to match.
            """
            n = self.laplacian.shape[0]
            L = self.laplacian

            # Reshape W to 2D: (rows, cols)
            if W.dim() == 1:
                W = W.unsqueeze(1)
            elif W.dim() > 2:
                W = W.reshape(W.shape[0], -1)

            # Project to Laplacian dimensions
            if W.shape[0] != n:
                if W.shape[0] > n:
                    W_proj = W[:n, :]
                else:
                    W_proj = torch.zeros(
                        n, W.shape[1], device=W.device, dtype=W.dtype
                    )
                    W_proj[:W.shape[0], :] = W
            else:
                W_proj = W

            # Tr(W^T · L · W) — the core spectral regularizer
            # Gradients flow through W_proj back to original W
            W_T_L = torch.matmul(W_proj.t(), L)
            W_T_L_W = torch.matmul(W_T_L, W_proj)
            return self.lambda_torsion * torch.trace(W_T_L_W)

        def trust_tier(self, h: float) -> str:
            """Map trust score to governance tier."""
            if h >= 0.75:
                return "ALLOW"
            elif h >= 0.40:
                return "QUARANTINE"
            elif h >= 0.15:
                return "ESCALATE"
            return "DENY"


    def poincare_aware_training_step(
        model: "nn.Module",
        loss_fn: TopologicalLossModule,
        optimizer: "torch.optim.Optimizer",
        task_preds: torch.Tensor,
        task_targets: torch.Tensor,
        h_pred: torch.Tensor,
        h_true: torch.Tensor,
        weight_key: str = None,
    ) -> dict:
        """
        One training step with topological loss and Poincaré clamping.

        After the optimizer step, clamps all weight norms to stay inside
        the Poincaré ball (radius < 1.0). This prevents the optimizer
        from pushing weights to the boundary where hyperbolic curvature
        diverges and gradients explode.

        Args:
            model: The neural network
            loss_fn: TopologicalLossModule instance
            optimizer: Any torch optimizer (Adam recommended — its
                       per-parameter learning rates adapt to curvature)
            task_preds, task_targets: Standard task data
            h_pred, h_true: Trust score prediction and ground truth
            weight_key: Named parameter to use for torsional penalty.
                        If None, uses the first weight matrix found.
        """
        optimizer.zero_grad()

        # Find weight matrix for torsional penalty
        W = None
        for name, param in model.named_parameters():
            if weight_key and name == weight_key:
                W = param
                break
            elif weight_key is None and "weight" in name and param.dim() >= 2:
                W = param
                break

        if W is None:
            W = torch.zeros(loss_fn.n_nodes, 1, requires_grad=True)

        total, breakdown = loss_fn(task_preds, task_targets, h_pred, h_true, W)
        total.backward()
        optimizer.step()

        # Poincaré ball clamping — keep weights inside the ball
        # This is the key safety mechanism: at the boundary (||w|| → 1),
        # hyperbolic distance → ∞ and gradients explode.
        # Clamping to 1 - ε keeps the model in the safe interior.
        BALL_RADIUS = 1.0 - 1e-5
        with torch.no_grad():
            for param in model.parameters():
                if param.dim() >= 2:
                    norms = param.norm(dim=-1, keepdim=True).clamp(min=1e-10)
                    mask = norms > BALL_RADIUS
                    if mask.any():
                        param.data = torch.where(
                            mask,
                            param.data * (BALL_RADIUS / norms),
                            param.data,
                        )

        breakdown["ball_clamped"] = True
        return breakdown


# =============================================================================
# DEMO / VERIFICATION
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("TOPOLOGICAL LOSS FUNCTION — ALGEBRAIC CONFINEMENT TRAINING")
    print("=" * 70)
    print()

    # Build friction Laplacian
    lap = build_default_friction_laplacian()
    print(f"Friction Laplacian:")
    print(f"  Nodes: {lap.n_nodes}, Edges: {lap.n_edges}")
    print(f"  Total friction energy: {lap.total_friction:.4f}")
    print(f"  Fiedler value (algebraic connectivity): {lap.fiedler_value:.4f}")
    print()

    # Show symmetry generators
    print("Symmetry Group Generators:")
    for name, gen_fn in SYMMETRY_GENERATORS.items():
        gens = gen_fn()
        print(f"  {name}: {len(gens)} generators, dim={gens[0].shape}")
    print()

    # ── Numpy proof-of-concept ──
    print("─" * 40)
    print("SECTION A: Numpy Proof-of-Concept")
    print("─" * 40)

    loss_fn = TopologicalLoss()
    legit = loss_fn.compute(
        l_task=0.5, h_predicted=0.98, h_true=0.995,
        W=np.random.randn(16, 4) * 0.01,
    )
    print(f"Legitimate: L_total={legit['l_total']:.6f}  "
          f"(intern={legit['l_internalization']:.6f}, torsion={legit['l_torsion']:.6f})")

    adv = loss_fn.compute(
        l_task=0.5, h_predicted=0.8, h_true=0.15,
        W=np.random.randn(16, 4) * 1.0,
    )
    print(f"Adversary:  L_total={adv['l_total']:.6f}  "
          f"(intern={adv['l_internalization']:.6f}, torsion={adv['l_torsion']:.6f})")
    print(f"Cost ratio: {adv['l_total'] / max(legit['l_total'], 1e-10):.1f}x")
    print()

    # Generator alignment
    W_random = np.random.randn(3, 3)
    W_aligned = icosahedral_generators_A5()[0]
    print(f"Generator Alignment (A5): random={loss_fn.generator_alignment_loss(W_random, 'A5'):.4f}, "
          f"aligned={loss_fn.generator_alignment_loss(W_aligned, 'A5'):.4f}")
    print()

    # Full training step
    step = topological_training_step(
        task_loss=0.3, h_predicted=0.92,
        polyhedral_distances={
            "tetrahedron": 0.01, "cube": 0.02, "octahedron": 0.01,
            "dodecahedron": 0.03, "icosahedron": 0.02,
        },
        phase_deviation=0.0,
        weight_matrix=np.random.randn(16, 4) * 0.01,
    )
    print(f"Full training step: L_total={step['l_total']:.6f}, "
          f"Tier={step['tier']}, H_true={step['h_true']:.6f}")
    print()

    # ── PyTorch backpropagable module ──
    if HAS_TORCH:
        print("─" * 40)
        print("SECTION B: PyTorch Differentiable Module")
        print("─" * 40)
        print()

        # 1. Poincaré initialization test
        print("1. Poincaré-Aware Initialization:")
        initializer = PoincareInitializer(lap, n_modes=4)

        # Compare Xavier vs Poincaré on a dummy layer
        W_xavier = torch.empty(16, 8)
        nn.init.xavier_uniform_(W_xavier)
        xavier_norms = W_xavier.norm(dim=0)

        W_poincare = torch.empty(16, 8)
        initializer.initialize(W_poincare)
        poincare_norms = W_poincare.norm(dim=0)

        print(f"  Xavier column norms:   mean={xavier_norms.mean():.4f}, "
              f"max={xavier_norms.max():.4f}, min={xavier_norms.min():.4f}")
        print(f"  Poincaré column norms: mean={poincare_norms.mean():.4f}, "
              f"max={poincare_norms.max():.4f}, min={poincare_norms.min():.4f}")
        print(f"  Target radius (φ⁻¹):  {PHI_INV:.4f}")

        # Compute initial torsional cost for each
        L_tensor = torch.tensor(lap.matrix, dtype=torch.float32)
        row_sums = L_tensor.abs().sum(dim=1, keepdim=True).clamp(min=1e-10)
        L_norm = L_tensor / row_sums

        xavier_cost = torch.trace(W_xavier.t() @ L_norm @ W_xavier).item()
        poincare_cost = torch.trace(W_poincare.t() @ L_norm @ W_poincare).item()
        print(f"  Xavier initial torsion:   {xavier_cost:.4f}")
        print(f"  Poincaré initial torsion: {poincare_cost:.4f}")
        print(f"  Torsion reduction:        {xavier_cost / max(poincare_cost, 1e-10):.1f}x")
        print()

        # 2. Differentiable loss with gradient flow
        print("2. Gradient Flow Test:")
        torch_loss = TopologicalLossModule(lap, gamma=1.0, lambda_torsion=0.5)

        # Tiny model: 16-dim input → 4 classes (routing decision)
        model = nn.Sequential(
            nn.Linear(16, 16),
            nn.ReLU(),
            nn.Linear(16, 4),
        )

        # Initialize with Poincaré (not Xavier)
        initializer.initialize_module(model)

        # Dummy forward pass
        x = torch.randn(8, 16)           # batch of 8
        targets = torch.randint(0, 4, (8,))  # 4 routing classes
        preds = model(x)
        h_pred = torch.sigmoid(preds.mean())  # crude trust prediction
        h_true = torch.tensor(0.995)          # legitimate traffic

        # Get weights for torsional penalty
        W_layer = list(model.parameters())[0]  # first weight matrix

        total, breakdown = torch_loss(preds, targets, h_pred, h_true, W_layer)
        total.backward()

        # Check gradients exist and are finite
        grad_norms = []
        for name, p in model.named_parameters():
            if p.grad is not None:
                gn = p.grad.norm().item()
                grad_norms.append((name, gn))

        print(f"  Total loss: {breakdown['total_loss']:.6f}")
        print(f"  Task:       {breakdown['task_loss']:.6f}")
        print(f"  Internal:   {breakdown['internalization_loss']:.6f}")
        print(f"  Torsion:    {breakdown['torsional_loss']:.6f}")
        print(f"  H error:    {breakdown['h_error']:.6f}")
        print(f"  Gradients:")
        for name, gn in grad_norms:
            status = "OK" if 0 < gn < 100 else "WARN"
            print(f"    {name}: ||grad||={gn:.6f} [{status}]")
        print()

        # 3. Mini training loop — 20 steps, watch torsion drop
        print("3. Mini Training Loop (20 steps):")
        model2 = nn.Sequential(
            nn.Linear(16, 16),
            nn.ReLU(),
            nn.Linear(16, 4),
        )
        initializer.initialize_module(model2)
        opt = torch.optim.Adam(model2.parameters(), lr=1e-3)

        for step_i in range(20):
            x = torch.randn(16, 16)
            targets = torch.randint(0, 4, (16,))
            preds = model2(x)
            h_p = torch.sigmoid(preds.mean())
            h_t = torch.tensor(0.99)
            W = list(model2.parameters())[0]

            result = poincare_aware_training_step(
                model2, torch_loss, opt,
                preds, targets, h_p, h_t, weight_key=None,
            )
            if step_i % 5 == 0 or step_i == 19:
                # Check Poincaré ball constraint
                max_norm = max(
                    p.norm(dim=-1).max().item()
                    for p in model2.parameters() if p.dim() >= 2
                )
                print(f"  Step {step_i:2d}: task={result['task_loss']:.4f} "
                      f"intern={result['internalization_loss']:.4f} "
                      f"torsion={result['torsional_loss']:.4f} "
                      f"max_norm={max_norm:.4f}")

        print(f"  All weights inside Poincaré ball: "
              f"{'YES' if max_norm < 1.0 else 'NO'} (max_norm={max_norm:.4f})")
        print()

    else:
        print("PyTorch not available — skipping differentiable module tests")
        print()

    print("=" * 70)
    print("The model's cheapest path: align weights with phi-winding.")
    if HAS_TORCH:
        print(f"Poincaré init reduces epoch-1 torsion by "
              f"{xavier_cost / max(poincare_cost, 1e-10):.0f}x vs Xavier.")
    print("Stop fighting the tornado. Become the geometry.")
    print("=" * 70)
