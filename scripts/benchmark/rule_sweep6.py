#!/usr/bin/env python3
"""Wave 6 sweep: deeper mining on 354 unsolved tasks.

Tests:
1. Why fill_enclosed misses aa300dc3 / d37a1ef5
2. Ray extension from fg pixels (horizontal/vertical lines)
3. Object outline / border drawing
4. Color spread / dilation
5. Gravity (fall down)
6. CC recolor by size rank
7. Neighbor-count-based pixel value
8. Fill bg with nearest fg color
"""
import json, sys, os, numpy as np
from pathlib import Path
from collections import Counter, deque

sys.path.insert(0, "C:/Users/issda/SCBE-AETHERMOORE/src")
sys.path.insert(0, "C:/Users/issda/SCBE-AETHERMOORE")

from neurogolf.arc_io import load_arc_task, ARCTask
from neurogolf.solver import synthesize_program, execute_program

# Load tasks
_REPO = Path("C:/Users/issda/SCBE-AETHERMOORE")
_TASKS_DIR = _REPO / "artifacts" / "arc-data" / "ARC-AGI-master" / "data" / "evaluation"
task_files = sorted(_TASKS_DIR.glob("*.json"))
tasks = [load_arc_task(f) for f in task_files]
print(f"Loaded {len(tasks)} tasks")

# Get unsolved (train-acc based, matching arc_batch logic)
unsolved = []
for task in tasks:
    try:
        sol = synthesize_program(task)
        ok = True
        for ex in task.train:
            pred = execute_program(ex.input, sol.program)
            if pred.shape != ex.output.shape or not (pred == ex.output).all():
                ok = False
                break
        if not ok:
            unsolved.append(task)
    except Exception:
        unsolved.append(task)

print(f"Unsolved: {len(unsolved)}")

def cc_labels(grid, ignore_zero=True):
    """Label connected components. Returns label grid."""
    h, w = grid.shape
    labels = np.zeros_like(grid, dtype=int)
    label_id = 0
    for r in range(h):
        for c in range(w):
            if labels[r, c] != 0:
                continue
            if ignore_zero and grid[r, c] == 0:
                continue
            label_id += 1
            q = deque([(r, c)])
            labels[r, c] = label_id
            while q:
                cr, cc_ = q.popleft()
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = cr+dr, cc_+dc
                    if 0 <= nr < h and 0 <= nc < w and labels[nr, nc] == 0 and grid[nr, nc] == grid[cr, cc_]:
                        labels[nr, nc] = label_id
                        q.append((nr, nc))
    return labels, label_id

def flood_reachable_bg(grid):
    """Find bg cells reachable from edges."""
    h, w = grid.shape
    visited = np.zeros((h, w), dtype=bool)
    q = deque()
    for r in range(h):
        for c in range(w):
            if (r == 0 or r == h-1 or c == 0 or c == w-1) and grid[r, c] == 0:
                visited[r, c] = True
                q.append((r, c))
    while q:
        r, c = q.popleft()
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc] and grid[nr, nc] == 0:
                visited[nr, nc] = True
                q.append((nr, nc))
    return visited

