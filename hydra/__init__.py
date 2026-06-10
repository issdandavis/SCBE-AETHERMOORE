"""Repo-local HYDRA compatibility package.

The full HYDRA agent runtime moved to ``scbe-agents``. This main repo keeps a
small storage-geometry subset because storage bridge tests and demos still
import ``hydra.lattice25d_ops`` and ``hydra.octree_sphere_grid``.
"""

__version__ = "1.3.0-mainrepo-compat"
