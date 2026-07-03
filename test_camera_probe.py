import sys
sys.path.insert(0, '.')

from python.scbe.browser_camera import (
    HIDDEN, SEEN, VISIBLE, ThreeStateFog, PageMinimap, Camera, cell_label
)

def probe_three_state_fog_transitions():
    print("\n[PROBE 1] ThreeStateFog transitions and snapshot staleness")
    fog = ThreeStateFog()
    
    fog.update({"A1", "B1"}, {"A1": ["r0"], "B1": ["r1"]})
    assert fog.of("A1") == VISIBLE
    assert fog.seen_snapshot("A1") == ["r0"]
    print("  [OK] Frame 1: A1, B1 visible with snapshots stored")
    
    fog.update({"B1", "C1"}, {"B1": ["r1_updated"], "C1": ["r2"]})
    
    assert fog.of("A1") == SEEN, f"A1 should be SEEN after scrolling out, got {fog.of('A1')}"
    assert fog.seen_snapshot("A1") == ["r0"]
    print("  [OK] Frame 2: A1 transitioned to SEEN with stale snapshot")
    
    assert fog.of("B1") == VISIBLE
    assert fog.seen_snapshot("B1") == ["r1_updated"]
    print("  [OK] Frame 2: B1 stayed VISIBLE and snapshot refreshed")
    
    assert fog.of("C1") == VISIBLE
    print("  [OK] Frame 2: C1 newly visible")
    
    fog.update({"A1", "B1"}, {"A1": ["r0_new"], "B1": ["r1_new"]})
    
    assert fog.of("A1") == VISIBLE
    assert fog.seen_snapshot("A1") == ["r0_new"]
    print("  [OK] Frame 3: A1 transitioned back to VISIBLE and snapshot refreshed")
    
    assert fog.of("C1") == SEEN
    print("  PASS: ThreeStateFog transitions correct")


def probe_page_minimap_doc_coords():
    print("\n[PROBE 2] PageMinimap doc-coord math with scroll")
    
    feed = {
        "viewport": {"w": 1000, "h": 800},
        "document": {"w": 2000, "h": 3000},
        "scroll": {"x": 0, "y": 500},
        "elements": [
            {"ref": "r0", "x": 100, "y": 100, "w": 50, "h": 50},
            {"ref": "r1", "x": 500, "y": 2500, "w": 50, "h": 50},
        ]
    }
    
    mm = PageMinimap(feed, cols=10, rows=10)
    
    assert mm.sx == 0 and mm.sy == 500
    print("  [OK] Scroll offset captured")
    
    cell_r0 = next((c for c, els in mm.by_cell.items() if els[0]["ref"] == "r0"), None)
    assert cell_r0 == (0, 2), f"r0 should be in cell (0,2), got {cell_r0}"
    print(f"  [OK] r0 placed correctly")
    
    cell_r1 = next((c for c, els in mm.by_cell.items() if els[0]["ref"] == "r1"), None)
    assert cell_r1 == (2, 9), f"r1 should be in cell (2,9), got {cell_r1}"
    print(f"  [OK] r1 placed correctly")
    
    print("  PASS: PageMinimap doc-coord math correct")


def probe_in_viewport():
    print("\n[PROBE 3] in_viewport correctness")
    
    feed = {
        "viewport": {"w": 500, "h": 500},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 250},
        "elements": [
            {"ref": "r_in", "x": 100, "y": 100, "w": 20, "h": 20},
            {"ref": "r_out", "x": 100, "y": 600, "w": 20, "h": 20},
        ]
    }
    
    mm = PageMinimap(feed, cols=10, rows=10)
    
    class MockCamera:
        def __init__(self):
            self.minimap = mm
        def _cell_of_ref(self, ref):
            for cell, els in self.minimap.by_cell.items():
                if any(e["ref"] == ref for e in els):
                    return cell
            return None
        def in_viewport(self, ref):
            cell = self._cell_of_ref(ref)
            return cell is not None and cell in self.minimap.viewport_cells()
    
    cam = MockCamera()
    assert cam.in_viewport("r_in")
    assert not cam.in_viewport("r_out")
    print("  [OK] in_viewport returns correct results")
    print("  PASS: in_viewport correctness verified")


def probe_fog_counts():
    print("\n[PROBE 4] observe() fog counts only over occupied cells")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": [
            {"ref": "r0", "x": 100, "y": 100, "w": 20, "h": 20},
            {"ref": "r1", "x": 600, "y": 600, "w": 20, "h": 20},
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
    fog_counts = obs["fog"]
    
    total = sum(fog_counts.values())
    assert total == 2, f"Should count exactly 2 occupied cells, got {total}"
    assert fog_counts["visible"] == 2
    print(f"  [OK] Fog counts = {fog_counts}")
    print("  PASS: fog.counts() over occupied cells correct")


if __name__ == "__main__":
    try:
        probe_three_state_fog_transitions()
        probe_page_minimap_doc_coords()
        probe_in_viewport()
        probe_fog_counts()
        
        print("\n" + "="*70)
        print("ALL PROBES PASSED")
        print("="*70)
    except AssertionError as e:
        print(f"\nPROBE FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\nPROBE ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
