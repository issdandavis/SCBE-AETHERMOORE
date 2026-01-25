#!/usr/bin/env python3
"""
Physics Simulator - Unified Time Evolution Engine

A comprehensive physics simulation engine that integrates all modules
for realistic time-based simulations:
- N-body gravitational systems
- Projectile motion with drag
- Orbital mechanics
- Coupled oscillators
- Electromagnetic systems
- Thermal diffusion

Supports multiple integration methods and event handling.
"""

import math
from typing import Dict, Any, Tuple, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

# Import numerical methods
from .numerical import (
    euler_step,
    rk4_step,
    verlet_step,
    leapfrog_step,
    vec_add,
    vec_sub,
    vec_scale,
    vec_norm,
    vec_cross_3d,
    vec_dot,
)

# =============================================================================
# CONSTANTS
# =============================================================================

G = 6.67430e-11  # Gravitational constant (m³/(kg·s²))
C = 299792458  # Speed of light (m/s)
EARTH_MASS = 5.972e24  # kg
EARTH_RADIUS = 6.371e6  # m
SUN_MASS = 1.989e30  # kg
AU = 1.495978707e11  # m


# =============================================================================
# SIMULATION CONFIGURATION
# =============================================================================


class IntegrationMethod(Enum):
    """Available integration methods."""

    EULER = "euler"
    RK4 = "rk4"
    VERLET = "verlet"
    LEAPFROG = "leapfrog"


@dataclass
class SimulationConfig:
    """Configuration for physics simulation."""

    dt: float = 0.01  # Time step (s)
    t_max: float = 10.0  # Maximum simulation time (s)
    method: IntegrationMethod = IntegrationMethod.RK4
    adaptive_step: bool = False
    tolerance: float = 1e-6
    max_iterations: int = 1000000
    save_interval: int = 1  # Save every N steps
    enable_collisions: bool = True
    boundary_mode: str = "none"  # "none", "reflect", "periodic"
    boundary_size: Optional[List[float]] = None


# =============================================================================
# PARTICLE / BODY CLASSES
# =============================================================================


@dataclass
class Particle:
    """A point particle for simulations."""

    mass: float
    position: List[float]
    velocity: List[float]
    name: str = ""
    charge: float = 0.0
    radius: float = 0.0
    fixed: bool = False
    acceleration: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    force: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])

    def kinetic_energy(self) -> float:
        """Calculate kinetic energy."""
        v_sq = sum(v**2 for v in self.velocity)
        return 0.5 * self.mass * v_sq

    def momentum(self) -> List[float]:
        """Calculate momentum vector."""
        return [self.mass * v for v in self.velocity]

    def update_acceleration(self) -> None:
        """Update acceleration from force."""
        if not self.fixed and self.mass > 0:
            self.acceleration = [f / self.mass for f in self.force]


@dataclass
class Spring:
    """A spring connecting two particles."""

    particle1_idx: int
    particle2_idx: int
    k: float  # Spring constant (N/m)
    rest_length: float  # Equilibrium length (m)
    damping: float = 0.0


# =============================================================================
# FORCE CALCULATORS
# =============================================================================


class ForceCalculator:
    """Base class for force calculators."""

    def calculate(self, particles: List[Particle], t: float) -> None:
        """Calculate and apply forces to all particles."""
        raise NotImplementedError


class GravityCalculator(ForceCalculator):
    """N-body gravitational force calculator."""

    def __init__(self, G: float = 6.67430e-11, softening: float = 0.0):
        self.G = G
        self.softening = softening  # Softening parameter to avoid singularity

    def calculate(self, particles: List[Particle], t: float) -> None:
        """Calculate gravitational forces between all pairs."""
        n = len(particles)

        for i in range(n):
            for j in range(i + 1, n):
                p1, p2 = particles[i], particles[j]

                # Displacement vector
                r = vec_sub(p2.position, p1.position)
                r_mag = vec_norm(r)

                # Add softening
                r_soft = math.sqrt(r_mag**2 + self.softening**2)

                if r_soft < 1e-10:
                    continue

                # Force magnitude
                F_mag = self.G * p1.mass * p2.mass / (r_soft**2)

                # Force direction (unit vector)
                r_hat = vec_scale(r, 1 / r_mag) if r_mag > 1e-10 else [0, 0, 0]

                # Apply forces (Newton's 3rd law)
                F = vec_scale(r_hat, F_mag)
                p1.force = vec_add(p1.force, F)
                p2.force = vec_sub(p2.force, F)


