"""
Hyperbolic Visualization - Poincare Ball Projections and Voxel Rendering
========================================================================

Visualization tools for the dual lattice system:
- 2D Poincare disk projection via classical MDS
- 3D voxel rendering with realm coloring
- Geodesic hyperpath overlays
- Multi-angle renders

All visualizations respect hyperbolic geometry:
- Light realms cluster near origin
- Shadow realms expand toward boundary
- Geodesics curve correctly for negative curvature
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

# Try to import matplotlib (optional for headless systems)
try:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from mpl_toolkits.mplot3d import Axes3D
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[VIZ] Warning: matplotlib not available, visualization disabled")


def hyperbolic_distance_safe(x: np.ndarray, y: np.ndarray, eps: float = 1e-8) -> float:
    """Safe hyperbolic distance for visualization."""
    nx = np.dot(x, x)
    ny = np.dot(y, y)

    if nx >= 1.0 or ny >= 1.0:
        return 10.0

    diff_norm_sq = np.dot(x - y, x - y)
    denominator = (1 - nx) * (1 - ny)
    arg = 1 + 2 * diff_norm_sq / (denominator + eps)

    if arg < 1.0:
        return 10.0

    return float(np.arccosh(arg))


def classical_mds(dist_matrix: np.ndarray, n_dims: int = 2) -> np.ndarray:
    """
    Classical multidimensional scaling from distance matrix.

    Projects high-dimensional hyperbolic distances to 2D while
    approximately preserving pairwise distances.

    Args:
        dist_matrix: Square matrix of pairwise distances
        n_dims: Output dimensions (usually 2 for visualization)

    Returns:
        n x n_dims array of coordinates
    """
    n = dist_matrix.shape[0]

    if n < 2:
        return np.zeros((n, n_dims))

    # Centering matrix
    H = np.eye(n) - np.ones((n, n)) / n

    # Double-centered Gram matrix
    B = -0.5 * H @ (dist_matrix ** 2) @ H

    # Eigendecomposition
    eigvals, eigvecs = np.linalg.eigh(B)

    # Sort descending
    idx = np.argsort(eigvals)[::-1]
    eigvals = eigvals[idx]
    eigvecs = eigvecs[:, idx]

    # Keep positive eigenvalues
    positive = eigvals > 1e-8
    n_positive = np.sum(positive)

    if n_positive < n_dims:
        # Pad with zeros if not enough positive eigenvalues
        coords = np.zeros((n, n_dims))
        if n_positive > 0:
            L = np.diag(np.sqrt(eigvals[positive]))
            V = eigvecs[:, positive]
            coords[:, :n_positive] = V @ L
        return coords

    # Top n_dims eigenvalues/vectors
    L = np.diag(np.sqrt(eigvals[:n_dims]))
    V = eigvecs[:, :n_dims]
    Y = V @ L

    return Y


def poincare_geodesic(
    u: np.ndarray,
    v: np.ndarray,
    t: float,
    eps: float = 1e-8
) -> np.ndarray:
    """
    Compute point on geodesic from u to v at parameter t in [0,1].

    Uses Mobius addition for exact Poincare ball geodesics.
    """
    def mobius_add(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        xy = np.dot(x, y)
        xx = np.dot(x, x)
        yy = np.dot(y, y)

        num = (1 + 2 * xy + yy) * x + (1 - xx) * y
        den = 1 + 2 * xy + xx * yy

        return num / (den + eps)

    # Distance for scaling
    dist = hyperbolic_distance_safe(u, v)
    if dist < eps:
        return u.copy()

    # Direction via Mobius addition
    neg_u = -u
    direction = mobius_add(neg_u, v)
    norm = np.linalg.norm(direction)
    if norm > eps:
        direction = direction / norm

    # Geodesic parameterization
    tanh_term = np.tanh(t * dist / 2.0)
    result = mobius_add(u, tanh_term * direction)

    # Ensure inside ball
    result_norm = np.linalg.norm(result)
    if result_norm >= 1.0:
        result = result / (result_norm + 0.01) * 0.95

    return result


def visualize_poincare_disk(
    points: np.ndarray,
    labels: List[str],
    filename: str = "poincare_disk_projection.png",
    title: str = "Poincare Disk Projection"
) -> bool:
    """
    Visualize lattice points in 2D Poincare disk.

    Uses MDS to project hyperbolic distances to 2D.

    Args:
        points: Array of points (can be high-dimensional, uses first dims for core)
        labels: Realm labels for each point
        filename: Output filename
        title: Plot title

    Returns:
        True if successful, False if matplotlib unavailable
    """
    if not MATPLOTLIB_AVAILABLE:
        print("[VIZ] matplotlib not available")
        return False

    n = len(points)
    if n < 2:
        print("[VIZ] Need at least 2 points")
        return False

    # Extract core coordinates (exclude phase if present)
    if points.shape[1] > 2:
        core_points = points[:, :-2] if points.shape[1] > 3 else points[:, :3]
    else:
        core_points = points

    # Truncate to 3D for manageable computation
    if core_points.shape[1] > 3:
        core_points = core_points[:, :3]

    # Project to Poincare ball if needed
    for i in range(n):
        norm = np.linalg.norm(core_points[i])
        if norm >= 1.0:
            core_points[i] = core_points[i] / (norm + 0.01) * 0.9

    # Compute pairwise hyperbolic distances
    hyp_dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = hyperbolic_distance_safe(core_points[i], core_points[j])
            hyp_dist_matrix[i, j] = hyp_dist_matrix[j, i] = d

    # MDS to 2D
    coords_2d = classical_mds(hyp_dist_matrix, n_dims=2)

    # Normalize to fit in disk with margin
    max_norm = np.max(np.linalg.norm(coords_2d, axis=1))
    if max_norm > 0:
        coords_2d = coords_2d / max_norm * 0.85

    # Colors by realm
    colors = []
    for label in labels:
        if 'light' in label.lower():
            colors.append('gold')
        elif 'shadow' in label.lower():
            colors.append('purple')
        else:
            colors.append('cyan')

    # Plot
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_facecolor('black')

    # Unit disk boundary
    disk = Circle((0, 0), 1.0, edgecolor='white', facecolor='none',
                  linewidth=2, linestyle='--')
    ax.add_patch(disk)

    # Origin
    ax.plot(0, 0, 'o', color='white', markersize=8)

    # Points
    ax.scatter(coords_2d[:, 0], coords_2d[:, 1],
               c=colors, s=150, edgecolors='white', linewidth=1, alpha=0.9)

    # Labels
    for i, label in enumerate(labels):
        ax.text(coords_2d[i, 0] + 0.02, coords_2d[i, 1] + 0.02,
                f"{i}", color='white', fontsize=8)

    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.set_aspect('equal')
    ax.axis('off')

    plt.title(f"{title}\nGold = Light Realm | Purple = Shadow Realm | Boundary = Hyperbolic Infinity",
              color='white', fontsize=12, pad=20)

    plt.tight_layout()
    plt.savefig(filename, dpi=300, facecolor='black')
    plt.close()

    print(f"[VIZ] Poincare disk saved: {filename}")
    return True


def visualize_3d_voxels(
    octree,
    paths: List[Tuple[np.ndarray, np.ndarray]] = None,
    filename_prefix: str = "poincare_voxels",
    views: List[Tuple[int, int]] = None
) -> bool:
    """
    Render 3D voxel visualization from octree.

    Args:
        octree: HyperbolicOctree instance
        paths: List of (start, end) coordinate pairs for geodesic overlays
        filename_prefix: Output filename prefix
        views: List of (elevation, azimuth) tuples for rendering

    Returns:
        True if successful
    """
    if not MATPLOTLIB_AVAILABLE:
        print("[VIZ] matplotlib not available")
        return False

    colors = octree.to_dense()
    occupied = colors != None

    if not np.any(occupied):
        print("[VIZ] No occupied voxels to render")
        return False

    # Build facecolors array
    facecolors = np.empty(colors.shape + (4,), dtype=float)
    facecolors[:] = (0, 0, 0, 0)  # transparent background

    # Color mapping
    color_map = {
        'gold': (1.0, 0.84, 0.0, 0.6),
        'purple': (0.5, 0.0, 0.5, 0.6),
        'cyan': (0.0, 1.0, 1.0, 0.9),
        'red': (1.0, 0.0, 0.0, 0.8),
        'magenta': (1.0, 0.0, 1.0, 0.8),
        'white': (1.0, 1.0, 1.0, 0.9),
    }

    for idx in np.argwhere(occupied):
        i, j, k = idx
        c = colors[i, j, k]
        facecolors[i, j, k] = color_map.get(c, (0.5, 0.5, 0.5, 0.5))

    # Default views
    if views is None:
        views = [(30, 30), (0, 0), (90, 0), (30, -60)]

    view_names = ["perspective", "front", "top", "side"]

    for (elev, azim), view_name in zip(views, view_names[:len(views)]):
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')

        ax.voxels(occupied, facecolors=facecolors, edgecolor='k', linewidth=0.1)

        # Unit ball wireframe (scaled to grid)
        u = np.linspace(0, 2 * np.pi, 30)
        v = np.linspace(0, np.pi, 30)
        grid_size = octree.grid_size
        half = grid_size / 2

        x = half + half * np.outer(np.cos(u), np.sin(v))
        y = half + half * np.outer(np.sin(u), np.sin(v))
        z = half + half * np.outer(np.ones_like(u), np.cos(v))
        ax.plot_wireframe(x, y, z, color='white', alpha=0.15, rstride=5, cstride=5)

        # Origin
        ax.scatter([half], [half], [half], color='white', s=100)

        # Geodesic paths as lines
        if paths:
            for start, end in paths:
                path_coords = []
                for t in np.linspace(0, 1, 50):
                    pt = poincare_geodesic(start[:3], end[:3], t)
                    # Convert to grid space
                    grid_pt = ((pt + 1.0) / 2.0 * (grid_size - 1))
                    path_coords.append(grid_pt)
                path_coords = np.array(path_coords)
                ax.plot(path_coords[:, 0], path_coords[:, 1], path_coords[:, 2],
                        color='white', linewidth=3, alpha=0.9)

        ax.set_xlim(0, grid_size)
        ax.set_ylim(0, grid_size)
        ax.set_zlim(0, grid_size)
        ax.axis('off')
        ax.view_init(elev=elev, azim=azim)
        ax.set_facecolor('black')
        fig.patch.set_facecolor('black')

        plt.title(f"3D Poincare Ball Voxels - {view_name.capitalize()}\n"
                  "Gold=Light | Purple=Shadow | Cyan=Paths",
                  color='white', fontsize=12)

        filename = f"{filename_prefix}_{view_name}.png"
        plt.savefig(filename, dpi=300, facecolor='black')
        plt.close()

    print(f"[VIZ] 3D voxel renders saved: {filename_prefix}_*.png")
    return True


def generate_demo_visualization(output_dir: str = ".") -> Dict[str, Any]:
    """
    Generate demo visualizations for testing.

    Creates sample light/shadow points and renders them.
    """
    if not MATPLOTLIB_AVAILABLE:
        return {"success": False, "error": "matplotlib not available"}

    # Import octree
    try:
        from .octree import HyperbolicOctree
    except ImportError:
        from octree import HyperbolicOctree

    # Create octree with demo data
    octree = HyperbolicOctree(grid_size=64)
    labels = []

    # Light realm points (near origin)
    for _ in range(30):
        point = np.random.randn(3) * 0.3
        norm = np.linalg.norm(point)
        if norm > 0:
            point = point / norm * min(0.4, norm)
        octree.insert(point, 'light_realm')
        labels.append('light_realm')

    # Shadow realm points (near boundary)
    for _ in range(30):
        point = np.random.randn(3)
        point = point / np.linalg.norm(point) * 0.85
        octree.insert(point, 'shadow_realm')
        labels.append('shadow_realm')

    # Collect points for 2D viz
    points = []
    for _ in range(30):
        point = np.random.randn(3) * 0.3
        norm = np.linalg.norm(point)
        if norm > 0:
            point = point / norm * min(0.4, norm)
        points.append(point)

    for _ in range(30):
        point = np.random.randn(3)
        point = point / np.linalg.norm(point) * 0.85
        points.append(point)

    points = np.array(points)

    # Generate visualizations
    results = {}

    # 2D disk
    disk_file = f"{output_dir}/poincare_disk_demo.png"
    results["disk"] = visualize_poincare_disk(points, labels, disk_file)

    # 3D voxels
    voxel_prefix = f"{output_dir}/poincare_voxels_demo"
    results["voxels"] = visualize_3d_voxels(octree, filename_prefix=voxel_prefix)

    results["success"] = results.get("disk", False) or results.get("voxels", False)
    return results


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("[VIZ] Running demo visualization...")
    result = generate_demo_visualization()
    print(f"[VIZ] Result: {result}")
