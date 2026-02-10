"""
HYDRA Spectral Analysis Module
==============================

Graph Fourier Scan Statistics (GFSS) for multi-agent anomaly detection.

Based on:
- He et al. (2025) "SentinelAgent: Graph-based Anomaly Detection in
  Multi-Agent Systems" arXiv:2505.24201
- UniGAD (2024) - Maximum Rayleigh Quotient Subgraph Sampler

Features:
- Graph Fourier Transform for agent interaction analysis
- Spectral right-shift detection (collusion indicator)
- Real-time anomaly scoring
- Byzantine agent identification
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import defaultdict
import json


@dataclass
class SpectralAnomaly:
    """Detected anomaly in the agent interaction graph."""
    key: str
    head_id: str
    anomaly_score: float
    spectral_energy: Dict[str, float]
    reason: str
    timestamp: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "head_id": self.head_id,
            "anomaly_score": self.anomaly_score,
            "spectral_energy": self.spectral_energy,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "severity": self.severity
        }


class GraphFourierAnalyzer:
    """
    Graph Fourier Transform analyzer for HYDRA.

    Uses spectral graph theory to detect:
    1. Multi-agent collusion (coordinated high-frequency patterns)
    2. Gradual logic drift (spectral signature changes over time)
    3. Covert data exfiltration (unusual edge patterns)
    """

    def __init__(self, sensitivity: float = 2.0):
        """
        Args:
            sensitivity: Threshold multiplier for anomaly detection.
                        Higher = fewer false positives but might miss subtle attacks.
        """
        self.sensitivity = sensitivity
        self.baseline_spectrum: Optional[np.ndarray] = None
        self.spectral_history: List[np.ndarray] = []

    def build_adjacency_matrix(
        self,
        knowledge_graph: Dict[str, List[str]],
        node_list: List[str] = None
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Build adjacency matrix from knowledge graph.

        Returns:
            Tuple of (adjacency_matrix, node_list)
        """
        # Get all nodes
        if node_list is None:
            nodes = set(knowledge_graph.keys())
            for targets in knowledge_graph.values():
                nodes.update(targets)
            node_list = sorted(list(nodes))

        n = len(node_list)
        node_to_idx = {node: i for i, node in enumerate(node_list)}

        # Build adjacency matrix
        A = np.zeros((n, n))
        for source, targets in knowledge_graph.items():
            if source in node_to_idx:
                i = node_to_idx[source]
                for target in targets:
                    if target in node_to_idx:
                        j = node_to_idx[target]
                        A[i, j] = 1
                        A[j, i] = 1  # Make symmetric for undirected analysis

        return A, node_list

    def compute_laplacian(self, A: np.ndarray) -> np.ndarray:
        """
        Compute normalized Graph Laplacian.

        L = I - D^(-1/2) * A * D^(-1/2)

        The eigenvalues of L capture the graph's spectral properties.
        """
        n = A.shape[0]

        # Degree matrix
        D = np.diag(np.sum(A, axis=1))

        # Handle isolated nodes
        D_inv_sqrt = np.zeros_like(D)
        for i in range(n):
            if D[i, i] > 0:
                D_inv_sqrt[i, i] = 1.0 / np.sqrt(D[i, i])

        # Normalized Laplacian
        I = np.eye(n)
        L = I - D_inv_sqrt @ A @ D_inv_sqrt

        return L

    def graph_fourier_transform(
        self,
        signal: np.ndarray,
        L: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute Graph Fourier Transform of signal.

        GFT(f) = U^T * f

        Where U contains eigenvectors of the Laplacian.

        Returns:
            Tuple of (spectral_coefficients, eigenvalues, eigenvectors)
        """
        # Eigendecomposition of Laplacian
        eigenvalues, eigenvectors = np.linalg.eigh(L)

        # Sort by eigenvalue (frequency)
        idx = np.argsort(eigenvalues)
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        # Graph Fourier Transform
        spectral_coefficients = eigenvectors.T @ signal

        return spectral_coefficients, eigenvalues, eigenvectors

    def compute_spectral_energy(
        self,
        spectral_coefficients: np.ndarray
    ) -> Dict[str, float]:
        """
        Compute energy distribution across frequency bands.

        Low frequency = smooth signals (normal behavior)
        High frequency = sharp variations (potential anomalies)
        """
        n = len(spectral_coefficients)
        quarter = n // 4

        low_freq = spectral_coefficients[:quarter]
        mid_low = spectral_coefficients[quarter:2*quarter]
        mid_high = spectral_coefficients[2*quarter:3*quarter]
        high_freq = spectral_coefficients[3*quarter:]

        total_energy = np.sum(spectral_coefficients ** 2) + 1e-10

        return {
            "low": float(np.sum(low_freq ** 2) / total_energy),
            "mid_low": float(np.sum(mid_low ** 2) / total_energy),
            "mid_high": float(np.sum(mid_high ** 2) / total_energy),
            "high": float(np.sum(high_freq ** 2) / total_energy),
            "total": float(total_energy)
        }

    def detect_spectral_rightshift(
        self,
        current_energy: Dict[str, float],
        baseline_energy: Dict[str, float] = None
    ) -> Tuple[bool, float]:
        """
        Detect spectral right-shift (anomaly indicator).

        A right-shift means energy is moving from low to high frequencies,
        indicating unusual/adversarial patterns in agent interactions.
        """
        if baseline_energy is None:
            # Use default "healthy" distribution
            baseline_energy = {"low": 0.6, "mid_low": 0.25, "mid_high": 0.1, "high": 0.05}

        # Compute shift score
        low_shift = baseline_energy["low"] - current_energy["low"]
        high_shift = current_energy["high"] - baseline_energy["high"]

        shift_score = (low_shift + high_shift) / 2

        # Detect significant right-shift
        is_anomaly = shift_score > (0.1 / self.sensitivity)

        return is_anomaly, shift_score

    def analyze_knowledge_graph(
        self,
        knowledge_graph: Dict[str, List[str]],
        node_signals: Dict[str, float] = None
    ) -> List[SpectralAnomaly]:
        """
        Full spectral analysis of knowledge graph.

        Args:
            knowledge_graph: Node -> [connected nodes] mapping
            node_signals: Optional signal values per node (e.g., confidence scores)

        Returns:
            List of detected anomalies sorted by severity
        """
        if len(knowledge_graph) < 3:
            return []  # Need minimum graph size

        # Build matrices
        A, node_list = self.build_adjacency_matrix(knowledge_graph)
        L = self.compute_laplacian(A)
        n = len(node_list)

        anomalies = []

        # Analyze each node's spectral signature
        for i, node in enumerate(node_list):
            # Create node signal (unit impulse at this node)
            signal = np.zeros(n)
            signal[i] = node_signals.get(node, 1.0) if node_signals else 1.0

            # GFT
            spectral_coeff, eigenvalues, _ = self.graph_fourier_transform(signal, L)

            # Compute energy distribution
            energy = self.compute_spectral_energy(spectral_coeff)

            # Check for right-shift
            is_anomaly, shift_score = self.detect_spectral_rightshift(energy)

            if is_anomaly:
                # Determine severity
                if shift_score > 0.4:
                    severity = "CRITICAL"
                elif shift_score > 0.25:
                    severity = "HIGH"
                elif shift_score > 0.15:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"

                anomalies.append(SpectralAnomaly(
                    key=node,
                    head_id=self._extract_head_id(node),
                    anomaly_score=float(shift_score),
                    spectral_energy=energy,
                    reason=f"Spectral right-shift detected: {shift_score:.3f}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    severity=severity
                ))

        # Sort by severity and score
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        anomalies.sort(key=lambda x: (severity_order[x.severity], -x.anomaly_score))

        return anomalies

    def _extract_head_id(self, node: str) -> str:
        """Extract head ID from node key if present."""
        if ":" in node:
            parts = node.split(":")
            for part in parts:
                if part.startswith("CT-") or part.startswith("CX-") or part.startswith("GP-"):
                    return part
        return "unknown"

    def update_baseline(
        self,
        knowledge_graph: Dict[str, List[str]],
        node_signals: Dict[str, float] = None
    ) -> None:
        """
        Update baseline spectral signature from current "healthy" state.

        Call this periodically when the system is known to be operating normally.
        """
        if len(knowledge_graph) < 3:
            return

        A, node_list = self.build_adjacency_matrix(knowledge_graph)
        L = self.compute_laplacian(A)
        n = len(node_list)

        # Compute average spectral energy
        total_energy = {"low": 0, "mid_low": 0, "mid_high": 0, "high": 0}
        count = 0

        for i, node in enumerate(node_list):
            signal = np.zeros(n)
            signal[i] = node_signals.get(node, 1.0) if node_signals else 1.0

            spectral_coeff, _, _ = self.graph_fourier_transform(signal, L)
            energy = self.compute_spectral_energy(spectral_coeff)

            for k in total_energy:
                total_energy[k] += energy[k]
            count += 1

        if count > 0:
            self.baseline_spectrum = {k: v / count for k, v in total_energy.items()}


class ByzantineDetector:
    """
    Byzantine agent detection using spectral clustering.

    Identifies agents that exhibit coordinated malicious behavior
    by analyzing their position in the spectral embedding space.
    """

    def __init__(self, tolerance_factor: float = 3.0):
        """
        Args:
            tolerance_factor: How many standard deviations from mean
                            is considered Byzantine.
        """
        self.tolerance = tolerance_factor

    def detect_byzantine_heads(
        self,
        interaction_graph: Dict[str, Dict[str, int]],
        head_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Detect potentially Byzantine heads using spectral embedding.

        Args:
            interaction_graph: head_id -> {target_head: interaction_count}
            head_ids: List of all head IDs to analyze

        Returns:
            List of suspected Byzantine heads with evidence
        """
        if len(head_ids) < 4:
            return []  # Need minimum for statistical analysis

        n = len(head_ids)
        head_to_idx = {h: i for i, h in enumerate(head_ids)}

        # Build weighted adjacency matrix
        A = np.zeros((n, n))
        for source, targets in interaction_graph.items():
            if source in head_to_idx:
                i = head_to_idx[source]
                for target, count in targets.items():
                    if target in head_to_idx:
                        j = head_to_idx[target]
                        A[i, j] = count

        # Symmetrize
        A = (A + A.T) / 2

        # Compute normalized Laplacian
        D = np.diag(np.sum(A, axis=1) + 1e-10)
        D_inv_sqrt = np.diag(1.0 / np.sqrt(np.diag(D)))
        L = np.eye(n) - D_inv_sqrt @ A @ D_inv_sqrt

        # Get spectral embedding (first few non-trivial eigenvectors)
        eigenvalues, eigenvectors = np.linalg.eigh(L)
        k = min(3, n - 1)  # Use 3 dimensions or less
        embedding = eigenvectors[:, 1:k+1]  # Skip first (trivial) eigenvector

        # Compute centroid and distances
        centroid = np.mean(embedding, axis=0)
        distances = np.linalg.norm(embedding - centroid, axis=1)

        # Find outliers
        mean_dist = np.mean(distances)
        std_dist = np.std(distances)
        threshold = mean_dist + self.tolerance * std_dist

        suspects = []
        for i, head_id in enumerate(head_ids):
            if distances[i] > threshold:
                suspects.append({
                    "head_id": head_id,
                    "spectral_distance": float(distances[i]),
                    "threshold": float(threshold),
                    "z_score": float((distances[i] - mean_dist) / (std_dist + 1e-10)),
                    "reason": "Spectral outlier in interaction graph"
                })

        return sorted(suspects, key=lambda x: x["spectral_distance"], reverse=True)


# =============================================================================
# Integration with HYDRA Librarian
# =============================================================================

async def analyze_hydra_system(
    librarian,  # HydraLibrarian instance
    gfss: GraphFourierAnalyzer = None,
    byzantine: ByzantineDetector = None
) -> Dict[str, Any]:
    """
    Run full spectral analysis on HYDRA system.

    Returns comprehensive security assessment.
    """
    if gfss is None:
        gfss = GraphFourierAnalyzer()
    if byzantine is None:
        byzantine = ByzantineDetector()

    # Get knowledge graph from librarian
    knowledge_graph = dict(librarian._keyword_index)  # Use keyword links as proxy

    # Node signals from memory importance
    node_signals = {}
    for key, entry in librarian.ledger.search_memory(limit=1000):
        if isinstance(entry, dict):
            node_signals[key] = entry.get("importance", 0.5)

    # Run GFSS analysis
    anomalies = gfss.analyze_knowledge_graph(knowledge_graph, node_signals)

    # Get active heads for Byzantine analysis
    active_heads = librarian.ledger.get_active_heads()
    head_ids = [h.get("head_id") for h in active_heads]

    # Build interaction graph from ledger
    interaction_graph = defaultdict(lambda: defaultdict(int))
    entries = librarian.ledger.query(limit=1000)
    for entry in entries:
        if entry.head_id:
            # Track head-to-head interactions via shared targets
            interaction_graph[entry.head_id][entry.action] += 1

    # Run Byzantine detection
    suspects = byzantine.detect_byzantine_heads(interaction_graph, head_ids)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "spectral_anomalies": [a.to_dict() for a in anomalies],
        "byzantine_suspects": suspects,
        "total_anomalies": len(anomalies),
        "critical_count": sum(1 for a in anomalies if a.severity == "CRITICAL"),
        "high_count": sum(1 for a in anomalies if a.severity == "HIGH"),
        "system_health": "HEALTHY" if len(anomalies) == 0 else (
            "CRITICAL" if any(a.severity == "CRITICAL" for a in anomalies) else
            "DEGRADED"
        )
    }
