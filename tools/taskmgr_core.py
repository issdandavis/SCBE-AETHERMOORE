"""Backend / headless API for the classic Task Manager.

The GUI in `tools/classic_taskmgr.py` is one consumer of this module;
scripts and other code can call the same functions to get the same
data without any tkinter dependency. Everything here is pure
psutil + stdlib so it imports cheaply and runs anywhere Python does.

API surface (intentionally small):

    list_processes(filter=None) -> List[ProcessSnapshot]
    list_agents()               -> List[AgentSnapshot]
    system_info()               -> SystemSnapshot
    scbe_state()                -> List[(label, value)]
    kill_process(pid, tree=False, dry_run=False) -> KillResult
    sample_cpu_mem_net(seconds=1.0) -> Sample

CLI:

    python -m tools.taskmgr_core procs       [--filter X] [--top N] [--json]
    python -m tools.taskmgr_core agents      [--json]
    python -m tools.taskmgr_core system      [--json]
    python -m tools.taskmgr_core scbe        [--json]
    python -m tools.taskmgr_core sample      [--seconds N] [--json]
    python -m tools.taskmgr_core kill PID    [--tree] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import List, Optional, Tuple

import psutil

# ============================================================
# Agent classification (shared with the AI Agents tab in the GUI).
# ============================================================
AGENT_NAME_HITS = {"ollama", "ollama.exe", "ollama-runner", "ollama-runner.exe"}
AGENT_CMDLINE_HITS: Tuple[str, ...] = (
    "claude-code",
    "claude_code",
    "claude.cli",
    "ollama",
    "scbe",
    "geoseal",
    "aetherbrowse",
    "aethermoore",
    "petri_governance_gate",
    "agent_bus",
    "swarm_browser",
    "antivirus_membrane",
    "n8n",
    "scbe_n8n_bridge",
)


def classify_agent(name: str, cmdline: List[str]) -> Optional[str]:
    """Tag the agent class for a process; None if not recognized."""
    nm = (name or "").lower()
    if nm in AGENT_NAME_HITS or nm.startswith("ollama"):
        return "Ollama"
    cl = " ".join(cmdline or []).lower()
    if "claude-code" in cl or "claude_code" in cl or "@anthropic" in cl:
        return "Claude Code"
    if "scbe" in cl and "petri" in cl:
        return "SCBE / Petri"
    if "scbe" in cl or "geoseal" in cl or "aethermoore" in cl or "aetherbrowse" in cl:
        return "SCBE Agent"
    if "agent_bus" in cl or "swarm_browser" in cl or "antivirus_membrane" in cl:
        return "SCBE Subsystem"
    if nm.startswith("n8n") or "scbe_n8n_bridge" in cl:
        return "n8n / Bridge"
    if any(h in cl for h in AGENT_CMDLINE_HITS):
        return "Agent (other)"
    return None


# ============================================================
# Snapshot dataclasses.
# ============================================================
@dataclass
class ProcessSnapshot:
    pid: int
    name: str
    user: str
    cpu_percent: float
    mem_rss_bytes: int
    cmdline: str = ""

    @property
    def mem_kb(self) -> int:
        return self.mem_rss_bytes // 1024


@dataclass
class AgentSnapshot(ProcessSnapshot):
    agent_class: str = ""
    open_files: List[str] = field(default_factory=list)


@dataclass
class SystemSnapshot:
    os: str
    machine: str
    processor: str
    python_version: str
    python_executable: str
    cpu_physical: int
    cpu_logical: int
    cpu_freq_mhz: Optional[float]
    cpu_freq_max_mhz: Optional[float]
    mem_total_bytes: int
    mem_available_bytes: int
    swap_total_bytes: int
    disks: List[dict] = field(default_factory=list)
    nics: List[dict] = field(default_factory=list)


@dataclass
class Sample:
    cpu_percent: float
    cpu_per_core: List[float]
    mem_percent: float
    mem_used_bytes: int
    net_bps_total: float
    net_recv_bytes: int
    net_sent_bytes: int


@dataclass
class KillResult:
    pid: int
    name: str
    requested_tree: bool
    dry_run: bool
    terminated_pids: List[int]
    failed_pids: List[Tuple[int, str]]
    skipped: bool = False
    error: Optional[str] = None


# ============================================================
# Public API.
# ============================================================
def list_processes(*, filter: str = "") -> List[ProcessSnapshot]:
    """Snapshot of all running processes. `filter` is a case-insensitive
    substring matched against name / pid / username."""
    out: List[ProcessSnapshot] = []
    flt = (filter or "").strip().lower()
    for p in psutil.process_iter(attrs=["pid", "name", "username", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            mem = info["memory_info"].rss if info["memory_info"] else 0
            row = ProcessSnapshot(
                pid=info["pid"],
                name=info["name"] or "?",
                user=(info["username"] or "").split("\\")[-1],
                cpu_percent=info["cpu_percent"] or 0.0,
                mem_rss_bytes=mem,
            )
            if flt and not (flt in row.name.lower() or flt in str(row.pid) or flt in row.user.lower()):
                continue
            out.append(row)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return out


def list_agents() -> List[AgentSnapshot]:
    """Filtered + tagged view of agent processes (Ollama / Claude / SCBE / etc.)
    with each agent's open-files list attached."""
    out: List[AgentSnapshot] = []
    for p in psutil.process_iter(attrs=["pid", "name", "username", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            cmd = p.cmdline()
            tag = classify_agent(info["name"] or "", cmd)
            if tag is None:
                continue
            mem = info["memory_info"].rss if info["memory_info"] else 0
            try:
                files = [f.path for f in p.open_files()]
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                files = []
            out.append(
                AgentSnapshot(
                    pid=info["pid"],
                    name=info["name"] or "?",
                    user=(info["username"] or "").split("\\")[-1],
                    cpu_percent=info["cpu_percent"] or 0.0,
                    mem_rss_bytes=mem,
                    cmdline=" ".join(cmd)[:240],
                    agent_class=tag,
                    open_files=files,
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    out.sort(key=lambda a: (a.agent_class, -a.cpu_percent))
    return out


def system_info() -> SystemSnapshot:
    """Architecture snapshot: OS, CPU, memory, disks, NICs."""
    import platform

    try:
        freq = psutil.cpu_freq()
        cur = freq.current if freq else None
        mx = freq.max if freq else None
    except Exception:
        cur = mx = None

    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()

    disks: List[dict] = []
    for part in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(part.mountpoint)
            disks.append(
                dict(
                    device=part.device,
                    mountpoint=part.mountpoint,
                    fstype=part.fstype,
                    used_bytes=u.used,
                    total_bytes=u.total,
                    percent=u.percent,
                )
            )
        except (PermissionError, OSError):
            continue

    nics: List[dict] = []
    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        for nic, addr_list in addrs.items():
            stat = stats.get(nic)
            if stat is None or not stat.isup:
                continue
            v4 = next((a.address for a in addr_list if a.family.name == "AF_INET"), None)
            nics.append(dict(name=nic, ipv4=v4, speed_mbps=stat.speed, mtu=stat.mtu))
    except Exception:
        pass

    return SystemSnapshot(
        os=f"{platform.system()} {platform.release()} ({platform.version()})",
        machine=platform.machine(),
        processor=platform.processor() or "",
        python_version=platform.python_version(),
        python_executable=sys.executable,
        cpu_physical=psutil.cpu_count(logical=False) or 0,
        cpu_logical=psutil.cpu_count(logical=True) or 0,
        cpu_freq_mhz=cur,
        cpu_freq_max_mhz=mx,
        mem_total_bytes=vm.total,
        mem_available_bytes=vm.available,
        swap_total_bytes=sm.total,
        disks=disks,
        nics=nics,
    )


def scbe_state() -> List[Tuple[str, str]]:
    """SCBE-specific rows: package version, git branch, ollama models.
    Returned as (label, value) pairs to keep the surface small."""
    import subprocess

    rows: List[Tuple[str, str]] = []
    pkg_version = "?"
    try:
        with open("package.json", encoding="utf-8") as fh:
            pkg = json.load(fh)
        pkg_version = pkg.get("version", "?")
    except Exception:
        pass
    rows.append(("scbe-aethermoore", f"v{pkg_version}"))

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        rows.append(("git branch", out.stdout.strip() or "(no git)"))
    except Exception:
        rows.append(("git branch", "(unavailable)"))

    try:
        out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=3, check=False)
        if out.returncode == 0:
            models = [ln.split()[0] for ln in out.stdout.splitlines()[1:] if ln.strip()]
            rows.append(("ollama models", ", ".join(models[:8]) or "(none)"))
        else:
            rows.append(("ollama models", "(ollama CLI unavailable)"))
    except Exception:
        rows.append(("ollama models", "(unavailable)"))

    return rows


def kill_process(pid: int, *, tree: bool = False, dry_run: bool = False) -> KillResult:
    """Terminate a process (and optionally its descendants).

    Returns a KillResult so callers can introspect what happened. Does
    not prompt; the GUI does its own confirmation before calling.
    """
    try:
        p = psutil.Process(pid)
        name = p.name()
    except psutil.NoSuchProcess as exc:
        return KillResult(
            pid=pid,
            name="",
            requested_tree=tree,
            dry_run=dry_run,
            terminated_pids=[],
            failed_pids=[],
            skipped=True,
            error=str(exc),
        )

    targets: List[psutil.Process] = []
    if tree:
        try:
            targets.extend(p.children(recursive=True))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    targets.append(p)

    terminated: List[int] = []
    failed: List[Tuple[int, str]] = []
    for t in targets:
        if dry_run:
            terminated.append(t.pid)
            continue
        try:
            t.terminate()
            terminated.append(t.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            failed.append((t.pid, str(exc)))

    return KillResult(
        pid=pid,
        name=name,
        requested_tree=tree,
        dry_run=dry_run,
        terminated_pids=terminated,
        failed_pids=failed,
    )


def sample_cpu_mem_net(*, seconds: float = 1.0) -> Sample:
    """One synchronous sample over `seconds`. Useful when the caller
    isn't running the GUI's persistent history sampler."""
    psutil.cpu_percent(interval=None)
    psutil.cpu_percent(interval=None, percpu=True)
    net0 = psutil.net_io_counters()
    t0 = time.monotonic()
    time.sleep(max(0.05, seconds))
    cpu = psutil.cpu_percent(interval=None)
    per_core = psutil.cpu_percent(interval=None, percpu=True)
    vm = psutil.virtual_memory()
    net1 = psutil.net_io_counters()
    dt = max(0.001, time.monotonic() - t0)
    delta = (net1.bytes_recv - net0.bytes_recv) + (net1.bytes_sent - net0.bytes_sent)
    return Sample(
        cpu_percent=cpu,
        cpu_per_core=list(per_core),
        mem_percent=vm.percent,
        mem_used_bytes=vm.total - vm.available,
        net_bps_total=delta / dt,
        net_recv_bytes=net1.bytes_recv,
        net_sent_bytes=net1.bytes_sent,
    )


# ============================================================
# CLI.
# ============================================================
def _print_table(headers: List[str], rows: List[List[str]]) -> None:
    widths = [len(h) for h in headers]
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(str(c)))
    fmt = "  ".join("{{:<{}}}".format(w) for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in widths]))
    for r in rows:
        print(fmt.format(*[str(c) for c in r]))


def _cmd_procs(args: argparse.Namespace) -> int:
    rows = list_processes(filter=args.filter)
    rows.sort(key=lambda p: -p.cpu_percent)
    if args.top:
        rows = rows[: args.top]
    if args.json:
        print(json.dumps([asdict(r) for r in rows], indent=2))
        return 0
    _print_table(
        ["PID", "NAME", "USER", "CPU%", "MEM_KB"],
        [[r.pid, r.name, r.user, f"{r.cpu_percent:.1f}", f"{r.mem_kb:,}"] for r in rows],
    )
    return 0


def _cmd_agents(args: argparse.Namespace) -> int:
    rows = list_agents()
    if args.json:
        print(json.dumps([asdict(r) for r in rows], indent=2))
        return 0
    _print_table(
        ["AGENT", "PID", "NAME", "CPU%", "MEM_KB", "CMDLINE"],
        [[r.agent_class, r.pid, r.name, f"{r.cpu_percent:.1f}", f"{r.mem_kb:,}", r.cmdline[:80]] for r in rows],
    )
    print(f"\n{len(rows)} agent processes")
    return 0


def _cmd_system(args: argparse.Namespace) -> int:
    s = system_info()
    if args.json:
        print(json.dumps(asdict(s), indent=2))
        return 0
    print(f"OS:         {s.os}")
    print(f"Machine:    {s.machine}")
    print(f"Processor:  {s.processor}")
    print(f"Python:     {s.python_version} ({s.python_executable})")
    cur = f"{s.cpu_freq_mhz:.0f} MHz" if s.cpu_freq_mhz else "?"
    mx = f"{s.cpu_freq_max_mhz:.0f} MHz" if s.cpu_freq_max_mhz else "?"
    print(f"CPU:        phys={s.cpu_physical} log={s.cpu_logical} freq={cur} max={mx}")
    print(
        f"Memory:     total={s.mem_total_bytes // (1024**3)} GB  "
        f"avail={s.mem_available_bytes // (1024**3)} GB  "
        f"swap={s.swap_total_bytes // (1024**3)} GB"
    )
    for d in s.disks:
        print(
            f"Disk:       {d['device']:<10} {d['fstype']:<6} "
            f"{d['used_bytes'] // (1024**3):>5}/{d['total_bytes'] // (1024**3):>5} GB "
            f"({d['percent']:.0f}%) @ {d['mountpoint']}"
        )
    for n in s.nics:
        print(f"NIC:        {n['name']:<20} {n['ipv4'] or '-':<16} {n['speed_mbps']} Mb/s mtu={n['mtu']}")
    return 0


def _cmd_scbe(args: argparse.Namespace) -> int:
    rows = scbe_state()
    if args.json:
        print(json.dumps(dict(rows), indent=2))
        return 0
    for k, v in rows:
        print(f"{k:<20}  {v}")
    return 0


def _cmd_sample(args: argparse.Namespace) -> int:
    s = sample_cpu_mem_net(seconds=args.seconds)
    if args.json:
        print(json.dumps(asdict(s), indent=2))
        return 0
    print(f"CPU:        {s.cpu_percent:5.1f} %  (per-core: {[round(x, 1) for x in s.cpu_per_core]})")
    print(f"Memory:     {s.mem_percent:5.1f} %   used={s.mem_used_bytes // (1024**3)} GB")
    if s.net_bps_total >= 1_000_000:
        print(f"Network:    {s.net_bps_total / 1_000_000:5.2f} MB/s")
    else:
        print(f"Network:    {s.net_bps_total / 1024:5.1f} KB/s")
    return 0


def _cmd_kill(args: argparse.Namespace) -> int:
    res = kill_process(args.pid, tree=args.tree, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(asdict(res), indent=2))
        return 0 if not res.failed_pids and not res.skipped else 1
    if res.skipped:
        print(f"PID {res.pid}: {res.error}")
        return 1
    label = "DRY-RUN" if res.dry_run else "TERMINATED"
    print(f"{label}: {res.name} (PID {res.pid}){' + tree' if res.requested_tree else ''}")
    print(f"  PIDs: {res.terminated_pids}")
    if res.failed_pids:
        print("  Failed:")
        for pid, err in res.failed_pids:
            print(f"    {pid}: {err}")
        return 1
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="taskmgr_core", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_procs = sub.add_parser("procs", help="list all processes")
    p_procs.add_argument("--filter", default="")
    p_procs.add_argument("--top", type=int, default=0, help="show top N by CPU pct")
    p_procs.add_argument("--json", action="store_true")
    p_procs.set_defaults(func=_cmd_procs)

    p_agents = sub.add_parser("agents", help="list AI agent processes")
    p_agents.add_argument("--json", action="store_true")
    p_agents.set_defaults(func=_cmd_agents)

    p_system = sub.add_parser("system", help="architecture readout")
    p_system.add_argument("--json", action="store_true")
    p_system.set_defaults(func=_cmd_system)

    p_scbe = sub.add_parser("scbe", help="SCBE component state")
    p_scbe.add_argument("--json", action="store_true")
    p_scbe.set_defaults(func=_cmd_scbe)

    p_sample = sub.add_parser("sample", help="one CPU/mem/net sample")
    p_sample.add_argument("--seconds", type=float, default=1.0)
    p_sample.add_argument("--json", action="store_true")
    p_sample.set_defaults(func=_cmd_sample)

    p_kill = sub.add_parser("kill", help="terminate a PID (optionally with its tree)")
    p_kill.add_argument("pid", type=int)
    p_kill.add_argument("--tree", action="store_true")
    p_kill.add_argument("--dry-run", action="store_true")
    p_kill.add_argument("--json", action="store_true")
    p_kill.set_defaults(func=_cmd_kill)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
