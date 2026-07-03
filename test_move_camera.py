import sys
sys.path.insert(0, '.')

from python.scbe.browser_camera import (
    HIDDEN, SEEN, VISIBLE, ThreeStateFog, PageMinimap, Camera
)

def probe_move_camera_scroll_calculation():
    """Test move_camera scroll coordinate calculation for a cell label."""
    print("\n[PROBE D] move_camera scroll calculation")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": [
            {"ref": "r_test", "x": 550, "y": 550, "w": 20, "h": 20},
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
    
    cam.move_camera("F6")
    action = move_called.get("action")
    assert action is not None
    
    value_str = action.value
    assert value_str is not None
    x_scroll, y_scroll = map(int, value_str.split(","))
    
    assert x_scroll == 50 and y_scroll == 50, f"Got ({x_scroll},{y_scroll}), expected (50,50)"
    print(f"  [OK] move_camera scroll calc: ({x_scroll},{y_scroll})")


def probe_move_camera_by_ref():
    """Test move_camera dispatches correctly with ref."""
    print("\n[PROBE D2] move_camera by ref")
    
    feed = {
        "viewport": {"w": 1000, "h": 1000},
        "document": {"w": 1000, "h": 1000},
        "scroll": {"x": 0, "y": 0},
        "elements": [
            {"ref": "r_button", "x": 250, "y": 350, "w": 20, "h": 20},
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
    
    cam.move_camera("r_button")
    action = move_called.get("action")
    assert action is not None
    assert action.ref == "r_button"
    assert action.value is None
    print(f"  [OK] move_camera by ref: ref={action.ref}")


if __name__ == "__main__":
    try:
        probe_move_camera_scroll_calculation()
        probe_move_camera_by_ref()
        print("\n" + "="*70)
        print("MOVE CAMERA PROBES PASSED")
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
