"""SCBE Full System Bench — aggregation harness.

Exposes :func:`run_full_bench`, which rolls every locally-available
benchmark/capability lane into a single "SCBE Full System Bench v1"
scorecard. See :mod:`src.bench.full_bench` for the lane definitions.
"""

from src.bench.full_bench import (  # noqa: F401
    LANE_KEYS,
    SCHEMA_VERSION,
    STATUS_VALUES,
    run_full_bench,
)

__all__ = ["run_full_bench", "LANE_KEYS", "SCHEMA_VERSION", "STATUS_VALUES"]