# ── Test 1: Diagnose fill_enclosed tasks ──
print("\n=== Diagnose fill_enclosed ===")
for task in unsolved:
    if task.task_id not in ("aa300dc3", "d37a1ef5"):
        continue
    print(f"\n  {task.task_id}:")
    for i, ex in enumerate(task.train):
        inp, out = ex.input, ex.output
        print(f"    train[{i}]: shape {inp.shape}->{out.shape}")
        if inp.shape != out.shape:
            print(f"      SHAPE MISMATCH")
            continue
        reachable = flood_reachable_bg(inp)
        enclosed = (inp == 0) & ~reachable
        print(f"      enclosed_cells={enclosed.sum()}, reachable_bg={reachable.sum()}")
        diff = inp != out
        changed_mask = diff
        if changed_mask.any():
            print(f"      changed_cells={changed_mask.sum()}")
            # What colors are in input at changed positions?
            inp_at_changed = np.unique(inp[changed_mask])
            out_at_changed = np.unique(out[changed_mask])
            print(f"      inp_colors_at_changed={inp_at_changed.tolist()}")
            print(f"      out_colors_at_changed={out_at_changed.tolist()}")
            # Are changed cells a subset of enclosed?
            if enclosed.any():
                overlap = (changed_mask & enclosed).sum()
                print(f"      overlap_with_enclosed={overlap}, enclosed_total={enclosed.sum()}")
            # Are non-changed cells the same?
            unchanged_match = np.array_equal(inp[~changed_mask], out[~changed_mask])
            print(f"      unchanged_cells_match={unchanged_match}")
        else:
            print(f"      NO CHANGES (identity)")

        # Check if bg=0 is the right assumption
        all_colors_in = np.unique(inp)
        all_colors_out = np.unique(out)
        print(f"      colors_in={all_colors_in.tolist()} colors_out={all_colors_out.tolist()}")

# ── Test 2: Ray extension (horizontal/vertical lines between same-color fg) ──
print("\n=== Ray extension (draw lines between same-color fg pixels) ===")
ray_hits = []
for task in unsolved:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue

    inp, out = ex0.input, ex0.output
    # Try: for each pair of same-color fg pixels on same row or col, fill bg between them
    test_out = inp.copy()
    h, w = inp.shape

    # Horizontal rays
    for r in range(h):
        for color in range(1, 10):
            cols = np.where(inp[r, :] == color)[0]
            if len(cols) >= 2:
                for i in range(len(cols)):
                    for j in range(i+1, len(cols)):
                        c1, c2 = cols[i], cols[j]
                        for cc in range(c1+1, c2):
                            if test_out[r, cc] == 0:
                                test_out[r, cc] = color
    # Vertical rays
    for c in range(w):
        for color in range(1, 10):
            rows = np.where(inp[:, c] == color)[0]
            if len(rows) >= 2:
                for i in range(len(rows)):
                    for j in range(i+1, len(rows)):
                        r1, r2 = rows[i], rows[j]
                        for rr in range(r1+1, r2):
                            if test_out[rr, c] == 0:
                                test_out[rr, c] = color

    if np.array_equal(test_out, out):
        ray_hits.append(task.task_id)

print(f"  ray_connect: {len(ray_hits)} tasks")
for uid in ray_hits[:10]:
    print(f"    {uid}")

# ── Test 3: Gravity (fg pixels fall to bottom) ──
print("\n=== Gravity (fall down) ===")
gravity_hits = []
for task in unsolved:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    h, w = inp.shape
    test_out = np.zeros_like(inp)
    for c in range(w):
        col_vals = [inp[r, c] for r in range(h) if inp[r, c] != 0]
        # Place at bottom
        for i, v in enumerate(reversed(col_vals)):
            test_out[h - 1 - i, c] = v
    if np.array_equal(test_out, out):
        # Verify on all train
        match = True
        for ex in task.train:
            inp2, out2 = ex.input, ex.output
            if inp2.shape != out2.shape:
                match = False; break
            h2, w2 = inp2.shape
            t = np.zeros_like(inp2)
            for c in range(w2):
                col_vals = [inp2[r, c] for r in range(h2) if inp2[r, c] != 0]
                for i, v in enumerate(reversed(col_vals)):
                    t[h2 - 1 - i, c] = v
            if not np.array_equal(t, out2):
                match = False; break
        if match:
            gravity_hits.append(task.task_id)

print(f"  gravity_down: {len(gravity_hits)} tasks")
for uid in gravity_hits[:10]:
    print(f"    {uid}")

