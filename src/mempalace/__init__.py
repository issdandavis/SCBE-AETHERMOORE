"""Memory palace built on the CA lexicon substrate.

Each of the 64 CA ops is a Room. Rooms are linked by three rules:
 1. Band chain: adjacent op_ids within the same band are neighbors.
 2. Wing gates: 0x0F<->0x10, 0x1F<->0x20, 0x2F<->0x30 bridge the bands.
 3. Tongue corridors: rooms sharing a non-CA +1 trit channel are linked.

Traversal uses five established recursion methods: DFS, BFS, tree-recursive
zoom, Banach fixed-point settle, and fold-walk.
"""

from src.mempalace.axiom_mesh import (
    AxiomMesh,
    BucketProfile,
    build_axiom_mesh,
    build_buckets,
    build_mesh_graph,
    bridge_joints,
    find_convergence_zones,
    tokenize,
)
from src.mempalace.recursion import (
    PHI,
    fold_walk,
    settle,
    walk_bfs,
    walk_dfs,
    zoom,
)
from src.mempalace.rooms import Room, build_palace
from src.mempalace.vault_link import (
    BAND_TO_PRIMARY_TONGUE,
    NoteRecord,
    TONGUE_TO_SPHERE_DIR,
    VaultIndex,
    dedup_report,
    link_rooms_to_notes,
    room_tongue_profile,
    stats_report,
    vault_stats,
)

__all__ = [
    "PHI",
    "Room",
    "build_palace",
    "fold_walk",
    "settle",
    "walk_bfs",
    "walk_dfs",
    "zoom",
    "BAND_TO_PRIMARY_TONGUE",
    "NoteRecord",
    "TONGUE_TO_SPHERE_DIR",
    "VaultIndex",
    "dedup_report",
    "link_rooms_to_notes",
    "room_tongue_profile",
    "stats_report",
    "vault_stats",
    "AxiomMesh",
    "BucketProfile",
    "build_axiom_mesh",
    "build_buckets",
    "build_mesh_graph",
    "bridge_joints",
    "find_convergence_zones",
    "tokenize",
]