class UniformGravityCalculator(ForceCalculator):
    """Uniform gravitational field (e.g., near Earth's surface)."""

    def __init__(self, g: List[float] = None):
        self.g = g or [0.0, -9.80665, 0.0]

    def calculate(self, particles: List[Particle], t: float) -> None:
        for p in particles:
            F_grav = vec_scale(self.g, p.mass)
            p.force = vec_add(p.force, F_grav)


class DragCalculator(ForceCalculator):
    """Aerodynamic drag force calculator."""

    def __init__(self, density: float = 1.225, Cd: float = 0.47):
        self.density = density  # Air density (kg/m³)
        self.Cd = Cd  # Drag coefficient

    def calculate(self, particles: List[Particle], t: float) -> None:
        for p in particles:
            v_mag = vec_norm(p.velocity)
            if v_mag < 1e-10:
                continue

            # F_drag = -½ρCdAv² (opposite to velocity)
            # Using cross-sectional area A = πr²
            A = math.pi * p.radius**2 if p.radius > 0 else 0.01
            F_mag = 0.5 * self.density * self.Cd * A * v_mag**2

            # Direction opposite to velocity
            v_hat = vec_scale(p.velocity, -1 / v_mag)
            F_drag = vec_scale(v_hat, F_mag)
            p.force = vec_add(p.force, F_drag)


class SpringCalculator(ForceCalculator):
    """Spring force calculator for connected particles."""

    def __init__(self, springs: List[Spring]):
        self.springs = springs

    def calculate(self, particles: List[Particle], t: float) -> None:
        for spring in self.springs:
            p1 = particles[spring.particle1_idx]
            p2 = particles[spring.particle2_idx]

            # Displacement vector
            r = vec_sub(p2.position, p1.position)
            r_mag = vec_norm(r)

            if r_mag < 1e-10:
                continue

            # Spring extension
            extension = r_mag - spring.rest_length

            # Hooke's law: F = -k*x
            F_mag = spring.k * extension

            # Direction
            r_hat = vec_scale(r, 1 / r_mag)

            # Spring force on p1 (towards p2 if stretched)
            F_spring = vec_scale(r_hat, F_mag)
            p1.force = vec_add(p1.force, F_spring)
            p2.force = vec_sub(p2.force, F_spring)

            # Damping
            if spring.damping > 0:
                v_rel = vec_sub(p2.velocity, p1.velocity)
                v_along_spring = vec_dot(v_rel, r_hat)
                F_damp_mag = spring.damping * v_along_spring
                F_damp = vec_scale(r_hat, F_damp_mag)
                p1.force = vec_add(p1.force, F_damp)
                p2.force = vec_sub(p2.force, F_damp)


class ElectrostaticCalculator(ForceCalculator):
    """Coulomb electrostatic force calculator."""

    def __init__(self, k: float = 8.9875517923e9):
        self.k = k  # Coulomb's constant

    def calculate(self, particles: List[Particle], t: float) -> None:
        n = len(particles)

        for i in range(n):
            for j in range(i + 1, n):
                p1, p2 = particles[i], particles[j]

                if p1.charge == 0 or p2.charge == 0:
                    continue

                # Displacement vector
                r = vec_sub(p2.position, p1.position)
                r_mag = vec_norm(r)

                if r_mag < 1e-10:
                    continue

                # Coulomb force: F = kq1q2/r²
                F_mag = self.k * p1.charge * p2.charge / (r_mag**2)

                r_hat = vec_scale(r, 1 / r_mag)
                F = vec_scale(r_hat, F_mag)

                # Like charges repel (F_mag > 0 pushes apart)
                # Unlike charges attract (F_mag < 0 pulls together)
                p1.force = vec_sub(p1.force, F)
                p2.force = vec_add(p2.force, F)


