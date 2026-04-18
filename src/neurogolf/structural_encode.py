from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from crypto.sacred_tongues import SacredTongueTokenizer, TONGUES
from crypto.geo_seal import ContextVector, hyperbolic_distance

from .components import ConnectedComponent, connected_components


_TOKENIZER = SacredTongueTokenizer(TONGUES)
_TONGUE_ORDER = ("ko", "av", "ru", "ca", "um", "dr")


@dataclass(frozen=True)
class StructuralEncoding:
    """Compact structural views over a single ARC grid."""

    padded_grid: np.ndarray
    tongue_bytes: np.ndarray
    tongue_token_ids: np.ndarray
    trichromatic_tensor: np.ndarray
    geo_radius: np.ndarray
    component_labels: np.ndarray
    components: tuple[ConnectedComponent, ...]


def _same_color_neighbor_count(grid: np.ndarray) -> np.ndarray:
    same = np.zeros_like(grid, dtype=np.int64)
    same[1:, :] += grid[1:, :] == grid[:-1, :]
    same[:-1, :] += grid[:-1, :] == grid[1:, :]
    same[:, 1:] += grid[:, 1:] == grid[:, :-1]
    same[:, :-1] += grid[:, :-1] == grid[:, 1:]
    return same


def _boundary_mask(grid: np.ndarray) -> np.ndarray:
    same = _same_color_neighbor_count(grid)
    return (same < 4).astype(np.int64)


def _build_tongue_bytes(grid: np.ndarray) -> np.ndarray:
    """Create six deterministic byte lanes from one ARC grid."""

    h, w = grid.shape
    rows, cols = np.indices((h, w))
    same = _same_color_neighbor_count(grid)
    boundary = _boundary_mask(grid)
    occupancy = (grid != 0).astype(np.int64)

    tongue_bytes = np.empty((6, h, w), dtype=np.uint8)
    tongue_bytes[0] = grid.astype(np.uint8)
    tongue_bytes[1] = ((occupancy * 127) + rows) % 256
    tongue_bytes[2] = ((boundary * 191) + same * 17) % 256
    tongue_bytes[3] = (rows * 31 + cols * 17 + grid * 13) % 256
    tongue_bytes[4] = ((rows - cols) % 256).astype(np.uint8)
    tongue_bytes[5] = ((rows + cols + boundary * 53 + occupancy * 29) % 256).astype(np.uint8)
    return tongue_bytes


def _build_trichromatic_tensor(grid: np.ndarray, tongue_bytes: np.ndarray) -> np.ndarray:
    """Build a deterministic 6 x 3 x H x W tensor.

    The three bands follow the repo's hidden-band framing:
    - IR: slower structural state
    - Visible: direct observed state
    - UV: fast anomaly / edge-sensitive state
    """

    same = _same_color_neighbor_count(grid).astype(np.float32) / 4.0
    boundary = _boundary_mask(grid).astype(np.float32)
    occupancy = (grid != 0).astype(np.float32)
    visible = tongue_bytes.astype(np.float32) / 255.0

    tri = np.empty((6, 3, *grid.shape), dtype=np.float32)
    tri[:, 0] = np.broadcast_to((0.7 * same + 0.3 * occupancy), grid.shape)
    tri[:, 1] = visible
    tri[:, 2] = np.broadcast_to((0.6 * boundary + 0.4 * (1.0 - same)), grid.shape)
    return tri


def _token_ids_from_tongue_bytes(tongue_bytes: np.ndarray) -> np.ndarray:
    """Translate lane-local bytes into fixed tokenizer IDs."""

    out = np.empty_like(tongue_bytes, dtype=np.int64)
    for lane, tongue in enumerate(_TONGUE_ORDER):
        offset = lane * 256
        out[lane] = offset + tongue_bytes[lane].astype(np.int64)
    return out


def _geoseal_radius_map(tongue_bytes: np.ndarray) -> np.ndarray:
    """Project each cell into a 6D context vector and measure hyperbolic radius."""

    _, h, w = tongue_bytes.shape
    anchor = ContextVector([0.0] * 6).to_poincare()
    radius = np.zeros((h, w), dtype=np.float32)
    for r in range(h):
        for c in range(w):
            vec = (tongue_bytes[:, r, c].astype(np.float64) / 127.5) - 1.0
            point = ContextVector(vec.tolist()).to_poincare()
            radius[r, c] = float(hyperbolic_distance(anchor, point))
    return radius


def encode_grid_structurally(grid: np.ndarray, target_size: int = 30) -> StructuralEncoding:
    """Build deterministic, fixed-shape features for ARC search / compilation."""

    from .arc_io import pad_grid

    padded = pad_grid(grid, target_size=target_size)
    tongue_bytes = _build_tongue_bytes(padded)
    token_ids = _token_ids_from_tongue_bytes(tongue_bytes)
    tri = _build_trichromatic_tensor(padded, tongue_bytes)
    radius = _geoseal_radius_map(tongue_bytes)
    component_labels, components = connected_components(padded)
    return StructuralEncoding(
        padded_grid=padded,
        tongue_bytes=tongue_bytes,
        tongue_token_ids=token_ids,
        trichromatic_tensor=tri,
        geo_radius=radius,
        component_labels=component_labels,
        components=components,
    )


def tokens_for_cell(encoding: StructuralEncoding, row: int, col: int) -> dict[str, str]:
    """Human-readable tokenizer surface for inspection and debugging."""

    return {
        tongue: _TOKENIZER.byte_to_token[tongue][int(encoding.tongue_bytes[idx, row, col])]
        for idx, tongue in enumerate(_TONGUE_ORDER)
    }
