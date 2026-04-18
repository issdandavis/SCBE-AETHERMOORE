from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ConnectedComponent:
    label: int
    color: int
    area: int
    row_min: int
    row_max: int
    col_min: int
    col_max: int

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (self.row_min, self.row_max, self.col_min, self.col_max)


def connected_components(
    grid: np.ndarray,
    *,
    background: int = 0,
    connectivity: int = 4,
) -> tuple[np.ndarray, tuple[ConnectedComponent, ...]]:
    """Label same-color connected components on an ARC grid.

    This runs on the compiler/search side. The final ONNX graph should still take
    only the task grid as input.
    """

    if connectivity not in {4, 8}:
        raise ValueError("connectivity must be 4 or 8")

    h, w = grid.shape
    labels = np.zeros((h, w), dtype=np.int64)
    components: list[ConnectedComponent] = []
    next_label = 1

    if connectivity == 4:
        neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))
    else:
        neighbors = (
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),
            (1, 1),
            (1, -1),
            (-1, 1),
            (-1, -1),
        )

    for row in range(h):
        for col in range(w):
            color = int(grid[row, col])
            if color == background or labels[row, col] != 0:
                continue

            queue: deque[tuple[int, int]] = deque([(row, col)])
            labels[row, col] = next_label
            coords: list[tuple[int, int]] = []

            while queue:
                r, c = queue.popleft()
                coords.append((r, c))
                for dr, dc in neighbors:
                    nr, nc = r + dr, c + dc
                    if nr < 0 or nr >= h or nc < 0 or nc >= w:
                        continue
                    if labels[nr, nc] != 0 or int(grid[nr, nc]) != color:
                        continue
                    labels[nr, nc] = next_label
                    queue.append((nr, nc))

            rows = [r for r, _ in coords]
            cols = [c for _, c in coords]
            components.append(
                ConnectedComponent(
                    label=next_label,
                    color=color,
                    area=len(coords),
                    row_min=min(rows),
                    row_max=max(rows),
                    col_min=min(cols),
                    col_max=max(cols),
                )
            )
            next_label += 1

    return labels, tuple(components)


def component_mask(label_map: np.ndarray, label: int) -> np.ndarray:
    return (label_map == label).astype(np.int64)


def extract_component(grid: np.ndarray, label_map: np.ndarray, label: int) -> np.ndarray:
    mask = component_mask(label_map, label).astype(bool)
    if not mask.any():
        raise ValueError(f"Unknown component label {label}")
    rows, cols = np.where(mask)
    row_min, row_max = rows.min(), rows.max()
    col_min, col_max = cols.min(), cols.max()
    cropped = np.zeros((row_max - row_min + 1, col_max - col_min + 1), dtype=grid.dtype)
    cropped_mask = mask[row_min : row_max + 1, col_min : col_max + 1]
    cropped[cropped_mask] = grid[row_min : row_max + 1, col_min : col_max + 1][cropped_mask]
    return cropped