class CentralForceCalculator(ForceCalculator):
    """Central force field (e.g., for orbital mechanics)."""

    def __init__(self, center: List[float], mass: float, G: float = 6.67430e-11):
        self.center = center
        self.mass = mass
        self.G = G
        self.mu = G * mass  # Gravitational parameter

    def calculate(self, particles: List[Particle], t: float) -> None:
        for p in particles:
            r = vec_sub(p.position, self.center)
            r_mag = vec_norm(r)

            if r_mag < 1e-10:
                continue

            # F = -GMm/r² (attractive)
            F_mag = self.G * self.mass * p.mass / (r_mag**2)

            r_hat = vec_scale(r, 1 / r_mag)
            F = vec_scale(r_hat, -F_mag)
            p.force = vec_add(p.force, F)


# =============================================================================
# PHYSICS SIMULATOR
# =============================================================================


class PhysicsSimulator:
    """
    Main physics simulation engine.

    Integrates particle dynamics with various force models.
    """

    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()
        self.particles: List[Particle] = []
        self.force_calculators: List[ForceCalculator] = []
        self.time: float = 0.0
        self.step_count: int = 0
        self.history: List[Dict[str, Any]] = []
        self.event_handlers: List[Callable] = []

    def add_particle(self, particle: Particle) -> int:
        """Add a particle and return its index."""
        self.particles.append(particle)
        return len(self.particles) - 1

    def add_force_calculator(self, calculator: ForceCalculator) -> None:
        """Add a force calculator."""
        self.force_calculators.append(calculator)

    def add_event_handler(self, handler: Callable) -> None:
        """Add an event handler called each step."""
        self.event_handlers.append(handler)

    def reset_forces(self) -> None:
        """Reset all particle forces to zero."""
        for p in self.particles:
            p.force = [0.0, 0.0, 0.0]

    def calculate_forces(self) -> None:
        """Calculate all forces on particles."""
        self.reset_forces()
        for calculator in self.force_calculators:
            calculator.calculate(self.particles, self.time)
        for p in self.particles:
            p.update_acceleration()

    def get_state(self) -> List[float]:
        """Get flattened state vector [x1, y1, z1, vx1, vy1, vz1, ...]."""
        state = []
        for p in self.particles:
            state.extend(p.position)
            state.extend(p.velocity)
        return state

    def set_state(self, state: List[float]) -> None:
        """Set state from flattened vector."""
        idx = 0
        for p in self.particles:
            p.position = list(state[idx : idx + 3])
            p.velocity = list(state[idx + 3 : idx + 6])
            idx += 6

    def derivative(self, t: float, state: List[float]) -> List[float]:
        """Calculate state derivative for ODE solver."""
        # Temporarily set state
        old_state = self.get_state()
        self.set_state(state)

        # Calculate forces
        self.calculate_forces()

        # Build derivative [vx1, vy1, vz1, ax1, ay1, az1, ...]
        deriv = []
        for p in self.particles:
            deriv.extend(p.velocity)
            deriv.extend(p.acceleration)

        # Restore state
        self.set_state(old_state)
        return deriv

    def step(self) -> None:
        """Perform one simulation step."""
        dt = self.config.dt

        if self.config.method == IntegrationMethod.EULER:
            state = self.get_state()
            new_state = euler_step(self.derivative, self.time, state, dt)
            self.set_state(new_state)

        elif self.config.method == IntegrationMethod.RK4:
            state = self.get_state()
            new_state = rk4_step(self.derivative, self.time, state, dt)
            self.set_state(new_state)

        elif self.config.method == IntegrationMethod.VERLET:
            # Velocity Verlet
            self.calculate_forces()

            for p in self.particles:
                if p.fixed:
                    continue
                # Update position
                p.position = vec_add(
                    vec_add(p.position, vec_scale(p.velocity, dt)),
                    vec_scale(p.acceleration, dt**2 / 2),
                )

            # Calculate new forces
            old_acc = [p.acceleration[:] for p in self.particles]
            self.calculate_forces()

            # Update velocity
            for i, p in enumerate(self.particles):
                if p.fixed:
                    continue
                avg_acc = vec_scale(vec_add(old_acc[i], p.acceleration), 0.5)
                p.velocity = vec_add(p.velocity, vec_scale(avg_acc, dt))

        elif self.config.method == IntegrationMethod.LEAPFROG:
            # Similar to Verlet with half-step velocity
            self.calculate_forces()

            for p in self.particles:
                if p.fixed:
                    continue
                # Half velocity update
                p.velocity = vec_add(p.velocity, vec_scale(p.acceleration, dt / 2))
                # Full position update
                p.position = vec_add(p.position, vec_scale(p.velocity, dt))

            # Recalculate forces at new position
            self.calculate_forces()

            for p in self.particles:
                if p.fixed:
                    continue
                # Remaining half velocity update
                p.velocity = vec_add(p.velocity, vec_scale(p.acceleration, dt / 2))

        self.time += dt
        self.step_count += 1

        # Handle collisions
        if self.config.enable_collisions:
            self._handle_collisions()

        # Handle boundaries
        if self.config.boundary_mode != "none" and self.config.boundary_size:
            self._handle_boundaries()

        # Call event handlers
        for handler in self.event_handlers:
            handler(self)

        # Save history
        if self.step_count % self.config.save_interval == 0:
            self._save_state()

    def _handle_collisions(self) -> None:
        """Simple elastic collision detection and response."""
        n = len(self.particles)
        for i in range(n):
            for j in range(i + 1, n):
                p1, p2 = self.particles[i], self.particles[j]

                if p1.radius == 0 or p2.radius == 0:
                    continue

                r = vec_sub(p2.position, p1.position)
                r_mag = vec_norm(r)
                min_dist = p1.radius + p2.radius

                if r_mag < min_dist and r_mag > 0:
                    # Collision detected - elastic collision
                    r_hat = vec_scale(r, 1 / r_mag)

                    # Relative velocity along collision normal
                    v_rel = vec_sub(p2.velocity, p1.velocity)
                    v_rel_n = vec_dot(v_rel, r_hat)

                    # Only process if approaching
                    if v_rel_n < 0:
                        # Conservation of momentum + kinetic energy
                        m1, m2 = p1.mass, p2.mass
                        factor = 2 * v_rel_n / (m1 + m2)

                        if not p1.fixed:
                            dv1 = vec_scale(r_hat, factor * m2)
                            p1.velocity = vec_add(p1.velocity, dv1)

                        if not p2.fixed:
                            dv2 = vec_scale(r_hat, -factor * m1)
                            p2.velocity = vec_add(p2.velocity, dv2)

                    # Separate overlapping particles
                    overlap = min_dist - r_mag
                    if not p1.fixed and not p2.fixed:
                        sep = vec_scale(r_hat, overlap / 2)
                        p1.position = vec_sub(p1.position, sep)
                        p2.position = vec_add(p2.position, sep)
                    elif not p1.fixed:
                        p1.position = vec_sub(p1.position, vec_scale(r_hat, overlap))
                    elif not p2.fixed:
                        p2.position = vec_add(p2.position, vec_scale(r_hat, overlap))

    def _handle_boundaries(self) -> None:
        """Handle boundary conditions."""
        bounds = self.config.boundary_size

        for p in self.particles:
            if p.fixed:
                continue

            for dim in range(min(3, len(bounds))):
                if self.config.boundary_mode == "reflect":
                    if p.position[dim] < -bounds[dim]:
                        p.position[dim] = -bounds[dim]
                        p.velocity[dim] = abs(p.velocity[dim])
                    elif p.position[dim] > bounds[dim]:
                        p.position[dim] = bounds[dim]
                        p.velocity[dim] = -abs(p.velocity[dim])

                elif self.config.boundary_mode == "periodic":
                    if p.position[dim] < -bounds[dim]:
                        p.position[dim] += 2 * bounds[dim]
                    elif p.position[dim] > bounds[dim]:
                        p.position[dim] -= 2 * bounds[dim]

    def _save_state(self) -> None:
        """Save current state to history."""
        state = {
            "time": self.time,
            "step": self.step_count,
            "particles": [
                {
                    "name": p.name,
                    "position": p.position[:],
                    "velocity": p.velocity[:],
                    "kinetic_energy": p.kinetic_energy(),
                }
                for p in self.particles
            ],
        }
        self.history.append(state)

    def run(self, t_max: float = None) -> List[Dict[str, Any]]:
        """
        Run simulation until t_max.

        Args:
            t_max: Maximum simulation time (uses config if not provided)

        Returns:
            Simulation history
        """
        t_max = t_max or self.config.t_max

        while self.time < t_max and self.step_count < self.config.max_iterations:
            self.step()

        return self.history

    def total_energy(self) -> Tuple[float, float, float]:
        """
        Calculate total system energy.

        Returns:
            Tuple of (kinetic, potential, total) energy
        """
        kinetic = sum(p.kinetic_energy() for p in self.particles)

        # Gravitational potential energy (if using gravity)
        potential = 0.0
        for i, calc in enumerate(self.force_calculators):
            if isinstance(calc, GravityCalculator):
                n = len(self.particles)
                for i in range(n):
                    for j in range(i + 1, n):
                        p1, p2 = self.particles[i], self.particles[j]
                        r = vec_norm(vec_sub(p2.position, p1.position))
                        if r > 0:
                            potential -= calc.G * p1.mass * p2.mass / r

        return kinetic, potential, kinetic + potential

    def total_momentum(self) -> List[float]:
        """Calculate total system momentum."""
        total = [0.0, 0.0, 0.0]
        for p in self.particles:
            total = vec_add(total, p.momentum())
        return total

    def center_of_mass(self) -> List[float]:
        """Calculate center of mass position."""
        total_mass = sum(p.mass for p in self.particles)
        if total_mass == 0:
            return [0.0, 0.0, 0.0]

        com = [0.0, 0.0, 0.0]
        for p in self.particles:
            weighted = vec_scale(p.position, p.mass)
            com = vec_add(com, weighted)

        return vec_scale(com, 1 / total_mass)


