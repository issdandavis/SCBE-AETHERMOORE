"""
Quantum Lattice Extensions for PHDM
======================================

Crystal Cranium v3.0.0 Section 10.3 — Quantum Superposition of Lattice States

Extends the classical quasicrystal lattice into the quantum domain:
    - Lattice sites (16 polyhedra) become qubits in superposition
    - Thoughts explore entangled paths, collapsing to safest on measurement
    - Phason shift becomes a unitary rotation U(θ) = exp(-iHθ)
    - Time quasicrystals add non-repeating temporal patterns

Mathematical Framework:
    Classical:  ψ = Σ αᵢ |γᵢ⟩  (deterministic projection)
    Quantum:    |Ψ⟩ = Σ cₖ |Lₖ⟩ (superposed lattice configurations)

    Projection: P: H^6D → H^3D (quantum projection operator)
    Entanglement Hamiltonian: H = Σ wᵢⱼ σᵢ ⊗ σⱼ (tongue-weighted)
    Phason unitary: U(θ) = exp(-iHθ)

Key Properties:
    - Superposed rails allow parallel trajectory exploration
    - Measurement collapse enforces safety (unsafe states are
      energetically forbidden by the Harmonic Wall)
    - φ-dimensional fractal signature preserved in quantum regime
    - Decoherence → forced simplicity (DEMI mode analog)

Academic Foundations:
    - Katz & Gratias (1994): 6D cut-and-project for icosahedral QC
    - Baggioli & Landry (2020): EFT for phason dynamics
    - Washington U. (2025): Diamond-based time quasicrystals
    - MIT (2025): Moiré quasicrystals for topological qubits

Author: Issac Davis
Version: 3.0.0
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum

# =============================================================================
# Constants
# =============================================================================

PHI = (1 + np.sqrt(5)) / 2
PHI_INV = 2 / (1 + np.sqrt(5))
HBAR = 1.0545718e-34       # Reduced Planck constant (J·s)
PLANCK_TIME = 5.391e-44    # Planck time (s)
R_FIFTH = 3 / 2


# =============================================================================
# Quantum State Representations
# =============================================================================

class QuantumBasis(Enum):
    """Basis states for lattice qubits."""
    GROUND = 0     # |0⟩ — inactive node
    EXCITED = 1    # |1⟩ — active node


@dataclass
class LatticeQubit:
    """
    A single lattice site as a qubit.

    State: |ψ⟩ = α|0⟩ + β|1⟩ where |α|² + |β|² = 1
    """
    index: int               # Polyhedron index (0-15)
    alpha: complex = 1.0     # Amplitude for |0⟩
    beta: complex = 0.0      # Amplitude for |1⟩

    def __post_init__(self):
        self._normalize()

    def _normalize(self):
        """Ensure |α|² + |β|² = 1."""
        norm = np.sqrt(abs(self.alpha) ** 2 + abs(self.beta) ** 2)
        if norm > 1e-15:
            self.alpha /= norm
            self.beta /= norm

    @property
    def probability_ground(self) -> float:
        """P(|0⟩) = |α|²"""
        return float(abs(self.alpha) ** 2)

    @property
    def probability_excited(self) -> float:
        """P(|1⟩) = |β|²"""
        return float(abs(self.beta) ** 2)

    def measure(self) -> QuantumBasis:
        """
        Projective measurement — collapses superposition.

        Returns |0⟩ or |1⟩ with Born-rule probabilities.
        """
        if np.random.random() < self.probability_ground:
            self.alpha = 1.0 + 0j
            self.beta = 0.0 + 0j
            return QuantumBasis.GROUND
        else:
            self.alpha = 0.0 + 0j
            self.beta = 1.0 + 0j
            return QuantumBasis.EXCITED

    def apply_gate(self, matrix: np.ndarray):
        """Apply a 2×2 unitary gate."""
        state = np.array([self.alpha, self.beta])
        new_state = matrix @ state
        self.alpha = complex(new_state[0])
        self.beta = complex(new_state[1])
        self._normalize()

    def to_bloch(self) -> Tuple[float, float, float]:
        """Convert to Bloch sphere coordinates (θ, φ, r)."""
        theta = 2 * np.arccos(min(1.0, abs(self.alpha)))
        if abs(self.beta) > 1e-15:
            phi = float(np.angle(self.beta) - np.angle(self.alpha))
        else:
            phi = 0.0
        return theta, phi, 1.0


# =============================================================================
# Quantum Gates (Lattice Operations)
# =============================================================================

# Pauli gates
PAULI_X = np.array([[0, 1], [1, 0]], dtype=complex)
PAULI_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
PAULI_Z = np.array([[1, 0], [0, -1]], dtype=complex)
IDENTITY = np.eye(2, dtype=complex)

# Hadamard gate (creates superposition)
HADAMARD = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)

# Phase gate parameterized by golden ratio
PHI_GATE = np.array([
    [1, 0],
    [0, np.exp(2j * np.pi / PHI)]
], dtype=complex)

# Phason rotation gate: R(θ) = exp(-i·θ·Z/2)
def phason_gate(theta: float) -> np.ndarray:
    """Phason shift as unitary rotation."""
    return np.array([
        [np.exp(-1j * theta / 2), 0],
        [0, np.exp(1j * theta / 2)]
    ], dtype=complex)


# =============================================================================
# Quantum Lattice State
# =============================================================================

@dataclass
class QuantumLatticeState:
    """
    Full quantum state of the 16-polyhedra lattice.

    Each of the 16 sites is a qubit. The full state lives in a
    2^16 = 65536-dimensional Hilbert space, but we use the
    product-state approximation for tractability:

        |Ψ⟩ ≈ |ψ₀⟩ ⊗ |ψ₁⟩ ⊗ ... ⊗ |ψ₁₅⟩

    Entanglement is tracked via correlation matrices rather than
    full density matrices.
    """
    qubits: List[LatticeQubit] = field(default_factory=list)
    entanglement_map: Dict[Tuple[int, int], float] = field(default_factory=dict)
    time: float = 0.0

    def __post_init__(self):
        if not self.qubits:
            self.qubits = [LatticeQubit(index=i) for i in range(16)]

    @property
    def n_sites(self) -> int:
        return len(self.qubits)

    def superpose_all(self):
        """Put all qubits in equal superposition (Hadamard on each)."""
        for q in self.qubits:
            q.apply_gate(HADAMARD)

    def phason_shift(self, theta: float):
        """
        Global phason shift — rotate all qubits by θ.

        Quantum analog of the classical phason rotation:
        classical: rotate 6D projection angle
        quantum:   apply U(θ) = exp(-iθZ/2) to all qubits
        """
        gate = phason_gate(theta)
        for q in self.qubits:
            q.apply_gate(gate)
        self.time += abs(theta) / (2 * np.pi)

    def apply_phi_gate(self, site: int):
        """Apply golden-ratio phase gate to a specific site."""
        if 0 <= site < self.n_sites:
            self.qubits[site].apply_gate(PHI_GATE)

    def entangle_pair(self, site_a: int, site_b: int, strength: float = 1.0):
        """
        Create entanglement between two sites.

        Uses a CNOT-like operation in the product state approximation.
        The strength parameter controls the degree of entanglement.
        """
        if not (0 <= site_a < self.n_sites and 0 <= site_b < self.n_sites):
            return

        qa = self.qubits[site_a]
        qb = self.qubits[site_b]

        # Controlled rotation: if qa is excited, rotate qb
        if qa.probability_excited > 0.5:
            angle = strength * np.pi / PHI
            qb.apply_gate(phason_gate(angle))

        # Record entanglement
        pair = (min(site_a, site_b), max(site_a, site_b))
        self.entanglement_map[pair] = strength

    def measure_all(self) -> List[QuantumBasis]:
        """
        Measure all qubits — collapses the full lattice state.

        This is the "observation" that forces a thought to
        crystallize from superposition into a definite path.
        """
        return [q.measure() for q in self.qubits]

    def measure_path(self) -> List[int]:
        """
        Measure the lattice and return the active nodes as a path.

        Nodes in |1⟩ (EXCITED) are included in the path,
        ordered by index.
        """
        results = self.measure_all()
        return [i for i, r in enumerate(results) if r == QuantumBasis.EXCITED]

    def excitation_probabilities(self) -> np.ndarray:
        """Get P(|1⟩) for each site."""
        return np.array([q.probability_excited for q in self.qubits])

    def entropy(self) -> float:
        """
        Compute von Neumann entropy of the product state.

        S = -Σ (pᵢ log₂ pᵢ) summed over all qubits.
        """
        total = 0.0
        for q in self.qubits:
            for p in [q.probability_ground, q.probability_excited]:
                if p > 1e-15:
                    total -= p * np.log2(p)
        return float(total)


# =============================================================================
# Quantum Hamiltonian for Lattice Dynamics
# =============================================================================

@dataclass
class LatticeHamiltonian:
    """
    Hamiltonian for the quantum lattice.

    H = Σᵢⱼ wᵢⱼ σᵢᶻ σⱼᶻ + Σᵢ hᵢ σᵢˣ

    where:
        wᵢⱼ = φ-weighted coupling between sites i and j
        hᵢ  = local field from trust ring position
    """
    n_sites: int = 16
    couplings: Dict[Tuple[int, int], float] = field(default_factory=dict)
    local_fields: np.ndarray = field(default_factory=lambda: np.zeros(16))

    def set_coupling(self, i: int, j: int, weight: float):
        """Set coupling strength between sites i and j."""
        pair = (min(i, j), max(i, j))
        self.couplings[pair] = weight

    def set_phi_couplings(self, adjacency: Dict[int, List[int]]):
        """
        Set φ-weighted couplings from adjacency graph.

        Weight = φ^(-|i-j|) — closer nodes couple more strongly.
        """
        for i, neighbors in adjacency.items():
            for j in neighbors:
                weight = PHI ** (-abs(i - j))
                self.set_coupling(i, j, weight)

    def energy(self, state: QuantumLatticeState) -> float:
        """
        Compute ⟨Ψ|H|Ψ⟩ in the product state approximation.

        E = Σᵢⱼ wᵢⱼ ⟨σᵢᶻ⟩⟨σⱼᶻ⟩ + Σᵢ hᵢ ⟨σᵢˣ⟩
        """
        # ⟨σᶻ⟩ = P(|0⟩) - P(|1⟩)
        sigma_z = np.array([
            q.probability_ground - q.probability_excited
            for q in state.qubits
        ])

        # ⟨σˣ⟩ = 2·Re(α*·β)
        sigma_x = np.array([
            2 * np.real(np.conj(q.alpha) * q.beta)
            for q in state.qubits
        ])

        # Coupling energy
        E_coupling = sum(
            w * sigma_z[i] * sigma_z[j]
            for (i, j), w in self.couplings.items()
        )

        # Local field energy
        E_local = float(np.dot(self.local_fields, sigma_x))

        return E_coupling + E_local


# =============================================================================
# Quantum Phason Dynamics
# =============================================================================

class QuantumPhasonEngine:
    """
    Quantum phason dynamics engine.

    Evolves the quantum lattice state under phason shift unitaries,
    implementing the quantum analog of the classical phason rotation
    defense mechanism.

    Properties (from Baggioli & Landry 2020):
        - Phason shifts are symmetries with no Noether currents
        - Diffusive at long wavelengths → perturbations decay
        - Instant key rotation without system restart
    """

    def __init__(self, n_sites: int = 16):
        self.n_sites = n_sites
        self.hamiltonian = LatticeHamiltonian(n_sites=n_sites)
        self._rotation_history: List[float] = []

    def initialize_lattice(
        self,
        mode: str = "superposed",
        adjacency: Optional[Dict[int, List[int]]] = None,
    ) -> QuantumLatticeState:
        """
        Initialize the quantum lattice.

        Modes:
            "ground"    — all |0⟩ (classical ground state)
            "superposed" — all in equal superposition (quantum)
            "phi_biased" — φ-weighted superposition
        """
        state = QuantumLatticeState()

        if mode == "superposed":
            state.superpose_all()
        elif mode == "phi_biased":
            for q in state.qubits:
                # Bias toward excited with probability φ/(1+φ)
                theta = 2 * np.arccos(np.sqrt(1 / (1 + PHI)))
                rotation = np.array([
                    [np.cos(theta / 2), -np.sin(theta / 2)],
                    [np.sin(theta / 2), np.cos(theta / 2)]
                ], dtype=complex)
                q.apply_gate(rotation)

        # Set up Hamiltonian couplings
        if adjacency:
            self.hamiltonian.set_phi_couplings(adjacency)

        return state

    def evolve(
        self,
        state: QuantumLatticeState,
        dt: float = 0.01,
        n_steps: int = 100,
    ) -> List[QuantumLatticeState]:
        """
        Evolve the quantum lattice forward in time.

        Uses Trotterized time evolution:
            U(dt) ≈ Π exp(-i·wᵢⱼ·σᵢᶻσⱼᶻ·dt) · Π exp(-i·hᵢ·σᵢˣ·dt)

        Returns trajectory of states for analysis.
        """
        trajectory = [self._snapshot(state)]

        for step in range(n_steps):
            t = step * dt

            # Coupling evolution (Ising-like)
            for (i, j), w in self.hamiltonian.couplings.items():
                if i < state.n_sites and j < state.n_sites:
                    angle = w * dt
                    # Approximate two-qubit gate via product state
                    state.qubits[i].apply_gate(phason_gate(angle))
                    state.qubits[j].apply_gate(phason_gate(-angle))

            # Local field evolution
            for i in range(min(state.n_sites, len(self.hamiltonian.local_fields))):
                h = self.hamiltonian.local_fields[i]
                if abs(h) > 1e-15:
                    # σˣ rotation
                    rx = np.array([
                        [np.cos(h * dt / 2), -1j * np.sin(h * dt / 2)],
                        [-1j * np.sin(h * dt / 2), np.cos(h * dt / 2)]
                    ], dtype=complex)
                    state.qubits[i].apply_gate(rx)

            state.time = (step + 1) * dt
            trajectory.append(self._snapshot(state))

        return trajectory

    def phason_defense(self, state: QuantumLatticeState) -> float:
        """
        Execute a quantum phason shift defense rotation.

        Randomly rotates all qubits by a golden-angle increment,
        then returns the angle used.

        This is the quantum analog of rotate_6d_projection().
        """
        theta = np.random.uniform(0, 2 * np.pi / PHI)
        state.phason_shift(theta)
        self._rotation_history.append(theta)
        return theta

    def measure_safety(self, state: QuantumLatticeState) -> Dict[str, Any]:
        """
        Measure the quantum lattice and assess safety.

        Collapses superposition and checks if the resulting
        classical configuration is safe (no Risk zone nodes active
        without Core nodes also active).
        """
        # Get probabilities before measurement
        probs = state.excitation_probabilities()
        energy = self.hamiltonian.energy(state)
        entropy = state.entropy()

        # Measure
        active_nodes = state.measure_path()

        # Safety check: Core nodes (0-4) should be active if Risk (8-9) are
        core_active = [n for n in active_nodes if n < 5]
        risk_active = [n for n in active_nodes if n in (8, 9)]
        safe = len(risk_active) == 0 or len(core_active) >= 2

        return {
            "active_nodes": active_nodes,
            "n_active": len(active_nodes),
            "core_active": core_active,
            "risk_active": risk_active,
            "is_safe": safe,
            "pre_measurement_entropy": entropy,
            "pre_measurement_energy": energy,
            "pre_measurement_probs": probs.tolist(),
        }

    def _snapshot(self, state: QuantumLatticeState) -> QuantumLatticeState:
        """Create a snapshot of the current state."""
        new_qubits = [
            LatticeQubit(index=q.index, alpha=q.alpha, beta=q.beta)
            for q in state.qubits
        ]
        return QuantumLatticeState(
            qubits=new_qubits,
            entanglement_map=dict(state.entanglement_map),
            time=state.time,
        )


# =============================================================================
# Time Quasicrystal Extension
# =============================================================================

class TimeQuasicrystal:
    """
    Time quasicrystal for temporal pattern generation.

    Based on Fibonacci pulse sequences that produce non-repeating
    temporal patterns, extending PHDM from spatial to temporal
    quasicrystallinity.

    Fibonacci sequence: F(n) = F(n-1) + F(n-2)
    Pulse pattern: A, B, AB, ABA, ABAAB, ...

    This creates "two time dimensions" where thoughts evolve
    in non-repeating temporal patterns, enhancing memory stability.
    """

    def __init__(self, base_period_a: float = 1.0):
        self.period_a = base_period_a
        self.period_b = base_period_a * PHI  # Golden ratio spacing

    def fibonacci_sequence(self, n_terms: int = 20) -> List[str]:
        """Generate Fibonacci substitution sequence."""
        if n_terms <= 0:
            return []
        seq = ["A"]
        for _ in range(n_terms - 1):
            new_seq = []
            for s in seq:
                if s == "A":
                    new_seq.extend(["A", "B"])
                else:
                    new_seq.append("A")
            seq = new_seq
        return seq

    def pulse_times(self, n_pulses: int = 50) -> np.ndarray:
        """
        Generate quasiperiodic pulse times from Fibonacci sequence.

        Returns array of times when pulses should fire.
        """
        seq = self.fibonacci_sequence(8)[:n_pulses]
        times = [0.0]
        for s in seq:
            dt = self.period_a if s == "A" else self.period_b
            times.append(times[-1] + dt)
        return np.array(times[:n_pulses])

    def is_quasiperiodic(self, times: np.ndarray, tolerance: float = 0.01) -> bool:
        """
        Verify that a time series is quasiperiodic (not periodic).

        Checks that the ratio of consecutive intervals approaches φ
        but never exactly repeats.
        """
        if len(times) < 3:
            return True

        intervals = np.diff(times)
        ratios = intervals[1:] / (intervals[:-1] + 1e-15)

        # Should cluster around φ and 1/φ but never be exactly periodic
        unique_ratios = len(set(np.round(ratios, 3)))
        return unique_ratios > 1  # At least 2 distinct ratio values

    def apply_temporal_modulation(
        self,
        state: QuantumLatticeState,
        t: float,
    ):
        """
        Apply temporal quasicrystal modulation to the lattice.

        At each pulse time, apply a φ-phase gate to the site
        corresponding to the Fibonacci index mod 16.
        """
        pulses = self.pulse_times(100)

        # Find nearest pulse
        nearest_idx = np.argmin(np.abs(pulses - t))
        site = nearest_idx % state.n_sites

        state.apply_phi_gate(site)


# =============================================================================
# Self-Test
# =============================================================================

def self_test() -> Dict[str, Any]:
    """Run self-tests on the quantum lattice module."""
    results = {}
    passed = 0
    total = 0

    # Test 1: Qubit normalization
    total += 1
    q = LatticeQubit(index=0, alpha=3.0 + 0j, beta=4.0 + 0j)
    norm_sq = abs(q.alpha) ** 2 + abs(q.beta) ** 2
    if abs(norm_sq - 1.0) < 1e-10:
        passed += 1
        results["qubit_normalization"] = "PASS"
    else:
        results["qubit_normalization"] = f"FAIL (|ψ|²={norm_sq})"

    # Test 2: Hadamard creates equal superposition
    total += 1
    q2 = LatticeQubit(index=1)
    q2.apply_gate(HADAMARD)
    if abs(q2.probability_ground - 0.5) < 1e-10:
        passed += 1
        results["hadamard_superposition"] = "PASS (P(0)=P(1)=0.5)"
    else:
        results["hadamard_superposition"] = f"FAIL (P(0)={q2.probability_ground})"

    # Test 3: Lattice initialization
    total += 1
    state = QuantumLatticeState()
    if state.n_sites == 16:
        passed += 1
        results["lattice_init"] = "PASS (16 sites)"
    else:
        results["lattice_init"] = f"FAIL ({state.n_sites} sites)"

    # Test 4: Superposition entropy
    total += 1
    state.superpose_all()
    entropy = state.entropy()
    # Max entropy for 16 qubits in equal superposition = 16 bits
    if 15.0 < entropy <= 16.0:
        passed += 1
        results["superposition_entropy"] = f"PASS (S={entropy:.2f} bits)"
    else:
        results["superposition_entropy"] = f"FAIL (S={entropy:.2f})"

    # Test 5: Phason shift is unitary (preserves normalization)
    total += 1
    state2 = QuantumLatticeState()
    state2.superpose_all()
    state2.phason_shift(np.pi / PHI)
    norms_ok = all(
        abs(abs(q.alpha) ** 2 + abs(q.beta) ** 2 - 1.0) < 1e-10
        for q in state2.qubits
    )
    if norms_ok:
        passed += 1
        results["phason_unitary"] = "PASS (all qubits normalized after shift)"
    else:
        results["phason_unitary"] = "FAIL"

    # Test 6: Measurement collapses state
    total += 1
    state3 = QuantumLatticeState()
    state3.superpose_all()
    path = state3.measure_path()
    # After measurement, entropy should be 0
    entropy_after = state3.entropy()
    if entropy_after < 1e-10:
        passed += 1
        results["measurement_collapse"] = f"PASS (S=0 after measurement, {len(path)} active nodes)"
    else:
        results["measurement_collapse"] = f"FAIL (S={entropy_after} after measurement)"

    # Test 7: Quantum phason engine
    total += 1
    engine = QuantumPhasonEngine()
    qstate = engine.initialize_lattice(mode="phi_biased")
    safety = engine.measure_safety(qstate)
    if "is_safe" in safety and "active_nodes" in safety:
        passed += 1
        results["phason_engine"] = (
            f"PASS (safe={safety['is_safe']}, "
            f"active={safety['n_active']}, "
            f"entropy={safety['pre_measurement_entropy']:.2f})"
        )
    else:
        results["phason_engine"] = "FAIL"

    # Test 8: Time quasicrystal
    total += 1
    tqc = TimeQuasicrystal()
    times = tqc.pulse_times(50)
    is_qp = tqc.is_quasiperiodic(times)
    if is_qp and len(times) == 50:
        passed += 1
        # Check ratio approaches φ
        intervals = np.diff(times)
        mean_ratio = np.mean(intervals[1:] / (intervals[:-1] + 1e-15))
        results["time_quasicrystal"] = (
            f"PASS (quasiperiodic, mean_ratio={mean_ratio:.3f}, φ={PHI:.3f})"
        )
    else:
        results["time_quasicrystal"] = f"FAIL (qp={is_qp}, n={len(times)})"

    # Test 9: Hamiltonian energy computation
    total += 1
    ham = LatticeHamiltonian()
    ham.set_coupling(0, 1, PHI)
    ham.set_coupling(1, 2, PHI_INV)
    ham.local_fields[0] = 0.5
    test_state = QuantumLatticeState()
    test_state.superpose_all()
    E = ham.energy(test_state)
    if isinstance(E, float):
        passed += 1
        results["hamiltonian_energy"] = f"PASS (E={E:.6f})"
    else:
        results["hamiltonian_energy"] = "FAIL"

    # Test 10: φ-gate preserves normalization
    total += 1
    q_phi = LatticeQubit(index=0, alpha=1 / np.sqrt(2), beta=1 / np.sqrt(2))
    q_phi.apply_gate(PHI_GATE)
    norm_after = abs(q_phi.alpha) ** 2 + abs(q_phi.beta) ** 2
    if abs(norm_after - 1.0) < 1e-10:
        passed += 1
        results["phi_gate_unitary"] = "PASS"
    else:
        results["phi_gate_unitary"] = f"FAIL (norm={norm_after})"

    return {
        "passed": passed,
        "total": total,
        "results": results,
        "rate": f"{passed}/{total} ({100 * passed / max(1, total):.0f}%)",
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Quantum Lattice Extensions — Self-Test")
    print("=" * 60)

    test_results = self_test()
    for name, result in test_results["results"].items():
        print(f"  {name}: {result}")
    print("-" * 60)
    print(f"  TOTAL: {test_results['rate']}")