# ── Test 4: Gravity preserving order (vs reversing) ──
print("\n=== Gravity (fall down, preserve top-to-bottom order) ===")
gravity_order_hits = []
for task in unsolved:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    h, w = inp.shape
    test_out = np.zeros_like(inp)
    for c in range(w):
        col_vals = [inp[r, c] for r in range(h) if inp[r, c] != 0]
        # Place at bottom, preserve order
        start = h - len(col_vals)
        for i, v in enumerate(col_vals):
            test_out[start + i, c] = v
    if np.array_equal(test_out, out):
        match = True
        for ex in task.train:
            inp2, out2 = ex.input, ex.output
            if inp2.shape != out2.shape:
                match = False; break
            h2, w2 = inp2.shape
            t = np.zeros_like(inp2)
            for c in range(w2):
                col_vals = [inp2[r, c] for r in range(h2) if inp2[r, c] != 0]
                start = h2 - len(col_vals)
                for i, v in enumerate(col_vals):
                    t[start + i, c] = v
            if not np.array_equal(t, out2):
                match = False; break
        if match:
            gravity_order_hits.append(task.task_id)

print(f"  gravity_ordered: {len(gravity_order_hits)} tasks")
for uid in gravity_order_hits[:10]:
    print(f"    {uid}")

# ── Test 5: Color spread / dilation ──
print("\n=== Color dilation (each fg pixel spreads to 4-adjacent bg) ===")
dilate_hits = []
for task in unsolved:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    h, w = inp.shape
    test_out = inp.copy()
    for r in range(h):
        for c in range(w):
            if inp[r, c] != 0:
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < h and 0 <= nc < w and inp[nr, nc] == 0:
                        test_out[nr, nc] = inp[r, c]
    if np.array_equal(test_out, out):
        match = True
        for ex in task.train:
            if ex.input.shape != ex.output.shape:
                match = False; break
            h2, w2 = ex.input.shape
            t = ex.input.copy()
            for r in range(h2):
                for c in range(w2):
                    if ex.input[r, c] != 0:
                        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                            nr, nc = r+dr, c+dc
                            if 0 <= nr < h2 and 0 <= nc < w2 and ex.input[nr, nc] == 0:
                                t[nr, nc] = ex.input[r, c]
            if not np.array_equal(t, ex.output):
                match = False; break
        if match:
            dilate_hits.append(task.task_id)

print(f"  dilation: {len(dilate_hits)} tasks")
for uid in dilate_hits[:10]:
    print(f"    {uid}")

# ── Test 6: Remove smallest CC ──
print("\n=== Remove smallest CC (by cell count) ===")
rm_small_hits = []
for task in unsolved:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    labels, n = cc_labels(inp)
    if n < 2:
        continue
    sizes = {}
    for lid in range(1, n+1):
        sizes[lid] = (labels == lid).sum()
    min_size = min(sizes.values())
    test_out = inp.copy()
    for lid, sz in sizes.items():
        if sz == min_size:
            test_out[labels == lid] = 0
    if np.array_equal(test_out, out):
        match = True
        for ex in task.train:
            if ex.input.shape != ex.output.shape:
                match = False; break
            l2, n2 = cc_labels(ex.input)
            if n2 < 2:
                match = False; break
            sz2 = {}
            for lid in range(1, n2+1):
                sz2[lid] = (l2 == lid).sum()
            ms = min(sz2.values())
            t = ex.input.copy()
            for lid, s in sz2.items():
                if s == ms:
                    t[l2 == lid] = 0
            if not np.array_equal(t, ex.output):
                match = False; break
        if match:
            rm_small_hits.append(task.task_id)

print(f"  remove_smallest_cc: {len(rm_small_hits)} tasks")
for uid in rm_small_hits[:10]:
    print(f"    {uid}")