# =============================================================================
# PRESET SIMULATIONS
# =============================================================================


def create_projectile_simulation(
    v0: float, angle_deg: float, height: float = 0, with_drag: bool = False
) -> PhysicsSimulator:
    """
    Create a projectile motion simulation.

    Args:
        v0: Initial velocity (m/s)
        angle_deg: Launch angle (degrees)
        height: Initial height (m)
        with_drag: Include air resistance

    Returns:
        Configured PhysicsSimulator
    """
    config = SimulationConfig(dt=0.01, t_max=30.0, method=IntegrationMethod.RK4)
    sim = PhysicsSimulator(config)

    angle_rad = math.radians(angle_deg)
    vx = v0 * math.cos(angle_rad)
    vy = v0 * math.sin(angle_rad)

    projectile = Particle(
        mass=1.0,
        position=[0.0, height, 0.0],
        velocity=[vx, vy, 0.0],
        name="Projectile",
        radius=0.1,
    )
    sim.add_particle(projectile)
    sim.add_force_calculator(UniformGravityCalculator())

    if with_drag:
        sim.add_force_calculator(DragCalculator())

    return sim


def create_orbital_simulation(
    central_mass: float,
    orbiter_mass: float,
    orbital_radius: float,
    eccentricity: float = 0,
) -> PhysicsSimulator:
    """
    Create an orbital mechanics simulation.

    Args:
        central_mass: Mass of central body (kg)
        orbiter_mass: Mass of orbiting body (kg)
        orbital_radius: Semi-major axis (m)
        eccentricity: Orbital eccentricity

    Returns:
        Configured PhysicsSimulator
    """
    # Calculate orbital period for time step
    mu = G * central_mass
    period = 2 * math.pi * math.sqrt(orbital_radius**3 / mu)

    config = SimulationConfig(
        dt=period / 1000,  # 1000 steps per orbit
        t_max=period * 2,
        method=IntegrationMethod.LEAPFROG,  # Good for orbital mechanics
    )
    sim = PhysicsSimulator(config)

    # Central body (fixed)
    central = Particle(
        mass=central_mass,
        position=[0.0, 0.0, 0.0],
        velocity=[0.0, 0.0, 0.0],
        name="Central",
        fixed=True,
    )
    sim.add_particle(central)

    # Orbiter at periapsis
    r_p = orbital_radius * (1 - eccentricity)
    v_p = math.sqrt(mu * (1 + eccentricity) / r_p)

    orbiter = Particle(
        mass=orbiter_mass,
        position=[r_p, 0.0, 0.0],
        velocity=[0.0, v_p, 0.0],
        name="Orbiter",
    )
    sim.add_particle(orbiter)

    sim.add_force_calculator(GravityCalculator(softening=1e3))

    return sim


