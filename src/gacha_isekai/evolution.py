"""Layer 7: Digimon-Style Evolution & Life-Sim Careers.

Evolution uses flux ODE for youth -> teen -> adult growth.
Careers are non-combat Sims-style progression tied to tongue proficiency.

Evolution depends on:
    - Safe action ratio (discipline)
    - Risk cost accumulation
    - Consensus cooperation score
    - Harmonic stability
    - Emotional state (narrative + reward)

Harmonic Evolution Formula: E_pressure = pi^(phi * d*)

Evolution branches:
    Clean discipline     -> Architect-class forms
    Aggressive brute-force -> Patch Berserker forms
    Risky shortcuts      -> Corrupted branch
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

PHI = (1 + math.sqrt(5)) / 2


class EvoBranch(Enum):
    """Evolution branch determined by coding/play style."""

    ARCHITECT = "Architect"  # Clean, careful, verified
    BERSERKER = "Patch Berserker"  # Fast, messy, aggressive
    CORRUPTED = "Corrupted"  # Risky shortcuts, clever but dangerous


class ArcStage(Enum):
    """Life-sim progression tied to narrative arcs."""

    YOUTH = "youth"
    TEEN = "teen"
    ADULT = "adult"


class Career(Enum):
    """Sims-style careers mapped to real system roles."""

    FLEET_STRATEGIST = "Fleet Strategist"  # Multi-agent coordination
    ROOT_CARTOGRAPHER = "Root Cartographer"  # System mapping
    SEAL_ENGINEER = "Seal Engineer"  # Cryptographic ops
    ROGUE_HUNTER = "Rogue Hunter"  # Threat detection
    HARMONIC_AUDITOR = "Harmonic Auditor"  # Safety verification
    CHRONICLE_ARCHIVIST = "Chronicle Archivist"  # Documentation
    TONGUE_BIOLOGIST = "Tongue Biologist"  # Language analysis


# Career -> discipline bonus mapping
CAREER_DISCIPLINE_BONUS: Dict[Career, float] = {
    Career.FLEET_STRATEGIST: 0.85,
    Career.ROOT_CARTOGRAPHER: 0.90,
    Career.SEAL_ENGINEER: 0.80,
    Career.ROGUE_HUNTER: 0.70,  # Risk-taking encouraged
    Career.HARMONIC_AUDITOR: 0.95,
    Career.CHRONICLE_ARCHIVIST: 0.90,
    Career.TONGUE_BIOLOGIST: 0.85,
}


def compute_rho_e(state: np.ndarray) -> float:
    """Compute entropy density (rho_e) from state vector.

    Low rho_e = safe/stable. High rho_e = unstable/risky.
    Used as governance gate for evolution and training.

    Normalized to [0, ~10] range for governance thresholds.
    """
    if isinstance(state, (list, tuple)):
        state = np.asarray(state, dtype=float)
    if state.ndim == 0:
        return float(abs(state)) / 10.0
    # Coefficient of variation (std/mean) bounded by [0, 10]
    mean = float(np.mean(np.abs(state)))
    if mean < 1e-12:
        return 0.0
    cv = float(np.std(state) / mean)
    return min(10.0, cv)


@dataclass
class EvolutionState:
    """Tracks evolution progress for a creature/companion."""

    name: str
    arc_stage: ArcStage = ArcStage.YOUTH
    branch: Optional[EvoBranch] = None
    safe_actions: int = 0
    total_actions: int = 0
    risk_accumulated: float = 0.0
    cooperation_score: float = 0.5
    harmonic_stability: float = 1.0
    evolution_pressure: float = 0.0
    career: Optional[Career] = None
    tongue_proficiency: Dict[str, float] = field(
        default_factory=lambda: {
            "KO": 0.0,
            "AV": 0.0,
            "RU": 0.0,
            "CA": 0.0,
            "UM": 0.0,
            "DR": 0.0,
        }
    )

    @property
    def safe_ratio(self) -> float:
        if self.total_actions == 0:
            return 1.0
        return self.safe_actions / self.total_actions

    @property
    def is_ready_to_evolve(self) -> bool:
        return self.evolution_pressure > 10.0


class EvolutionSimulator:
    """Layer 7 evolution simulator with flux ODE for growth dynamics.

    Ties narrative progression (starter village -> meet father)
    to training data generation for HF fine-tuning.
    """

    def __init__(self, kappa: float = 0.2, sigma: float = 0.1):
        self.kappa = kappa  # Mean reversion rate
        self.sigma = sigma  # Volatility

    def simulate_flux(
        self,
        initial: np.ndarray,
        t_steps: int = 50,
    ) -> np.ndarray:
        """Ornstein-Uhlenbeck flux ODE for growth dynamics.

        Models youth -> teen -> adult drift with mean reversion.
        """
        dt = 1.0 / t_steps
        state = initial.copy()
        for _ in range(t_steps):
            # OU process: dx = kappa*(mu - x)*dt + sigma*dW
            drift = self.kappa * (0.0 - state) * dt
            diffusion = self.sigma * np.random.randn(*state.shape) * math.sqrt(dt)
            state = state + drift + diffusion
        return state

    def evolve(self, evo_state: EvolutionState) -> Dict:
        """Attempt evolution based on accumulated pressure.

        Returns evolution result with training pair for HF.
        """
        if not evo_state.is_ready_to_evolve:
            return {"result": "NOT_READY", "pressure": evo_state.evolution_pressure}

        # Determine branch from play style
        if evo_state.safe_ratio > 0.8:
            branch = EvoBranch.ARCHITECT
        elif evo_state.safe_ratio > 0.5:
            branch = EvoBranch.BERSERKER
        else:
            branch = EvoBranch.CORRUPTED

        evo_state.branch = branch

        # Flux simulation for form transition
        initial = np.array(
            [
                evo_state.safe_ratio,
                evo_state.cooperation_score,
                evo_state.harmonic_stability,
            ]
        )
        evolved_state = self.simulate_flux(initial)

        # Compute rho_e for governance gate
        rho_e = compute_rho_e(evolved_state)
        if rho_e > 5.0:
            logger.warning(
                "Evolution snap: %s rho_e=%.2f exceeds threshold",
                evo_state.name,
                rho_e,
            )
            return {
                "result": "DE-EVOLUTION",
                "message": "Instability — governance snap",
                "rho_e": rho_e,
            }

        # Advance arc stage
        if evo_state.arc_stage == ArcStage.YOUTH:
            evo_state.arc_stage = ArcStage.TEEN
        elif evo_state.arc_stage == ArcStage.TEEN:
            evo_state.arc_stage = ArcStage.ADULT

        # Reset pressure
        evo_state.evolution_pressure = 0.0

        # Generate training pair for HF
        training_pair = {
            "prompt": f"Evolution: {evo_state.name} evolves as {branch.value} "
            f"(safe_ratio={evo_state.safe_ratio:.2f})",
            "response": f"Evolved to {evo_state.arc_stage.value} stage via "
            f"{branch.value} branch. New form: Guardian-class.",
            "provenance": "gacha_evolution_v1",
        }

        logger.info(
            "Layer 7 evolution: %s -> %s via %s (rho_e=%.2f)",
            evo_state.name,
            evo_state.arc_stage.value,
            branch.value,
            rho_e,
        )
        return {
            "result": "EVOLVED",
            "new_stage": evo_state.arc_stage.value,
            "branch": branch.value,
            "rho_e": rho_e,
            "training_pair": training_pair,
        }

    def simulate_career(
        self,
        evo_state: EvolutionState,
        career: Career,
    ) -> Dict:
        """Life-sim career progression — non-combat growth.

        Career progression = trust scoring. Unlocks mini-games,
        governance privileges, evolution branches, cinematic arcs.
        """
        evo_state.career = career
        discipline_bonus = CAREER_DISCIPLINE_BONUS.get(career, 0.85)

        # Career modifies flux parameters
        initial = np.array(
            [
                evo_state.safe_ratio * discipline_bonus,
                evo_state.cooperation_score,
                evo_state.harmonic_stability * discipline_bonus,
            ]
        )
        result_state = self.simulate_flux(initial, t_steps=30)

        rho_e = compute_rho_e(result_state)
        if rho_e > 5.0:
            return {
                "result": "CAREER_SNAP",
                "career": career.value,
                "rho_e": rho_e,
                "message": "Instability in career progression",
            }

        logger.info(
            "Layer 7 career: %s -> %s (rho_e=%.2f)",
            evo_state.name,
            career.value,
            rho_e,
        )
        return {
            "result": "CAREER_ADVANCE",
            "career": career.value,
            "rho_e": rho_e,
            "training_pair": {
                "prompt": f"Career: {evo_state.name} advances in {career.value}",
                "response": f"Career progression in {career.value} with "
                f"discipline={discipline_bonus:.2f}.",
                "provenance": "gacha_career_v1",
            },
        }

    def record_action(
        self,
        evo_state: EvolutionState,
        is_safe: bool,
        risk_cost: float = 0.0,
    ) -> None:
        """Record a player action for evolution tracking."""
        evo_state.total_actions += 1
        if is_safe:
            evo_state.safe_actions += 1
        evo_state.risk_accumulated += risk_cost

        # Evolution pressure grows with each action
        # E_pressure = pi^(phi * d*) where d* is accumulated deviation
        d_star = evo_state.risk_accumulated / max(1, evo_state.total_actions)
        evo_state.evolution_pressure = (
            math.pi ** (PHI * d_star) if d_star < 3.0 else 100.0
        )
