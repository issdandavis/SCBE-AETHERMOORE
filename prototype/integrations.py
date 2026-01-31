"""
SCBE-AETHERMOORE Open Source Integrations
==========================================

Integration examples for recommended open source libraries:
- geoopt: Hyperbolic geometry with PyTorch
- liboqs-python: Post-quantum cryptography
- mesa: Agent-based modeling
- pettingzoo: Multi-agent RL environments
- pyswarms: Particle swarm optimization

Install: pip install geoopt liboqs-python mesa pettingzoo pyswarms

Each integration is optional and gracefully degrades if library is unavailable.
"""

import numpy as np
from typing import Optional, Tuple, List, Dict, Any
import warnings

# ============================================================================
# GEOOPT Integration: Hyperbolic Geometry with PyTorch
# ============================================================================

GEOOPT_AVAILABLE = False
try:
    import geoopt
    import torch
    GEOOPT_AVAILABLE = True
except ImportError:
    pass


class GeooptHyperbolicSpace:
    """
    Hyperbolic geometry using Geoopt's Poincaré Ball.

    Provides GPU-accelerated hyperbolic operations for SCBE.
    """

    def __init__(self, dim: int = 6, curvature: float = -1.0):
        if not GEOOPT_AVAILABLE:
            raise ImportError("Install geoopt: pip install geoopt torch")

        self.dim = dim
        self.curvature = curvature
        self.ball = geoopt.PoincareBall(c=-curvature)

    def distance(self, x: np.ndarray, y: np.ndarray) -> float:
        """Compute hyperbolic distance using Geoopt."""
        x_t = torch.tensor(x, dtype=torch.float64)
        y_t = torch.tensor(y, dtype=torch.float64)
        return self.ball.dist(x_t, y_t).item()

    def mobius_add(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Möbius addition in the Poincaré ball."""
        x_t = torch.tensor(x, dtype=torch.float64)
        y_t = torch.tensor(y, dtype=torch.float64)
        result = self.ball.mobius_add(x_t, y_t)
        return result.numpy()

    def exp_map(self, x: np.ndarray, v: np.ndarray) -> np.ndarray:
        """Exponential map from tangent space to manifold."""
        x_t = torch.tensor(x, dtype=torch.float64)
        v_t = torch.tensor(v, dtype=torch.float64)
        result = self.ball.expmap(x_t, v_t)
        return result.numpy()

    def log_map(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Logarithmic map from manifold to tangent space."""
        x_t = torch.tensor(x, dtype=torch.float64)
        y_t = torch.tensor(y, dtype=torch.float64)
        result = self.ball.logmap(x_t, y_t)
        return result.numpy()

    def project(self, x: np.ndarray) -> np.ndarray:
        """Project point back onto the Poincaré ball."""
        x_t = torch.tensor(x, dtype=torch.float64)
        result = self.ball.projx(x_t)
        return result.numpy()

    def random_point(self) -> np.ndarray:
        """Generate random point in the ball."""
        x = torch.randn(self.dim, dtype=torch.float64) * 0.5
        return self.ball.projx(x).numpy()


# ============================================================================
# LIBOQS Integration: Post-Quantum Cryptography
# ============================================================================

LIBOQS_AVAILABLE = False
try:
    import oqs
    LIBOQS_AVAILABLE = True
except ImportError:
    pass


class PostQuantumSigner:
    """
    Post-quantum digital signatures using liboqs.

    Provides Dilithium signatures for SCBE consensus.
    """

    def __init__(self, algorithm: str = "Dilithium3"):
        if not LIBOQS_AVAILABLE:
            raise ImportError("Install liboqs-python: pip install liboqs-python")

        self.algorithm = algorithm
        self.signer = oqs.Signature(algorithm)
        self.public_key, self.secret_key = self.signer.keypair()

    def sign(self, message: bytes) -> bytes:
        """Sign a message."""
        return self.signer.sign(message)

    def verify(self, message: bytes, signature: bytes, public_key: bytes = None) -> bool:
        """Verify a signature."""
        pk = public_key or self.public_key
        verifier = oqs.Signature(self.algorithm)
        return verifier.verify(message, signature, pk)

    @staticmethod
    def available_algorithms() -> List[str]:
        """List available signature algorithms."""
        if not LIBOQS_AVAILABLE:
            return []
        return oqs.get_enabled_sig_mechanisms()


class PostQuantumKEM:
    """
    Post-quantum key encapsulation using liboqs.

    Provides Kyber KEM for SCBE secure channels.
    """

    def __init__(self, algorithm: str = "Kyber768"):
        if not LIBOQS_AVAILABLE:
            raise ImportError("Install liboqs-python: pip install liboqs-python")

        self.algorithm = algorithm
        self.kem = oqs.KeyEncapsulation(algorithm)
        self.public_key, self.secret_key = self.kem.keypair()

    def encapsulate(self, public_key: bytes = None) -> Tuple[bytes, bytes]:
        """Generate shared secret and ciphertext."""
        pk = public_key or self.public_key
        return self.kem.encap_secret(pk)

    def decapsulate(self, ciphertext: bytes) -> bytes:
        """Recover shared secret from ciphertext."""
        return self.kem.decap_secret(ciphertext)

    @staticmethod
    def available_algorithms() -> List[str]:
        """List available KEM algorithms."""
        if not LIBOQS_AVAILABLE:
            return []
        return oqs.get_enabled_kem_mechanisms()


# ============================================================================
# MESA Integration: Agent-Based Modeling
# ============================================================================

MESA_AVAILABLE = False
try:
    from mesa import Agent, Model
    from mesa.space import ContinuousSpace
    from mesa.time import RandomActivation
    from mesa.datacollection import DataCollector
    MESA_AVAILABLE = True
except ImportError:
    pass


if MESA_AVAILABLE:
    class SCBEAgent(Agent):
        """
        SCBE Sacred Tongue Agent for Mesa simulation.

        Each agent represents a Sacred Tongue with position in Poincaré disk.
        """

        def __init__(self, unique_id: int, model: 'SCBEModel',
                     tongue: str, position: Tuple[float, float],
                     trust_score: float = 0.5):
            super().__init__(unique_id, model)
            self.tongue = tongue
            self.trust_score = trust_score
            self.phase = unique_id * np.pi / 3  # Evenly distributed phases
            self.weight = 1.618 ** (unique_id % 6)  # φ^k weights

        def step(self):
            """Agent step: update trust and detect anomalies."""
            # Check neighbors for phase coherence
            neighbors = self.model.space.get_neighbors(self.pos, radius=0.3)

            if neighbors:
                # Compute average phase difference
                phase_diffs = []
                for neighbor in neighbors:
                    if hasattr(neighbor, 'phase') and neighbor.phase is not None:
                        diff = abs(self.phase - neighbor.phase)
                        diff = min(diff, 2 * np.pi - diff)
                        phase_diffs.append(diff)

                if phase_diffs:
                    avg_diff = np.mean(phase_diffs)
                    # High coherence increases trust
                    if avg_diff < np.pi / 4:
                        self.trust_score = min(1.0, self.trust_score + 0.01)
                    else:
                        self.trust_score = max(0.0, self.trust_score - 0.01)


    class SCBEModel(Model):
        """
        SCBE Agent-Based Model using Mesa.

        Simulates Sacred Tongue swarm dynamics in Poincaré disk.
        """

        def __init__(self, n_agents: int = 6, width: float = 2.0, height: float = 2.0):
            super().__init__()
            self.n_agents = n_agents
            self.space = ContinuousSpace(width, height, torus=False)
            self.schedule = RandomActivation(self)

            # Sacred Tongues
            tongues = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']

            for i in range(n_agents):
                tongue = tongues[i % 6]

                # Position in Poincaré disk (shifted to positive coords)
                r = 0.3 + (i % 6) * 0.1
                theta = i * np.pi / 3
                x = 1.0 + r * np.cos(theta)
                y = 1.0 + r * np.sin(theta)

                agent = SCBEAgent(i, self, tongue, (x, y))
                self.space.place_agent(agent, (x, y))
                self.schedule.add(agent)

            # Data collection
            self.datacollector = DataCollector(
                model_reporters={"AvgTrust": lambda m: np.mean([a.trust_score for a in m.schedule.agents])},
                agent_reporters={"Trust": "trust_score", "Tongue": "tongue"}
            )

        def step(self):
            """Advance model by one step."""
            self.datacollector.collect(self)
            self.schedule.step()


# ============================================================================
# PYSWARMS Integration: Particle Swarm Optimization
# ============================================================================

PYSWARMS_AVAILABLE = False
try:
    import pyswarms as ps
    from pyswarms.utils.functions import single_obj as fx
    PYSWARMS_AVAILABLE = True
except ImportError:
    pass


class SwarmOptimizer:
    """
    Particle Swarm Optimization for SCBE hyperparameter tuning.

    Uses PySwarms to optimize governance parameters.
    """

    def __init__(self, n_particles: int = 20, dimensions: int = 4):
        if not PYSWARMS_AVAILABLE:
            raise ImportError("Install pyswarms: pip install pyswarms")

        self.n_particles = n_particles
        self.dimensions = dimensions

        # PSO options
        self.options = {
            'c1': 1.5,  # Cognitive parameter
            'c2': 1.5,  # Social parameter
            'w': 0.7    # Inertia weight
        }

    def optimize_blocking_threshold(self, test_intents: List[Tuple[str, bool]],
                                     phdm_class, iterations: int = 50) -> Dict[str, float]:
        """
        Optimize blocking threshold using PSO.

        Args:
            test_intents: List of (intent, should_block) tuples
            phdm_class: ToyPHDM class
            iterations: Number of optimization iterations

        Returns:
            Dict with optimal parameters
        """
        # Bounds: [threshold_min, threshold_max, cost_scale_min, cost_scale_max]
        bounds = (np.array([10, 0.5]), np.array([200, 5.0]))

        def objective(params):
            """Objective: minimize false positives + false negatives."""
            costs = []
            for p in params:
                threshold, cost_scale = p
                phdm = phdm_class()
                phdm.blocking_threshold = threshold

                errors = 0
                for intent, should_block in test_intents:
                    result = phdm.evaluate_intent(intent)
                    is_blocked = result.blocked
                    if is_blocked != should_block:
                        errors += 1

                costs.append(errors / len(test_intents))

            return np.array(costs)

        optimizer = ps.single.GlobalBestPSO(
            n_particles=self.n_particles,
            dimensions=2,
            options=self.options,
            bounds=bounds
        )

        best_cost, best_params = optimizer.optimize(objective, iters=iterations, verbose=False)

        return {
            'blocking_threshold': best_params[0],
            'cost_scale': best_params[1],
            'error_rate': best_cost
        }


# ============================================================================
# Integration Status Check
# ============================================================================

def check_integrations() -> Dict[str, bool]:
    """Check which integrations are available."""
    return {
        'geoopt': GEOOPT_AVAILABLE,
        'liboqs': LIBOQS_AVAILABLE,
        'mesa': MESA_AVAILABLE,
        'pyswarms': PYSWARMS_AVAILABLE,
    }


def print_integration_status():
    """Print integration status with install commands."""
    print("=" * 60)
    print("SCBE-AETHERMOORE Integration Status")
    print("=" * 60)

    status = check_integrations()

    install_commands = {
        'geoopt': 'pip install geoopt torch',
        'liboqs': 'pip install liboqs-python',
        'mesa': 'pip install mesa',
        'pyswarms': 'pip install pyswarms',
    }

    for lib, available in status.items():
        icon = "✓" if available else "✗"
        status_text = "Available" if available else "Not installed"
        print(f"  {icon} {lib:12} - {status_text}")
        if not available:
            print(f"    Install: {install_commands[lib]}")

    print("=" * 60)

    available_count = sum(status.values())
    print(f"Total: {available_count}/{len(status)} integrations available")

    return status


# ============================================================================
# Demo / Test
# ============================================================================

if __name__ == "__main__":
    print_integration_status()

    # Test available integrations
    status = check_integrations()

    if status['geoopt']:
        print("\n--- Geoopt Demo ---")
        space = GeooptHyperbolicSpace(dim=6)
        x = space.random_point()
        y = space.random_point()
        dist = space.distance(x, y)
        print(f"Random points distance: {dist:.4f}")

    if status['liboqs']:
        print("\n--- liboqs Demo ---")
        signer = PostQuantumSigner()
        message = b"SCBE consensus message"
        signature = signer.sign(message)
        valid = signer.verify(message, signature)
        print(f"Signature valid: {valid}")
        print(f"Available algorithms: {PostQuantumSigner.available_algorithms()[:5]}...")

    if status['mesa']:
        print("\n--- Mesa Demo ---")
        model = SCBEModel(n_agents=6)
        for _ in range(10):
            model.step()
        data = model.datacollector.get_model_vars_dataframe()
        print(f"Average trust after 10 steps: {data['AvgTrust'].iloc[-1]:.3f}")

    if status['pyswarms']:
        print("\n--- PySwarms Demo ---")
        print("Swarm optimization ready (run with test intents)")