def create_spring_pendulum_simulation(
    mass: float, k: float, rest_length: float, initial_angle: float
) -> PhysicsSimulator:
    """
    Create a spring pendulum simulation.

    Args:
        mass: Bob mass (kg)
        k: Spring constant (N/m)
        rest_length: Spring rest length (m)
        initial_angle: Initial angle from vertical (degrees)

    Returns:
        Configured PhysicsSimulator
    """
    config = SimulationConfig(dt=0.001, t_max=20.0, method=IntegrationMethod.RK4)
    sim = PhysicsSimulator(config)

    # Fixed pivot
    pivot = Particle(
        mass=1.0,
        position=[0.0, 0.0, 0.0],
        velocity=[0.0, 0.0, 0.0],
        name="Pivot",
        fixed=True,
    )
    sim.add_particle(pivot)

    # Pendulum bob
    angle_rad = math.radians(initial_angle)
    x = rest_length * math.sin(angle_rad)
    y = -rest_length * math.cos(angle_rad)

    bob = Particle(
        mass=mass, position=[x, y, 0.0], velocity=[0.0, 0.0, 0.0], name="Bob"
    )
    sim.add_particle(bob)

    # Spring connecting pivot to bob
    spring = Spring(
        particle1_idx=0, particle2_idx=1, k=k, rest_length=rest_length, damping=0.1
    )

    sim.add_force_calculator(UniformGravityCalculator())
    sim.add_force_calculator(SpringCalculator([spring]))

    return sim


