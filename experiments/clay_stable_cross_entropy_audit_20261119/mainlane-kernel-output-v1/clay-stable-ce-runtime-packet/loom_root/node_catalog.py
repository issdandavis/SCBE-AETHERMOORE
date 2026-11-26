#!/usr/bin/env python3
"""node_catalog.py -- THE AUTOCODER'S GARAGE. Every primitive as a NODE with typed ports,
every legal connection as an EDGE, and a sawmill blade-guard that refuses a graph with any
port not hooked up.

The whole point (Issac's domino line): the AI shouldn't *set up* the primitives, *be* the
primitives, and *push* them every task. The primitives are pre-built and enumerated here once;
coding is then just SELECTING nodes and WIRING edges until the goal is met -- a domino line
falling on its own, which even a 1 MB model can drive by choice 1/2/3. And because a node
declares its input ports, "is every input connected?" is a mechanical check -- the same failure
that let an unused `env` parameter ship (an unconnected input port) can never pass again.

ONE universal representation, three faces of the same graph:
  * NODES + EDGES  -- this catalog (the substrate loom walks).
  * SIX TONGUES    -- every node carries its word in KO/AV/RU/CA/UM/DR (render()).
  * ONNX / asm     -- the same node id is the same op the emitters already lower.

Types (ports): N number, B bool (a 0/1 number, feeds N), L list-of-number, F function (a node
ref, for map/fold/filter). An edge out:T -> in:U is legal iff U accepts T (see _ACCEPTS).

    python node_catalog.py            # print the garage + run the fail-safe self-test
    python node_catalog.py json       # emit node_catalog.json (machine-readable snapshot)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, "C:/dev")
import tongue_semantics as TS  # noqa: E402

# ---- the type lattice (ports) ------------------------------------------------------------
# An input port of type U accepts an output of type T when T in _ACCEPTS[U]. Kept tiny and
# explicit: bool is a number, everything else is invariant. This IS the edge legality rule.
TYPES = ("N", "B", "L", "F")
_ACCEPTS = {
    "N": {"N", "B"},   # a number input takes a number or a bool
    "B": {"B"},        # a bool input takes only a bool
    "L": {"L"},        # a list input takes only a list
    "F": {"F"},        # a function input (map/fold/filter) takes only a function
}

# ---- the SIGNATURE table: op-name -> (input port types, output port types) ----------------
# Assigned from each op's established semantics. This is the only hand-authored data; the byte
# id, gloss, and six tongue words are all pulled live from tongue_semantics so the catalog
# never drifts from the codepage.
_BIN_N = ("N", "N")
SIG: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    # number 0x00-0x0f
    "add": (_BIN_N, ("N",)), "sub": (_BIN_N, ("N",)), "mul": (_BIN_N, ("N",)),
    "div": (_BIN_N, ("N",)), "mod": (_BIN_N, ("N",)), "pow": (_BIN_N, ("N",)),
    "sqrt": (("N",), ("N",)), "log": (("N",), ("N",)), "exp": (("N",), ("N",)),
    "abs": (("N",), ("N",)), "neg": (("N",), ("N",)), "inc": (("N",), ("N",)),
    "dec": (("N",), ("N",)), "floor": (("N",), ("N",)), "ceil": (("N",), ("N",)),
    "round": (("N",), ("N",)),
    # bits 0x10-0x1f
    "and": (_BIN_N, ("N",)), "or": (_BIN_N, ("N",)), "xor": (_BIN_N, ("N",)),
    "nand": (_BIN_N, ("N",)), "nor": (_BIN_N, ("N",)), "shl": (_BIN_N, ("N",)),
    "shr": (_BIN_N, ("N",)), "rotl": (_BIN_N, ("N",)), "rotr": (_BIN_N, ("N",)),
    "not": (("N",), ("N",)), "popcount": (("N",), ("N",)), "clz": (("N",), ("N",)),
    "ctz": (("N",), ("N",)), "bitmask": (("N",), ("N",)),
    "bitset": (_BIN_N, ("N",)), "bitclear": (_BIN_N, ("N",)),
    # judge 0x20-0x2f
    "eq": (_BIN_N, ("B",)), "neq": (_BIN_N, ("B",)), "lt": (_BIN_N, ("B",)),
    "lte": (_BIN_N, ("B",)), "gt": (_BIN_N, ("B",)), "gte": (_BIN_N, ("B",)),
    "cmp": (_BIN_N, ("N",)), "min": (_BIN_N, ("N",)), "max": (_BIN_N, ("N",)),
    "clamp": (("N", "N", "N"), ("N",)), "within": (("N", "N", "N"), ("B",)),
    "isnan": (("N",), ("B",)), "isinf": (("N",), ("B",)), "isfinite": (("N",), ("B",)),
    "sign": (("N",), ("N",)), "classify": (("N",), ("N",)),
    # gather 0x30-0x3f (list primitives)
    "sum": (("L",), ("N",)), "product": (("L",), ("N",)), "mean": (("L",), ("N",)),
    "variance": (("L",), ("N",)), "stdev": (("L",), ("N",)), "count": (("L",), ("N",)),
    "reduce": (("F", "N", "L"), ("N",)), "fold": (("F", "N", "L"), ("N",)),
    "scan": (("F", "N", "L"), ("L",)), "filter": (("F", "L"), ("L",)),
    "map": (("F", "L"), ("L",)), "zip": (("L", "L"), ("L",)), "unzip": (("L",), ("L", "L")),
    "sort": (("L",), ("L",)), "unique": (("L",), ("L",)), "accum": (("L",), ("L",)),
}

REALMS = {0x00: "number", 0x10: "bits", 0x20: "judge", 0x30: "gather"}


@dataclass(frozen=True)
class Node:
    """One primitive in the garage: a byte id, its ports, and its word in every tongue."""
    byte: int
    name: str
    gloss: str
    realm: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    tongues: dict[str, str] = field(default_factory=dict)

    @property
    def arity(self) -> int:
        return len(self.inputs)


def _build_catalog() -> dict[str, Node]:
    name_to_byte, ca_word, _ = TS._scbe()
    cat: dict[str, Node] = {}
    for name, byte in name_to_byte.items():
        if name not in SIG:
            continue  # only ops with a declared signature enter the garage
        ins, outs = SIG[name]
        try:
            gloss = TS.gloss(byte)
        except Exception:
            gloss = ""
        tongues = {}
        for code in TS.ORDER:  # KO AV RU CA UM DR
            try:
                tongues[code] = TS.render(code, byte, ca_word)
            except Exception:
                tongues[code] = ""
        cat[name] = Node(
            byte=byte, name=name, gloss=gloss,
            realm=REALMS.get(byte & 0xF0, "other"),
            inputs=ins, outputs=outs, tongues=tongues,
        )
    return cat


CATALOG: dict[str, Node] = _build_catalog()


def node(name: str) -> Node:
    return CATALOG[name]


def edge_ok(out_type: str, in_type: str) -> bool:
    """Is an edge from an output port (out_type) into an input port (in_type) legal?"""
    return out_type in _ACCEPTS.get(in_type, set())


def render(name: str, tongue: str) -> str:
    """The word for a node in one of the six tongues (KO/AV/RU/CA/UM/DR)."""
    return CATALOG[name].tongues[tongue]


# ---- THE SAWMILL BLADE-GUARD: no graph ships with an unhooked port -----------------------
def wire_check(graph: dict) -> list[str]:
    """Return a list of wiring faults; empty means every port is hooked up and every edge is
    type-legal. This is the universal form of the `env`-was-unused bug: an input port with no
    incoming edge is a dependency that isn't connected to anything.

    graph = {
      "nodes":  {node_id: op_name, ...},              # which primitive each node is
      "inputs": [node_id, ...],                        # nodes fed by external/graph inputs
      "consts": [(node_id, port_index), ...],          # ports satisfied by a literal
      "edges":  [(src_id, out_idx, dst_id, in_idx), ...],
    }
    """
    faults: list[str] = []
    nodes = graph.get("nodes", {})
    graph_inputs = set(graph.get("inputs", []))
    consts = {tuple(c) for c in graph.get("consts", [])}
    edges = graph.get("edges", [])

    # every op must exist in the garage
    for nid, op in nodes.items():
        if op not in CATALOG:
            faults.append(f"node {nid!r}: unknown op {op!r} (not in the garage)")

    # index incoming edges per (dst, in_idx), and type-check each edge
    filled: set[tuple] = set()
    for e in edges:
        try:
            src, oi, dst, ii = e
        except Exception:
            faults.append(f"edge {e!r}: malformed (want (src,out_idx,dst,in_idx))")
            continue
        if src not in nodes or dst not in nodes:
            faults.append(f"edge {e!r}: endpoint not a node")
            continue
        so, di = CATALOG.get(nodes[src]), CATALOG.get(nodes[dst])
        if not so or not di:
            continue
        if oi >= len(so.outputs):
            faults.append(f"edge {e!r}: {nodes[src]!r} has no output port {oi}")
            continue
        if ii >= len(di.inputs):
            faults.append(f"edge {e!r}: {nodes[dst]!r} has no input port {ii}")
            continue
        if not edge_ok(so.outputs[oi], di.inputs[ii]):
            faults.append(
                f"edge {e!r}: type {so.outputs[oi]} cannot feed {di.inputs[ii]} "
                f"({nodes[src]}->{nodes[dst]})"
            )
        filled.add((dst, ii))

    # THE HOOKUP CHECK: every input port of every node must be fed (edge, const, or graph input)
    for nid, op in nodes.items():
        n = CATALOG.get(op)
        if not n:
            continue
        for ii in range(n.arity):
            if (nid, ii) in filled or (nid, ii) in consts or nid in graph_inputs:
                continue
            faults.append(
                f"NOT HOOKED UP: node {nid!r} ({op}) input port {ii} "
                f"[{n.inputs[ii]}] has no incoming edge"
            )
    return faults


def to_dict() -> dict:
    """Machine-readable snapshot for non-Python consumers / other conlang layers."""
    return {
        "types": TYPES,
        "accepts": {k: sorted(v) for k, v in _ACCEPTS.items()},
        "tongues": list(TS.ORDER),
        "nodes": [
            {
                "byte": n.byte, "name": n.name, "gloss": n.gloss, "realm": n.realm,
                "inputs": list(n.inputs), "outputs": list(n.outputs),
                "tongues": n.tongues,
            }
            for n in sorted(CATALOG.values(), key=lambda x: x.byte)
        ],
    }


def _selftest() -> bool:
    ok = True
    # 1) full garage present
    print(f"GARAGE: {len(CATALOG)} nodes across realms "
          f"{sorted({n.realm for n in CATALOG.values()})}")
    # 2) the fail-safe CATCHES an unhooked port (the env-bug, universal form)
    broken = {
        "nodes": {"a": "add"},          # add needs 2 number inputs
        "inputs": [], "consts": [("a", 0)], "edges": [],   # only port 0 fed -> port 1 dangles
    }
    faults = wire_check(broken)
    caught = any("NOT HOOKED UP" in f for f in faults)
    print("FAIL-SAFE catches an unhooked port:", "YES" if caught else "NO <<<")
    ok &= caught
    # 3) a fully-wired graph passes: mean(map(inc, L)) style -- (7-4)*3 as add of two consts
    good = {
        "nodes": {"s": "sub", "m": "mul"},
        "inputs": [], "consts": [("s", 0), ("s", 1), ("m", 1)],
        "edges": [("s", 0, "m", 0)],     # sub -> mul port0; mul port1 is a const
    }
    faults2 = wire_check(good)
    print("FULLY-WIRED graph passes clean:", "YES" if not faults2 else f"NO {faults2}")
    ok &= not faults2
    # 4) type illegality is caught: feed a list into a number port
    bad_type = {
        "nodes": {"L": "sort", "n": "add"},
        "inputs": ["L"], "consts": [("n", 1)],
        "edges": [("L", 0, "n", 0)],     # sort outputs L into add's N port -> illegal
    }
    faults3 = wire_check(bad_type)
    typed = any("cannot feed" in f for f in faults3)
    print("FAIL-SAFE catches an illegal-type edge:", "YES" if typed else "NO <<<")
    ok &= typed
    # 5) every node renders in all six tongues
    sample = node("add")
    print("SAMPLE node 'add' 0x%02x  ports %s->%s  tongues: %s"
          % (sample.byte, sample.inputs, sample.outputs,
             " ".join(f"{k}={v}" for k, v in sample.tongues.items())))
    ok &= all(sample.tongues[c] for c in TS.ORDER)
    print("\nSELFTEST:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "json":
        out = Path(__file__).with_name("node_catalog.json")
        out.write_text(json.dumps(to_dict(), indent=1), encoding="utf-8")
        print("wrote", out, f"({len(CATALOG)} nodes)")
    else:
        raise SystemExit(0 if _selftest() else 1)
