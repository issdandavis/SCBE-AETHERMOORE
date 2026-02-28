"""TernaryHybridEncoder -- 7-module unified encoding pipeline.

Pipeline flow:
  Input -> StateAdapter -> 21D state
    -> [1] DualTernarySystem.encode(state_21d)
    -> [2] Extract 6 tongue trits from DualTernaryState pairs
    -> [3] gate_swap.map_gates_to_trimanifold()
    -> [4] QuasicrystalLattice.map_ternary_state()
    -> [5] ChemistryAgent.process_input(lattice_distance)
    -> [6] BalancedTernary.pack_decisions() + NegaBinary
    -> [7] Governance decision
    -> Feedback: deposit onto SphereGridNetwork

@layer Layer 5, 9, 12, 13
@component HybridEncoder.Pipeline
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional

from src.hybrid_encoder.types import (
    EncoderInput,
    EncoderResult,
    HybridRepresentation,
    MolecularBond,
    Decision,
    TONGUE_NAMES,
)
from src.hybrid_encoder.state_adapter import StateAdapter
from src.hybrid_encoder.negative_space import NegativeSpaceEncoder
from src.hybrid_encoder.molecular_code import MolecularCodeMapper
from src.hybrid_encoder.hamiltonian_path import HamiltonianTraversal

# -- Existing module imports (the 7 we are connecting) --
from src.symphonic_cipher.scbe_aethermoore.ai_brain.dual_ternary import (
    DualTernarySystem,
    DualTernaryState,
)
from src.symphonic_cipher.scbe_aethermoore.gate_swap import (
    map_gates_to_trimanifold,
    apply_tri_manifold_governance,
    GateTriState,
)
from src.crypto.quasicrystal_lattice import QuasicrystalLattice
from src.symphonic_cipher.scbe_aethermoore.ede.chemistry_agent import (
    ChemistryAgent,
    ThreatType,
)
from src.symphonic_cipher.scbe_aethermoore.trinary import (
    BalancedTernary,
    Trit,
)
from src.symphonic_cipher.scbe_aethermoore.negabinary import NegaBinary

# SphereGridNetwork requires numpy -- optional for headless environments
try:
    from src.geoseed.sphere_grid import SphereGridNetwork
    import numpy as np
    _HAS_SPHERE = True
except ImportError:
    _HAS_SPHERE = False

PHI = (1 + math.sqrt(5)) / 2


class TernaryHybridEncoder:
    """Unified pipeline connecting 7 encoding modules.

    Args:
        sphere_network: Optional external SphereGridNetwork for feedback.
                        If None, creates an internal one (when numpy available).
        chemistry_threat_level: Initial ChemistryAgent threat level (1-10).
    """

    def __init__(
        self,
        sphere_network: Any = None,
        chemistry_threat_level: int = 5,
    ):
        self._adapter = StateAdapter()
        self._dual_ternary = DualTernarySystem()
        self._lattice = QuasicrystalLattice()
        self._chemistry = ChemistryAgent(agent_id="hybrid-encoder")
        self._chemistry.set_threat_level(chemistry_threat_level)
        self._chemistry.activate()
        self._negative_space = NegativeSpaceEncoder()
        self._molecular = MolecularCodeMapper()
        self._hamiltonian = HamiltonianTraversal()
        self._encode_count = 0

        # SphereGridNetwork for feedback loop
        self._sphere_net: Any = sphere_network
        if self._sphere_net is None and _HAS_SPHERE:
            self._sphere_net = SphereGridNetwork(resolution=1, signal_dim=64)

    def encode(self, inp: EncoderInput) -> EncoderResult:
        """Run the full 7-module pipeline on an input."""
        self._encode_count += 1
        audit: List[Dict[str, Any]] = []
        t0 = time.time()

        # ── Step 1: StateAdapter -> 21D state ──
        state_21d = self._adapter.adapt(inp)
        audit.append({"step": "state_adapter", "state_21d_norm": sum(v * v for v in state_21d) ** 0.5})

        # ── Step 2: DualTernarySystem.encode(21D) -> DualTernaryStates ──
        dual_states = self._dual_ternary.encode(state_21d)
        analysis = self._dual_ternary.full_analysis()
        threat_score = analysis.get("threat_score", 0.0)
        audit.append({"step": "dual_ternary", "states": len(dual_states), "threat_score": threat_score})

        # ── Step 3: Extract 6 tongue trits ──
        tongue_trits = self._extract_tongue_trits(dual_states)
        audit.append({"step": "tongue_trits", "trits": tongue_trits})

        # ── Step 4: Hamiltonian traversal check ──
        trav_valid, trav_decision, visit_count = self._hamiltonian.check(tongue_trits)
        self._hamiltonian.record(tongue_trits)
        audit.append({
            "step": "hamiltonian",
            "valid": trav_valid,
            "decision": trav_decision,
            "visits": visit_count,
            "coverage": self._hamiltonian.coverage,
        })

        # ── Step 5: Gate swap ──
        gate_vector = self._build_gate_vector(tongue_trits)
        gate_state = map_gates_to_trimanifold(gate_vector)
        gate_decision = apply_tri_manifold_governance(gate_state)
        audit.append({
            "step": "gate_swap",
            "gate_vector": gate_vector,
            "gate_state": gate_state.to_tuple(),
            "decision": gate_decision,
        })

        # ── Step 6: QuasicrystalLattice ──
        lattice_point = self._lattice.map_ternary_state(tongue_trits)
        lattice_valid = lattice_point.is_valid
        lattice_distance = lattice_point.distance_to_window
        defect_report = self._lattice.detect_defects()
        defect_score = defect_report.defect_score
        audit.append({
            "step": "quasicrystal",
            "valid": lattice_valid,
            "distance": lattice_distance,
            "defect_score": defect_score,
        })

        # ── Step 7: ChemistryAgent ──
        chem_input = lattice_distance + threat_score
        processed_val, chemistry_blocked = self._chemistry.process_input(
            chem_input, ThreatType.NORMAL
        )
        chemistry_energy = math.log(1 + chem_input ** 2)
        audit.append({
            "step": "chemistry",
            "input": chem_input,
            "blocked": chemistry_blocked,
            "energy": chemistry_energy,
        })

        # ── Step 8: BalancedTernary packing + NegaBinary ──
        stage_decisions = [gate_decision, trav_decision]
        if not lattice_valid:
            stage_decisions.append("QUARANTINE")
        if chemistry_blocked:
            stage_decisions.append("DENY")
        if defect_score > 0.7:
            stage_decisions.append("QUARANTINE")

        ternary_packed = BalancedTernary.pack_decisions(stage_decisions)
        gov_summary = ternary_packed.governance_summary()

        # Build hybrid representation
        trit_sum = sum(tongue_trits)
        hybrid = self._build_hybrid(trit_sum)

        # ── Step 9: Final governance decision ──
        decision = self._decision_from_stages(
            gate_decision=gate_decision,
            lattice_valid=lattice_valid,
            chemistry_blocked=chemistry_blocked,
            threat_score=threat_score,
            traversal_decision=trav_decision,
            defect_score=defect_score,
        )
        audit.append({"step": "governance", "decision": decision})

        # ── Step 10: Negative space embedding ──
        neg_space = self._negative_space.encode(tongue_trits)

        # ── Step 11: Molecular bonds (if code text) ──
        bonds: List[MolecularBond] = []
        if inp.code_text:
            bonds = self._molecular.map_code(inp.code_text)
            audit.append({"step": "molecular", "bonds": len(bonds)})

        # ── Step 12: Feedback to SphereGridNetwork ──
        self._feedback_to_sphere(state_21d, tongue_trits, decision)

        elapsed = time.time() - t0
        audit.append({"step": "complete", "elapsed_ms": elapsed * 1000})

        return EncoderResult(
            decision=decision,
            hybrid=hybrid,
            negative_space=neg_space,
            gate_state=gate_state,
            lattice_valid=lattice_valid,
            lattice_distance=lattice_distance,
            chemistry_blocked=chemistry_blocked,
            chemistry_energy=chemistry_energy,
            ternary_packed=ternary_packed,
            governance_summary=gov_summary,
            threat_score=threat_score,
            defect_score=defect_score,
            state_21d_used=state_21d,
            tongue_trits=tongue_trits,
            traversal_valid=trav_valid,
            molecular_bonds=bonds,
            audit_trail=audit,
        )

    def _extract_tongue_trits(self, dual_states: List[DualTernaryState]) -> List[int]:
        """Extract 6 Sacred Tongue trits from DualTernaryState pairs.

        Takes the first 6 DualTernaryStates.  For each, compute:
          net = primary + mirror
          trit = +1 if net > 0, -1 if net < 0, 0 otherwise
        Maps to tongues [KO, AV, RU, CA, UM, DR] in order.
        """
        trits: List[int] = []
        for i in range(6):
            if i < len(dual_states):
                s = dual_states[i]
                net = s.primary + s.mirror
                if net > 0:
                    trits.append(1)
                elif net < 0:
                    trits.append(-1)
                else:
                    trits.append(0)
            else:
                trits.append(0)
        return trits

    def _build_gate_vector(self, tongue_trits: List[int]) -> List[int]:
        """Convert 6 tongue trits into a 6-element gate vector for gate_swap.

        Trits are in {-1, 0, +1}.  Gate vector needs non-negative ints.
        Shift each trit: gate = trit + 1, giving {0, 1, 2}.
        Tongue pairs: (KO,AV)->dim1, (RU,CA)->dim2, (UM,DR)->dim3.
        """
        return [t + 1 for t in tongue_trits[:6]]

    def _build_hybrid(self, trit_sum: int) -> HybridRepresentation:
        """Build simultaneous ternary + binary representation."""
        bt = BalancedTernary.from_int(trit_sum)
        nb = NegaBinary.from_int(trit_sum)

        polarity = nb.tongue_polarity()

        return HybridRepresentation(
            ternary_trits=tuple(t.value for t in bt.trits_msb),
            binary_bits=nb.bits_msb,
            ternary_int=bt.to_int(),
            binary_int=nb.to_int(),
            tongue_polarity=polarity,
        )

    def _decision_from_stages(
        self,
        gate_decision: str,
        lattice_valid: bool,
        chemistry_blocked: bool,
        threat_score: float,
        traversal_decision: str,
        defect_score: float,
    ) -> Decision:
        """Combine all stage signals into a single governance decision.

        DENY if any hard deny signal present.
        QUARANTINE if suspicious but not definitive.
        ALLOW only if all stages agree safe.
        """
        # Hard deny conditions
        if gate_decision == "DENY":
            return "DENY"
        if chemistry_blocked:
            return "DENY"
        if traversal_decision == "DENY":
            return "DENY"
        if threat_score > 0.85:
            return "DENY"

        # Quarantine conditions
        if gate_decision == "QUARANTINE":
            return "QUARANTINE"
        if not lattice_valid:
            return "QUARANTINE"
        if traversal_decision == "QUARANTINE":
            return "QUARANTINE"
        if defect_score > 0.5:
            return "QUARANTINE"
        if threat_score > 0.5:
            return "QUARANTINE"

        return "ALLOW"

    def _feedback_to_sphere(
        self,
        state_21d: List[float],
        tongue_trits: List[int],
        decision: str,
    ) -> None:
        """Deposit encoding result back onto the SphereGridNetwork.

        Places a 64-dim signal on the dominant tongue's sphere grid,
        encoding the governance decision and tongue trits into the signal.
        """
        if self._sphere_net is None or not _HAS_SPHERE:
            return

        # Find dominant tongue (highest absolute trit value, prefer first)
        dominant_idx = 0
        max_abs = 0
        for i, t in enumerate(tongue_trits):
            if abs(t) > max_abs:
                max_abs = abs(t)
                dominant_idx = i

        try:
            # Build a 64-dim signal encoding the result
            signal = np.zeros(64)
            # First 21 dims = state
            for i, v in enumerate(state_21d[:21]):
                signal[i] = v
            # Dims 21-26 = tongue trits
            for i, t in enumerate(tongue_trits[:6]):
                signal[21 + i] = float(t)
            # Dim 27 = decision encoding
            decision_val = {"ALLOW": 1.0, "QUARANTINE": 0.0, "DENY": -1.0}
            signal[27] = decision_val.get(decision, 0.0)

            # Pick a vertex on the dominant tongue's grid
            tongue_name = TONGUE_NAMES[dominant_idx]
            grid = self._sphere_net.grids.get(tongue_name)
            if grid is not None and len(grid.vertices) > 0:
                vertex_idx = self._encode_count % len(grid.vertices)
                grid.signals[vertex_idx] = signal
        except Exception:
            pass  # Non-critical feedback -- don't break the pipeline

    @property
    def encode_count(self) -> int:
        return self._encode_count

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return pipeline health diagnostics."""
        return {
            "encode_count": self._encode_count,
            "dual_ternary_history": self._dual_ternary.history_length,
            "hamiltonian_coverage": self._hamiltonian.coverage,
            "hamiltonian_unique": self._hamiltonian.unique_states_visited,
            "chemistry_state": self._chemistry.state.value,
            "chemistry_health": self._chemistry.health,
            "has_sphere_net": self._sphere_net is not None,
        }

    def reset(self) -> None:
        """Reset all stateful modules."""
        self._dual_ternary.reset()
        self._hamiltonian.reset()
        self._lattice.gate_history.clear()
        self._encode_count = 0
