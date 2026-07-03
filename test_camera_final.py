import sys
sys.path.insert(0, '.')

from python.scbe.browser_camera import (
    HIDDEN, SEEN, VISIBLE, ThreeStateFog, PageMinimap, Camera
)

def probe_fog_state_machine():
    """Test all transitions of the ThreeStateFog state machine:
    HIDDEN -> VISIBLE (first seen)
    VISIBLE -> SEEN (scrolled out)
    SEEN -> VISIBLE (scrolled back in)
    HIDDEN -> HIDDEN (never seen)
    SEEN -> SEEN (stays scrolled out)
    """
    print("\n[PROBE H] Complete ThreeStateFog state machine")
    
    fog = ThreeStateFog()
    
    # Transition 1: HIDDEN -> VISIBLE (initial render)
    fog.update({"A1", "B1"}, {"A1": ["data_a1"], "B1": ["data_b1"]})
    assert fog.of("A1") == VISIBLE and fog.of("B1") == VISIBLE
    assert fog.of("C1") == HIDDEN  # Never seen
    print("  [OK] HIDDEN -> VISIBLE (initial render)")
    
    # Transition 2: VISIBLE -> SEEN (A1 scrolls out, B1 stays, C1 enters)
    fog.update({"B1", "C1"}, {"B1": ["data_b1_new"], "C1": ["data_c1"]})
    assert fog.of("A1") == SEEN, "A1 transitioned to SEEN"
    assert fog.of("B1") == VISIBLE, "B1 stayed VISIBLE"
    assert fog.of("C1") == VISIBLE, "C1 transitioned to VISIBLE"
    print("  [OK] VISIBLE -> SEEN (scroll out)")
    
    # Transition 3: SEEN -> VISIBLE (A1 scrolls back in)
    fog.update({"A1", "B1"}, {"A1": ["data_a1_new"], "B1": ["data_b1_newer"]})
    assert fog.of("A1") == VISIBLE, "A1 transitioned back to VISIBLE"
    print("  [OK] SEEN -> VISIBLE (scroll back in)")
    
    # Transition 4: SEEN -> SEEN (C1 stays out)
    assert fog.of("C1") == SEEN, "C1 stayed SEEN"
    print("  [OK] SEEN -> SEEN (stays scrolled out)")
    
    # Transition 5: HIDDEN -> HIDDEN (D1 never enters)
    assert fog.of("D1") == HIDDEN, "D1 stayed HIDDEN"
    print("  [OK] HIDDEN -> HIDDEN (never scrolled in)")
    
    print("  PASS: All state transitions correct")


def probe_minimap_cell_arithmetic():
    """Test edge cases in PageMinimap cell calculation:
    - Element exactly at grid line
    - Element center off by 0.5
    - Cell width/height with fractional division
    """
    print("\n[PROBE I] PageMinimap cell arithmetic edge cases")
    
    # Document 1000x1000, 10x10 grid -> cw=ch=100
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": [
            # Center exactly at grid line x=100 (between cells 0 and 1)
            # x=50, w=100 -> center = 50 + 50 = 100
            # cell_x = int(100 / 1000 * 10) = int(1.0) = 1 (cell 1, not 0)
            {"ref": "r_gridline", "x": 50, "y": 50, "w": 100, "h": 100},
            
            # Center at x=99.5 (should still be in cell 0)
            # center = 25 + 49.5 = 74.5
            # cell_x = int(74.5 / 1000 * 10) = int(0.745) = 0
            {"ref": "r_almost_gridline", "x": 25, "y": 25, "w": 49, "h": 49},
        ]
    }
    
    mm = PageMinimap(feed, cols=10, rows=10)
    
    c1 = next((c for c, els in mm.by_cell.items() if els[0]["ref"] == "r_gridline"), None)
    assert c1 == (1, 1), f"Element at gridline should be in (1,1), got {c1}"
    print(f"  [OK] Element at gridline placed in (1,1)")
    
    c2 = next((c for c, els in mm.by_cell.items() if els[0]["ref"] == "r_almost_gridline"), None)
    assert c2 == (0, 0), f"Element just before gridline should be in (0,0), got {c2}"
    print(f"  [OK] Element just before gridline placed in (0,0)")
    
    print("  PASS: Cell arithmetic edge cases correct")


