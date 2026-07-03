import sys
sys.path.insert(0, '.')

from python.scbe.browser_camera import Camera

def probe_observe_minimap_overview():
    """Test observe().minimap contains correct fog states."""
    print("\n[PROBE M] observe().minimap fog states")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": [
            {"ref": "r0", "x": 100, "y": 100, "w": 20, "h": 20},
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
    
    cells = minimap["cells"]
    
    # Element center is (110, 110), so in cell (1, 1) -> label B2
    assert "B2" in cells, f"B2 should be in minimap cells, got: {list(cells.keys())}"
    assert cells["B2"]["n"] == 1, f"B2 should have 1 element, got {cells['B2']['n']}"
    assert cells["B2"]["fog"] == "visible", f"B2 should be visible, got {cells['B2']['fog']}"
    
    print(f"  [OK] Minimap contains correct cell fog states")
    print("  PASS: observe().minimap overview correct")

if __name__ == "__main__":
    try:
        probe_observe_minimap_overview()
        print("\n" + "="*70)
        print("MINIMAP OVERVIEW PROBE PASSED")
        print("="*70)
    except AssertionError as e:
        print(f"\nPROBE FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
