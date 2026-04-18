from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


GridLike = Iterable[Iterable[int]]


@dataclass(frozen=True)
class ARCExample:
    input: np.ndarray
    output: np.ndarray


@dataclass(frozen=True)
class ARCTask:
    task_id: str
    train: tuple[ARCExample, ...]
    test_inputs: tuple[np.ndarray, ...]
    source_path: Path


def _as_grid(data: GridLike) -> np.ndarray:
    grid = np.asarray(list(list(int(v) for v in row) for row in data), dtype=np.int64)
    if grid.ndim != 2:
        raise ValueError(f"ARC grids must be rank-2, got shape {grid.shape}")
    if grid.shape[0] == 0 or grid.shape[1] == 0:
        raise ValueError("ARC grids must be non-empty")
    if np.any((grid < 0) | (grid > 9)):
        raise ValueError("ARC grid colors must stay in the range [0, 9]")
    return grid


def load_arc_task(path: str | Path) -> ARCTask:
    """Load one ARC task JSON file into fixed Python dataclasses."""

    source_path = Path(path)
    raw: dict[str, Any] = json.loads(source_path.read_text(encoding="utf-8"))
    train = tuple(
        ARCExample(input=_as_grid(example["input"]), output=_as_grid(example["output"]))
        for example in raw.get("train", [])
    )
    test_inputs = tuple(_as_grid(example["input"]) for example in raw.get("test", []))
    return ARCTask(
        task_id=source_path.stem,
        train=train,
        test_inputs=test_inputs,
        source_path=source_path,
    )


def pad_grid(grid: np.ndarray, target_size: int = 30, pad_value: int = 0) -> np.ndarray:
    """Pad a 2D ARC grid to a static square shape."""

    h, w = grid.shape
    if h > target_size or w > target_size:
        raise ValueError(f"Grid shape {grid.shape} exceeds target size {target_size}")
    out = np.full((target_size, target_size), pad_value, dtype=grid.dtype)
    out[:h, :w] = grid
    return out


def grid_to_one_hot(
    grid: np.ndarray,
    *,
    num_colors: int = 10,
    target_size: int | None = 30,
    dtype: np.dtype = np.float32,
) -> np.ndarray:
    """Convert an ARC color grid into a static `[C, H, W]` one-hot tensor."""

    if target_size is not None:
        grid = pad_grid(grid, target_size=target_size)
    h, w = grid.shape
    one_hot = np.zeros((num_colors, h, w), dtype=dtype)
    rows, cols = np.indices((h, w))
    one_hot[grid, rows, cols] = 1.0
    return one_hot
