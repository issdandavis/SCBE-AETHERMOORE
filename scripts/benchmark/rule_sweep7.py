#!/usr/bin/env python3
"""Wave 7 sweep: visualize specific tasks + try more sophisticated patterns.

Focus areas:
1. Visualize aa300dc3, d37a1ef5, e0fb7511 to understand actual patterns
2. Per-region flood fill (each enclosed region independently)
3. Object translation (detect moved objects)
4. Grid-cell operations (divider lines + cell transforms)
5. Conditional color replacement
6. Horizontal/vertical line fill between objects
"""
import sys, numpy as np
from pathlib import Path
from collections import Counter, deque

sys.path.insert(0, "C:/Users/issda/SCBE-AETHERMOORE/src")
sys.path.insert(0, "C:/Users/issda/SCBE-AETHERMOORE")

from neurogolf.arc_io import load_arc_task
from neurogolf.solver import synthesize_program, execute_program

_REPO = Path("C:/Users/issda/SCBE-AETHERMOORE")
_TASKS_DIR = _REPO / "artifacts" / "arc-data" / "ARC-AGI-master" / "data" / "evaluation"
task_files = sorted(_TASKS_DIR.glob("*.json"))
tasks = {f.stem: load_arc_task(f) for f in task_files}

# Build unsolved set
unsolved_ids = set()
for tid, task in tasks.items():
    try:
        sol = synthesize_program(task)
        ok = all(
            execute_program(ex.input, sol.program).shape == ex.output.shape
            and (execute_program(ex.input, sol.program) == ex.output).all()
            for ex in task.train
        )
        if not ok:
            unsolved_ids.add(tid)
    except Exception:
        unsolved_ids.add(tid)

print(f"Unsolved: {len(unsolved_ids)}")

def print_grid(g, label=""):
    """Print small grid with color symbols."""
    if label:
        print(f"  {label}:")
    for r in range(g.shape[0]):
        row = " ".join(str(int(g[r, c])) for c in range(g.shape[1]))
        print(f"    {row}")

def cc_labels_color(grid, target_color):
    """Label CCs of a specific color."""
    h, w = grid.shape
    labels = np.zeros((h, w), dtype=int)
    lid = 0
    for r in range(h):
        for c in range(w):
            if labels[r, c] != 0 or grid[r, c] != target_color:
                continue
            lid += 1
            q = deque([(r, c)])
            labels[r, c] = lid
            while q:
                cr, cc_ = q.popleft()
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = cr+dr, cc_+dc
                    if 0 <= nr < h and 0 <= nc < w and labels[nr, nc] == 0 and grid[nr, nc] == target_color:
                        labels[nr, nc] = lid
                        q.append((nr, nc))
    return labels, lid

# ── Visualize specific tasks ──
print("\n=== Visualize aa300dc3 ===")
if "aa300dc3" in tasks:
    t = tasks["aa300dc3"]
    for i, ex in enumerate(t.train[:2]):
        print_grid(ex.input, f"train[{i}] input")
        print_grid(ex.output, f"train[{i}] output")
        diff = ex.input != ex.output
        print(f"  Changed positions: {list(zip(*np.where(diff)))}")
        # What are neighbors of changed cells?
        for r, c in zip(*np.where(diff)):
            h, w = ex.input.shape
            neigh = []
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < h and 0 <= nc < w:
                    neigh.append(int(ex.input[nr, nc]))
            print(f"    ({r},{c}): inp={ex.input[r,c]} -> out={ex.output[r,c]}, neighbors={neigh}")
        print()

print("\n=== Visualize d37a1ef5 ===")
if "d37a1ef5" in tasks:
    t = tasks["d37a1ef5"]
    for i, ex in enumerate(t.train[:2]):
        print_grid(ex.input, f"train[{i}] input")
        print_grid(ex.output, f"train[{i}] output")
        diff = ex.input != ex.output
        # What enclosed cells did NOT change?
        from neurogolf.solver import _flood_reachable_background
        reachable = _flood_reachable_background(ex.input)
        enclosed = (ex.input == 0) & ~reachable
        unchanged_enclosed = enclosed & ~diff
        print(f"  Enclosed unchanged positions: {list(zip(*np.where(unchanged_enclosed)))}")
        print()

