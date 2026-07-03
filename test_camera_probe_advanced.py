import sys
sys.path.insert(0, '.')

from python.scbe.browser_camera import (
    HIDDEN, SEEN, VISIBLE, ThreeStateFog, PageMinimap, Camera
)

def probe_page_minimap_element_centering():
    """Test if element center calculation in PageMinimap.by_cell is correct.
    The code adds scroll to element position: dx = e.get("x", 0) + self.sx + e.get("w", 0) / 2.0
    This is correct for doc-coords (viewport coords + scroll).
    """
    print("\n[PROBE A] Element center calculation with scroll")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 100, "y": 100},
        "elements": [
            # Element at viewport (0, 0) with size 20x20
            # Center in viewport: (10, 10)
            # Center in doc: (10 + 100, 10 + 100) = (110, 110)
            # In 10x10 grid: cell = (int(110/100), int(110/100)) = (1, 1)
            {"ref": "r0", "x": 0, "y": 0, "w": 20, "h": 20},
        ]
    }
    
    mm = PageMinimap(feed, cols=10, rows=10)
    
    cell = next((c for c, els in mm.by_cell.items() if els[0]["ref"] == "r0"), None)
    assert cell == (1, 1), f"Element should be in cell (1,1), got {cell}"
    print("  [OK] Element center calculation with scroll correct")


def probe_viewport_cells_boundary():
    """Test viewport_cells() calculation at scroll boundaries.
    When scrolled far down, ensure r1 doesn't exceed rows-1.
    """
    print("\n[PROBE B] viewport_cells() at max scroll")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 10000},
        "scroll": {"x": 0, "y": 9000},  # Scrolled way down
        "elements": []
    }
    
    mm = PageMinimap(feed, cols=10, rows=10)
    vp_cells = mm.viewport_cells()
    
    # Check that all cells are within bounds
    for c, r in vp_cells:
        assert 0 <= c < mm.cols, f"Column {c} out of bounds"
        assert 0 <= r < mm.rows, f"Row {r} out of bounds"
    
    print(f"  [OK] viewport_cells at max scroll = {len(vp_cells)} cells, all in bounds")


def probe_element_out_of_bounds():
    """Test that elements outside viewport are not placed in by_cell.
    PageMinimap._cell_of in browser_grid.py returns None if x,y out of bounds.
    But PageMinimap uses a different formula that always clamps, so elements
    should always be placed (never off-grid).
    """
    print("\n[PROBE C] Element placement (should always clamp, never 'off')")
    
    # Element way outside viewport
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": [
            # At screen (5000, 5000) - way off to the right/down
            {"ref": "r_far", "x": 5000, "y": 5000, "w": 20, "h": 20},
        ]
    }
    
    mm = PageMinimap(feed, cols=10, rows=10)
    
    # Element should be clamped to cell (9, 9) (bottom-right)
    cell = next((c for c, els in mm.by_cell.items() if els[0]["ref"] == "r_far"), None)
    assert cell == (9, 9), f"Element should be clamped to (9,9), got {cell}"
    print(f"  [OK] Off-screen element clamped to (9,9)")


def probe_move_camera_scroll_calculation():
    """Test move_camera scroll coordinate calculation for a cell label.
    Formula: x = int((cell[0] + 0.5) * cw - vw / 2)
    y = int((cell[1] + 0.5) * ch - vh / 2)
    
    For a 1000x1000 doc, 10x10 grid, 1000x1000 viewport:
    cw = ch = 100
    vw = vh = 1000
    
    To scroll cell (5, 5) to center:
    x = int((5.5) * 100 - 1000/2) = int(550 - 500) = 50
    y = int((5.5) * 100 - 1000/2) = int(550 - 500) = 50
    """
    print("\n[PROBE D] move_camera scroll calculation")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": [
            {"ref": "r_test", "x": 550, "y": 550, "w": 20, "h": 20},  # In cell (5,5)
        ]
    }
    
    move_called = {}
    
    class MockBrowser:
        def read(self, page):
            return feed
        def act(self, page, action):
            move_called["action"] = action
    
    br = MockBrowser()
    cam = Camera(br, None, cols=10, rows=10)
    
    # move_camera with label "F6" (cell 5,5)
    cam.move_camera("F6")
    action = move_called.get("action")
    assert action is not None, "move_camera should call browser.act()"
    
    value_str = action.kwargs.get("value")
    assert value_str is not None, "Should have computed scroll value"
    x_scroll, y_scroll = map(int, value_str.split(","))
    
    # Expected: x = int(5.5 * 100 - 1000/2) = int(550 - 500) = 50
    # But clamped to max(0, x)
    assert x_scroll == 50 and y_scroll == 50, f"Scroll coords: got ({x_scroll},{y_scroll}), expected (50,50)"
    print(f"  [OK] move_camera scroll calc: ({x_scroll},{y_scroll})")


