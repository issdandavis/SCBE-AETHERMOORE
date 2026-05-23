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
from .dcp_routes import (  # noqa: F401
    GITHUB_COPILOT_PR_COMBO,
    TETRIS_TREE_PR_PIECES,
    TETRIS_TREE_PR_SLOTS,
    approved_agentic_tools,
    copilot_command_route,
    create_github_pr_dcp,
    github_command_route,
    route_tetris_tree,
)
