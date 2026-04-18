from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ColorRemapCorridor:
    """Admissible corridor for same-shape global color remap families.

    `fixed_mapping` holds source colors whose destination is fully determined by
    all observed examples. `free_sources` are colors that have not appeared in
    the observations and therefore remain unconstrained inside the corridor.
    """

    fixed_mapping: dict[int, int]
    free_sources: frozenset[int]
    pinned_sources: frozenset[int]

    def is_total(self) -> bool:
        """Observed colors are fully constrained even if unseen colors remain free."""
        return True

    def materialize(self, *, identity_for_free: bool = False) -> dict[int, int] | None:
        """Collapse the corridor to one executable mapping.

        When `identity_for_free` is true, unconstrained colors are left as
        identity mappings. Otherwise only the pinned mapping is emitted and
        unseen colors remain outside the executable remap.
        """
        if not identity_for_free:
            return dict(self.fixed_mapping)
        mapping = dict(self.fixed_mapping)
        for src in self.free_sources:
            mapping[src] = src
        return mapping


def intersect_color_remap_corridors(
    mappings: Iterable[dict[int, int] | None],
    *,
    universe: Iterable[int] = range(10),
) -> ColorRemapCorridor | None:
    """Intersect per-example color mappings into one admissible corridor."""

    fixed: dict[int, int] = {}
    pinned: set[int] = set()
    for mapping in mappings:
        if mapping is None:
            return None
        for src, dst in mapping.items():
            prev = fixed.get(src)
            if prev is not None and prev != dst:
                return None
            fixed[src] = dst
            pinned.add(src)
    free = set(int(color) for color in universe) - pinned
    return ColorRemapCorridor(
        fixed_mapping=fixed,
        free_sources=frozenset(free),
        pinned_sources=frozenset(pinned),
    )


# ---------------------------------------------------------------------------
# Upscale corridor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UpscaleCorridor:
    """Admissible corridor for upscale (and optional post-upscale recolor).

    `scale_k` is always pinned — the integer scale factor inferred from all
    training examples must agree.  `color_remap_corridor` is None for a pure
    upscale (output = np.repeat(input, k)), or a ColorRemapCorridor when every
    training example matches upscale(input) up to a consistent color remap.
    """

    scale_k: int
    color_remap_corridor: ColorRemapCorridor | None

    def is_pure_upscale(self) -> bool:
        """True when no recolor step is needed (exact pixel repeat)."""
        return self.color_remap_corridor is None

    def materialize_color_remap(self) -> dict[int, int] | None:
        """Return the executable mapping for the recolor step.

        Returns None for pure upscale.  Free sources receive identity
        mappings so every observed color has a deterministic destination.
        """
        if self.color_remap_corridor is None:
            return None
        return self.color_remap_corridor.materialize(identity_for_free=True)
