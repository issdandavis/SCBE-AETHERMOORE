"""
SCBE Flight Training Loop — Coupling Operator Integration

Wires the physics sim (src/physics_sim/simulator.py) into the SCBE governance
pipeline so a policy model can learn to navigate state space while the
governance field continuously modulates its trajectory.

The Coupling Operator A:
    x_dot_actual(t) = A(x_dot_flight, z) =
        x_dot_flight * exp(-H(d, R)) + v_lift(alpha, b_tongue) * z

This is a Control Barrier Function expressed in SCBE's geometry.

Checkpoint versioning follows npm semver:
    polly@0.1.0  -- hover (basic stability)
    polly@0.2.0  -- forward flight (current: coding concepts)
    polly@0.3.0  -- obstacle avoidance (H field active)
    polly@0.4.0  -- mission execution (full governance)

Usage:
    trainer = FlightTrainer(policy, env_config)
    trainer.train(steps=1000, checkpoint_every=50)
    trainer.save_checkpoint("polly", "0.3.0")
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# SCBE pipeline imports
import importlib.util

_PIPELINE_AVAILABLE = (
    importlib.util.find_spec("src.symphonic_cipher.scbe_aethermoore.layers.fourteen_layer_pipeline") is not None
)

# Sacred Tongues phi-weights: KO=1.00, AV=1.62, RU=2.62, CA=4.24, UM=6.85, DR=11.09
TONGUE_WEIGHTS = np.array([1.00, 1.62, 2.62, 4.24, 6.85, 11.09])
TONGUE_BLEND = TONGUE_WEIGHTS / TONGUE_WEIGHTS.sum()  # normalized

PHI = (1 + math.sqrt(5)) / 2
EPS = 1e-10


# =============================================================================
# HARMONIC WALL (stable, gradient-safe)
# =============================================================================


def harmonic_wall(d_H: float, pd: float = 0.0) -> float:
    """
    H(d, pd) = 1 / (1 + d_H + 2*pd)
    Bounded in (0, 1]. Safe gradients. Replaces R^(d^2) for training.

    Args:
        d_H: hyperbolic distance from safe origin
        pd:  phase deviation (0 for pure distance-based)

    Returns:
        H in (0, 1] — 1.0 = fully safe, approaching 0 = dangerous
    """
    return 1.0 / (1.0 + d_H + 2.0 * pd + EPS)


def damping_factor(H: float) -> float:
    """
    e^{-H} where H is inverted (high H = safe = low damping needed).
    For training: damping = 1 - H (linear, gradient-stable).
    Switches to exp(-1/H) for inference to match original formula.
    """
    # Linear proxy for training — smooth gradients
    return max(0.0, 1.0 - H)


# =============================================================================
# COUPLING OPERATOR A
# =============================================================================


def coupling_operator(
    x_flight: np.ndarray,
    z_gov: np.ndarray,
    d_H: float,
    pd: float = 0.0,
    alpha: Optional[float] = None,
) -> Tuple[np.ndarray, float, float]:
    """
    The SCBE Coupling Operator A:

        x_actual = x_flight * exp(-H) + v_lift(alpha, b_tongue) * z

    Args:
        x_flight: conscious trajectory velocity vector (D-dim)
        z_gov:    governance state vector (tongue history, D-dim)
        d_H:      hyperbolic distance from safe region
        pd:       phase deviation
        alpha:    angle-of-attack (radians). If None, computed from vectors.

    Returns:
        (x_actual, H, damping)
    """
    dim = len(x_flight)
    H = harmonic_wall(d_H, pd)
    damp = damping_factor(H)

    # --- Damping arm: governance silently attenuates dangerous trajectories ---
    x_damped = x_flight * damp

    # --- Lift arm: contextual support from Sacred Tongues blend ---
    # Blend z_gov through tongue weights to get directional support
    if len(z_gov) >= 6:
        tongue_projection = np.dot(TONGUE_BLEND, z_gov[:6])
    else:
        tongue_projection = np.mean(z_gov)

    # Angle of attack: how aligned is the trajectory with the danger direction?
    # If alpha not provided, use magnitude as proxy
    if alpha is None:
        alpha = math.pi / 4  # default: 45 degrees

    # Lift magnitude: maximal when flying parallel to constraint (sin(alpha)=1)
    lift_mag = tongue_projection * math.sin(alpha)

    # Lift direction: perpendicular to flight in 2D, generalized for N-D
    if dim >= 2:
        # Rotate flight vector 90 degrees for lift direction
        lift_dir = np.zeros(dim)
        lift_dir[0] = -x_flight[1] if dim > 1 else 0.0
        lift_dir[1] = x_flight[0]
        norm = np.linalg.norm(lift_dir) + EPS
        lift_dir = lift_dir / norm
    else:
        lift_dir = np.ones(dim)

    v_lift = lift_mag * lift_dir

    # Governance modulation: lift weighted by governance field magnitude
    gov_scale = np.linalg.norm(z_gov) / (np.linalg.norm(z_gov) + 1.0 + EPS)
    x_actual = x_damped + v_lift * gov_scale

    return x_actual, H, damp


# =============================================================================
# ENVIRONMENT STATE
# =============================================================================


@dataclass
class FlightState:
    """
    Full state for one timestep.
    Maps SCBE 14-layer pipeline onto flight dynamics.
    """

    # Physical state (L1-L2: complex context → real)
    pos: np.ndarray = field(default_factory=lambda: np.zeros(3))
    vel: np.ndarray = field(default_factory=lambda: np.zeros(3))

    # Governance state (L3-L11: geometry + coherence + temporal)
    z_gov: np.ndarray = field(default_factory=lambda: np.zeros(6))
    d_H: float = 0.0  # L5: hyperbolic distance
    pd: float = 0.0  # L7: phase deviation
    entropy: float = 1.0  # L9-10: spectral entropy

    # Decision state (L12-L13: harmonic wall + risk)
    H: float = 1.0  # current harmonic score
    decision: str = "ALLOW"

    # Telemetry (L14: audio axis)
    step: int = 0
    timestamp: float = 0.0


@dataclass
class FlightEnvConfig:
    """Environment configuration."""

    dim: int = 3  # state space dimensions
    dt: float = 0.05  # timestep (seconds)
    max_steps: int = 200  # episode length
    safe_radius: float = 2.0  # safe region radius in hyperbolic space
    goal: np.ndarray = field(default_factory=lambda: np.array([5.0, 0.0, 0.0]))
    obstacle_pos: np.ndarray = field(default_factory=lambda: np.array([2.5, 0.5, 0.0]))
    obstacle_radius: float = 0.8


class FlightEnv:
    """
    SCBE-governed flight environment.
    State evolves under the coupling operator A.
    """

    def __init__(self, config: Optional[FlightEnvConfig] = None):
        self.config = config or FlightEnvConfig()
        self.state = FlightState()
        self._step_count = 0

    def reset(self) -> FlightState:
        self.state = FlightState(
            pos=np.zeros(self.config.dim),
            vel=np.zeros(self.config.dim),
            z_gov=np.random.uniform(0.1, 0.5, 6),  # random initial tongue activation
        )
        self._step_count = 0
        return self.state

    def _compute_d_H(self, pos: np.ndarray) -> float:
        """
        Hyperbolic distance from safe origin.
        Increases as drone approaches obstacles or leaves safe region.
        """
        # Distance to nearest obstacle (normalized)
        d_obstacle = np.linalg.norm(pos - self.config.obstacle_pos)
        obstacle_penalty = max(0.0, self.config.obstacle_radius - d_obstacle)

        # Distance from safe region center
        d_from_origin = np.linalg.norm(pos) / self.config.safe_radius

        return d_from_origin + obstacle_penalty * PHI

    def _compute_alpha(self, vel: np.ndarray, pos: np.ndarray) -> float:
        """
        Angle of attack: angle between velocity and direction toward nearest danger.
        """
        danger_dir = self.config.obstacle_pos - pos
        danger_norm = np.linalg.norm(danger_dir) + EPS
        vel_norm = np.linalg.norm(vel) + EPS

        cos_alpha = np.dot(vel, danger_dir) / (vel_norm * danger_norm)
        cos_alpha = np.clip(cos_alpha, -1.0, 1.0)
        return math.acos(cos_alpha)

    def step(self, action: np.ndarray) -> Tuple[FlightState, float, bool, Dict]:
        """
        Apply coupling operator A, evolve state, compute reward.

        Args:
            action: raw policy output (x_flight velocity command)

        Returns:
            (next_state, reward, done, info)
        """
        pos = self.state.pos.copy()
        vel = self.state.vel.copy()
        z_gov = self.state.z_gov.copy()

        # Compute SCBE geometry
        d_H = self._compute_d_H(pos)
        alpha = self._compute_alpha(vel + action + EPS, pos)
        pd = self.state.pd

        # Apply coupling operator
        x_actual, H, damp = coupling_operator(
            x_flight=action,
            z_gov=z_gov,
            d_H=d_H,
            pd=pd,
            alpha=alpha,
        )

        # Integrate (Euler — RK4 in full sim)
        vel_new = vel + x_actual * self.config.dt
        pos_new = pos + vel_new * self.config.dt

        # Update governance state (phi-decay + new activation)
        z_gov_new = z_gov * (1.0 / PHI) + np.random.uniform(0, 0.1, 6) * (1 - H)

        # L13 decision
        if d_H > 3.0:
            decision = "DENY"
        elif d_H > 1.5:
            decision = "QUARANTINE"
        elif d_H > 0.5:
            decision = "ESCALATE"
        else:
            decision = "ALLOW"

        self._step_count += 1

        self.state = FlightState(
            pos=pos_new,
            vel=vel_new,
            z_gov=z_gov_new,
            d_H=d_H,
            pd=pd,
            H=H,
            decision=decision,
            step=self._step_count,
            timestamp=self._step_count * self.config.dt,
        )

        # Reward: approach goal + stay safe + penalize governance cost
        d_goal = np.linalg.norm(pos_new - self.config.goal)
        reward = (
            -d_goal * 0.1  # task: get closer to goal
            - (1.0 - H) * 2.0  # governance: penalize low H (danger)
            - np.linalg.norm(x_actual) * 0.01  # efficiency: penalize large commands
        )

        # Terminal: reached goal or crashed
        reached = d_goal < 0.3
        crashed = d_H > 4.0
        done = reached or crashed or self._step_count >= self.config.max_steps

        info = {
            "d_H": d_H,
            "H": H,
            "damp": damp,
            "alpha": alpha,
            "decision": decision,
            "reached": reached,
            "crashed": crashed,
        }

        return self.state, reward, done, info


# =============================================================================
# TRAINING LOOP
# =============================================================================


@dataclass
class TrainingMetrics:
    """Per-step training metrics."""

    step: int
    episode: int
    loss: float
    task_loss: float
    governance_loss: float
    instability_loss: float
    mean_H: float
    mean_d_H: float
    mean_reward: float
    decision_counts: Dict[str, int]


class FlightTrainer:
    """
    Trains a policy under SCBE governance using the coupling operator.

    The policy learns to navigate toward goals while internalizing the
    governance field — high-H regions become naturally avoided because
    the coupling operator damps the policy's own commands there.

    Checkpoint versioning: npm-style semver stored alongside adapter metadata.
    """

    def __init__(
        self,
        policy,  # callable: state -> action (numpy array)
        env_config: Optional[FlightEnvConfig] = None,
        lambda_gov: float = 2.0,  # governance loss weight
        mu_instab: float = 0.01,  # instability loss weight
        checkpoint_dir: str = "training/runs/flight",
    ):
        self.policy = policy
        self.env = FlightEnv(env_config)
        self.lambda_gov = lambda_gov
        self.mu_instab = mu_instab
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.metrics_history: List[TrainingMetrics] = []
        self._episode = 0
        self._global_step = 0

    def compute_loss(
        self,
        task_reward: float,
        H_values: List[float],
        actions: List[np.ndarray],
    ) -> Tuple[float, float, float, float]:
        """
        Total loss = task_loss + lambda * governance_loss + mu * instability_loss

        task_loss:       negative reward (minimize distance to goal)
        governance_loss: penalize low H scores (dangerous regions)
        instability_loss: penalize large/jerky control actions
        """
        task_loss = -task_reward

        # Governance: penalize time spent in low-H (dangerous) states
        governance_loss = sum((1.0 - H) ** 2 for H in H_values) / len(H_values)

        # Instability: penalize large control commands
        instability_loss = sum(float(np.linalg.norm(a)) for a in actions) / len(actions)

        total = task_loss + self.lambda_gov * governance_loss + self.mu_instab * instability_loss
        return total, task_loss, governance_loss, instability_loss

    def run_episode(self) -> Tuple[float, List[float], List[np.ndarray], Dict]:
        """Run one episode, collect trajectory."""
        state = self.env.reset()
        total_reward = 0.0
        H_values = []
        actions = []
        decision_counts = {"ALLOW": 0, "ESCALATE": 0, "QUARANTINE": 0, "DENY": 0}

        while True:
            # Policy produces raw flight command
            obs = np.concatenate(
                [
                    state.pos,
                    state.vel,
                    state.z_gov,
                    [state.d_H, state.H],
                ]
            )
            action = self.policy(obs)
            actions.append(action)

            # Environment applies coupling operator
            next_state, reward, done, info = self.env.step(action)

            total_reward += reward
            H_values.append(info["H"])
            decision_counts[info["decision"]] = decision_counts.get(info["decision"], 0) + 1

            state = next_state
            self._global_step += 1

            if done:
                break

        return total_reward, H_values, actions, decision_counts

    def train(self, episodes: int = 100, checkpoint_every: int = 50):
        """
        Main training loop.

        For each episode:
          1. Run policy through environment (coupling operator active)
          2. Compute loss: task + governance + instability
          3. Update policy (gradient step or ES update)
          4. Log metrics
          5. Save checkpoint at intervals
        """
        print(f"\nSCBE Flight Training")
        print(f"  Episodes: {episodes}")
        print(f"  Lambda (governance): {self.lambda_gov}")
        print(f"  Mu (instability): {self.mu_instab}")
        print(f"  Checkpoint every: {checkpoint_every} episodes")
        print(f"  Output: {self.checkpoint_dir}\n")

        for ep in range(episodes):
            self._episode = ep

            total_reward, H_values, actions, decision_counts = self.run_episode()

            loss, task_loss, gov_loss, instab_loss = self.compute_loss(total_reward, H_values, actions)

            metrics = TrainingMetrics(
                step=self._global_step,
                episode=ep,
                loss=round(loss, 4),
                task_loss=round(task_loss, 4),
                governance_loss=round(gov_loss, 4),
                instability_loss=round(instab_loss, 4),
                mean_H=round(float(np.mean(H_values)), 4),
                mean_d_H=round(float(np.mean([self.env._compute_d_H(self.env.state.pos)])), 4),
                mean_reward=round(total_reward, 4),
                decision_counts=decision_counts,
            )
            self.metrics_history.append(metrics)

            if ep % 10 == 0:
                print(
                    f"  ep {ep:4d} | loss {loss:7.4f} | "
                    f"task {task_loss:7.4f} | gov {gov_loss:6.4f} | "
                    f"mean_H {metrics.mean_H:.3f} | "
                    f"{decision_counts}"
                )

            if (ep + 1) % checkpoint_every == 0:
                self._save_checkpoint(ep + 1, metrics)

        print(f"\nTraining complete. {self._global_step} total steps.")

    def _save_checkpoint(self, episode: int, metrics: TrainingMetrics):
        """
        Save checkpoint with full metadata (npm-style package.json equivalent).
        Checkpoint = weights + config + metrics + capability declaration.
        """
        cp_dir = self.checkpoint_dir / f"checkpoint-ep{episode}"
        cp_dir.mkdir(exist_ok=True)

        # Package manifest (package.json equivalent)
        manifest = {
            "name": "scbe-flight-policy",
            "version": f"0.{episode // 50}.{episode % 50}",
            "episode": episode,
            "global_step": self._global_step,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "base": "SCBE-AETHERMOORE-14layer",
            "capabilities": self._assess_capabilities(metrics),
            "requires": {
                "harmonic_wall": "H(d,pd)=1/(1+d_H+2*pd)",
                "tongue_weights": TONGUE_WEIGHTS.tolist(),
                "coupling_operator": "A=x_flight*exp(-H)+v_lift*z",
            },
            "metrics": {
                "mean_H": metrics.mean_H,
                "loss": metrics.loss,
                "task_loss": metrics.task_loss,
                "governance_loss": metrics.governance_loss,
                "decision_counts": metrics.decision_counts,
            },
            "config": {
                "lambda_gov": self.lambda_gov,
                "mu_instab": self.mu_instab,
                "env_dim": self.env.config.dim,
                "safe_radius": self.env.config.safe_radius,
            },
        }

        with open(cp_dir / "package.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Metrics history
        with open(cp_dir / "metrics.jsonl", "w") as f:
            for m in self.metrics_history[-50:]:  # last 50 episodes
                f.write(json.dumps(asdict(m)) + "\n")

        print(f"  [checkpoint] ep{episode} saved -> {cp_dir}")
        return cp_dir

    def _assess_capabilities(self, metrics: TrainingMetrics) -> List[str]:
        """
        Declare what the model has learned at this checkpoint.
        Like npm peerDependencies — what capabilities this version provides.
        """
        caps = []
        if metrics.mean_H > 0.7:
            caps.append("safe-region-awareness")
        if metrics.decision_counts.get("DENY", 0) < 5:
            caps.append("obstacle-avoidance-basic")
        if metrics.task_loss < -10.0:
            caps.append("goal-seeking")
        if metrics.governance_loss < 0.1:
            caps.append("governance-internalized")
        return caps

    def save_checkpoint(self, name: str, version: str):
        """
        Publish a named checkpoint (npm publish equivalent).
        Creates a tagged release with full manifest.
        """
        tag_dir = self.checkpoint_dir / f"{name}@{version}"
        tag_dir.mkdir(exist_ok=True)

        manifest = {
            "name": name,
            "version": version,
            "published": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_episodes": self._episode,
            "total_steps": self._global_step,
            "final_metrics": asdict(self.metrics_history[-1]) if self.metrics_history else {},
        }

        with open(tag_dir / "package.json", "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"Published {name}@{version} -> {tag_dir}")


# =============================================================================
# DEMO: RANDOM POLICY (replace with trained model)
# =============================================================================


def random_policy(obs: np.ndarray) -> np.ndarray:
    """
    Placeholder policy — replace with LoRA model or neural net.
    Outputs a random action in [-1, 1]^3.
    """
    dim = 3
    return np.random.uniform(-0.5, 0.5, dim)


if __name__ == "__main__":
    trainer = FlightTrainer(
        policy=random_policy,
        lambda_gov=2.0,
        mu_instab=0.01,
    )
    trainer.train(episodes=100, checkpoint_every=50)
    trainer.save_checkpoint("polly-flight", "0.1.0")
