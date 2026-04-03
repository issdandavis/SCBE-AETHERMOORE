import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# =============================================================================
# SCATTERED ATTENTION SPHERE - Holographic Weight Matrix Router
# =============================================================================
# Concept:
# 1. Fractalize: Break a 2D weight matrix into smaller components (e.g., nibbles).
# 2. Scatter: Map these components into a 3D Memory Lattice.
# 3. Layer/Cycle: Assign components to "Sacred Tongues" (longitudes).
# 4. Band of Focus: Use phi_wall (latitude/phase) to filter resonant bits.
# =============================================================================

class ScatteredAttentionSphere:
    def __init__(self, matrix_size=64):
        self.matrix_size = matrix_size
        self.tongues = {
            'KO': 0.0 * np.pi,
            'AV': (1/3) * np.pi,
            'RU': (2/3) * np.pi,
            'CA': 1.0 * np.pi,
            'UM': (4/3) * np.pi,
            'DR': (5/3) * np.pi
        }
        self.lattice = []

    def fractalize_and_scatter(self, weight_matrix):
        print(f"\nFractalizing {weight_matrix.shape} matrix into Scattered Sphere...")
        self.lattice = []
        rows, cols = weight_matrix.shape
        tongue_keys = list(self.tongues.keys())

        for i in range(rows):
            for j in range(cols):
                val = weight_matrix[i, j]
                if abs(val) < 0.01:
                    continue
                tongue_idx = (i * cols + j) % 6
                tongue_name = tongue_keys[tongue_idx]
                theta = self.tongues[tongue_name]
                theta += np.random.uniform(-0.1, 0.1)
                phi = np.tanh(val) * (np.pi / 2)
                radius = 1.0 + np.random.uniform(-0.05, 0.05)
                self.lattice.append({
                    'value': val,
                    'tongue': tongue_name,
                    'r': radius,
                    'theta': theta,
                    'phi': phi,
                    'orig_coord': (i, j)
                })
        print(f"Scattered {len(self.lattice)} active bits into the 3D Lattice.")

    def get_band_of_focus(self, phi_wall, bandwidth=0.2):
        return [p for p in self.lattice if abs(p['phi'] - phi_wall) <= bandwidth]

    def visualize_sphere(self, active_phi_wall=None, bandwidth=0.2):
        if not self.lattice:
            print("Lattice is empty. Scatter a matrix first.")
            return
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        xs, ys, zs, colors = [], [], [], []
        color_map = {
            'KO': 'red', 'AV': 'orange', 'RU': 'yellow',
            'CA': 'green', 'UM': 'blue', 'DR': 'purple'
        }
        for pt in self.lattice:
            r, theta, phi = pt['r'], pt['theta'], pt['phi']
            x = r * np.cos(phi) * np.cos(theta)
            y = r * np.cos(phi) * np.sin(theta)
            z = r * np.sin(phi)
            xs.append(x); ys.append(y); zs.append(z)
            if active_phi_wall is not None and abs(phi - active_phi_wall) <= bandwidth:
                colors.append('cyan')
            else:
                colors.append(color_map[pt['tongue']])
        ax.scatter(xs, ys, zs, c=colors, s=10, alpha=0.6)
        if active_phi_wall is not None:
            u = np.linspace(0, 2 * np.pi, 100)
            z_ring = np.sin(active_phi_wall)
            r_ring = np.cos(active_phi_wall)
            ax.plot(r_ring * np.cos(u), r_ring * np.sin(u), z_ring,
                    color='cyan', linewidth=3, label='Band of Focus')
            ax.legend()
        ax.set_title("Holographic Matrix Sphere (6 Sacred Tongues)")
        ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z (Phase)")
        plt.show()


if __name__ == "__main__":
    np.random.seed(42)
    matrix = np.random.randn(32, 32) * 0.5
    sphere = ScatteredAttentionSphere()
    sphere.fractalize_and_scatter(matrix)
    active = sphere.get_band_of_focus(phi_wall=0.5, bandwidth=0.1)
    print(f"\nPhase Tunnel at 0.5 rad. Resonant bits: {len(active)}")
    sphere.visualize_sphere(active_phi_wall=0.5, bandwidth=0.1)
