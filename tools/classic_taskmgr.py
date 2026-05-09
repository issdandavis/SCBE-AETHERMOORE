"""Classic Windows Task Manager -- the original was good because it was
small, fast, and showed exactly what mattered. This reimplementation
keeps that ethos (single file, stdlib + psutil, sub-second refresh)
and adds the handful of features the original was missing or that
later Windows builds added before bloat set in.

Tabs:
  - Applications: top-level windows. Win32-only (EnumWindows via
    ctypes); on other platforms the tab shows a stub.
  - Processes: psutil-backed sortable table (PID / name / user / CPU%
    / mem / disk-rate). Filter box for typing-as-you-search. Right-
    click row for End Process / End Process Tree / Open File Location.
  - Performance: live CPU + memory + network history graphs in the
    iconic green-on-black style. XP-SP1 added net; modern systems
    need it.

Update Speed setting (View menu) ports the XP "Paused/Low/Normal/
High" cadence -- when you're inspecting a UI hang you don't want
the table reshuffling under the cursor.

Run:
    python -m tools.classic_taskmgr
or
    python tools/classic_taskmgr.py
"""

from __future__ import annotations

import sys
import tkinter as tk
import tkinter.font as tkfont
from collections import deque
from tkinter import messagebox, ttk
from typing import Deque, List, Optional, Tuple

import psutil

# --- Colors / sizes (locked to the classic Win2k/XP palette). -------
BG_DARK = "#000000"
GRID_DARK = "#101810"
GRID_LINE = "#003800"
GREEN_LINE = "#00FF00"
GREEN_FILL = "#003C00"
PANEL_BG = "#ECE9D8"  # XP "Luna" beige
TEXT_DARK = "#000000"
HISTORY_LEN = 60  # samples visible
DEFAULT_REFRESH_MS = 1000

# View > Update Speed: Paused/Low/Normal/High (XP-faithful cadences).
SPEED_PRESETS = {
    "High": 500,
    "Normal": 1000,
    "Low": 4000,
    "Paused": None,  # None = no auto-refresh
}


# ============================================================
# Applications tab -- Win32-only, stubbed elsewhere.
# ============================================================
def _enumerate_windows() -> List[Tuple[int, str]]:
    """Return [(hwnd, title)] for visible top-level windows on Win32."""
    if not sys.platform.startswith("win"):
        return []
    import ctypes
    from ctypes import wintypes

    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

    hits: List[Tuple[int, str]] = []

    def _proc(hwnd: int, _lparam: int) -> bool:
        if not IsWindowVisible(hwnd):
            return True
        n = GetWindowTextLength(hwnd)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        GetWindowText(hwnd, buf, n + 1)
        title = buf.value
        if title:
            hits.append((int(hwnd), title))
        return True

    EnumWindows(EnumWindowsProc(_proc), 0)
    return hits