def probe_minimap_with_fractional_cw_ch():
    """Test PageMinimap when cw/ch are fractional.
    Document 1000x1000, 3x3 grid -> cw=ch=333.33...
    Element at center (500, 500) should be in cell (1, 1).
    """
    print("\n[PROBE J] PageMinimap with fractional cell dimensions")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": [
            # Center at (500, 500)
            # cell_x = int(500 / 1000 * 3) = int(1.5) = 1
            # cell_y = int(500 / 1000 * 3) = int(1.5) = 1
            {"ref": "r_center", "x": 490, "y": 490, "w": 20, "h": 20},
        ]
    }
    
    mm = PageMinimap(feed, cols=3, rows=3)
    
    c = next((c for c, els in mm.by_cell.items() if els[0]["ref"] == "r_center"), None)
    assert c == (1, 1), f"Element at center should be in (1,1), got {c}"
    print(f"  [OK] Element at center placed in (1,1)")
    print("  PASS: Fractional cell dimensions handled correctly")


def probe_viewport_cells_single_cell():
    """Test viewport_cells when viewport is smaller than one cell."""
    print("\n[PROBE K] viewport_cells with viewport < 1 cell")
    
    feed = {
        "viewport": {"w": 50, "h": 50},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 100, "y": 100},
        "elements": []
    }
    
    mm = PageMinimap(feed, cols=10, rows=10)
    
    vp_cells = mm.viewport_cells()
    
    # Viewport is at (100, 100) with size 50x50
    # In a 10x10 grid over 1000x1000:
    # c0 = int(100 / 1000 * 10) = 1
    # r0 = int(100 / 1000 * 10) = 1
    # c1 = int(150 / 1000 * 10) = int(1.5) = 1
    # r1 = int(150 / 1000 * 10) = int(1.5) = 1
    # So viewport should contain only cell (1, 1)
    
    assert (1, 1) in vp_cells, f"Cell (1,1) should be in viewport"
    assert len(vp_cells) == 1, f"Viewport should contain only 1 cell, got {len(vp_cells)}"
    print(f"  [OK] Small viewport contains single cell")
    print("  PASS: Single-cell viewport correct")


def probe_fog_counts_empty_document():
    """Test fog.counts() when document has no elements."""
    print("\n[PROBE L] fog.counts() with empty document")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": []
    }
    
    class MockBrowser:
        def read(self, page):
            return feed
        def act(self, page, action):
            pass
    
    br = MockBrowser()
    cam = Camera(br, None, cols=10, rows=10)
    
    obs = cam.observe()
    fog_counts = obs["fog"]
    
    # With no elements, all counts should be 0
    assert fog_counts["hidden"] == 0
    assert fog_counts["seen"] == 0
    assert fog_counts["visible"] == 0
    assert sum(fog_counts.values()) == 0
    print(f"  [OK] Empty document: fog counts all 0")
    print("  PASS: Empty document handled correctly")


def probe_observe_minimap_overview():
    """Test that observe().minimap contains correct fog states for all occupied cells."""
    print("\n[PROBE M] observe().minimap fog states")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": [
            {"ref": "r0", "x": 100, "y": 100, "w": 20, "h": 20},  # Cell (0,0)
        ]
    }
    
    class MockBrowser:
        def read(self, page):
            return feed
        def act(self, page, action):
            pass
    
    br = MockBrowser()
    cam = Camera(br, None, cols=10, rows=10)
    
    obs = cam.observe()
    minimap = obs["minimap"]
    
    # Cell A1 should have n=1, fog=visible
    cells = minimap["cells"]
    assert "A1" in cells, "A1 should be in minimap cells"
    assert cells["A1"]["n"] == 1, f"A1 should have 1 element, got {cells['A1']['n']}"
    assert cells["A1"]["fog"] == "visible", f"A1 should be visible, got {cells['A1']['fog']}"
    
    print(f"  [OK] Minimap contains correct cell fog states")
    print("  PASS: observe().minimap overview correct")


if __name__ == "__main__":
    try:
        probe_fog_state_machine()
        probe_minimap_cell_arithmetic()
        probe_minimap_with_fractional_cw_ch()
        probe_viewport_cells_single_cell()
        probe_fog_counts_empty_document()
        probe_observe_minimap_overview()
        
        print("\n" + "="*70)
        print("ALL FINAL PROBES PASSED")
        print("="*70)
    except AssertionError as e:
        print(f"\nFINAL PROBE FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\nFINAL PROBE ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