def create_n_body_simulation(
    n: int, box_size: float = 1e10, mass_range: Tuple[float, float] = (1e24, 1e26)
) -> PhysicsSimulator:
    """
    Create an N-body gravitational simulation with random initial conditions.

    Args:
        n: Number of bodies
        box_size: Initial distribution box size (m)
        mass_range: (min_mass, max_mass) in kg

    Returns:
        Configured PhysicsSimulator
    """
    import random

    config = SimulationConfig(
        dt=86400,  # 1 day
        t_max=86400 * 365,  # 1 year
        method=IntegrationMethod.LEAPFROG,
    )
    sim = PhysicsSimulator(config)

    for i in range(n):
        mass = random.uniform(*mass_range)
        position = [
            random.uniform(-box_size, box_size),
            random.uniform(-box_size, box_size),
            random.uniform(-box_size, box_size),
        ]
        # Random velocity (scaled to box size)
        v_scale = math.sqrt(G * sum(mass_range) / 2 / box_size) * 0.1
        velocity = [
            random.uniform(-v_scale, v_scale),
            random.uniform(-v_scale, v_scale),
            random.uniform(-v_scale, v_scale),
        ]

        particle = Particle(
            mass=mass, position=position, velocity=velocity, name=f"Body_{i}"
        )
        sim.add_particle(particle)

    sim.add_force_calculator(GravityCalculator(softening=box_size * 0.01))

    return sim
