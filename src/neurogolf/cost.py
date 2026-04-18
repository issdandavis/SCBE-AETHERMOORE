from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class NetworkCost:
    parameters: int
    memory_bytes: int
    macs: int

    @property
    def total(self) -> int:
        return self.parameters + self.memory_bytes + self.macs


def tensor_nbytes(shape: tuple[int, ...], dtype_bytes: int = 4) -> int:
    total = dtype_bytes
    for dim in shape:
        total *= dim
    return total


def conv2d_parameter_count(
    out_channels: int,
    in_channels: int,
    kernel_h: int,
    kernel_w: int,
    *,
    bias: bool = True,
) -> int:
    params = out_channels * in_channels * kernel_h * kernel_w
    return params + (out_channels if bias else 0)


def conv2d_macs(
    out_h: int,
    out_w: int,
    out_channels: int,
    in_channels: int,
    kernel_h: int,
    kernel_w: int,
) -> int:
    return out_h * out_w * out_channels * in_channels * kernel_h * kernel_w


def score_from_total_cost(total_cost: int) -> float:
    if total_cost <= 0:
        raise ValueError("Total cost must be positive")
    return max(1.0, 25.0 - math.log(total_cost))