def probe_cell_label_function():
    """Test the cell_label function generates correct labels.
    A1 = (0,0), Z1 = (25,0), AA1 = (26,0), etc.
    """
    print("\n[PROBE E] cell_label function correctness")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": []
    }
    
    mm = PageMinimap(feed, cols=100, rows=100)
    
    # Test single-letter labels
    assert mm.label((0, 0)) == "A1", "Cell (0,0) should be A1"
    assert mm.label((1, 0)) == "B1", "Cell (1,0) should be B1"
    assert mm.label((25, 0)) == "Z1", "Cell (25,0) should be Z1"
    print("  [OK] Single-letter labels correct")
    
    # Test two-letter labels
    assert mm.label((26, 0)) == "AA1", f"Cell (26,0) should be AA1, got {mm.label((26, 0))}"
    assert mm.label((27, 0)) == "AB1", f"Cell (27,0) should be AB1, got {mm.label((27, 0))}"
    print("  [OK] Two-letter labels correct")


def probe_three_state_fog_not_refreshing_seen():
    """Critical edge case: when a SEEN cell stays SEEN (not in visible set),
    its snapshot should NOT be updated even if new cell_data is provided.
    """
    print("\n[PROBE F] ThreeStateFog: SEEN cell snapshot must stay stale")
    
    fog = ThreeStateFog()
    
    # Frame 1: A1 visible
    fog.update({"A1"}, {"A1": ["r0", "r1"]})
    assert fog.seen_snapshot("A1") == ["r0", "r1"]
    print("  [OK] Frame 1: A1 visible with 2 elements")
    
    # Frame 2: A1 scrolls out (SEEN), with DIFFERENT data in visible set
    # The code iterates over self.state.items() to mark scrolled-out cells as SEEN.
    # Then it processes visible cells and ALWAYS updates their snapshot.
    # So a SEEN cell that stays SEEN should NOT be updated.
    fog.update({"B1"}, {"B1": ["r2"]})
    
    # A1 should still be SEEN with OLD snapshot
    assert fog.of("A1") == SEEN
    assert fog.seen_snapshot("A1") == ["r0", "r1"], "A1 snapshot should remain unchanged"
    print("  [OK] SEEN cell snapshot remains stale")


def probe_available_actions_move_camera_per_cell():
    """Test that available_actions includes move_camera for each off-screen occupied cell,
    not just once per cell but with correct cell label.
    """
    print("\n[PROBE G] available_actions move_camera for off-screen cells")
    
    feed = {
        "viewport": {"w": 500, "h": 500},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": [
            # In-viewport: cell (2, 2)
            {"ref": "r_in", "x": 250, "y": 250, "w": 20, "h": 20},
            # Off-viewport (below): cell (2, 8)
            {"ref": "r_out", "x": 250, "y": 850, "w": 20, "h": 20},
        ]
    }
    
    class MockBrowser:
        def read(self, page):
            return feed
        def act(self, page, action):
            pass
    
    br = MockBrowser()
    cam = Camera(br, None, cols=10, rows=10)
    
    acts = cam.available_actions()
    
    # Should have "read" + "activate:r_in" (in-viewport) + "move_camera:C9" (off-screen)
    assert "read" in acts
    assert any("activate:" in str(a) and "r_in" in str(a) for a in acts)
    assert any("move_camera:" in str(a) and "C9" in str(a) for a in acts)
    
    print(f"  [OK] available_actions includes move_camera for off-screen cells")


if __name__ == "__main__":
    try:
        probe_page_minimap_element_centering()
        probe_viewport_cells_boundary()
        probe_element_out_of_bounds()
        probe_move_camera_scroll_calculation()
        probe_cell_label_function()
        probe_three_state_fog_not_refreshing_seen()
        probe_available_actions_move_camera_per_cell()
        
        print("\n" + "="*70)
        print("ALL ADVANCED PROBES PASSED")
        print("="*70)
    except AssertionError as e:
        print(f"\nADVANCED PROBE FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\nADVANCED PROBE ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
