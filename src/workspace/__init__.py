"""
SCBE AI Workspace Engine

A tree-structured cognitive workspace for AI processing, inspired by
Obsidian's workspace architecture but designed for AI-native use cases.

Obsidian gives humans splits, tabs, and leaves to organize how they
see knowledge. This engine gives AI the same primitives to organize
how it PROCESSES knowledge — what channels are active, what's linked,
what's deliberately null, and what layout (Sacred Egg) governs the
current cognitive configuration.

Core types:
    WorkspaceItem  — base node in the tree
    Split          — children processed in parallel (horizontal or vertical)
    Tabs           — one child active, others null (tongue routing)
    Leaf           — terminal processing node with a view type
    Workspace      — root container with left/root/right splits
    WorkspaceLayout — saveable/restorable configuration (Sacred Egg bridge)
"""

from .engine import (
    WorkspaceItem,
    Split,
    Tabs,
    Leaf,
    Workspace,
    WorkspaceLayout,
    Direction,
    ViewType,
)

__all__ = [
    "WorkspaceItem",
    "Split",
    "Tabs",
    "Leaf",
    "Workspace",
    "WorkspaceLayout",
    "Direction",
    "ViewType",
]