# ── Test 7: Keep only largest CC ──
print("\n=== Keep only largest CC ===")
keep_large_hits = []
for task in unsolved:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    labels, n = cc_labels(inp)
    if n < 2:
        continue
    sizes = {}
    for lid in range(1, n+1):
        sizes[lid] = (labels == lid).sum()
    max_size = max(sizes.values())
    test_out = np.zeros_like(inp)
    for lid, sz in sizes.items():
        if sz == max_size:
            test_out[labels == lid] = inp[labels == lid]
    if np.array_equal(test_out, out):
        match = True
        for ex in task.train:
            if ex.input.shape != ex.output.shape:
                match = False; break
            l2, n2 = cc_labels(ex.input)
            if n2 < 2:
                match = False; break
            sz2 = {}
            for lid in range(1, n2+1):
                sz2[lid] = (l2 == lid).sum()
            mx = max(sz2.values())
            t = np.zeros_like(ex.input)
            for lid, s in sz2.items():
                if s == mx:
                    t[l2 == lid] = ex.input[l2 == lid]
            if not np.array_equal(t, ex.output):
                match = False; break
        if match:
            keep_large_hits.append(task.task_id)

print(f"  keep_largest_cc: {len(keep_large_hits)} tasks")
for uid in keep_large_hits[:10]:
    print(f"    {uid}")

# ── Test 8: Fill bg with nearest fg color (L1 distance) ──
print("\n=== Fill bg with nearest fg color ===")
nearest_hits = []
for task in unsolved:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    h, w = inp.shape
    if (inp == 0).sum() == 0:
        continue
    # BFS from all fg pixels simultaneously
    test_out = inp.copy()
    dist = np.full((h, w), 999999, dtype=int)
    q = deque()
    for r in range(h):
        for c in range(w):
            if inp[r, c] != 0:
                dist[r, c] = 0
                q.append((r, c))
    while q:
        r, c = q.popleft()
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < h and 0 <= nc < w and dist[nr, nc] > dist[r, c] + 1:
                dist[nr, nc] = dist[r, c] + 1
                test_out[nr, nc] = test_out[r, c]
                q.append((nr, nc))
    if np.array_equal(test_out, out):
        match = True
        for ex in task.train[1:]:
            if ex.input.shape != ex.output.shape:
                match = False; break
            h2, w2 = ex.input.shape
            t = ex.input.copy()
            d = np.full((h2, w2), 999999, dtype=int)
            q2 = deque()
            for r in range(h2):
                for c in range(w2):
                    if ex.input[r, c] != 0:
                        d[r, c] = 0
                        q2.append((r, c))
            while q2:
                r, c = q2.popleft()
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < h2 and 0 <= nc < w2 and d[nr, nc] > d[r, c] + 1:
                        d[nr, nc] = d[r, c] + 1
                        t[nr, nc] = t[r, c]
                        q2.append((nr, nc))
            if not np.array_equal(t, ex.output):
                match = False; break
        if match:
            nearest_hits.append(task.task_id)

print(f"  nearest_fg_fill: {len(nearest_hits)} tasks")
for uid in nearest_hits[:10]:
    print(f"    {uid}")

# ── Test 9: Draw outline around each CC (in a fixed color) ──
print("\n=== Outline CCs ===")
outline_hits = {}  # color -> list of uids
for task in unsolved:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    diff = inp != out
    if not diff.any():
        continue
    # Changed cells: what are their output colors?
    out_colors_at_changed = np.unique(out[diff])
    if len(out_colors_at_changed) != 1:
        continue
    outline_color = int(out_colors_at_changed[0])
    # Check: each changed cell is bg (0) and adjacent to fg
    h, w = inp.shape
    valid = True
    for r in range(h):
        for c in range(w):
            if diff[r, c]:
                if inp[r, c] != 0:
                    valid = False; break
                # Must be adjacent to fg
                has_fg_neighbor = False
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < h and 0 <= nc < w and inp[nr, nc] != 0:
                        has_fg_neighbor = True; break
                if not has_fg_neighbor:
                    valid = False; break
        if not valid:
            break
    if not valid:
        continue

    # Also check: ALL bg cells adjacent to fg should be changed
    all_outline = True
    for r in range(h):
        for c in range(w):
            if inp[r, c] == 0:
                has_fg = False
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < h and 0 <= nc < w and inp[nr, nc] != 0:
                        has_fg = True; break
                if has_fg and not diff[r, c]:
                    all_outline = False; break
        if not all_outline:
            break

    if all_outline:
        # Verify on all train
        match = True
        for ex in task.train[1:]:
            if ex.input.shape != ex.output.shape:
                match = False; break
            d2 = ex.input != ex.output
            h2, w2 = ex.input.shape
            for r in range(h2):
                for c in range(w2):
                    is_outline = (ex.input[r, c] == 0)
                    hfn = False
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < h2 and 0 <= nc < w2 and ex.input[nr, nc] != 0:
                            hfn = True; break
                    expected_change = is_outline and hfn
                    if expected_change:
                        if not d2[r, c] or ex.output[r, c] != outline_color:
                            match = False; break
                    else:
                        if d2[r, c]:
                            match = False; break
                if not match:
                    break
            if not match:
                break
        if match:
            if outline_color not in outline_hits:
                outline_hits[outline_color] = []
            outline_hits[outline_color].append(task.task_id)

