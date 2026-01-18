"""
Chemistry-Inspired Defensive Agent

Implements immune system-like threat response with:
- Squared-input energy release (like kinetic energy ½mv²)
- Ray refraction defense (phase-shift deflection)
- Self-healing harmonics (chemical equilibrium)
- Antibody wave propagation (StarCraft AI meets immune system)

The key insight: Small legitimate inputs remain stable;
large malicious inputs trigger exponential energy release
that modulates defense variables.

Document ID: EDE-CHEM-2026-001
Version: 1.0.0
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Callable
from enum import Enum

# Import AETHERMOORE constants
from ..constants import (
    PHI, R_FIFTH, harmonic_scale, DEFAULT_R,
)


# =============================================================================
# CONSTANTS
# =============================================================================

# Threat levels (1-10 scale)
THREAT_LEVEL_MIN = 1
THREAT_LEVEL_MAX = 10
DEFAULT_THREAT_LEVEL = 5

# Defense parameters
REFRACTION_BASE = 0.8              # Max refraction coefficient
ANTIBODY_EFFICIENCY_BASE = 1.5     # Base antibody kill rate
ANTIBODY_EFFICIENCY_BOOST = 0.1    # Boost per threat level
HEALING_RATE = 0.1                 # Self-healing per step
ENERGY_DECAY = 0.05                # Energy dissipation per step

# Wave propagation
MALICIOUS_SPAWN_RATE = 0.5         # Base spawn rate
MALICIOUS_SQUARED_FACTOR = 0.1     # Squared growth coefficient
ANTIBODY_RESPONSE_DELAY = 2        # Steps before antibody response


class AgentState(Enum):
    """Chemistry agent states."""
    DORMANT = "dormant"
    MONITORING = "monitoring"
    RESPONDING = "responding"
    COMBAT = "combat"
    RECOVERING = "recovering"


class ThreatType(Enum):
    """Types of threats."""
    NORMAL = "normal"
    MALICIOUS = "malicious"
    INJECTION = "injection"
    OVERFLOW = "overflow"
    REPLAY = "replay"


# =============================================================================
# SQUARED-INPUT ENERGY MODEL
# =============================================================================

def squared_energy(input_value: float) -> float:
    """
    Calculate energy using squared-input model.

    Like kinetic energy (½mv²), input values are squared to model
    chemical reaction rates. Small inputs = stable; large inputs =
    exponential energy release.

    energy = log(1 + input²)

    Args:
        input_value: Input magnitude

    Returns:
        Energy value (logarithmic scaling prevents overflow)
    """
    return math.log(1 + input_value ** 2)


def reaction_rate(
    concentration_a: float,
    concentration_b: float,
    temperature: float = 1.0
) -> float:
    """
    Calculate reaction rate using mass action kinetics.

    rate = k * [A] * [B] * exp(-Ea/T)

    Args:
        concentration_a: First reactant concentration
        concentration_b: Second reactant concentration
        temperature: System temperature (activity level)

    Returns:
        Reaction rate
    """
    k = R_FIFTH  # Rate constant from harmonic ratio
    activation_energy = 1.0 / PHI  # Activation energy

    rate = k * concentration_a * concentration_b
    rate *= math.exp(-activation_energy / max(temperature, 0.01))

    return rate


# =============================================================================
# RAY REFRACTION DEFENSE
# =============================================================================

def ray_refraction(
    value: float,
    threat_level: int,
    max_refraction: float = REFRACTION_BASE
) -> float:
    """
    Apply ray refraction defense.

    Phase-shift deflection on malicious trajectories. Higher threat
    levels increase refraction strength, bending attack "rays" away
    from the system core into harmonic sinks.

    deflected = value × (1 - level/10 × max_refraction)

    Args:
        value: Incoming value/trajectory
        threat_level: Current threat level (1-10)
        max_refraction: Maximum refraction coefficient

    Returns:
        Deflected value
    """
    refraction_strength = (threat_level / THREAT_LEVEL_MAX) * max_refraction
    return value * (1 - refraction_strength)


def harmonic_sink(
    value: float,
    sink_depth: int = 3
) -> float:
    """
    Absorb energy into a harmonic sink.

    Uses AETHERMOORE harmonic scaling to create exponentially
    deep energy sinks.

    Args:
        value: Energy to absorb
        sink_depth: Sink dimension (1-6)

    Returns:
        Absorbed (reduced) energy
    """
    h_scale = harmonic_scale(sink_depth, R_FIFTH)
    return value / h_scale


# =============================================================================
# SELF-HEALING HARMONICS
# =============================================================================

def self_heal(
    current_health: float,
    target_health: float,
    healing_rate: float = HEALING_RATE
) -> float:
    """
    Apply self-healing using chemical equilibrium.

    Like Le Chatelier's principle, the system re-centers
    disturbed trajectories toward equilibrium.

    Args:
        current_health: Current health value
        target_health: Target (equilibrium) health
        healing_rate: Healing rate per step

    Returns:
        New health value
    """
    delta = target_health - current_health
    return current_health + delta * healing_rate


def equilibrium_force(
    position: float,
    equilibrium: float,
    spring_constant: float = 1.0
) -> float:
    """
    Calculate restoring force toward equilibrium.

    F = -k(x - x_eq)

    Args:
        position: Current position
        equilibrium: Equilibrium position
        spring_constant: Spring constant (stiffness)

    Returns:
        Restoring force
    """
    return -spring_constant * (position - equilibrium)


# =============================================================================
# ANTIBODY WAVE PROPAGATION
# =============================================================================

@dataclass
class Unit:
    """A unit in the propagation simulation (malicious or antibody)."""
    id: int
    unit_type: str  # "malicious" or "antibody"
    strength: float
    position: Tuple[float, float]
    velocity: Tuple[float, float] = (0.0, 0.0)
    alive: bool = True
    spawn_time: int = 0

    def move(self, dt: float = 1.0) -> None:
        """Move unit by velocity * dt."""
        self.position = (
            self.position[0] + self.velocity[0] * dt,
            self.position[1] + self.velocity[1] * dt
        )

    def distance_to(self, other: 'Unit') -> float:
        """Calculate distance to another unit."""
        dx = self.position[0] - other.position[0]
        dy = self.position[1] - other.position[1]
        return math.sqrt(dx**2 + dy**2)


@dataclass
class WaveSimulation:
    """
    Unit propagation wave simulation.

    Inspired by StarCraft AI and immune systems. Malicious "units"
    spawn in waves (squared growth); antibody "units" counter-propagate.
    """
    threat_level: int
    step: int = 0
    malicious_units: List[Unit] = field(default_factory=list)
    antibody_units: List[Unit] = field(default_factory=list)
    neutralized: List[Unit] = field(default_factory=list)
    unit_counter: int = 0
    health: float = 100.0
    max_health: float = 100.0

    # Metrics
    total_malicious_spawned: float = 0.0
    total_antibodies_spawned: float = 0.0
    total_neutralized: float = 0.0

    def spawn_malicious(self, count: float = 1.0) -> None:
        """Spawn malicious units with squared growth."""
        # Squared growth based on threat level
        growth_factor = 1 + (self.threat_level / 10) ** 2 * MALICIOUS_SQUARED_FACTOR
        actual_count = count * growth_factor

        for _ in range(int(actual_count)):
            self.unit_counter += 1
            unit = Unit(
                id=self.unit_counter,
                unit_type="malicious",
                strength=random.uniform(0.5, 1.5),
                position=(random.uniform(-10, 10), random.uniform(-10, 10)),
                velocity=(random.uniform(-1, 1), random.uniform(-1, 1)),
                spawn_time=self.step
            )
            self.malicious_units.append(unit)
            self.total_malicious_spawned += 1

    def spawn_antibodies(self, count: float = 1.0) -> None:
        """Spawn antibody units in response to threat."""
        # Antibodies get efficiency boost at higher threat levels
        efficiency = ANTIBODY_EFFICIENCY_BASE + self.threat_level * ANTIBODY_EFFICIENCY_BOOST

        for _ in range(int(count)):
            self.unit_counter += 1
            unit = Unit(
                id=self.unit_counter,
                unit_type="antibody",
                strength=efficiency,
                position=(0, 0),  # Spawn from center
                velocity=(random.uniform(-2, 2), random.uniform(-2, 2)),
                spawn_time=self.step
            )
            self.antibody_units.append(unit)
            self.total_antibodies_spawned += 1

    def step_simulation(self) -> Dict[str, float]:
        """
        Advance simulation by one step.

        Returns:
            Step metrics
        """
        self.step += 1

        # Move all units
        for unit in self.malicious_units + self.antibody_units:
            if unit.alive:
                unit.move()

        # Antibody-malicious interactions
        neutralized_this_step = 0.0
        for ab in self.antibody_units:
            if not ab.alive:
                continue

            for mal in self.malicious_units:
                if not mal.alive:
                    continue

                dist = ab.distance_to(mal)
                if dist < 1.5:  # Interaction range
                    # Neutralization: antibody kills malicious
                    neutralize_power = ab.strength * (1.5 + self.threat_level / 10)
                    if neutralize_power >= mal.strength:
                        mal.alive = False
                        self.neutralized.append(mal)
                        neutralized_this_step += 1
                        self.total_neutralized += 1

        # Remove dead units
        self.malicious_units = [u for u in self.malicious_units if u.alive]
        self.antibody_units = [u for u in self.antibody_units if u.alive]

        # Calculate health impact
        damage = len(self.malicious_units) * 0.1 * (self.threat_level / 5)
        self.health = max(0, self.health - damage)

        # Self-healing
        self.health = self_heal(self.health, self.max_health)

        return {
            "step": self.step,
            "malicious_count": len(self.malicious_units),
            "antibody_count": len(self.antibody_units),
            "neutralized_this_step": neutralized_this_step,
            "health": self.health,
        }

    def run_wave(
        self,
        steps: int = 100,
        spawn_interval: int = 5
    ) -> List[Dict[str, float]]:
        """
        Run a complete wave simulation.

        Args:
            steps: Number of simulation steps
            spawn_interval: Steps between spawns

        Returns:
            List of step metrics
        """
        metrics = []

        for _ in range(steps):
            # Spawn malicious units periodically
            if self.step % spawn_interval == 0:
                self.spawn_malicious(MALICIOUS_SPAWN_RATE * self.threat_level)

            # Delayed antibody response
            if self.step > ANTIBODY_RESPONSE_DELAY and self.step % spawn_interval == 0:
                self.spawn_antibodies(len(self.malicious_units) * 0.5)

            step_metrics = self.step_simulation()
            metrics.append(step_metrics)

        return metrics

    def get_final_metrics(self) -> Dict[str, Any]:
        """Get final simulation metrics."""
        propagation_success = (
            self.total_malicious_spawned - self.total_neutralized
        ) / max(1, self.total_malicious_spawned)

        detection_rate = self.total_neutralized / max(1, self.total_malicious_spawned)

        return {
            "threat_level": self.threat_level,
            "total_steps": self.step,
            "total_malicious_spawned": self.total_malicious_spawned,
            "total_antibodies_spawned": self.total_antibodies_spawned,
            "total_neutralized": self.total_neutralized,
            "remaining_malicious": len(self.malicious_units),
            "remaining_antibodies": len(self.antibody_units),
            "final_health": self.health,
            "propagation_success_rate": propagation_success,
            "detection_rate": detection_rate,
            "system_stability": self.health / self.max_health,
            "antibody_efficiency": (
                self.total_neutralized / max(1, self.total_antibodies_spawned)
            ),
        }


# =============================================================================
# CHEMISTRY AGENT
# =============================================================================

@dataclass
class ChemistryAgent:
    """
    Chemistry-inspired defensive agent.

    Combines squared-input reactions, ray refraction, and
    self-healing harmonics for adaptive threat response.
    """
    agent_id: str
    threat_level: int = DEFAULT_THREAT_LEVEL
    state: AgentState = AgentState.DORMANT
    health: float = 100.0
    max_health: float = 100.0
    energy_pool: float = 100.0
    max_energy: float = 100.0

    # Defense state
    active_deflections: int = 0
    total_threats_blocked: int = 0
    reaction_history: List[Dict[str, Any]] = field(default_factory=list)

    def activate(self) -> None:
        """Activate the agent."""
        self.state = AgentState.MONITORING

    def deactivate(self) -> None:
        """Deactivate the agent."""
        self.state = AgentState.DORMANT

    def set_threat_level(self, level: int) -> None:
        """Set current threat level (1-10)."""
        self.threat_level = max(THREAT_LEVEL_MIN, min(THREAT_LEVEL_MAX, level))

        # Update state based on threat level
        if level >= 8:
            self.state = AgentState.COMBAT
        elif level >= 5:
            self.state = AgentState.RESPONDING
        elif level >= 2:
            self.state = AgentState.MONITORING
        else:
            self.state = AgentState.RECOVERING

    def process_input(
        self,
        input_value: float,
        threat_type: ThreatType = ThreatType.NORMAL
    ) -> Tuple[float, bool]:
        """
        Process an input through the defense system.

        Args:
            input_value: Incoming input magnitude
            threat_type: Type of threat

        Returns:
            (processed_value, was_blocked)
        """
        # Calculate energy from input
        energy = squared_energy(abs(input_value))

        # Record reaction
        reaction = {
            "timestamp": time.time(),
            "input": input_value,
            "energy": energy,
            "threat_type": threat_type.value,
            "threat_level": self.threat_level,
        }

        # Determine if blocking is needed
        energy_threshold = 5.0 - (self.threat_level * 0.3)
        is_threat = energy > energy_threshold or threat_type != ThreatType.NORMAL

        if is_threat:
            # Apply ray refraction
            deflected = ray_refraction(input_value, self.threat_level)

            # Absorb remaining energy
            remaining = harmonic_sink(abs(deflected), min(6, self.threat_level))

            # Consume energy for defense
            defense_cost = energy * 0.1
            self.energy_pool = max(0, self.energy_pool - defense_cost)

            self.active_deflections += 1
            self.total_threats_blocked += 1

            reaction["blocked"] = True
            reaction["deflected_to"] = remaining

            self.reaction_history.append(reaction)
            return remaining, True

        # Normal processing
        reaction["blocked"] = False
        self.reaction_history.append(reaction)
        return input_value, False

    def run_simulation(
        self,
        steps: int = 100
    ) -> WaveSimulation:
        """
        Run a wave propagation simulation.

        Args:
            steps: Number of simulation steps

        Returns:
            Completed WaveSimulation
        """
        sim = WaveSimulation(threat_level=self.threat_level)
        sim.run_wave(steps)
        return sim

    def heal(self) -> None:
        """Apply self-healing."""
        self.health = self_heal(self.health, self.max_health)
        self.energy_pool = self_heal(self.energy_pool, self.max_energy, healing_rate=0.05)

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "threat_level": self.threat_level,
            "health": self.health,
            "health_percent": self.health / self.max_health * 100,
            "energy_pool": self.energy_pool,
            "energy_percent": self.energy_pool / self.max_energy * 100,
            "active_deflections": self.active_deflections,
            "total_threats_blocked": self.total_threats_blocked,
            "recent_reactions": len(self.reaction_history),
        }


# =============================================================================
# QUICK FUNCTIONS
# =============================================================================

def quick_defense_check(
    input_value: float,
    threat_level: int = DEFAULT_THREAT_LEVEL
) -> Tuple[float, bool, float]:
    """
    Quick check if input should be blocked.

    Args:
        input_value: Input to check
        threat_level: Current threat level

    Returns:
        (processed_value, was_blocked, energy)
    """
    energy = squared_energy(abs(input_value))
    threshold = 5.0 - (threat_level * 0.3)

    if energy > threshold:
        deflected = ray_refraction(input_value, threat_level)
        absorbed = harmonic_sink(abs(deflected), min(6, threat_level))
        return absorbed, True, energy

    return input_value, False, energy


def run_threat_simulation(
    threat_level: int = 5,
    steps: int = 100
) -> Dict[str, Any]:
    """
    Run a quick threat simulation.

    Args:
        threat_level: Threat level (1-10)
        steps: Simulation steps

    Returns:
        Simulation metrics
    """
    sim = WaveSimulation(threat_level=threat_level)
    sim.run_wave(steps)
    return sim.get_final_metrics()