class ApplicationsTab(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=4)
        cols = ("task", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        self.tree.heading("task", text="Task")
        self.tree.heading("status", text="Status")
        self.tree.column("task", width=440, anchor="w")
        self.tree.column("status", width=100, anchor="w")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        btns = ttk.Frame(self)
        btns.grid(row=1, column=0, columnspan=2, sticky="e", pady=(4, 0))
        ttk.Button(btns, text="End Task", command=self._end_task).pack(side="right", padx=2)
        ttk.Button(btns, text="Switch To", command=self._switch_to).pack(side="right", padx=2)
        ttk.Button(btns, text="New Task...", command=self._new_task).pack(side="right", padx=2)

        self.refresh()

    def refresh(self) -> None:
        sel_hwnd = self._selected_hwnd()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for hwnd, title in _enumerate_windows():
            self.tree.insert("", "end", iid=str(hwnd), values=(title, "Running"))
        if sel_hwnd is not None and self.tree.exists(str(sel_hwnd)):
            self.tree.selection_set(str(sel_hwnd))

    def _selected_hwnd(self) -> Optional[int]:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _end_task(self) -> None:
        hwnd = self._selected_hwnd()
        if hwnd is None or not sys.platform.startswith("win"):
            return
        import ctypes

        WM_CLOSE = 0x0010
        ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)

    def _switch_to(self) -> None:
        hwnd = self._selected_hwnd()
        if hwnd is None or not sys.platform.startswith("win"):
            return
        import ctypes

        ctypes.windll.user32.SetForegroundWindow(hwnd)

    def _new_task(self) -> None:
        dlg = tk.Toplevel(self)
        dlg.title("Create New Task")
        dlg.resizable(False, False)
        ttk.Label(dlg, text="Open:").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        var = tk.StringVar()
        e = ttk.Entry(dlg, textvariable=var, width=42)
        e.grid(row=0, column=1, padx=4, pady=8)
        e.focus_set()

        def _go() -> None:
            cmd = var.get().strip()
            if not cmd:
                return
            try:
                import subprocess

                subprocess.Popen(cmd, shell=True)
                dlg.destroy()
            except Exception as exc:
                messagebox.showerror("Create New Task", str(exc), parent=dlg)

        ttk.Button(dlg, text="OK", command=_go).grid(row=1, column=1, sticky="e", padx=4, pady=4)
        dlg.bind("<Return>", lambda _e: _go())