print(f"  outline_cc (total): {sum(len(v) for v in outline_hits.values())} tasks")
for color, uids in sorted(outline_hits.items()):
    print(f"    color={color}: {len(uids)} tasks: {uids[:5]}")

# ── Test 10: Extend fg pixels to edges (ray to edge) ===
print("\n=== Extend fg pixels as rays to all edges ===")
ray_edge_hits = []
for task in unsolved:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    h, w = inp.shape
    test_out = inp.copy()
    for r in range(h):
        for c in range(w):
            if inp[r, c] != 0:
                color = inp[r, c]
                # Extend in all 4 directions
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = r+dr, c+dc
                    while 0 <= nr < h and 0 <= nc < w:
                        if test_out[nr, nc] == 0:
                            test_out[nr, nc] = color
                        elif test_out[nr, nc] != color:
                            break
                        nr += dr
                        nc += dc
    if np.array_equal(test_out, out):
        match = True
        for ex in task.train[1:]:
            if ex.input.shape != ex.output.shape:
                match = False; break
            h2, w2 = ex.input.shape
            t = ex.input.copy()
            for r in range(h2):
                for c in range(w2):
                    if ex.input[r, c] != 0:
                        color = ex.input[r, c]
                        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                            nr, nc = r+dr, c+dc
                            while 0 <= nr < h2 and 0 <= nc < w2:
                                if t[nr, nc] == 0:
                                    t[nr, nc] = color
                                elif t[nr, nc] != color:
                                    break
                                nr += dr
                                nc += dc
            if not np.array_equal(t, ex.output):
                match = False; break
        if match:
            ray_edge_hits.append(task.task_id)

print(f"  ray_to_edge: {len(ray_edge_hits)} tasks")
for uid in ray_edge_hits[:10]:
    print(f"    {uid}")

# ── Test 11: Denoise - replace minority pixels with majority neighbor ──
print("\n=== Denoise (replace each pixel with majority of its neighbors) ===")
denoise_hits = []
for task in unsolved:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    h, w = inp.shape
    test_out = inp.copy()
    for r in range(h):
        for c in range(w):
            neighbors = []
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < h and 0 <= nc < w:
                        neighbors.append(int(inp[nr, nc]))
            cnt = Counter(neighbors)
            test_out[r, c] = cnt.most_common(1)[0][0]
    if np.array_equal(test_out, out):
        match = True
        for ex in task.train[1:]:
            if ex.input.shape != ex.output.shape:
                match = False; break
            h2, w2 = ex.input.shape
            t = ex.input.copy()
            for r in range(h2):
                for c in range(w2):
                    nb = []
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            nr, nc = r+dr, c+dc
                            if 0 <= nr < h2 and 0 <= nc < w2:
                                nb.append(int(ex.input[nr, nc]))
                    cnt = Counter(nb)
                    t[r, c] = cnt.most_common(1)[0][0]
            if not np.array_equal(t, ex.output):
                match = False; break
        if match:
            denoise_hits.append(task.task_id)

print(f"  denoise: {len(denoise_hits)} tasks")
for uid in denoise_hits[:10]:
    print(f"    {uid}")

