import sys
sys.path.insert(0, '.')

from python.scbe.browser_camera import (
    HIDDEN, SEEN, VISIBLE, ThreeStateFog, PageMinimap, Camera
)

def probe_page_minimap_element_centering():
    """Test if element center calculation in PageMinimap.by_cell is correct."""
    print("\n[PROBE A] Element center calculation with scroll")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 100, "y": 100},
        "elements": [
            {"ref": "r0", "x": 0, "y": 0, "w": 20, "h": 20},
        ]
    }
    
    mm = PageMinimap(feed, cols=10, rows=10)
    
    cell = next((c for c, els in mm.by_cell.items() if els[0]["ref"] == "r0"), None)
    assert cell == (1, 1), f"Element should be in cell (1,1), got {cell}"
    print("  [OK] Element center calculation with scroll correct")


def probe_viewport_cells_boundary():
    """Test viewport_cells() calculation at scroll boundaries."""
    print("\n[PROBE B] viewport_cells() at max scroll")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 10000},
        "scroll": {"x": 0, "y": 9000},
        "elements": []
    }
    
    mm = PageMinimap(feed, cols=10, rows=10)
    vp_cells = mm.viewport_cells()
    
    for c, r in vp_cells:
        assert 0 <= c < mm.cols, f"Column {c} out of bounds"
        assert 0 <= r < mm.rows, f"Row {r} out of bounds"
    
    print(f"  [OK] viewport_cells at max scroll = {len(vp_cells)} cells, all in bounds")


def probe_element_out_of_bounds():
    """Test that elements outside viewport are clamped."""
    print("\n[PROBE C] Element placement (should always clamp)")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": [
            {"ref": "r_far", "x": 5000, "y": 5000, "w": 20, "h": 20},
        ]
    }
    
    mm = PageMinimap(feed, cols=10, rows=10)
    
    cell = next((c for c, els in mm.by_cell.items() if els[0]["ref"] == "r_far"), None)
    assert cell == (9, 9), f"Element should be clamped to (9,9), got {cell}"
    print(f"  [OK] Off-screen element clamped to (9,9)")


def probe_cell_label_function():
    """Test the cell_label function generates correct labels."""
    print("\n[PROBE E] cell_label function correctness")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": []
    }
    
    mm = PageMinimap(feed, cols=100, rows=100)
    
    assert mm.label((0, 0)) == "A1"
    assert mm.label((1, 0)) == "B1"
    assert mm.label((25, 0)) == "Z1"
    print("  [OK] Single-letter labels correct")
    
    assert mm.label((26, 0)) == "AA1", f"Cell (26,0) should be AA1, got {mm.label((26, 0))}"
    assert mm.label((27, 0)) == "AB1", f"Cell (27,0) should be AB1, got {mm.label((27, 0))}"
    print("  [OK] Two-letter labels correct")


def probe_three_state_fog_not_refreshing_seen():
    """Critical: SEEN cell snapshot must stay stale."""
    print("\n[PROBE F] ThreeStateFog: SEEN cell snapshot must stay stale")
    
    fog = ThreeStateFog()
    
    fog.update({"A1"}, {"A1": ["r0", "r1"]})
    assert fog.seen_snapshot("A1") == ["r0", "r1"]
    print("  [OK] Frame 1: A1 visible with 2 elements")
    
    fog.update({"B1"}, {"B1": ["r2"]})
    
    assert fog.of("A1") == SEEN
    assert fog.seen_snapshot("A1") == ["r0", "r1"], "A1 snapshot should remain unchanged"
    print("  [OK] SEEN cell snapshot remains stale")


def probe_available_actions_move_camera_per_cell():
    """Test available_actions includes move_camera for each off-screen occupied cell."""
    print("\n[PROBE G] available_actions move_camera for off-screen cells")
    
    feed = {
        "viewport": {"w": 500, "h": 500},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": [
            {"ref": "r_in", "x": 250, "y": 250, "w": 20, "h": 20},
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
    
    assert "read" in acts
    assert any("activate:" in str(a) and "r_in" in str(a) for a in acts)
    assert any("move_camera:" in str(a) and "C9" in str(a) for a in acts)
    
    print(f"  [OK] available_actions includes move_camera for off-screen cells")


if __name__ == "__main__":
    try:
        probe_page_minimap_element_centering()
        probe_viewport_cells_boundary()
        probe_element_out_of_bounds()
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
