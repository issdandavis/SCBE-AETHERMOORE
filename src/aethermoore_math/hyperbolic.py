"""
Hyperbolic Geometry for Trust Routing
=====================================
Hyperbolic space naturally embeds hierarchical structures.
Nodes closer to center = more trusted.
Distance grows exponentially toward periphery.
"""

import numpy as np
from typing import Tuple


def hyperbolic_distance(
    r1: float, theta1: float,
    r2: float, theta2: float
) -> float:
    """
    Calculate hyperbolic distance using the hyperbolic law of cosines.

    cosh(d) = cosh(r1)cosh(r2) - sinh(r1)sinh(r2)cos(θ1 - θ2)

    Args:
        r1, theta1: Polar coordinates of point 1
        r2, theta2: Polar coordinates of point 2

    Returns:
        Hyperbolic distance d
    """
    cos_delta = np.cos(theta1 - theta2)
    cosh_d = np.cosh(r1) * np.cosh(r2) - np.sinh(r1) * np.sinh(r2) * cos_delta
    # Clamp to valid range for acosh (must be >= 1)
    cosh_d = max(1.0, cosh_d)
    return np.arccosh(cosh_d)


def poincare_to_klein(x: float, y: float) -> Tuple[float, float]:
    """
    Convert Poincaré disk coordinates to Klein disk.

    Klein model has straight-line geodesics (easier for routing).
    Poincaré model preserves angles (better for visualization).
    """
    denom = 1 + x**2 + y**2
    return (2*x / denom, 2*y / denom)


def trust_cost(
    agent_radius: float,
    target_radius: float,
    angular_distance: float,
    curvature: float = -1.0
) -> float:
    """
    Calculate trust-based routing cost in hyperbolic space.

    Cost increases exponentially as:
    - Agent is further from center (less trusted)
    - Target is further from center (higher risk)
    - Angular distance is large (different trust domains)

    Args:
        agent_radius: Radial position of requesting agent (0 = core, >0 = edge)
        target_radius: Radial position of target resource
        angular_distance: Angle between agent and target (radians)
        curvature: Hyperbolic curvature (default -1)

    Returns:
        Trust cost (higher = more verification required)
    """
    # Base hyperbolic distance
    d = hyperbolic_distance(agent_radius, 0, target_radius, angular_distance)

    # Apply curvature scaling
    # More negative curvature = steeper trust gradient
    return d * np.sqrt(-curvature)


def embed_hierarchy(
    depth: int,
    breadth: int,
    max_radius: float = 4.0
) -> list:
    """
    Embed a hierarchical tree into hyperbolic space.

    Args:
        depth: Number of levels
        breadth: Children per node
        max_radius: Maximum radial extent

    Returns:
        List of (r, theta) coordinates for each node
    """
    nodes = []

    for level in range(depth):
        r = (level / (depth - 1)) * max_radius if depth > 1 else 0
        n_nodes = breadth ** level

        for i in range(n_nodes):
            theta = (2 * np.pi * i) / n_nodes
            nodes.append((r, theta, level))

    return nodes
