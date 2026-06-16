"""
poly_mountain — the polylinear-recursive-mountain runtime packet.

GeoSeal's per-goal routing unit (Night Synthesis 2026-05-01, sections 6 & 11):
many lanes climb the same goal from different faces, exchange compressed state at
recursive checkpoints, and act ONLY through a destructive-safety apply gate. Z3
proves the route is satisfiable BEFORE any lane runs. Training records are the
exhaust of real routes — not the goal.

This assembles existing surfaces rather than inventing new ones:
  * context views + octree   -> coding_spine.lightning_indexer.select_sparse_candidates
  * six semantic tongue views -> scbe.tongue_roles  (KO/DR/AV/RU/CA/UM)
  * destructive apply gate     -> scbe.blocks       (drive/home/system scope refused)
  * route satisfiability       -> z3                (no two lanes write one file; bounded budgets)

Systems spine (section 6): a failed checkpoint becomes a correction signal, the
prior state is retained as a durable anchor (the heavily-compressed view that
survives compaction), and the lane re-climbs. Failure is metabolized into structure.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from python.scbe.tongue_roles import TONGUE_ROLE, TONGUES
except ModuleNotFoundError:  # pragma: no cover - direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from python.scbe.tongue_roles import TONGUE_ROLE, TONGUES

# How each tongue reads the same goal — the six semantic operating views.
_TONGUE_LENS = {
    "KO": "intent / control flow: the ordered steps and routing to reach the goal",
    "AV": "input/output: the files, tools, and surfaces the goal reads and writes",
    "RU": "scope/context: the boundaries, packages, and naming scope in play",
    "CA": "math/logic: the exact, deterministic facts/opcodes the goal depends on",
    "UM": "security: the invariants, permissions, and safety constraints to preserve",
    "DR": "transforms: the data-shape changes and structure the goal produces",
}

# Goal keyword -> DH sector (section 5). A goal usually touches several.
_SECTOR_HINTS = {
    "coding": ("code", "fix", "implement", "refactor", "function", "bug", "compile", "test"),
    "governance": ("policy", "gate", "govern", "approve", "route", "decision"),
    "retrieval": ("find", "search", "retrieve", "look up", "where", "context"),
    "verification": ("verify", "prove", "check", "validate", "assert", "test"),
    "safety": ("delete", "remove", "destroy", "secret", "credential", "secure", "wipe"),
    "user_output": ("explain", "summarize", "report", "draft", "write", "document"),
    "tool_execution": ("run", "exec", "deploy", "install", "build", "command"),
    "memory": ("remember", "recall", "checkpoint", "history", "log"),
    "training_value": ("train", "dataset", "sft", "adapter", "record", "example"),
}

# Which HYDRA lane owns which sector, and the file each lane declares it writes
# (declared up front so Z3 can prove no two lanes collide on one file).
_LANE_FOR_SECTOR = {
    "coding": ("Builder", "impl"),
    "tool_execution": ("Builder", "impl"),
    "retrieval": ("Researcher", "research-notes"),
    "training_value": ("Researcher", "research-notes"),
    "verification": ("Verifier", "tests"),
    "safety": ("Verifier", "tests"),
    "governance": ("Navigator", "route-plan"),
    "user_output": ("Navigator", "route-plan"),
    "memory": ("Memory", "checkpoint-log"),
}


def _tongue_views(goal: str) -> Dict[str, Dict[str, str]]:
    """Project the goal through all six Sacred-Tongue roles."""
    return {
        t: {"role": TONGUE_ROLE[t]["role"], "lens": f"{_TONGUE_LENS[t]} — for: {goal}"}
        for t in TONGUES
    }


def _dh_sectors(goal: str) -> List[str]:
    """Label which DH sectors the goal involves (keyword heuristic)."""
    low = goal.lower()
    hits = [sec for sec, words in _SECTOR_HINTS.items() if any(w in low for w in words)]
    return hits or ["coding"]  # default: treat an unlabelled goal as a coding task


def _assign_lanes(sectors: List[str]) -> List[Dict[str, Any]]:
    """Assign HYDRA lanes for the involved sectors, each with a distinct write target."""
    lanes: Dict[str, Dict[str, Any]] = {}
    for sec in sectors:
        role, target = _LANE_FOR_SECTOR.get(sec, ("Builder", "impl"))
        lane = lanes.setdefault(role, {
            "name": role, "role": role, "sectors": [], "writes": target,
            "token_budget": 20000, "tool_budget": 4,
        })
        lane["sectors"].append(sec)
    # Memory lane always present — it owns the recursive checkpoint anchor.
    lanes.setdefault("Memory", {
        "name": "Memory", "role": "Memory", "sectors": ["memory"], "writes": "checkpoint-log",
        "token_budget": 8000, "tool_budget": 1,
    })
    return list(lanes.values())


def _checkpoint_policy() -> Dict[str, Any]:
    """Recursive checkpoint + failure-metabolizing policy (sections 6 & 11)."""
    return {
        "every_segments": 1,
        "on_segment": "summarize lane state into the heavily_compressed anchor",
        "on_failure": "convert error to a correction signal, retain prior anchor, re-climb",
        "anchor_survives_compaction": True,
        "max_reclimbs": 3,
    }


def _apply_gate(goal: str) -> Dict[str, Any]:
    """The destructive double-check any lane action must pass before it runs."""
    gate: Dict[str, Any] = {
        "engine": "scbe.blocks",
        "policy": "destructive ops require an explicit confirm reason; "
                  "drive/home/system-scope destruction is refused outright (no override)",
        "verified": False,
    }
    try:
        from python.scbe import blocks  # noqa: F401  (presence is the verification)
        gate["verified"] = True
    except Exception as exc:  # pragma: no cover - defensive
        gate["error"] = f"{type(exc).__name__}: {exc}"
    return gate


def _context_views(goal: str, candidates: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """The 3 attention views + octree retrieval, from the lightning indexer."""
    try:
        from src.coding_spine.lightning_indexer import select_sparse_candidates
    except Exception as exc:  # pragma: no cover - import guard
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    out = select_sparse_candidates(goal, candidates or [])
    channels = out.get("context_channels", {})
    return {
        "available": True,
        "dense_local": channels.get("dense_local") or channels.get("local") or [],
        "compressed_sparse": channels.get("compressed_sparse") or channels.get("sparse") or [],
        "heavily_compressed": channels.get("heavily_compressed") or channels.get("anchor") or [],
        "hybrid_attention_plan": out.get("hybrid_attention_plan", {}),
        "octree_retrieval": out.get("octree_retrieval", {}),
    }


def route_satisfiability(
    lanes: List[Dict[str, Any]], *, token_cap: int = 100_000, tool_cap: int = 20
) -> Dict[str, Any]:
    """Prove the route is runnable BEFORE any lane acts (section 4, section 9).

    Hard constraints, all checked by Z3:
      * no two lanes write the same file (write-collision is UNSAT),
      * total token budget across lanes is bounded,
      * total tool-call budget across lanes is bounded.
    """
    try:
        import z3
    except ImportError:  # pragma: no cover - z3 optional
        return {"engine": "z3", "available": False, "satisfiable": None,
                "note": "z3 not installed (pip install z3-solver)"}

    s = z3.Solver()
    writers = [ln for ln in lanes if ln.get("writes")]
    target_ids: Dict[str, int] = {}
    slots = []
    for ln in writers:
        target_ids.setdefault(ln["writes"], len(target_ids))
        slot = z3.Int(f"slot_{ln['name']}")
        s.add(slot == target_ids[ln["writes"]])
        slots.append(slot)
    if len(slots) >= 2:
        s.add(z3.Distinct(*slots))  # no two lanes write the same file

    tok = [z3.Int(f"tok_{ln['name']}") for ln in lanes]
    tool = [z3.Int(f"tool_{ln['name']}") for ln in lanes]
    for v, ln in zip(tok, lanes):
        s.add(v == int(ln.get("token_budget", 0)), v >= 0)
    for v, ln in zip(tool, lanes):
        s.add(v == int(ln.get("tool_budget", 0)), v >= 0)
    s.add(z3.Sum(tok) <= token_cap)
    s.add(z3.Sum(tool) <= tool_cap)

    res = s.check()
    out: Dict[str, Any] = {
        "engine": "z3", "available": True, "satisfiable": res == z3.sat,
        "token_cap": token_cap, "tool_cap": tool_cap,
        "total_token_budget": sum(int(ln.get("token_budget", 0)) for ln in lanes),
        "total_tool_budget": sum(int(ln.get("tool_budget", 0)) for ln in lanes),
    }
    if res != z3.sat:
        seen: Dict[str, str] = {}
        collisions = []
        for ln in writers:
            if ln["writes"] in seen.values():
                collisions.append(ln["writes"])
            seen[ln["name"]] = ln["writes"]
        out["violations"] = {
            "write_collisions": sorted(set(collisions)),
            "token_over": out["total_token_budget"] > token_cap,
            "tool_over": out["total_tool_budget"] > tool_cap,
        }
    return out


def build_packet(
    goal: str, *, candidates: Optional[List[Dict[str, Any]]] = None,
    token_cap: int = 100_000, tool_cap: int = 20,
) -> Dict[str, Any]:
    """Assemble the full polylinear-recursive-mountain packet for a goal."""
    sectors = _dh_sectors(goal)
    lanes = _assign_lanes(sectors)
    route = route_satisfiability(lanes, token_cap=token_cap, tool_cap=tool_cap)
    return {
        "schema_version": "scbe-poly-mountain-v1",
        "goal": goal,
        "context_views": _context_views(goal, candidates),
        "tongue_views": _tongue_views(goal),
        "dh_sector_labels": sectors,
        "assigned_lanes": lanes,
        "checkpoint_policy": _checkpoint_policy(),
        "route_satisfiability": route,
        "apply_gate": _apply_gate(goal),
        "may_proceed": bool(route.get("satisfiable")) and _apply_gate(goal)["verified"],
    }


def _demo() -> None:
    import json
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    pkt = build_packet("fix the failing GeoSeal route test and verify it")
    print("poly-mountain packet (abridged):")
    print(f"  goal            : {pkt['goal']}")
    print(f"  dh sectors      : {pkt['dh_sector_labels']}")
    print(f"  lanes           : {[ln['name'] + '->' + ln['writes'] for ln in pkt['assigned_lanes']]}")
    print(f"  route satisfiable: {pkt['route_satisfiability']['satisfiable']} "
          f"(z3, {pkt['route_satisfiability']['total_token_budget']} tok / "
          f"{pkt['route_satisfiability']['total_tool_budget']} tools)")
    print(f"  apply gate      : {pkt['apply_gate']['engine']} verified={pkt['apply_gate']['verified']}")
    print(f"  may proceed     : {pkt['may_proceed']}")
    print(f"  tongue views    : {list(pkt['tongue_views'].keys())}")
    print("\nfull packet keys:", list(pkt.keys()))
    print(json.dumps(pkt["route_satisfiability"], indent=2))


if __name__ == "__main__":
    _demo()