print("\n=== Visualize e0fb7511 ===")
if "e0fb7511" in tasks:
    t = tasks["e0fb7511"]
    for i, ex in enumerate(t.train[:2]):
        print_grid(ex.input, f"train[{i}] input")
        print_grid(ex.output, f"train[{i}] output")
        print()

# ── More sophisticated sweeps on unsolved ──
unsolved_tasks = [tasks[tid] for tid in sorted(unsolved_ids)]

# ── Test A: Per-region flood fill ──
# Each separate bg region enclosed by fg gets filled independently
print("\n=== Per-region flood fill (each enclosed region fills with boundary color) ===")
per_region_hits = []
for task in unsolved_tasks:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    h, w = inp.shape

    # Find enclosed bg regions (each separate region)
    bg_labels, n_bg = cc_labels_color(inp, 0)
    if n_bg == 0:
        continue

    # For each bg region, check if it's enclosed (doesn't touch border)
    test_out = inp.copy()
    any_fill = False
    for lid in range(1, n_bg + 1):
        mask = bg_labels == lid
        # Check if region touches border
        touches_border = False
        positions = np.argwhere(mask)
        for r, c in positions:
            if r == 0 or r == h-1 or c == 0 or c == w-1:
                touches_border = True
                break
        if touches_border:
            continue

        # Region is enclosed. What color does it become in output?
        out_colors = np.unique(out[mask])
        if len(out_colors) == 1 and out_colors[0] != 0:
            # Find the boundary color (most common non-zero neighbor)
            boundary_colors = Counter()
            for r, c in positions:
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < h and 0 <= nc < w and inp[nr, nc] != 0:
                        boundary_colors[int(inp[nr, nc])] += 1
            if boundary_colors:
                # Does the fill color equal the boundary color?
                fill_c = int(out_colors[0])
                most_common_boundary = boundary_colors.most_common(1)[0][0]
                test_out[mask] = fill_c
                any_fill = True

    if any_fill and np.array_equal(test_out, out):
        # Now verify which rule works: fill with most common boundary color
        match = True
        for ex in task.train:
            if ex.input.shape != ex.output.shape:
                match = False; break
            h2, w2 = ex.input.shape
            t = ex.input.copy()
            bl, nb = cc_labels_color(ex.input, 0)
            for lid in range(1, nb + 1):
                m = bl == lid
                positions = np.argwhere(m)
                touches = any(r == 0 or r == h2-1 or c == 0 or c == w2-1 for r, c in positions)
                if touches:
                    continue
                bc = Counter()
                for r, c in positions:
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < h2 and 0 <= nc < w2 and ex.input[nr, nc] != 0:
                            bc[int(ex.input[nr, nc])] += 1
                if bc:
                    t[m] = bc.most_common(1)[0][0]
            if not np.array_equal(t, ex.output):
                match = False; break
        if match:
            per_region_hits.append(task.task_id)

print(f"  per_region_boundary_fill: {len(per_region_hits)} tasks")
for uid in per_region_hits:
    print(f"    {uid}")

# ── Test B: Object translation detection ──
print("\n=== Object translation (each CC moves by same delta) ===")
translate_hits = []
for task in unsolved_tasks:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    h, w = inp.shape

    # For each non-zero color, find positions in inp and out
    colors = set(int(v) for v in np.unique(inp) if v != 0)
    if not colors:
        continue

    # Try: all non-zero pixels shifted by same (dr, dc)
    inp_nz = np.argwhere(inp != 0)
    out_nz = np.argwhere(out != 0)
    if len(inp_nz) != len(out_nz) or len(inp_nz) == 0:
        continue

    # Try all possible shifts
    for try_dr in range(-h+1, h):
        for try_dc in range(-w+1, w):
            if try_dr == 0 and try_dc == 0:
                continue
            test = np.zeros_like(inp)
            valid = True
            for r, c in inp_nz:
                nr, nc = r + try_dr, c + try_dc
                if 0 <= nr < h and 0 <= nc < w:
                    test[nr, nc] = inp[r, c]
                else:
                    valid = False
                    break
            if valid and np.array_equal(test, out):
                # Verify on all train
                match = True
                for ex in task.train[1:]:
                    if ex.input.shape != ex.output.shape:
                        match = False; break
                    h2, w2 = ex.input.shape
                    t = np.zeros_like(ex.input)
                    for r2, c2 in np.argwhere(ex.input != 0):
                        nr2, nc2 = r2 + try_dr, c2 + try_dc
                        if 0 <= nr2 < h2 and 0 <= nc2 < w2:
                            t[nr2, nc2] = ex.input[r2, c2]
                        else:
                            match = False; break
                    if not match or not np.array_equal(t, ex.output):
                        match = False; break
                if match:
                    translate_hits.append((task.task_id, try_dr, try_dc))
                break  # found a shift that works
        else:
            continue
        break

