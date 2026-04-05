"""
AI Workspace Engine — tree-structured cognitive workspace.

The workspace is a tree where each node is a WorkspaceItem.
Parent items (Split, Tabs) contain children.
Leaf items are terminal processing nodes.

The key insight: Obsidian's workspace hides tabs you're not looking at.
The AI workspace hides TONGUES the model shouldn't process — the null
tongue pattern IS a tabs configuration. When KO is active and
[AV, RU, CA, UM] are null, that's a Tabs node with KO's leaf visible
and four leaves hidden.

This means every training record already encodes a workspace state.
This engine makes that structure explicit and manipulable.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Direction(Enum):
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


class ViewType(Enum):
    """Leaf view types — what kind of processing this leaf performs."""
    # Tongue views (one per sacred tongue)
    TONGUE_KO = "tongue_ko"    # Control/orchestration
    TONGUE_AV = "tongue_av"    # Data flow
    TONGUE_RU = "tongue_ru"    # Rules/constraints
    TONGUE_CA = "tongue_ca"    # Computation
    TONGUE_UM = "tongue_um"    # Risk/uncertainty
    TONGUE_DR = "tongue_dr"    # Structure/lore

    # Layer views
    SUBSTRATE = "substrate"       # L0 — binary invariants
    COORDINATION = "coordination" # L1 — token patterns
    ORIENTATION = "orientation"   # L2 — intent classification
    EXPRESSION = "expression"     # L3 — natural language output

    # Functional views
    GOVERNANCE = "governance"   # L13 — decision gate
    GRAPH = "graph"             # Relation view (like Obsidian's graph)
    OUTLINE = "outline"         # Structure view
    ACTIVATION = "activation"   # FU status monitor
    FLOW = "flow"               # Routing/fractional angle
    LINKED = "linked"           # Cross-reference view

    # Meta
    EMPTY = "empty"             # Placeholder / unassigned


# Tongue ↔ ViewType mapping
TONGUE_VIEWS = {
    "KO": ViewType.TONGUE_KO,
    "AV": ViewType.TONGUE_AV,
    "RU": ViewType.TONGUE_RU,
    "CA": ViewType.TONGUE_CA,
    "UM": ViewType.TONGUE_UM,
    "DR": ViewType.TONGUE_DR,
}

TONGUE_NAMES = {v: k for k, v in TONGUE_VIEWS.items()}


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

@dataclass
class WorkspaceItem:
    """Base node in the workspace tree."""
    id: str = ""
    parent: Optional[WorkspaceItem] = field(default=None, repr=False)

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.sha256(
                f"{type(self).__name__}_{id(self)}_{time.time_ns()}".encode()
            ).hexdigest()[:12]

    @property
    def item_type(self) -> str:
        return type(self).__name__.lower()

    @property
    def depth(self) -> int:
        """Distance from root."""
        d = 0
        node = self.parent
        while node is not None:
            d += 1
            node = node.parent
        return d

    @property
    def path(self) -> list[str]:
        """Path from root to this node."""
        parts = []
        node: Optional[WorkspaceItem] = self
        while node is not None:
            parts.append(node.id)
            node = node.parent
        return list(reversed(parts))

    def detach(self):
        """Remove this item from its parent."""
        if self.parent is not None and isinstance(self.parent, _ParentItem):
            self.parent._children = [c for c in self.parent._children if c is not self]
            self.parent = None

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.item_type, "id": self.id}


# ---------------------------------------------------------------------------
# Parent items
# ---------------------------------------------------------------------------

@dataclass
class _ParentItem(WorkspaceItem):
    """Internal base for items that contain children."""
    _children: list[WorkspaceItem] = field(default_factory=list, repr=False)

    @property
    def children(self) -> list[WorkspaceItem]:
        return list(self._children)

    def add_child(self, item: WorkspaceItem) -> WorkspaceItem:
        if item.parent is not None:
            item.detach()
        item.parent = self
        self._children.append(item)
        return item

    def insert_child(self, index: int, item: WorkspaceItem) -> WorkspaceItem:
        if item.parent is not None:
            item.detach()
        item.parent = self
        self._children.insert(index, item)
        return item

    def remove_child(self, item: WorkspaceItem):
        item.detach()

    @property
    def leaf_count(self) -> int:
        count = 0
        for child in self._children:
            if isinstance(child, Leaf):
                count += 1
            elif isinstance(child, _ParentItem):
                count += child.leaf_count
        return count

    def iterate_leaves(self):
        """Yield all leaves under this node."""
        for child in self._children:
            if isinstance(child, Leaf):
                yield child
            elif isinstance(child, _ParentItem):
                yield from child.iterate_leaves()


@dataclass
class Split(_ParentItem):
    """Lays out children side by side (parallel processing channels)."""
    direction: Direction = Direction.HORIZONTAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "split",
            "id": self.id,
            "direction": self.direction.value,
            "children": [c.to_dict() for c in self._children],
        }


@dataclass
class Tabs(_ParentItem):
    """Shows one child at a time, others are null/hidden.

    This is the tongue router: the active leaf is the active tongue,
    hidden leaves are null tongues. Switching tabs = changing which
    tongue processes the input.
    """
    _active_index: int = 0

    @property
    def active_index(self) -> int:
        if not self._children:
            return 0
        return min(self._active_index, len(self._children) - 1)

    @active_index.setter
    def active_index(self, value: int):
        self._active_index = max(0, min(value, len(self._children) - 1))

    @property
    def active_leaf(self) -> Optional[WorkspaceItem]:
        if not self._children:
            return None
        return self._children[self.active_index]

    @property
    def null_leaves(self) -> list[WorkspaceItem]:
        """Leaves that are NOT active — the absence signal."""
        return [c for i, c in enumerate(self._children) if i != self.active_index]

    def activate(self, item_or_id):
        """Switch to a specific tab by item or ID."""
        for i, child in enumerate(self._children):
            if child is item_or_id or child.id == item_or_id:
                self._active_index = i
                return
        raise ValueError(f"Item not found in tabs: {item_or_id}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "tabs",
            "id": self.id,
            "active_index": self.active_index,
            "children": [c.to_dict() for c in self._children],
        }


# ---------------------------------------------------------------------------
# Leaf
# ---------------------------------------------------------------------------

@dataclass
class Leaf(WorkspaceItem):
    """Terminal processing node with a view type.

    A leaf is one perspective on the data. Its view_type determines
    what kind of processing it represents. Leaves in the same group
    are linked — when one updates, the others react.
    """
    view_type: ViewType = ViewType.EMPTY
    group: Optional[str] = None
    state: dict[str, Any] = field(default_factory=dict)
    pinned: bool = False

    @property
    def is_tongue(self) -> bool:
        return self.view_type.value.startswith("tongue_")

    @property
    def tongue_name(self) -> Optional[str]:
        return TONGUE_NAMES.get(self.view_type)

    def get_view_state(self) -> dict[str, Any]:
        return {
            "type": self.view_type.value,
            "state": self.state,
            "group": self.group,
            "pinned": self.pinned,
        }

    def set_group(self, group: str):
        """Assign this leaf to a linked group."""
        self.group = group

    def to_dict(self) -> dict[str, Any]:
        d = {
            "type": "leaf",
            "id": self.id,
            "view_type": self.view_type.value,
        }
        if self.group:
            d["group"] = self.group
        if self.state:
            d["state"] = self.state
        if self.pinned:
            d["pinned"] = True
        return d


# ---------------------------------------------------------------------------
# Workspace — the root container
# ---------------------------------------------------------------------------

class Workspace:
    """Root workspace with left/root/right splits.

    Mirrors Obsidian's three-region layout:
    - left:  sidebar processing (auxiliary views, monitoring)
    - root:  main processing (primary tongue/layer views)
    - right: sidebar processing (governance, linked views)

    For AI, this maps to:
    - left:  context/history channels
    - root:  active processing pipeline (tongue tabs + layer splits)
    - right: governance and meta-processing
    """

    def __init__(self):
        self.left = Split(id="left", direction=Direction.VERTICAL)
        self.root = Split(id="root", direction=Direction.VERTICAL)
        self.right = Split(id="right", direction=Direction.VERTICAL)
        self._layouts: dict[str, WorkspaceLayout] = {}

    # -- Leaf creation helpers --

    def create_leaf_in_root(self, view_type: ViewType = ViewType.EMPTY,
                            **state) -> Leaf:
        """Add a new leaf to the root split."""
        leaf = Leaf(view_type=view_type, state=state)
        self.root.add_child(leaf)
        return leaf

    def create_leaf_in_left(self, view_type: ViewType = ViewType.EMPTY,
                            new_tab_group: bool = True, **state) -> Leaf:
        """Add a leaf to the left sidebar. Creates a new tabs group if requested."""
        leaf = Leaf(view_type=view_type, state=state)
        if new_tab_group:
            tabs = Tabs()
            self.left.add_child(tabs)
            tabs.add_child(leaf)
        else:
            # Add to last tabs group
            if self.left.children and isinstance(self.left.children[-1], Tabs):
                self.left.children[-1].add_child(leaf)
            else:
                tabs = Tabs()
                self.left.add_child(tabs)
                tabs.add_child(leaf)
        return leaf

    def create_leaf_in_right(self, view_type: ViewType = ViewType.EMPTY,
                             new_tab_group: bool = True, **state) -> Leaf:
        """Add a leaf to the right sidebar."""
        leaf = Leaf(view_type=view_type, state=state)
        if new_tab_group:
            tabs = Tabs()
            self.right.add_child(tabs)
            tabs.add_child(leaf)
        else:
            if self.right.children and isinstance(self.right.children[-1], Tabs):
                self.right.children[-1].add_child(leaf)
            else:
                tabs = Tabs()
                self.right.add_child(tabs)
                tabs.add_child(leaf)
        return leaf

    def create_tongue_tabs(self, active_tongue: str = "KO",
                           null_tongues: list[str] | None = None) -> Tabs:
        """Create a tabs group with tongue leaves.

        This is the core workspace primitive: a Tabs node where the
        active tab is the processing tongue and the rest are null.
        Exactly mirrors the training data's tongues_active/tongues_null.
        """
        all_tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
        if null_tongues is None:
            null_tongues = [t for t in all_tongues if t != active_tongue]

        tabs = Tabs()
        active_idx = 0

        # Add all tongues that are either active or in the null list.
        # Tongues not in either set are excluded entirely (custom configs).
        included = {active_tongue} | set(null_tongues)
        for tongue in all_tongues:
            if tongue not in included:
                continue
            view = TONGUE_VIEWS[tongue]
            leaf = Leaf(view_type=view, state={"tongue": tongue})
            tabs.add_child(leaf)
            if tongue == active_tongue:
                active_idx = len(tabs.children) - 1

        tabs.active_index = active_idx
        self.root.add_child(tabs)
        return tabs

    def create_layer_split(self, layers: list[str] | None = None,
                           direction: Direction = Direction.HORIZONTAL) -> Split:
        """Create a split with one leaf per layer.

        Layers processed in parallel = horizontal split.
        Layers processed in sequence = vertical split.
        """
        if layers is None:
            layers = ["L0", "L1", "L2", "L3"]

        layer_views = {
            "L0": ViewType.SUBSTRATE,
            "L1": ViewType.COORDINATION,
            "L2": ViewType.ORIENTATION,
            "L3": ViewType.EXPRESSION,
        }

        split = Split(direction=direction)
        for layer in layers:
            view = layer_views.get(layer, ViewType.EMPTY)
            leaf = Leaf(view_type=view, state={"layer": layer})
            split.add_child(leaf)

        self.root.add_child(split)
        return split

    # -- Iteration --

    def iterate_all_leaves(self):
        """Yield every leaf in the workspace."""
        yield from self.left.iterate_leaves()
        yield from self.root.iterate_leaves()
        yield from self.right.iterate_leaves()

    def get_leaves_of_type(self, view_type: ViewType) -> list[Leaf]:
        return [l for l in self.iterate_all_leaves() if l.view_type == view_type]

    def get_active_leaves(self) -> list[Leaf]:
        """Get all currently-visible leaves (not hidden by tabs)."""
        active = []
        self._collect_active(self.left, active)
        self._collect_active(self.root, active)
        self._collect_active(self.right, active)
        return active

    def get_null_leaves(self) -> list[Leaf]:
        """Get all hidden/null leaves (hidden by tabs)."""
        null = []
        self._collect_null(self.left, null)
        self._collect_null(self.root, null)
        self._collect_null(self.right, null)
        return null

    def _collect_active(self, node: WorkspaceItem, out: list):
        if isinstance(node, Leaf):
            out.append(node)
        elif isinstance(node, Tabs):
            active = node.active_leaf
            if active is not None:
                self._collect_active(active, out)
        elif isinstance(node, Split):
            for child in node.children:
                self._collect_active(child, out)

    def _collect_null(self, node: WorkspaceItem, out: list):
        if isinstance(node, Tabs):
            for leaf in node.null_leaves:
                if isinstance(leaf, Leaf):
                    out.append(leaf)
                elif isinstance(leaf, _ParentItem):
                    out.extend(leaf.iterate_leaves())
            # Also recurse into active to find nested null
            active = node.active_leaf
            if active is not None and isinstance(active, _ParentItem):
                self._collect_null(active, out)
        elif isinstance(node, Split):
            for child in node.children:
                self._collect_null(child, out)

    def get_linked_group(self, group: str) -> list[Leaf]:
        """Get all leaves in a linked group."""
        return [l for l in self.iterate_all_leaves() if l.group == group]

    # -- Tongue state extraction (bridges to training data) --

    def get_tongue_state(self) -> dict[str, Any]:
        """Extract the current tongue activation state.

        Returns the same format as training data:
        {"tongues_active": [...], "tongues_null": [...]}
        """
        active_tongues = []
        null_tongues = []

        for leaf in self.iterate_all_leaves():
            if not leaf.is_tongue:
                continue
            tongue = leaf.tongue_name
            # Check if this leaf is visible (active path from root)
            if leaf in self.get_active_leaves():
                active_tongues.append(tongue)
            else:
                null_tongues.append(tongue)

        return {
            "tongues_active": active_tongues,
            "tongues_null": null_tongues,
        }

    def get_active_views(self) -> list[str]:
        """Get view types of all active (visible) leaves."""
        return [l.view_type.value for l in self.get_active_leaves()]

    # -- Layout save/restore (Sacred Egg bridge) --

    def save_layout(self, name: str, metadata: dict | None = None) -> WorkspaceLayout:
        """Save current workspace state as a named layout."""
        layout = WorkspaceLayout(
            name=name,
            tree=self.to_dict(),
            tongue_state=self.get_tongue_state(),
            active_views=self.get_active_views(),
            metadata=metadata or {},
        )
        self._layouts[name] = layout
        return layout

    def list_layouts(self) -> list[str]:
        return list(self._layouts.keys())

    def get_layout(self, name: str) -> Optional[WorkspaceLayout]:
        return self._layouts.get(name)

    # -- Serialization --

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "workspace",
            "left": self.left.to_dict(),
            "root": self.root.to_dict(),
            "right": self.right.to_dict(),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> Workspace:
        """Reconstruct workspace from serialized dict."""
        ws = cls()
        ws.left = _rebuild_item(data.get("left", {}))
        ws.root = _rebuild_item(data.get("root", {}))
        ws.right = _rebuild_item(data.get("right", {}))
        return ws

    # -- Training data bridge --

    def to_training_record(self, instruction: str = "", response: str = "",
                           layer: str = "L0", governance: str = "ALLOW",
                           category: str = "workspace_state") -> dict[str, Any]:
        """Export current workspace state as an SFT-compatible training record.

        This is the key bridge: every workspace configuration IS a training
        sample that teaches the model how to organize its processing.
        """
        tongue_state = self.get_tongue_state()
        active = tongue_state["tongues_active"]
        null = tongue_state["tongues_null"]

        return {
            "instruction": instruction,
            "output": response,
            "layer": layer,
            "tongue": active[0] if active else "KO",
            "tongues_active": active,
            "tongues_null": null,
            "category": category,
            "governance": governance,
            "workspace": {
                "active_views": self.get_active_views(),
                "leaf_count": sum(1 for _ in self.iterate_all_leaves()),
                "active_count": len(self.get_active_leaves()),
                "null_count": len(self.get_null_leaves()),
                "depth": max((l.depth for l in self.iterate_all_leaves()), default=0),
            },
        }

    def __repr__(self) -> str:
        total = sum(1 for _ in self.iterate_all_leaves())
        active = len(self.get_active_leaves())
        return f"Workspace(leaves={total}, active={active}, null={total - active})"


# ---------------------------------------------------------------------------
# WorkspaceLayout — saved configuration (Sacred Egg bridge)
# ---------------------------------------------------------------------------

@dataclass
class WorkspaceLayout:
    """A saved workspace configuration.

    In SCBE terms, this is a Sacred Egg: a frozen cognitive state
    that can be hatched to restore a specific processing configuration.

    name:         Layout identifier
    tree:         Serialized workspace tree
    tongue_state: Which tongues were active/null
    active_views: Which view types were visible
    metadata:     Arbitrary metadata (timestamp, source, ritual type)
    """
    name: str
    tree: dict[str, Any]
    tongue_state: dict[str, Any]
    active_views: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tree": self.tree,
            "tongue_state": self.tongue_state,
            "active_views": self.active_views,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> WorkspaceLayout:
        return cls(
            name=data["name"],
            tree=data["tree"],
            tongue_state=data["tongue_state"],
            active_views=data["active_views"],
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Reconstruction helper
# ---------------------------------------------------------------------------

def _rebuild_item(data: dict) -> WorkspaceItem:
    """Rebuild a workspace item from serialized dict."""
    item_type = data.get("type", "leaf")

    if item_type == "split":
        split = Split(
            id=data.get("id", ""),
            direction=Direction(data.get("direction", "horizontal")),
        )
        for child_data in data.get("children", []):
            child = _rebuild_item(child_data)
            split.add_child(child)
        return split

    elif item_type == "tabs":
        tabs = Tabs(id=data.get("id", ""))
        for child_data in data.get("children", []):
            child = _rebuild_item(child_data)
            tabs.add_child(child)
        tabs.active_index = data.get("active_index", 0)
        return tabs

    elif item_type == "leaf":
        vt = data.get("view_type", "empty")
        try:
            view_type = ViewType(vt)
        except ValueError:
            view_type = ViewType.EMPTY
        return Leaf(
            id=data.get("id", ""),
            view_type=view_type,
            group=data.get("group"),
            state=data.get("state", {}),
            pinned=data.get("pinned", False),
        )

    return WorkspaceItem(id=data.get("id", ""))


# ---------------------------------------------------------------------------
# Preset workspaces (common configurations)
# ---------------------------------------------------------------------------

def create_single_tongue_workspace(tongue: str = "KO") -> Workspace:
    """Simplest workspace: one tongue active, others null.
    Maps to the most common training record pattern."""
    ws = Workspace()
    ws.create_tongue_tabs(active_tongue=tongue)
    ws.create_leaf_in_right(ViewType.GOVERNANCE, governance="active")
    return ws


def create_multi_view_workspace(tongue: str = "KO",
                                 layers: list[str] | None = None) -> Workspace:
    """Full multi-view: tongue tabs + layer split + governance sidebar."""
    ws = Workspace()
    ws.create_tongue_tabs(active_tongue=tongue)
    ws.create_layer_split(layers or ["L0", "L1", "L2", "L3"])
    ws.create_leaf_in_left(ViewType.GRAPH, graph_type="local")
    ws.create_leaf_in_right(ViewType.GOVERNANCE, governance="active")
    ws.create_leaf_in_right(ViewType.ACTIVATION, new_tab_group=True)
    return ws


def create_governance_workspace() -> Workspace:
    """Governance-focused: all tongues visible in split, governance + flow prominent."""
    ws = Workspace()

    # All tongues in a horizontal split (parallel processing)
    tongue_split = Split(direction=Direction.HORIZONTAL)
    for tongue in ["KO", "AV", "RU", "CA", "UM", "DR"]:
        view = TONGUE_VIEWS[tongue]
        leaf = Leaf(view_type=view, state={"tongue": tongue})
        tongue_split.add_child(leaf)
    ws.root.add_child(tongue_split)

    ws.create_leaf_in_right(ViewType.GOVERNANCE, governance="active")
    ws.create_leaf_in_right(ViewType.FLOW, new_tab_group=True)
    ws.create_leaf_in_left(ViewType.OUTLINE, outline_type="governance")
    return ws


def workspace_from_training_record(record: dict) -> Workspace:
    """Reconstruct a workspace from an existing training record.

    This closes the loop: training records encode workspace states,
    and we can reconstruct the workspace from any record.
    """
    tongues_active = record.get("tongues_active", [record.get("tongue", "KO")])
    tongues_null = record.get("tongues_null", [])
    layer = record.get("layer", "L0")
    governance = record.get("governance", "ALLOW")

    ws = Workspace()

    # Build tongue tabs from the record's tongue state
    if tongues_active:
        active = tongues_active[0]
        ws.create_tongue_tabs(active_tongue=active, null_tongues=tongues_null)

    # Add layer view
    layer_map = {"L0": ViewType.SUBSTRATE, "L1": ViewType.COORDINATION,
                 "L2": ViewType.ORIENTATION, "L3": ViewType.EXPRESSION}
    view = layer_map.get(layer, ViewType.SUBSTRATE)
    ws.create_leaf_in_root(view, layer=layer)

    # Governance sidebar
    ws.create_leaf_in_right(ViewType.GOVERNANCE, decision=governance)

    return ws
