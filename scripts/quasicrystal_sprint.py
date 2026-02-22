import numpy as np
import hashlib
from dataclasses import dataclass
from typing import Tuple, List, Optional
from numpy.fft import fft, fftfreq  # Use numpy FFT (faster import than scipy)

# Constants
PHI = (1 + np.sqrt(5)) / 2  # The Golden Ratio
TAU = 2 * np.pi

class QuasicrystalLattice:
    """
    SCBE v3.0: Icosahedral Quasicrystal Verification System.
    Maps 6-dimensional authentication gates onto a 3D aperiodic lattice.
    """

    def __init__(self, lattice_constant: float = 1.0):
        self.a = lattice_constant
        # The acceptance radius in Perpendicular Space (E_perp).
        # Points are valid iff ||r_perp|| < R_accept
        # This defines the "Atomic Surface" of the quasicrystal.
        self.acceptance_radius = 1.5 * self.a

        # Current Phason Strain Vector (Secret Key Component)
        self.phason_strain = np.zeros(3)

        # Initialize 6D -> 3D Projection Matrices
        self.M_par, self.M_perp = self._generate_basis_matrices()

    def _generate_basis_matrices(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generates the projection matrices from 6D Z^6 to 3D E_parallel (Physical)
        and 3D E_perp (Internal/Window) using Icosahedral symmetry.
        """
        norm = 1 / np.sqrt(1 + PHI**2)

        e_par = np.array([
            [1, PHI, 0],
            [-1, PHI, 0],
            [0, 1, PHI],
            [0, -1, PHI],
            [PHI, 0, 1],
            [PHI, 0, -1]
        ]).T * norm # Shape (3, 6)

        e_perp = np.array([
            [1, -1/PHI, 0],
            [-1, -1/PHI, 0],
            [0, 1, -1/PHI],
            [0, -1, -1/PHI],
            [-1/PHI, 0, 1],
            [-1/PHI, 0, -1]
        ]).T * norm # Shape (3, 6)

        return e_par, e_perp

    def map_gates_to_lattice(self, gate_vector: List[int]) -> Tuple[np.ndarray, np.ndarray, bool]:
        """
        Maps the 6 integer inputs (SCBE Gates) to the Quasicrystal.
        """
        n = np.array(gate_vector, dtype=float)

        r_phys = self.M_par @ n
        r_perp_raw = self.M_perp @ n

        distance = np.linalg.norm(r_perp_raw - self.phason_strain)
        is_valid = distance < self.acceptance_radius

        return r_phys, r_perp_raw, is_valid

    def apply_phason_rekey(self, entropy_seed: bytes):
        """
        Applies a Phason Strain ("Deformation") to the lattice.
        """
        h = hashlib.sha256(entropy_seed).digest()
        v = np.array([
            int.from_bytes(h[0:4], 'big') / (2**32) * 2 - 1,
            int.from_bytes(h[4:8], 'big') / (2**32) * 2 - 1,
            int.from_bytes(h[8:12], 'big') / (2**32) * 2 - 1
        ])

        self.phason_strain = v * self.acceptance_radius * 2.0
        print(f"[SCBE] Phason Shift Applied: {self.phason_strain}")

    def detect_crystalline_defects(self, history_vectors: List[List[int]]) -> float:
        """
        Detects if an attacker is trying to force periodicity (Crystalline Defect).
        """
        if len(history_vectors) < 32:
            return 0.0

        norms = np.array([np.linalg.norm(v) for v in history_vectors])

        N = len(norms)
        window = np.hanning(N)
        windowed_norms = norms * window

        yf = fft(windowed_norms)
        xf = fftfreq(N, 1)

        power_spectrum = np.abs(yf[1:N//2])**2
        frequencies = xf[1:N//2]

        if len(power_spectrum) == 0 or np.sum(power_spectrum) == 0:
            return 0.0

        dominant_freq_idx = np.argmax(power_spectrum)
        dominant_frequency = frequencies[dominant_freq_idx]
        dominant_power = power_spectrum[dominant_freq_idx]

        total_power = np.sum(power_spectrum)
        normalized_dominant_power = dominant_power / total_power

        crystallinity_threshold_freq = 0.1
        crystallinity_threshold_power = 0.5

        defect_score = 0.0
        if dominant_frequency > 0 and dominant_frequency < crystallinity_threshold_freq and \
           normalized_dominant_power > crystallinity_threshold_power:
            defect_score = min(1.0, normalized_dominant_power * 1.5)

        return defect_score


def run_sprint_test():
    print("\n--- SCBE v3.0: Quasicrystal Lattice Verification Sprint ---")
    qc = QuasicrystalLattice()

    # 1. Simulate Valid Authentication
    valid_gates = [1, 2, 3, 5, 8, 13]

    r_phys, r_perp, valid = qc.map_gates_to_lattice(valid_gates)

    print(f"Gate Input: {valid_gates}")
    print(f"Projected Key (3D): {r_phys}")
    print(f"Internal Check (E_perp dist): {np.linalg.norm(r_perp - qc.phason_strain):.4f} vs Rad {qc.acceptance_radius:.4f}")
    print(f"Status: {'VALID' if valid else 'INVALID (Rejected by Atomic Surface)'}")

    # 2. Simulate Phason Rekeying
    print("\n--- Applying Phason Deformation (Rekey) ---")
    qc.apply_phason_rekey(b"dynamic_entropy_seed_v99")

    r_phys_2, r_perp_2, valid_2 = qc.map_gates_to_lattice(valid_gates)

    print(f"Re-evaluating Gate Input: {valid_gates}")
    print(f"Internal Check (E_perp dist): {np.linalg.norm(r_perp_2 - qc.phason_strain):.4f}")
    print(f"Status: {'VALID' if valid_2 else 'INVALID - REJECTED (Phason Shift)'}")

    if valid and not valid_2:
        print(">> SUCCESS: Phason shift successfully invalidated old key.")

    # 3. Defect Detection
    print("\n--- Checking for Crystalline Defects ---")

    history_vectors_aperiodic = [
        [1, 2, 3, 5, 8, 13],
        [1, 1, 2, 3, 5, 8],
        [2, 3, 5, 8, 13, 21],
        [3, 5, 8, 13, 21, 34],
        [5, 8, 13, 21, 34, 55],
        [8, 13, 21, 34, 55, 89],
        [13, 21, 34, 55, 89, 144],
        [21, 34, 55, 89, 144, 233],
        [34, 55, 89, 144, 233, 377],
        [55, 89, 144, 233, 377, 610],
        [89, 144, 233, 377, 610, 987],
        [144, 233, 377, 610, 987, 1597],
        [233, 377, 610, 987, 1597, 2584],
        [377, 610, 987, 1597, 2584, 4181],
        [610, 987, 1597, 2584, 4181, 6765],
        [987, 1597, 2584, 4181, 6765, 10946],
        [1597, 2584, 4181, 6765, 10946, 17711],
        [2584, 4181, 6765, 10946, 17711, 28657],
        [4181, 6765, 10946, 17711, 28657, 46368],
        [6765, 10946, 17711, 28657, 46368, 75025],
        [10946, 17711, 28657, 46368, 75025, 121393],
        [17711, 28657, 46368, 75025, 121393, 196418],
        [28657, 46368, 75025, 121393, 196418, 317811],
        [46368, 75025, 121393, 196418, 317811, 514229],
        [75025, 121393, 196418, 317811, 514229, 832040],
        [121393, 196418, 317811, 514229, 832040, 1346269],
        [196418, 317811, 514229, 832040, 1346269, 2180309],
        [317811, 514229, 832040, 1346269, 2180309, 3526938],
        [514229, 832040, 1346269, 2180309, 3526938, 5702887],
        [832040, 1346269, 2180309, 3526938, 5702887, 9227825],
        [1346269, 2180309, 3526938, 5702887, 9227825, 14930352],
        [2180309, 3526938, 5702887, 9227825, 14930352, 24157817]
    ]

    history_vectors_periodic = []
    for i in range(32):
        if i % 4 == 0:
            history_vectors_periodic.append([10, 20, 30, 40, 50, 60])
        elif i % 4 == 1:
            history_vectors_periodic.append([11, 21, 31, 41, 51, 61])
        elif i % 4 == 2:
            history_vectors_periodic.append([12, 22, 32, 42, 52, 62])
        else:
            history_vectors_periodic.append([13, 23, 33, 43, 53, 63])

    defect_score_aperiodic = qc.detect_crystalline_defects(history_vectors_aperiodic)
    print(f"Crystallinity Score (Aperiodic Input): {defect_score_aperiodic:.4f}")

    defect_score_periodic = qc.detect_crystalline_defects(history_vectors_periodic)
    print(f"Crystallinity Score (Periodic Input): {defect_score_periodic:.4f}")

if __name__ == "__main__":
    run_sprint_test()
