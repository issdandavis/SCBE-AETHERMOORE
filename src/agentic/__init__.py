"""Python package surface for src/agentic.

The TypeScript modules in this directory are imported by the Node side; the
Python modules here are imported by the bus, the meet-in-the-middle codegen
protocol, and related tooling.
"""

from .meet_in_the_middle import (  # noqa: F401
    CodeHalf,
    MergeReport,
    SEAM_MARKER,
    SeamContract,
    merge_halves,
)