print(f"  translate: {len(translate_hits)} tasks")
for uid, dr, dc in translate_hits[:10]:
    print(f"    {uid} (dr={dr}, dc={dc})")

# ── Test C: Grid-cell operations ──
print("\n=== Grid divider detection ===")
grid_tasks = []
for task in unsolved_tasks:
    ex0 = task.train[0]
    inp = ex0.input
    h, w = inp.shape

    # Check for row dividers (full row of one color)
    row_dividers = []
    for r in range(h):
        vals = np.unique(inp[r, :])
        if len(vals) == 1 and vals[0] != 0:
            row_dividers.append((r, int(vals[0])))

    # Check for col dividers
    col_dividers = []
    for c in range(w):
        vals = np.unique(inp[:, c])
        if len(vals) == 1 and vals[0] != 0:
            col_dividers.append((c, int(vals[0])))

    if len(row_dividers) >= 1 or len(col_dividers) >= 1:
        grid_tasks.append((task.task_id, len(row_dividers), len(col_dividers)))

print(f"  tasks_with_dividers: {len(grid_tasks)}")
for uid, nr, nc in grid_tasks[:15]:
    print(f"    {uid}: {nr} row dividers, {nc} col dividers")

# ── Test D: Horizontal line between same-color pixels (only fill bg, stop at other fg) ──
print("\n=== H/V line between same-color pixels (stop at other colors) ===")
line_connect_hits = []
for task in unsolved_tasks:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    h, w = inp.shape

    test_out = inp.copy()

    # For each color, find same-color pixels and connect them if on same row/col with only bg between
    for color in range(1, 10):
        # Horizontal
        for r in range(h):
            cols = list(np.where(inp[r, :] == color)[0])
            if len(cols) >= 2:
                for i in range(len(cols) - 1):
                    c1, c2 = cols[i], cols[i+1]
                    # Check only bg between
                    all_bg = all(inp[r, cc] == 0 for cc in range(c1+1, c2))
                    if all_bg and c2 - c1 > 1:
                        for cc in range(c1+1, c2):
                            test_out[r, cc] = color
        # Vertical
        for c in range(w):
            rows = list(np.where(inp[:, c] == color)[0])
            if len(rows) >= 2:
                for i in range(len(rows) - 1):
                    r1, r2 = rows[i], rows[i+1]
                    all_bg = all(inp[rr, c] == 0 for rr in range(r1+1, r2))
                    if all_bg and r2 - r1 > 1:
                        for rr in range(r1+1, r2):
                            test_out[rr, c] = color

    if np.array_equal(test_out, out):
        match = True
        for ex in task.train[1:]:
            if ex.input.shape != ex.output.shape:
                match = False; break
            h2, w2 = ex.input.shape
            t = ex.input.copy()
            for color in range(1, 10):
                for r in range(h2):
                    cols = list(np.where(ex.input[r, :] == color)[0])
                    if len(cols) >= 2:
                        for i in range(len(cols) - 1):
                            c1, c2 = cols[i], cols[i+1]
                            if all(ex.input[r, cc] == 0 for cc in range(c1+1, c2)) and c2 - c1 > 1:
                                for cc in range(c1+1, c2):
                                    t[r, cc] = color
                for c in range(w2):
                    rows = list(np.where(ex.input[:, c] == color)[0])
                    if len(rows) >= 2:
                        for i in range(len(rows) - 1):
                            r1, r2 = rows[i], rows[i+1]
                            if all(ex.input[rr, c] == 0 for rr in range(r1+1, r2)) and r2 - r1 > 1:
                                for rr in range(r1+1, r2):
                                    t[rr, c] = color
            if not np.array_equal(t, ex.output):
                match = False; break
        if match:
            line_connect_hits.append(task.task_id)

