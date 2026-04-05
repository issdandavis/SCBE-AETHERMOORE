"""
Test suite for the AI Workspace Engine.

Tests the full alphabet:
  A. Tree structure (parent/child, depth, path)
  B. Split behavior (direction, parallel children)
  C. Tabs behavior (active/null selection, switching)
  D. Leaf properties (view type, tongue detection, groups)
  E. Workspace regions (left/root/right)
  F. Tongue tabs (active/null mapping, state extraction)
  G. Layer splits (parallel/sequential processing)
  H. Iteration (all leaves, active leaves, null leaves, by type)
  I. Linked groups (cross-reference views)
  J. Serialization (to_dict, to_json, round-trip)
  K. Layout save/restore (Sacred Egg bridge)
  L. Training record bridge (workspace → SFT record)
  M. Preset workspaces (single tongue, multi-view, governance)
  N. Reconstruction from training record (record → workspace)
  O. Edge cases (empty workspace, detach, deep nesting)
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from workspace import (
    WorkspaceItem, Split, Tabs, Leaf, Workspace, WorkspaceLayout,
    Direction, ViewType,
)
from workspace.engine import (
    TONGUE_VIEWS, TONGUE_NAMES,
    create_single_tongue_workspace,
    create_multi_view_workspace,
    create_governance_workspace,
    workspace_from_training_record,
    _rebuild_item,
)


# ===========================================================================
# A. TREE STRUCTURE
# ===========================================================================

class TestTreeStructure:
    def test_item_gets_unique_id(self):
        a = WorkspaceItem()
        b = WorkspaceItem()
        assert a.id != b.id

    def test_explicit_id(self):
        item = WorkspaceItem(id="custom")
        assert item.id == "custom"

    def test_depth_root_is_zero(self):
        item = WorkspaceItem()
        assert item.depth == 0

    def test_depth_increases_with_nesting(self):
        split = Split()
        tabs = Tabs()
        leaf = Leaf()
        split.add_child(tabs)
        tabs.add_child(leaf)
        assert split.depth == 0
        assert tabs.depth == 1
        assert leaf.depth == 2

    def test_path_from_root(self):
        split = Split(id="s")
        tabs = Tabs(id="t")
        leaf = Leaf(id="l")
        split.add_child(tabs)
        tabs.add_child(leaf)
        assert leaf.path == ["s", "t", "l"]

    def test_parent_reference(self):
        split = Split()
        leaf = Leaf()
        split.add_child(leaf)
        assert leaf.parent is split

    def test_detach_removes_from_parent(self):
        split = Split()
        leaf = Leaf()
        split.add_child(leaf)
        leaf.detach()
        assert leaf.parent is None
        assert leaf not in split.children


# ===========================================================================
# B. SPLIT BEHAVIOR
# ===========================================================================

class TestSplit:
    def test_default_direction_horizontal(self):
        s = Split()
        assert s.direction == Direction.HORIZONTAL

    def test_vertical_direction(self):
        s = Split(direction=Direction.VERTICAL)
        assert s.direction == Direction.VERTICAL

    def test_add_multiple_children(self):
        s = Split()
        l1 = Leaf(view_type=ViewType.SUBSTRATE)
        l2 = Leaf(view_type=ViewType.EXPRESSION)
        s.add_child(l1)
        s.add_child(l2)
        assert len(s.children) == 2

    def test_insert_child_at_index(self):
        s = Split()
        l1 = Leaf(id="first")
        l2 = Leaf(id="second")
        l3 = Leaf(id="middle")
        s.add_child(l1)
        s.add_child(l2)
        s.insert_child(1, l3)
        assert s.children[1].id == "middle"

    def test_leaf_count(self):
        s = Split()
        s.add_child(Leaf())
        s.add_child(Leaf())
        nested = Split()
        nested.add_child(Leaf())
        s.add_child(nested)
        assert s.leaf_count == 3

    def test_item_type(self):
        assert Split().item_type == "split"


# ===========================================================================
# C. TABS BEHAVIOR
# ===========================================================================

class TestTabs:
    def test_active_index_default_zero(self):
        tabs = Tabs()
        tabs.add_child(Leaf(id="a"))
        tabs.add_child(Leaf(id="b"))
        assert tabs.active_index == 0

    def test_active_leaf(self):
        tabs = Tabs()
        l1 = Leaf(id="a")
        l2 = Leaf(id="b")
        tabs.add_child(l1)
        tabs.add_child(l2)
        assert tabs.active_leaf is l1

    def test_null_leaves(self):
        tabs = Tabs()
        l1 = Leaf(id="a")
        l2 = Leaf(id="b")
        l3 = Leaf(id="c")
        tabs.add_child(l1)
        tabs.add_child(l2)
        tabs.add_child(l3)
        assert len(tabs.null_leaves) == 2
        assert l1 not in tabs.null_leaves

    def test_activate_by_id(self):
        tabs = Tabs()
        l1 = Leaf(id="a")
        l2 = Leaf(id="b")
        tabs.add_child(l1)
        tabs.add_child(l2)
        tabs.activate("b")
        assert tabs.active_leaf is l2

    def test_activate_by_item(self):
        tabs = Tabs()
        l1 = Leaf(id="a")
        l2 = Leaf(id="b")
        tabs.add_child(l1)
        tabs.add_child(l2)
        tabs.activate(l2)
        assert tabs.active_leaf is l2

    def test_activate_invalid_raises(self):
        tabs = Tabs()
        tabs.add_child(Leaf(id="a"))
        with pytest.raises(ValueError):
            tabs.activate("nonexistent")

    def test_empty_tabs_active_is_none(self):
        tabs = Tabs()
        assert tabs.active_leaf is None

    def test_active_index_clamped(self):
        tabs = Tabs()
        tabs.add_child(Leaf())
        tabs._active_index = 99
        assert tabs.active_index == 0  # clamped to len-1

    def test_item_type(self):
        assert Tabs().item_type == "tabs"


# ===========================================================================
# D. LEAF PROPERTIES
# ===========================================================================

class TestLeaf:
    def test_default_view_type_empty(self):
        assert Leaf().view_type == ViewType.EMPTY

    def test_is_tongue(self):
        assert Leaf(view_type=ViewType.TONGUE_KO).is_tongue
        assert not Leaf(view_type=ViewType.GOVERNANCE).is_tongue

    def test_tongue_name(self):
        assert Leaf(view_type=ViewType.TONGUE_DR).tongue_name == "DR"
        assert Leaf(view_type=ViewType.GOVERNANCE).tongue_name is None

    def test_get_view_state(self):
        leaf = Leaf(view_type=ViewType.SUBSTRATE, group="g1", pinned=True)
        vs = leaf.get_view_state()
        assert vs["type"] == "substrate"
        assert vs["group"] == "g1"
        assert vs["pinned"] is True

    def test_set_group(self):
        leaf = Leaf()
        leaf.set_group("analysis")
        assert leaf.group == "analysis"

    def test_item_type(self):
        assert Leaf().item_type == "leaf"


# ===========================================================================
# E. WORKSPACE REGIONS
# ===========================================================================

class TestWorkspaceRegions:
    def test_three_regions_exist(self):
        ws = Workspace()
        assert ws.left.id == "left"
        assert ws.root.id == "root"
        assert ws.right.id == "right"

    def test_regions_are_vertical_splits(self):
        ws = Workspace()
        assert ws.left.direction == Direction.VERTICAL
        assert ws.root.direction == Direction.VERTICAL
        assert ws.right.direction == Direction.VERTICAL

    def test_create_leaf_in_root(self):
        ws = Workspace()
        leaf = ws.create_leaf_in_root(ViewType.SUBSTRATE)
        assert leaf.view_type == ViewType.SUBSTRATE
        assert leaf in list(ws.root.iterate_leaves())

    def test_create_leaf_in_left_creates_tabs(self):
        ws = Workspace()
        ws.create_leaf_in_left(ViewType.GRAPH)
        # Left sidebar should have a Tabs child
        assert len(ws.left.children) == 1
        assert isinstance(ws.left.children[0], Tabs)

    def test_create_leaf_in_right(self):
        ws = Workspace()
        ws.create_leaf_in_right(ViewType.GOVERNANCE)
        assert len(ws.right.children) == 1
        assert isinstance(ws.right.children[0], Tabs)

    def test_add_to_existing_tab_group(self):
        ws = Workspace()
        ws.create_leaf_in_left(ViewType.GRAPH)
        ws.create_leaf_in_left(ViewType.OUTLINE, new_tab_group=False)
        # Should still be 1 tabs group with 2 leaves
        assert len(ws.left.children) == 1
        assert ws.left.children[0].leaf_count == 2


# ===========================================================================
# F. TONGUE TABS
# ===========================================================================

class TestTongueTabs:
    def test_create_tongue_tabs_default(self):
        ws = Workspace()
        tabs = ws.create_tongue_tabs("KO")
        assert tabs.leaf_count == 6
        assert tabs.active_leaf.view_type == ViewType.TONGUE_KO

    def test_null_tongues(self):
        ws = Workspace()
        tabs = ws.create_tongue_tabs("CA")
        null = tabs.null_leaves
        null_types = {l.view_type for l in null}
        assert ViewType.TONGUE_CA not in null_types
        assert len(null) == 5

    def test_tongue_state_extraction(self):
        ws = Workspace()
        ws.create_tongue_tabs("RU")
        state = ws.get_tongue_state()
        assert "RU" in state["tongues_active"]
        assert "RU" not in state["tongues_null"]
        assert len(state["tongues_null"]) == 5

    def test_custom_null_tongues(self):
        ws = Workspace()
        tabs = ws.create_tongue_tabs("KO", null_tongues=["AV", "RU"])
        # KO (active) + AV, RU (null) = 3 leaves in the tabs
        assert tabs.leaf_count == 3

    def test_switch_tongue(self):
        ws = Workspace()
        tabs = ws.create_tongue_tabs("KO")
        # Find DR leaf and activate it
        for child in tabs.children:
            if isinstance(child, Leaf) and child.tongue_name == "DR":
                tabs.activate(child)
                break
        state = ws.get_tongue_state()
        assert "DR" in state["tongues_active"]
        assert "KO" in state["tongues_null"]


# ===========================================================================
# G. LAYER SPLITS
# ===========================================================================

class TestLayerSplits:
    def test_default_four_layers(self):
        ws = Workspace()
        split = ws.create_layer_split()
        assert split.leaf_count == 4

    def test_custom_layers(self):
        ws = Workspace()
        split = ws.create_layer_split(["L0", "L3"])
        assert split.leaf_count == 2

    def test_direction(self):
        ws = Workspace()
        split = ws.create_layer_split(direction=Direction.VERTICAL)
        assert split.direction == Direction.VERTICAL

    def test_layer_view_types(self):
        ws = Workspace()
        split = ws.create_layer_split(["L0", "L1", "L2", "L3"])
        types = [l.view_type for l in split.iterate_leaves()]
        assert ViewType.SUBSTRATE in types
        assert ViewType.COORDINATION in types
        assert ViewType.ORIENTATION in types
        assert ViewType.EXPRESSION in types


# ===========================================================================
# H. ITERATION
# ===========================================================================

class TestIteration:
    def test_iterate_all_leaves(self):
        ws = Workspace()
        ws.create_leaf_in_root(ViewType.SUBSTRATE)
        ws.create_leaf_in_left(ViewType.GRAPH)
        ws.create_leaf_in_right(ViewType.GOVERNANCE)
        all_leaves = list(ws.iterate_all_leaves())
        assert len(all_leaves) == 3

    def test_get_active_leaves_from_tabs(self):
        ws = Workspace()
        tabs = ws.create_tongue_tabs("KO")
        active = ws.get_active_leaves()
        # Only KO should be active
        tongue_active = [l for l in active if l.is_tongue]
        assert len(tongue_active) == 1
        assert tongue_active[0].tongue_name == "KO"

    def test_get_null_leaves_from_tabs(self):
        ws = Workspace()
        ws.create_tongue_tabs("KO")
        null = ws.get_null_leaves()
        null_tongues = {l.tongue_name for l in null if l.is_tongue}
        assert "KO" not in null_tongues
        assert len(null_tongues) == 5

    def test_get_leaves_of_type(self):
        ws = Workspace()
        ws.create_leaf_in_root(ViewType.SUBSTRATE)
        ws.create_leaf_in_root(ViewType.SUBSTRATE)
        ws.create_leaf_in_root(ViewType.GOVERNANCE)
        assert len(ws.get_leaves_of_type(ViewType.SUBSTRATE)) == 2
        assert len(ws.get_leaves_of_type(ViewType.GOVERNANCE)) == 1

    def test_active_views(self):
        ws = Workspace()
        ws.create_leaf_in_root(ViewType.SUBSTRATE)
        views = ws.get_active_views()
        assert "substrate" in views


# ===========================================================================
# I. LINKED GROUPS
# ===========================================================================

class TestLinkedGroups:
    def test_set_and_get_group(self):
        ws = Workspace()
        l1 = ws.create_leaf_in_root(ViewType.TONGUE_CA)
        l2 = ws.create_leaf_in_root(ViewType.OUTLINE)
        l1.set_group("analysis")
        l2.set_group("analysis")
        group = ws.get_linked_group("analysis")
        assert len(group) == 2

    def test_empty_group(self):
        ws = Workspace()
        assert ws.get_linked_group("nonexistent") == []


# ===========================================================================
# J. SERIALIZATION
# ===========================================================================

class TestSerialization:
    def test_leaf_to_dict(self):
        leaf = Leaf(id="l1", view_type=ViewType.GOVERNANCE, group="g1")
        d = leaf.to_dict()
        assert d["type"] == "leaf"
        assert d["view_type"] == "governance"
        assert d["group"] == "g1"

    def test_tabs_to_dict(self):
        tabs = Tabs(id="t1")
        tabs.add_child(Leaf(id="a", view_type=ViewType.TONGUE_KO))
        tabs.add_child(Leaf(id="b", view_type=ViewType.TONGUE_AV))
        d = tabs.to_dict()
        assert d["type"] == "tabs"
        assert d["active_index"] == 0
        assert len(d["children"]) == 2

    def test_split_to_dict(self):
        s = Split(id="s1", direction=Direction.VERTICAL)
        s.add_child(Leaf(id="l1"))
        d = s.to_dict()
        assert d["direction"] == "vertical"
        assert len(d["children"]) == 1

    def test_workspace_to_dict(self):
        ws = Workspace()
        ws.create_leaf_in_root(ViewType.SUBSTRATE)
        d = ws.to_dict()
        assert d["type"] == "workspace"
        assert "left" in d
        assert "root" in d
        assert "right" in d

    def test_workspace_to_json_parses(self):
        ws = Workspace()
        ws.create_tongue_tabs("KO")
        j = ws.to_json()
        parsed = json.loads(j)
        assert parsed["type"] == "workspace"

    def test_round_trip(self):
        ws = Workspace()
        ws.create_tongue_tabs("DR")
        ws.create_leaf_in_right(ViewType.GOVERNANCE)
        d = ws.to_dict()
        ws2 = Workspace.from_dict(d)
        all_leaves_1 = list(ws.iterate_all_leaves())
        all_leaves_2 = list(ws2.iterate_all_leaves())
        assert len(all_leaves_1) == len(all_leaves_2)

    def test_rebuild_leaf(self):
        data = {"type": "leaf", "id": "x", "view_type": "governance", "pinned": True}
        leaf = _rebuild_item(data)
        assert isinstance(leaf, Leaf)
        assert leaf.view_type == ViewType.GOVERNANCE
        assert leaf.pinned is True

    def test_rebuild_unknown_view_type(self):
        data = {"type": "leaf", "id": "x", "view_type": "future_type"}
        leaf = _rebuild_item(data)
        assert isinstance(leaf, Leaf)
        assert leaf.view_type == ViewType.EMPTY


# ===========================================================================
# K. LAYOUT SAVE/RESTORE
# ===========================================================================

class TestLayouts:
    def test_save_layout(self):
        ws = Workspace()
        ws.create_tongue_tabs("KO")
        layout = ws.save_layout("default")
        assert layout.name == "default"
        assert "KO" in layout.tongue_state["tongues_active"]

    def test_list_layouts(self):
        ws = Workspace()
        ws.save_layout("a")
        ws.save_layout("b")
        assert set(ws.list_layouts()) == {"a", "b"}

    def test_get_layout(self):
        ws = Workspace()
        ws.save_layout("test", metadata={"ritual": "genesis"})
        layout = ws.get_layout("test")
        assert layout is not None
        assert layout.metadata["ritual"] == "genesis"

    def test_layout_serialization(self):
        ws = Workspace()
        ws.create_tongue_tabs("UM")
        layout = ws.save_layout("um_focus")
        j = layout.to_json()
        parsed = json.loads(j)
        restored = WorkspaceLayout.from_dict(parsed)
        assert restored.name == "um_focus"
        assert restored.tongue_state == layout.tongue_state

    def test_layout_captures_active_views(self):
        ws = Workspace()
        ws.create_tongue_tabs("CA")
        ws.create_leaf_in_root(ViewType.SUBSTRATE)
        layout = ws.save_layout("ca_substrate")
        assert "substrate" in layout.active_views


# ===========================================================================
# L. TRAINING RECORD BRIDGE
# ===========================================================================

class TestTrainingBridge:
    def test_to_training_record_basic(self):
        ws = Workspace()
        ws.create_tongue_tabs("KO")
        rec = ws.to_training_record(
            instruction="What is the nesting quad?",
            response="The nesting quad follows pattern [1,3,0,2]...",
            layer="L0",
        )
        assert rec["tongue"] == "KO"
        assert "KO" in rec["tongues_active"]
        assert len(rec["tongues_null"]) == 5
        assert rec["layer"] == "L0"
        assert rec["instruction"] != ""
        assert rec["workspace"]["active_count"] >= 1
        assert rec["workspace"]["null_count"] >= 5

    def test_to_training_record_has_workspace_metadata(self):
        ws = create_multi_view_workspace("DR", ["L0", "L3"])
        rec = ws.to_training_record()
        assert "workspace" in rec
        assert rec["workspace"]["leaf_count"] > 0
        assert rec["workspace"]["depth"] > 0

    def test_to_training_record_governance(self):
        ws = Workspace()
        ws.create_tongue_tabs("KO")
        rec = ws.to_training_record(governance="QUARANTINE")
        assert rec["governance"] == "QUARANTINE"


# ===========================================================================
# M. PRESET WORKSPACES
# ===========================================================================

class TestPresets:
    def test_single_tongue_workspace(self):
        ws = create_single_tongue_workspace("AV")
        state = ws.get_tongue_state()
        assert "AV" in state["tongues_active"]
        assert len(state["tongues_null"]) == 5
        # Should have governance in right sidebar
        gov = ws.get_leaves_of_type(ViewType.GOVERNANCE)
        assert len(gov) >= 1

    def test_multi_view_workspace(self):
        ws = create_multi_view_workspace("RU", ["L0", "L1"])
        state = ws.get_tongue_state()
        assert "RU" in state["tongues_active"]
        # Should have graph in left, governance + activation in right
        assert len(ws.get_leaves_of_type(ViewType.GRAPH)) >= 1
        assert len(ws.get_leaves_of_type(ViewType.GOVERNANCE)) >= 1
        assert len(ws.get_leaves_of_type(ViewType.ACTIVATION)) >= 1

    def test_governance_workspace(self):
        ws = create_governance_workspace()
        # All 6 tongues should be visible (in split, not tabs)
        all_leaves = list(ws.iterate_all_leaves())
        tongue_leaves = [l for l in all_leaves if l.is_tongue]
        assert len(tongue_leaves) == 6
        # All should be active (split, not tabs)
        active = ws.get_active_leaves()
        active_tongues = [l for l in active if l.is_tongue]
        assert len(active_tongues) == 6

    def test_each_preset_serializes(self):
        for factory in [
            lambda: create_single_tongue_workspace("KO"),
            lambda: create_multi_view_workspace("CA"),
            lambda: create_governance_workspace(),
        ]:
            ws = factory()
            j = ws.to_json()
            parsed = json.loads(j)
            assert parsed["type"] == "workspace"


# ===========================================================================
# N. RECONSTRUCTION FROM TRAINING RECORD
# ===========================================================================

class TestRecordReconstruction:
    def test_basic_reconstruction(self):
        record = {
            "instruction": "test",
            "output": "test output",
            "tongue": "DR",
            "tongues_active": ["DR"],
            "tongues_null": ["KO", "AV", "RU", "CA", "UM"],
            "layer": "L0",
            "governance": "ALLOW",
        }
        ws = workspace_from_training_record(record)
        state = ws.get_tongue_state()
        assert "DR" in state["tongues_active"]
        assert "DR" not in state["tongues_null"]

    def test_reconstructed_has_layer_view(self):
        record = {"tongue": "KO", "layer": "L3", "governance": "ALLOW"}
        ws = workspace_from_training_record(record)
        expr = ws.get_leaves_of_type(ViewType.EXPRESSION)
        assert len(expr) >= 1

    def test_reconstructed_has_governance(self):
        record = {"tongue": "KO", "layer": "L0", "governance": "QUARANTINE"}
        ws = workspace_from_training_record(record)
        gov = ws.get_leaves_of_type(ViewType.GOVERNANCE)
        assert len(gov) >= 1
        assert gov[0].state.get("decision") == "QUARANTINE"

    def test_round_trip_record_workspace_record(self):
        ws1 = create_single_tongue_workspace("UM")
        rec1 = ws1.to_training_record(instruction="x", response="y", layer="L2")
        ws2 = workspace_from_training_record(rec1)
        rec2 = ws2.to_training_record(instruction="x", response="y", layer="L2")
        # Tongue state should match
        assert rec1["tongues_active"] == rec2["tongues_active"]


# ===========================================================================
# O. EDGE CASES
# ===========================================================================

class TestEdgeCases:
    def test_empty_workspace(self):
        ws = Workspace()
        assert list(ws.iterate_all_leaves()) == []
        assert ws.get_active_leaves() == []
        assert ws.get_null_leaves() == []

    def test_workspace_repr(self):
        ws = Workspace()
        ws.create_tongue_tabs("KO")
        r = repr(ws)
        assert "leaves=" in r
        assert "active=" in r

    def test_detach_leaf_from_tabs(self):
        tabs = Tabs()
        l1 = Leaf(id="a")
        l2 = Leaf(id="b")
        tabs.add_child(l1)
        tabs.add_child(l2)
        l1.detach()
        assert tabs.leaf_count == 1
        assert tabs.active_leaf is l2

    def test_deep_nesting(self):
        s1 = Split()
        s2 = Split()
        s3 = Split()
        leaf = Leaf()
        s1.add_child(s2)
        s2.add_child(s3)
        s3.add_child(leaf)
        assert leaf.depth == 3
        assert s1.leaf_count == 1

    def test_move_leaf_between_parents(self):
        s1 = Split()
        s2 = Split()
        leaf = Leaf()
        s1.add_child(leaf)
        assert s1.leaf_count == 1
        s2.add_child(leaf)  # Should auto-detach from s1
        assert s1.leaf_count == 0
        assert s2.leaf_count == 1
        assert leaf.parent is s2

    def test_all_view_types_constructable(self):
        for vt in ViewType:
            leaf = Leaf(view_type=vt)
            assert leaf.view_type == vt

    def test_all_tongues_have_views(self):
        for tongue in ["KO", "AV", "RU", "CA", "UM", "DR"]:
            assert tongue in TONGUE_VIEWS
            assert TONGUE_VIEWS[tongue].value.startswith("tongue_")

    def test_tongue_names_reverse_mapping(self):
        for tongue, view in TONGUE_VIEWS.items():
            assert TONGUE_NAMES[view] == tongue


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