# ── Test 12: Sort rows by some criterion ──
print("\n=== Sort rows by number of non-zero pixels ===")
sort_row_hits = []
for task in unsolved:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    h, w = inp.shape
    # Sort rows by number of non-zero pixels (ascending)
    row_counts = [(np.count_nonzero(inp[r, :]), r) for r in range(h)]
    row_counts.sort()
    test_asc = np.array([inp[r, :] for _, r in row_counts])
    row_counts_desc = sorted(row_counts, reverse=True)
    test_desc = np.array([inp[r, :] for _, r in row_counts_desc])

    if np.array_equal(test_asc, out) or np.array_equal(test_desc, out):
        ascending = np.array_equal(test_asc, out)
        match = True
        for ex in task.train[1:]:
            if ex.input.shape != ex.output.shape:
                match = False; break
            h2, w2 = ex.input.shape
            rc = [(np.count_nonzero(ex.input[r, :]), r) for r in range(h2)]
            if ascending:
                rc.sort()
            else:
                rc.sort(reverse=True)
            t = np.array([ex.input[r, :] for _, r in rc])
            if not np.array_equal(t, ex.output):
                match = False; break
        if match:
            sort_row_hits.append((task.task_id, "asc" if ascending else "desc"))

print(f"  sort_rows: {len(sort_row_hits)} tasks")
for uid, d in sort_row_hits[:10]:
    print(f"    {uid} ({d})")

# ── Test 13: Sort columns ──
print("\n=== Sort columns by number of non-zero pixels ===")
sort_col_hits = []
for task in unsolved:
    ex0 = task.train[0]
    if ex0.input.shape != ex0.output.shape:
        continue
    inp, out = ex0.input, ex0.output
    h, w = inp.shape
    col_counts = [(np.count_nonzero(inp[:, c]), c) for c in range(w)]
    col_counts.sort()
    test_asc = np.column_stack([inp[:, c] for _, c in col_counts])
    col_counts_desc = sorted(col_counts, reverse=True)
    test_desc = np.column_stack([inp[:, c] for _, c in col_counts_desc])

    if np.array_equal(test_asc, out) or np.array_equal(test_desc, out):
        ascending = np.array_equal(test_asc, out)
        match = True
        for ex in task.train[1:]:
            if ex.input.shape != ex.output.shape:
                match = False; break
            h2, w2 = ex.input.shape
            cc2 = [(np.count_nonzero(ex.input[:, c]), c) for c in range(w2)]
            if ascending:
                cc2.sort()
            else:
                cc2.sort(reverse=True)
            t = np.column_stack([ex.input[:, c] for _, c in cc2])
            if not np.array_equal(t, ex.output):
                match = False; break
        if match:
            sort_col_hits.append((task.task_id, "asc" if ascending else "desc"))

print(f"  sort_cols: {len(sort_col_hits)} tasks")
for uid, d in sort_col_hits[:10]:
    print(f"    {uid} ({d})")

print("\n=== SUMMARY ===")
all_hits = set()
for name, hits in [
    ("ray_connect", ray_hits),
    ("gravity_down", gravity_hits),
    ("gravity_ordered", gravity_order_hits),
    ("dilation", dilate_hits),
    ("remove_smallest_cc", rm_small_hits),
    ("keep_largest_cc", keep_large_hits),
    ("nearest_fg_fill", nearest_hits),
    ("ray_to_edge", ray_edge_hits),
    ("denoise", denoise_hits),
]:
    if hits:
        print(f"  {name}: {len(hits)} tasks")
        all_hits.update(hits)
for name, hits in [("sort_rows", sort_row_hits), ("sort_cols", sort_col_hits)]:
    if hits:
        print(f"  {name}: {len(hits)} tasks")
        all_hits.update(uid for uid, _ in hits)
for color, uids in outline_hits.items():
    print(f"  outline(color={color}): {len(uids)} tasks")
    all_hits.update(uids)

print(f"\nTotal unique new solvable: {len(all_hits)}")