print(f"  line_connect: {len(line_connect_hits)} tasks")
for uid in line_connect_hits[:10]:
    print(f"    {uid}")

# ── Test E: Replace color X with color Y consistently ──
print("\n=== Simple consistent color replacement ===")
color_replace_hits = []
for task in unsolved_tasks:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output

    # Find mapping: for each input color, what does it become in output?
    mapping = {}
    valid = True
    for color in range(10):
        mask = inp == color
        if not mask.any():
            continue
        out_at = np.unique(out[mask])
        if len(out_at) != 1:
            valid = False; break
        mapping[color] = int(out_at[0])
    if not valid:
        continue
    # Is this already identity? Skip
    if all(k == v for k, v in mapping.items()):
        continue
    # Check on all train
    match = True
    for ex in task.train:
        if ex.input.shape != ex.output.shape:
            match = False; break
        t = ex.input.copy()
        for src, dst in mapping.items():
            t[ex.input == src] = dst
        if not np.array_equal(t, ex.output):
            match = False; break
    if match:
        color_replace_hits.append((task.task_id, mapping))

print(f"  color_replace: {len(color_replace_hits)} tasks")
for uid, m in color_replace_hits[:10]:
    non_id = {k: v for k, v in m.items() if k != v}
    print(f"    {uid}: {non_id}")

# ── Test F: Invert colors (swap fg/bg) ──
print("\n=== Invert (swap two colors) ===")
invert_hits = []
for task in unsolved_tasks:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    colors = list(set(int(v) for v in np.unique(inp)))
    if len(colors) != 2:
        continue
    a, b = colors
    test = inp.copy()
    test[inp == a] = b
    test[inp == b] = a
    if np.array_equal(test, out):
        match = True
        for ex in task.train[1:]:
            if ex.input.shape != ex.output.shape:
                match = False; break
            t = ex.input.copy()
            t[ex.input == a] = b
            t[ex.input == b] = a
            if not np.array_equal(t, ex.output):
                match = False; break
        if match:
            invert_hits.append((task.task_id, a, b))

print(f"  invert: {len(invert_hits)} tasks")
for uid, a, b in invert_hits[:10]:
    print(f"    {uid}: swap {a}<->{b}")

# ── Test G: Most common color becomes bg, second most becomes fg ──
print("\n=== Conditional recolor: majority->0, minority->specific ===")

# ── Test H: Detect "frame" tasks (border pixels are special) ──
print("\n=== Frame tasks (border is one color, interior changes) ===")
frame_hits = []
for task in unsolved_tasks:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    h, w = inp.shape
    if h < 3 or w < 3:
        continue

    # Check if border is all one color
    border = np.concatenate([inp[0,:], inp[-1,:], inp[1:-1,0], inp[1:-1,-1]])
    border_colors = np.unique(border)
    if len(border_colors) != 1:
        continue
    bc = int(border_colors[0])

    # Check if border is preserved in output
    border_out = np.concatenate([out[0,:], out[-1,:], out[1:-1,0], out[1:-1,-1]])
    if not np.array_equal(border, border_out):
        continue

    # Interior changed?
    interior_in = inp[1:-1, 1:-1]
    interior_out = out[1:-1, 1:-1]
    if np.array_equal(interior_in, interior_out):
        continue

    frame_hits.append((task.task_id, bc, h, w))

print(f"  frame_tasks: {len(frame_hits)}")
for uid, bc, h, w in frame_hits[:15]:
    print(f"    {uid}: border_color={bc}, size={h}x{w}")

# ── SUMMARY ──
print("\n=== SUMMARY ===")
all_new = set()
for name, hits in [
    ("per_region_boundary_fill", per_region_hits),
    ("line_connect", line_connect_hits),
]:
    if hits:
        print(f"  {name}: {len(hits)}")
        all_new.update(hits)
for name, hits in [("translate", translate_hits)]:
    if hits:
        print(f"  {name}: {len(hits)}")
        all_new.update(uid for uid, *_ in hits)
for name, hits in [
    ("color_replace", color_replace_hits),
    ("invert", invert_hits),
]:
    if hits:
        print(f"  {name}: {len(hits)}")
        all_new.update(uid for uid, *_ in hits)

print(f"\nTotal new solvable: {len(all_new)}")