# ============================================================
# Processes tab -- psutil-backed sortable table.
# ============================================================
class ProcessesTab(ttk.Frame):
    COLUMNS = (
        ("pid", "PID", 70, "e"),
        ("name", "Image Name", 220, "w"),
        ("user", "User Name", 130, "w"),
        ("cpu", "CPU", 55, "e"),
        ("mem", "Mem Usage", 100, "e"),
        ("io", "I/O KB/s", 80, "e"),
    )

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=4)
        # Top: filter / search box. Tiny addition; massive value when
        # you're hunting a process by name in a list of 400+.
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Label(bar, text="Filter:").pack(side="left", padx=(2, 4))
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(bar, textvariable=self._filter_var, width=30).pack(side="left")
        ttk.Label(bar, textvariable=self._make_count_var()).pack(side="right", padx=4)

        col_ids = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(self, columns=col_ids, show="headings", height=20)
        for cid, label, width, anchor in self.COLUMNS:
            self.tree.heading(cid, text=label, command=lambda c=cid: self._sort_by(c))
            self.tree.column(cid, width=width, anchor=anchor)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        sb.grid(row=1, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Right-click context menu (End / End Tree / Open Location).
        self._menu = tk.Menu(self, tearoff=0)
        self._menu.add_command(label="End Process", command=self._end_process)
        self._menu.add_command(label="End Process Tree", command=self._end_process_tree)
        self._menu.add_separator()
        self._menu.add_command(label="Open File Location", command=self._open_file_location)
        self._menu.add_command(label="Properties...", command=self._properties)
        self.tree.bind("<Button-3>", self._popup_menu)

        btns = ttk.Frame(self)
        btns.grid(row=2, column=0, columnspan=2, sticky="e", pady=(4, 0))
        ttk.Button(btns, text="End Process", command=self._end_process).pack(side="right", padx=2)

        self._sort_col = "cpu"
        self._sort_desc = True
        # I/O rate calc needs prior-tick byte counts.
        self._io_prev: dict[int, Tuple[int, float]] = {}
        self.refresh()

    def _make_count_var(self) -> tk.StringVar:
        self._count_var = tk.StringVar(value="")
        return self._count_var

    def _sort_by(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = col
            self._sort_desc = True
        self.refresh()

    def refresh(self) -> None:
        import time

        sel = self._selected_pid()
        flt = self._filter_var.get().strip().lower()
        rows: List[dict] = []
        now = time.monotonic()
        new_io: dict[int, Tuple[int, float]] = {}
        for p in psutil.process_iter(attrs=["pid", "name", "username", "cpu_percent", "memory_info"]):
            try:
                info = p.info
                mem = info["memory_info"].rss if info["memory_info"] else 0
                # Disk I/O rate (KB/s) via delta between ticks.
                io_kbs = 0.0
                try:
                    io = p.io_counters()
                    total_bytes = io.read_bytes + io.write_bytes
                    new_io[info["pid"]] = (total_bytes, now)
                    prev = self._io_prev.get(info["pid"])
                    if prev is not None:
                        prev_bytes, prev_t = prev
                        dt = max(0.001, now - prev_t)
                        io_kbs = max(0.0, (total_bytes - prev_bytes) / dt / 1024)
                except (psutil.AccessDenied, AttributeError):
                    pass
                row = {
                    "pid": info["pid"],
                    "name": info["name"] or "?",
                    "user": (info["username"] or "").split("\\")[-1],
                    "cpu_raw": info["cpu_percent"] or 0.0,
                    "mem_raw": mem,
                    "io_raw": io_kbs,
                }
                if (
                    flt
                    and flt not in row["name"].lower()
                    and flt not in str(row["pid"])
                    and flt not in row["user"].lower()
                ):
                    continue
                rows.append(row)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        self._io_prev = new_io

        key_map = {
            "pid": lambda r: r["pid"],
            "name": lambda r: r["name"].lower(),
            "user": lambda r: r["user"].lower(),
            "cpu": lambda r: r["cpu_raw"],
            "mem": lambda r: r["mem_raw"],
            "io": lambda r: r["io_raw"],
        }
        rows.sort(key=key_map[self._sort_col], reverse=self._sort_desc)

        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for r in rows:
            self.tree.insert(
                "",
                "end",
                iid=str(r["pid"]),
                values=(
                    r["pid"],
                    r["name"],
                    r["user"],
                    f"{r['cpu_raw']:>5.1f}",
                    f"{r['mem_raw'] // 1024:>9,} K",
                    f"{r['io_raw']:>8.0f}",
                ),
            )
        if sel is not None and self.tree.exists(str(sel)):
            self.tree.selection_set(str(sel))
        self._count_var.set(f"{len(rows)} processes")

    def _selected_pid(self) -> Optional[int]:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _popup_menu(self, event: tk.Event) -> None:
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        self._menu.tk_popup(event.x_root, event.y_root)

    def _confirm_end(self, name: str, pid: int, *, tree: bool = False) -> bool:
        msg = f"Are you sure you want to end the process {name!r} (PID {pid})?"
        if tree:
            msg = f"End {name!r} (PID {pid}) and ALL of its child processes?"
        msg += "\n\nData may be lost. Unsaved changes will not be saved."
        return messagebox.askyesno("End Process" if not tree else "End Process Tree", msg, icon="warning")

    def _end_process(self) -> None:
        pid = self._selected_pid()
        if pid is None:
            return
        try:
            p = psutil.Process(pid)
            name = p.name()
        except psutil.NoSuchProcess:
            return
        if not self._confirm_end(name, pid):
            return
        try:
            p.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            messagebox.showerror("End Process", f"Could not terminate PID {pid}: {exc}")

    def _end_process_tree(self) -> None:
        pid = self._selected_pid()
        if pid is None:
            return
        try:
            p = psutil.Process(pid)
            name = p.name()
            kids = p.children(recursive=True)
        except psutil.NoSuchProcess:
            return
        if not self._confirm_end(name, pid, tree=True):
            return
        for child in kids:
            try:
                child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        try:
            p.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            messagebox.showerror("End Process Tree", f"Could not terminate PID {pid}: {exc}")

    def _open_file_location(self) -> None:
        pid = self._selected_pid()
        if pid is None:
            return
        try:
            exe = psutil.Process(pid).exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            messagebox.showerror("Open File Location", str(exc))
            return
        if not exe:
            return
        if sys.platform.startswith("win"):
            import subprocess

            subprocess.Popen(["explorer", "/select,", exe])
        else:
            messagebox.showinfo("Open File Location", exe)

    def _properties(self) -> None:
        pid = self._selected_pid()
        if pid is None:
            return
        try:
            p = psutil.Process(pid)
            info = (
                f"Name:    {p.name()}\n"
                f"PID:     {p.pid}\n"
                f"User:    {p.username()}\n"
                f"Status:  {p.status()}\n"
                f"Started: {p.create_time()}\n"
                f"Threads: {p.num_threads()}\n"
                f"Exe:     {p.exe()}\n"
                f"Cmdline: {' '.join(p.cmdline())[:200]}"
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            info = f"Error: {exc}"
        messagebox.showinfo(f"Properties: PID {pid}", info, parent=self)


# ============================================================
# Performance tab -- the iconic green line graphs.
# ============================================================
class HistoryGraph(tk.Canvas):
    """Single green-on-black line graph with grid, like the XP graphs."""

    def __init__(self, parent: tk.Misc, *, title: str, width: int = 320, height: int = 110) -> None:
        super().__init__(
            parent, width=width, height=height, bg=BG_DARK, highlightthickness=1, highlightbackground="#666"
        )
        self._title = title
        # Don't use _w / _h here -- tkinter reserves _w for the widget
        # path name. Renamed to _gw / _gh to keep the canvas working.
        self._gw = width
        self._gh = height
        self._history: Deque[float] = deque(maxlen=HISTORY_LEN)
        # Pre-fill so the line starts on the right and scrolls left.
        for _ in range(HISTORY_LEN):
            self._history.append(0.0)

    def push(self, value_pct: float) -> None:
        """Append a sample (0..100) and redraw."""
        v = max(0.0, min(100.0, float(value_pct)))
        self._history.append(v)
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        # Grid (10x10 cells, scrolling 1 cell every 6s like XP).
        cell_w = self._gw / 10
        cell_h = self._gh / 10
        for i in range(1, 10):
            x = i * cell_w
            self.create_line(x, 0, x, self._gh, fill=GRID_LINE)
            y = i * cell_h
            self.create_line(0, y, self._gw, y, fill=GRID_LINE)

        # Filled area + line.
        n = len(self._history)
        if n < 2:
            return
        step = self._gw / (HISTORY_LEN - 1)
        coords: List[float] = []
        for i, v in enumerate(self._history):
            x = i * step
            y = self._gh - (v / 100.0) * self._gh
            coords.extend([x, y])

        # Fill polygon: line + bottom corners.
        poly = list(coords) + [self._gw, self._gh, 0, self._gh]
        self.create_polygon(*poly, fill=GREEN_FILL, outline="")
        self.create_line(*coords, fill=GREEN_LINE, width=1)

        # Title in the corner.
        self.create_text(6, 6, anchor="nw", text=self._title, fill=GREEN_LINE, font=("Lucida Console", 8, "bold"))


class PerformanceTab(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=8)

        # Top: two big readouts (CPU usage % + memory usage %).
        top = ttk.Frame(self)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        self.cpu_label = ttk.Label(top, text="CPU Usage", font=("Tahoma", 8))
        self.cpu_label.grid(row=0, column=0, padx=4, sticky="w")
        self.cpu_history_label = ttk.Label(top, text="CPU Usage History", font=("Tahoma", 8))
        self.cpu_history_label.grid(row=0, column=1, padx=4, sticky="w")
        self.mem_label = ttk.Label(top, text="PF Usage", font=("Tahoma", 8))
        self.mem_label.grid(row=2, column=0, padx=4, sticky="w", pady=(8, 0))
        self.mem_history_label = ttk.Label(top, text="Page File Usage History", font=("Tahoma", 8))
        self.mem_history_label.grid(row=2, column=1, padx=4, sticky="w", pady=(8, 0))

        # CPU panel: little gauge + history strip.
        self.cpu_gauge = HistoryGraph(top, title="CPU", width=120, height=110)
        self.cpu_gauge.grid(row=1, column=0, padx=4)
        self.cpu_history = HistoryGraph(top, title="CPU Usage History", width=420, height=110)
        self.cpu_history.grid(row=1, column=1, padx=4, sticky="w")

        self.mem_gauge = HistoryGraph(top, title="MEM", width=120, height=110)
        self.mem_gauge.grid(row=3, column=0, padx=4)
        self.mem_history = HistoryGraph(top, title="Memory Usage History", width=420, height=110)
        self.mem_history.grid(row=3, column=1, padx=4, sticky="w")

        # XP-SP1 added Networking; modern systems are net-bound often.
        self.net_label = ttk.Label(top, text="Network", font=("Tahoma", 8))
        self.net_label.grid(row=4, column=0, padx=4, sticky="w", pady=(8, 0))
        self.net_history_label = ttk.Label(top, text="Network Throughput", font=("Tahoma", 8))
        self.net_history_label.grid(row=4, column=1, padx=4, sticky="w", pady=(8, 0))
        self.net_gauge = HistoryGraph(top, title="NET", width=120, height=110)
        self.net_gauge.grid(row=5, column=0, padx=4)
        self.net_history = HistoryGraph(top, title="Network Throughput History", width=420, height=110)
        self.net_history.grid(row=5, column=1, padx=4, sticky="w")
        # Net rate is normalized against an adaptive ceiling so the line
        # is readable regardless of link speed.
        self._net_prev: Optional[Tuple[int, int, float]] = None
        self._net_ceiling_bps = 1_000_000.0  # starts at 1 MB/s, grows

        # Bottom: totals (Win2k/XP-style fixed-grid readouts).
        totals = ttk.LabelFrame(self, text="Totals")
        totals.grid(row=4, column=0, sticky="nsew", pady=(8, 0))
        self.totals_vars = {
            "Handles": tk.StringVar(value="-"),
            "Threads": tk.StringVar(value="-"),
            "Processes": tk.StringVar(value="-"),
        }
        for i, (k, v) in enumerate(self.totals_vars.items()):
            ttk.Label(totals, text=k, width=12).grid(row=i, column=0, sticky="w", padx=6, pady=2)
            ttk.Label(totals, textvariable=v, width=10, anchor="e").grid(row=i, column=1, sticky="e", padx=6, pady=2)

        commit = ttk.LabelFrame(self, text="Commit Charge (K)")
        commit.grid(row=4, column=1, sticky="nsew", pady=(8, 0), padx=(8, 0))
        self.commit_vars = {
            "Total": tk.StringVar(value="-"),
            "Limit": tk.StringVar(value="-"),
            "Peak": tk.StringVar(value="-"),
        }
        for i, (k, v) in enumerate(self.commit_vars.items()):
            ttk.Label(commit, text=k, width=12).grid(row=i, column=0, sticky="w", padx=6, pady=2)
            ttk.Label(commit, textvariable=v, width=14, anchor="e").grid(row=i, column=1, sticky="e", padx=6, pady=2)

        phys = ttk.LabelFrame(self, text="Physical Memory (K)")
        phys.grid(row=5, column=0, sticky="nsew", pady=(6, 0))
        self.phys_vars = {
            "Total": tk.StringVar(value="-"),
            "Available": tk.StringVar(value="-"),
            "System Cache": tk.StringVar(value="-"),
        }
        for i, (k, v) in enumerate(self.phys_vars.items()):
            ttk.Label(phys, text=k, width=14).grid(row=i, column=0, sticky="w", padx=6, pady=2)
            ttk.Label(phys, textvariable=v, width=14, anchor="e").grid(row=i, column=1, sticky="e", padx=6, pady=2)

        kern = ttk.LabelFrame(self, text="Kernel Memory (K)")
        kern.grid(row=5, column=1, sticky="nsew", pady=(6, 0), padx=(8, 0))
        self.kern_vars = {
            "Total": tk.StringVar(value="-"),
            "Paged": tk.StringVar(value="-"),
            "Nonpaged": tk.StringVar(value="-"),
        }
        for i, (k, v) in enumerate(self.kern_vars.items()):
            ttk.Label(kern, text=k, width=12).grid(row=i, column=0, sticky="w", padx=6, pady=2)
            ttk.Label(kern, textvariable=v, width=14, anchor="e").grid(row=i, column=1, sticky="e", padx=6, pady=2)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self._peak_commit_kb = 0
        self.refresh()

    def refresh(self) -> None:
        import time

        cpu = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()
        self.cpu_gauge.push(cpu)
        self.cpu_history.push(cpu)
        mem_pct = vm.percent
        self.mem_gauge.push(mem_pct)
        self.mem_history.push(mem_pct)

        # Network: aggregate bytes/sec across all NICs, normalized to
        # an adaptive ceiling so the graph stays readable.
        net = psutil.net_io_counters()
        now = time.monotonic()
        net_pct = 0.0
        net_bps = 0.0
        if self._net_prev is not None:
            prev_in, prev_out, prev_t = self._net_prev
            dt = max(0.001, now - prev_t)
            delta_bytes = max(0, (net.bytes_recv - prev_in) + (net.bytes_sent - prev_out))
            net_bps = delta_bytes / dt
            if net_bps > self._net_ceiling_bps:
                self._net_ceiling_bps = net_bps * 1.25
            net_pct = min(100.0, (net_bps / self._net_ceiling_bps) * 100.0)
        self._net_prev = (net.bytes_recv, net.bytes_sent, now)
        self.net_gauge.push(net_pct)
        self.net_history.push(net_pct)

        # Top labels.
        self.cpu_label.configure(text=f"CPU Usage: {cpu:5.1f} %")
        self.mem_label.configure(text=f"Memory Usage: {mem_pct:5.1f} %")
        if net_bps >= 1_000_000:
            self.net_label.configure(text=f"Network: {net_bps / 1_000_000:5.2f} MB/s")
        else:
            self.net_label.configure(text=f"Network: {net_bps / 1024:5.1f} KB/s")

        # Totals.
        try:
            n_threads = sum(p.num_threads() for p in psutil.process_iter(attrs=["pid"]) if p.is_running())
        except Exception:
            n_threads = 0
        self.totals_vars["Threads"].set(f"{n_threads:,}")
        self.totals_vars["Processes"].set(f"{len(psutil.pids()):,}")
        self.totals_vars["Handles"].set("(N/A)")

        commit_k = (vm.total - vm.available + sm.used) // 1024
        limit_k = (vm.total + sm.total) // 1024
        self._peak_commit_kb = max(self._peak_commit_kb, commit_k)
        self.commit_vars["Total"].set(f"{commit_k:,}")
        self.commit_vars["Limit"].set(f"{limit_k:,}")
        self.commit_vars["Peak"].set(f"{self._peak_commit_kb:,}")

        self.phys_vars["Total"].set(f"{vm.total // 1024:,}")
        self.phys_vars["Available"].set(f"{vm.available // 1024:,}")
        cached = getattr(vm, "cached", 0) // 1024
        self.phys_vars["System Cache"].set(f"{cached:,}" if cached else "(N/A)")

        # Kernel memory only meaningful on Win32. Otherwise stub.
        self.kern_vars["Total"].set("(N/A)")
        self.kern_vars["Paged"].set("(N/A)")
        self.kern_vars["Nonpaged"].set("(N/A)")


# ============================================================
# Main window.
# ============================================================
class TaskManager(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Windows Task Manager")
        self.geometry("700x680")
        self.minsize(540, 480)

        # Force a more retro-feeling default font where possible.
        try:
            tkfont.nametofont("TkDefaultFont").configure(family="Tahoma", size=8)
        except tk.TclError:
            pass

        # Menu bar (skeletal, classic layout).
        menubar = tk.Menu(self)
        for label in ("File", "Options", "View", "Windows", "Help"):
            m = tk.Menu(menubar, tearoff=0)
            if label == "File":
                m.add_command(label="New Task (Run...)", command=lambda: self.apps_tab._new_task())
                m.add_separator()
                m.add_command(label="Exit Task Manager", command=self.destroy)
            elif label == "Options":
                m.add_command(label="Always On Top", command=self._toggle_topmost)
            elif label == "View":
                m.add_command(label="Refresh Now", command=self._refresh_now)
                m.add_separator()
                speed_menu = tk.Menu(m, tearoff=0)
                self._speed_var = tk.StringVar(value="Normal")
                for name in ("High", "Normal", "Low", "Paused"):
                    speed_menu.add_radiobutton(
                        label=name,
                        value=name,
                        variable=self._speed_var,
                        command=self._on_speed_change,
                    )
                m.add_cascade(label="Update Speed", menu=speed_menu)
            elif label == "Help":
                m.add_command(label="About Task Manager", command=self._about)
            else:
                m.add_command(label="(none)")
            menubar.add_cascade(label=label, menu=m)
        self.config(menu=menubar)

        nb = ttk.Notebook(self)
        nb.pack(expand=True, fill="both", padx=4, pady=4)
        self.apps_tab = ApplicationsTab(nb)
        self.proc_tab = ProcessesTab(nb)
        self.perf_tab = PerformanceTab(nb)
        nb.add(self.apps_tab, text="Applications")
        nb.add(self.proc_tab, text="Processes")
        nb.add(self.perf_tab, text="Performance")

        # Status bar.
        self._status_proc = tk.StringVar(value="Processes: -")
        self._status_cpu = tk.StringVar(value="CPU Usage: -")
        self._status_mem = tk.StringVar(value="Commit Charge: -")
        status = ttk.Frame(self, relief="sunken", padding=(4, 2))
        status.pack(fill="x", side="bottom")
        ttk.Label(status, textvariable=self._status_proc, width=20).pack(side="left")
        ttk.Label(status, textvariable=self._status_cpu, width=20).pack(side="left")
        ttk.Label(status, textvariable=self._status_mem, width=40).pack(side="left")

        # Prime psutil's CPU percent so first reading is meaningful.
        psutil.cpu_percent(interval=None)
        for p in psutil.process_iter():
            try:
                p.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        self._refresh_ms = DEFAULT_REFRESH_MS
        self._scheduled_after: Optional[str] = None
        self._schedule_next()

    def _schedule_next(self) -> None:
        if self._refresh_ms is None:
            self._scheduled_after = None
            return
        self._scheduled_after = self.after(self._refresh_ms, self._tick)

    def _tick(self) -> None:
        self.apps_tab.refresh()
        self.proc_tab.refresh()
        self.perf_tab.refresh()
        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()
        self._status_proc.set(f"Processes: {len(psutil.pids())}")
        self._status_cpu.set(f"CPU Usage: {psutil.cpu_percent(interval=None):.0f}%")
        commit_k = (vm.total - vm.available + sm.used) // 1024
        limit_k = (vm.total + sm.total) // 1024
        self._status_mem.set(f"Commit Charge: {commit_k // 1024:,}M / {limit_k // 1024:,}M")
        self._schedule_next()

    def _on_speed_change(self) -> None:
        self._refresh_ms = SPEED_PRESETS[self._speed_var.get()]
        if self._scheduled_after is not None:
            self.after_cancel(self._scheduled_after)
            self._scheduled_after = None
        if self._refresh_ms is not None:
            self._schedule_next()

    def _refresh_now(self) -> None:
        self._tick()

    def _toggle_topmost(self) -> None:
        self.attributes("-topmost", not self.attributes("-topmost"))

    def _about(self) -> None:
        messagebox.showinfo(
            "About Task Manager",
            "Classic Task Manager (NT/2000/XP-style)\n"
            "Reimplemented in Python + tkinter + psutil\n\n"
            "Tabs: Applications, Processes, Performance.\n"
            "Refresh: 1 Hz. End Process / End Task supported.",
            parent=self,
        )


def main() -> int:
    app = TaskManager()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
