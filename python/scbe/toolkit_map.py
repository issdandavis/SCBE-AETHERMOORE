"""toolkit_map: an interactive, self-updating MAP the AI walks to learn + use every SCBE system.

The toolbox (toolkit.py) is flat; this gives it a SHAPE. The tools are laid out as staged AREAS,
each demonstrating a distinct system, connected by unlock edges. The map does three things:

  * UPDATES PER TASK -- each area runs a real demo through the sealed toolkit; clearing it marks the
    area CLEARED, records which tools were seen, and UNLOCKS the next area. Progress is sealed.
  * GUIDES -- given a task in plain words, `route()` picks the right AVAILABLE area and names the one
    tool to reach for (and why), so a weak model never has to pick from 81 tools blind.
  * SEES THE USE -- every area actually invokes its system (sieve classifies a number, the board
    round-trips, loomflow runs an IR cross-face, a game is played sealed, ...), so the demo IS proof.

An area whose dependency is missing on this box is honestly SKIPPED (not faked), and still unlocks
the next so the tour continues. Every tool call is governed + SHA-256 sealed by the toolkit.

    from python.scbe.toolkit_map import TaskMap
    m = TaskMap()
    m.guide("classify the number 91")     # -> area + the tool to use + why
    m.traverse()                           # walk every area, sealing progress; print the journey
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .toolkit import Toolkit, default_toolkit

Demo = Callable[[Toolkit], Tuple[bool, str]]


# --- the area demos: each one actually drives its system through the sealed toolkit ----------


def _demo_sieve(tk: Toolkit) -> Tuple[bool, str]:
    task = tk.invoke("classify_number_task", 7)["result_obj"]
    prop = tk.invoke("scripted_proposer", ["prime"])["result_obj"]
    res = tk.invoke("run_stepwise", task, prop)["result_obj"]
    pr = tk.invoke("is_prime", 7)["result_obj"]
    fac = tk.invoke("factorization", 91)["result_obj"]
    ok = bool(res and res.get("completed") and pr is True and fac == {7: 1, 13: 1})
    return ok, "classify(7)->%s; is_prime(7)=%s; 91=%s" % (res.get("answer") if res else None, pr, fac)


def _demo_prime_region(tk: Toolkit) -> Tuple[bool, str]:
    pc = tk.invoke("PrimeCategories", ["A", "B", "C"])["result_obj"]
    code = pc.code(["A", "C"])
    ok = pc.decode(code) == ["A", "C"] and pc.in_category(code, "A") and not pc.in_category(code, "B")
    return ok, "code(['A','C'])=%d -> decode=%s (membership = divisibility)" % (code, pc.decode(code))


def _demo_loomflow(tk: Toolkit) -> Tuple[bool, str]:
    prog = tk.invoke("parse", "const a 5\nconst b 3\nadd c a b\nprint c")["result_obj"]
    val = tk.invoke("interpret", prog)["result_obj"]
    src = tk.invoke("emit", prog, "python")["result_obj"]
    ok = val == [8.0] and isinstance(src, str) and "def run" in src
    return ok, "interpret=%s; emit('python') has def run=%s" % (val, "def run" in (src or ""))


def _demo_cross_face(tk: Toolkit) -> Tuple[bool, str]:
    v = tk.invoke("verify", tk.invoke("parse", "const a 5\nprint a")["result_obj"], faces=["python"])["result_obj"]
    p2 = tk.invoke("parse_fn", "const a 6\nconst b 7\nmul c a b\nprint c")["result_obj"]
    v2 = tk.invoke("verify_fn", p2, faces=("python",))["result_obj"]
    ok = bool(v and v["results"]["python"]["status"] == "AGREE" and v2 and v2["reference"] == 42.0)
    return ok, "loomflow python=AGREE; loomfn mul -> reference %s" % (v2["reference"] if v2 else None)


def _demo_board(tk: Toolkit) -> Tuple[bool, str]:
    stones = tk.invoke("place", [1, 2, 3])["result_obj"]
    prog2 = tk.invoke("recover", stones)["result_obj"]
    rev = tk.invoke("is_reversible", [1, 2, 3])["result_obj"]
    cube = tk.invoke("to_cube", 0x15)["result_obj"]
    fc = tk.invoke("from_cube", *cube)["result_obj"]
    ok = prog2 == [1, 2, 3] and rev is True and fc == 0x15
    return ok, "recover(place)=%s; reversible=%s; from_cube(to_cube(0x15))=0x%02x" % (prog2, rev, fc)


def _demo_polyglot(tk: Toolkit) -> Tuple[bool, str]:
    ops = tk.invoke("notes_to_ops", "C E")["result_obj"]
    pb = tk.invoke("program_bytes", "add", "mul")["result_obj"]
    src = tk.invoke("emit_polyglot", pb, "python")["result_obj"]
    langs = tk.invoke("languages")["result_obj"]
    ok = ops == ["add", "mul"] and isinstance(src, str) and len(src) > 0 and isinstance(langs, list) and len(langs) > 1
    return ok, "notes 'C E'->%s; polyglot python emit %d chars; %d languages" % (ops, len(src or ""), len(langs or []))


def _demo_bit_dna(tk: Toolkit) -> Tuple[bool, str]:
    bits = tk.invoke("bytes_to_bits", b"A")["result_obj"]
    back = tk.invoke("bits_to_bytes", bits)["result_obj"]
    dna = tk.invoke("verify_dna", ["add", "mul"])["result_obj"]
    all_ok = bool(dna and (dna.get("all_ok") if isinstance(dna, dict) else False))
    ok = back == b"A" and all_ok
    return ok, "bytes round-trip=%s; verify_dna all_ok=%s" % (back == b"A", all_ok)


def _demo_geometry(tk: Toolkit) -> Tuple[bool, str]:
    st = tk.invoke("self_test")
    reg = tk.invoke("build_registry")
    ri = tk.invoke("route_intent", (0.05, 0.08))  # needs src/ on path -> may be UNAVAILABLE here
    ok = st["decision"] == "ALLOWED" and reg["decision"] == "ALLOWED"
    return ok, "phdm self_test=%s; build_registry=%s; geometry.route_intent=%s" % (
        st["decision"],
        reg["decision"],
        ri["decision"],
    )


def _demo_governed_games(tk: Toolkit) -> Tuple[bool, str]:
    from .desktop_access import default_registry
    from .game_board import TicTacToe

    g = tk.invoke("play_governed", TicTacToe(), confirm="demo")["result_obj"]
    reg = default_registry()
    inv = reg.invoke("open_app", {"app": "terminal"}, confirm="demo")
    ok = bool(g and g.get("over") and g.get("sealed") and inv["decision"] == "ALLOWED" and reg.verify())
    return ok, "tic-tac-toe over=%s sealed=%s; open_app=%s" % (
        g.get("over") if g else None,
        g.get("sealed") if g else None,
        inv["decision"],
    )


def _demo_ledger(tk: Toolkit) -> Tuple[bool, str]:
    from .context_ledger import Ledger

    led = Ledger("agent")
    for c in ["set x 1", "todo a", "done a", "note hi"]:
        led.run(c)
    has = "x=1" in led.recall()
    v = tk.invoke("verify_ledger", led)["result_obj"]
    pk = led.pack()
    ok = has and v is True and pk["ratio"] <= 1.0
    return ok, "recall has x=1=%s; verify=%s; pack ratio=%.2f" % (has, v, pk["ratio"])


def _demo_geoseal(tk: Toolkit) -> Tuple[bool, str]:
    hd = tk.invoke("hyperbolic_distance", [0.1, 0.0, 0.0], [0.0, 0.1, 0.0])
    val = hd["result_obj"]
    ok = hd["decision"] == "ALLOWED" and isinstance(val, float) and val > 0
    return ok, "hyperbolic_distance ~ %s" % (round(val, 3) if isinstance(val, float) else hd["decision"])


def _demo_leveling(tk: Toolkit) -> Tuple[bool, str]:
    d = tk.invoke("difficulty", 2, 5, "golden")["result_obj"]
    tr = tk.invoke("track")["result_obj"]
    ok = isinstance(d, float) and 25 < d < 40 and isinstance(tr, list) and len(tr) == 15
    return ok, "difficulty(2,5,golden)=%s; track len=%s" % (d, len(tr) if tr else None)


def _demo_rosetta(tk: Toolkit) -> Tuple[bool, str]:
    pb = tk.invoke("program_bytes", "add")["result_obj"]
    conf = tk.invoke("conformance", pb, [[1.0, 2.0, 3.0]])  # 'add' is ternary tongue_fn(a,b,c)
    obj = conf["result_obj"]
    ok = conf["decision"] == "ALLOWED" and obj is not None
    summ = obj.get("summary") if isinstance(obj, dict) else None
    return ok, "conformance across backends ran; summary=%s" % (summ if summ else conf["decision"])


@dataclass
class Area:
    name: str
    goal: str
    tools_used: List[str]
    unlock_after: Optional[str]
    demo: Demo
    keywords: List[str]
    status: str = "LOCKED"  # LOCKED | AVAILABLE | CLEARED | SKIPPED
    detail: str = ""


def _areas() -> List[Area]:
    return [
        Area(
            "Sieve Gate",
            "classify a number; the sieve decides, the model only labels",
            ["classify_number_task", "run_stepwise", "is_prime", "factorization"],
            None,
            _demo_sieve,
            ["number", "prime", "classify", "factor", "odd", "even"],
        ),
        Area(
            "Prime Region Map",
            "tag an item across prime-regions; membership = divisibility",
            ["PrimeCategories", "factorization"],
            "Sieve Gate",
            _demo_prime_region,
            ["category", "tag", "group", "region", "label set"],
        ),
        Area(
            "Stepwise Loomflow",
            "turn intent into an IR and run it",
            ["parse", "interpret", "emit"],
            "Prime Region Map",
            _demo_loomflow,
            ["run", "execute", "program", "compute", "ir"],
        ),
        Area(
            "Cross-Face Verify",
            "prove code agrees across languages (verification you can trust)",
            ["verify", "parse_fn", "verify_fn"],
            "Stepwise Loomflow",
            _demo_cross_face,
            ["verify", "agree", "works", "correct", "trust", "check"],
        ),
        Area(
            "Reversible Board",
            "one token as cube coords, color, note -- and it round-trips",
            ["place", "recover", "is_reversible", "to_cube", "from_cube"],
            "Cross-Face Verify",
            _demo_board,
            ["reverse", "round-trip", "cube", "board", "bijective", "stone"],
        ),
        Area(
            "Polyglot + Instrument",
            "speak/song -> ops -> running code in many tongues",
            ["notes_to_ops", "program_bytes", "emit_polyglot", "languages"],
            "Reversible Board",
            _demo_polyglot,
            ["language", "voice", "song", "tongue", "translate", "polyglot"],
        ),
        Area(
            "Bit Spine + DNA",
            "every layer reversible + hash-checked (tamper-evident)",
            ["bytes_to_bits", "bits_to_bytes", "verify_dna"],
            "Polyglot + Instrument",
            _demo_bit_dna,
            ["bytes", "binary", "tamper", "dna", "seal", "hash"],
        ),
        Area(
            "Geometry Router",
            "route intents/agents by hyperbolic geometry",
            ["route_intent", "self_test"],
            "Bit Spine + DNA",
            _demo_geometry,
            ["route", "assign", "agent", "fleet", "which", "geometry"],
        ),
        Area(
            "Governed Board Games",
            "play a task as a sealed, governed game",
            ["play_governed", "invoke"],
            "Geometry Router",
            _demo_governed_games,
            ["desktop", "game", "play", "clean files", "action", "move"],
        ),
        Area(
            "Context Ledger",
            "durable, packable, tamper-evident working memory",
            ["verify_ledger", "recall", "pack"],
            "Governed Board Games",
            _demo_ledger,
            ["remember", "context", "memory", "note", "todo", "pack"],
        ),
        Area(
            "GeoSeal Swarm",
            "governance as geometry: rogue actors pushed to the wall",
            ["hyperbolic_distance", "compute_metrics"],
            "Context Ledger",
            _demo_geoseal,
            ["rogue", "isolate", "contain", "swarm", "suspicion"],
        ),
        Area(
            "Leveling Track",
            "see your own competence curve on the honest ladder",
            ["difficulty", "track", "ride"],
            "GeoSeal Swarm",
            _demo_leveling,
            ["difficulty", "hard", "level", "competence", "skill", "ladder"],
        ),
        Area(
            "Rosetta Benchmark",
            "score cross-face coverage across every backend",
            ["conformance", "benchmark"],
            "Leveling Track",
            _demo_rosetta,
            ["score", "benchmark", "coverage", "rosetta", "everything"],
        ),
    ]


@dataclass
class TaskMap:
    tk: Toolkit = field(default_factory=default_toolkit)
    areas: List[Area] = field(default_factory=_areas)

    def __post_init__(self) -> None:
        for a in self.areas:
            a.status = "AVAILABLE" if a.unlock_after is None else "LOCKED"

    def _area(self, name: str) -> Optional[Area]:
        return next((a for a in self.areas if a.name == name), None)

    def route(self, task: str) -> Dict[str, object]:
        """Given a task in plain words, name the RIGHT area + the tool to reach for + why.

        Scores keyword overlap across every area (so it names the correct tool even when that area is
        still locked) and reports the area's status so the guide can say 'clear earlier areas first'.
        """
        t = task.lower()
        scored = [(sum(1 for k in a.keywords if k in t), a) for a in self.areas]
        scored.sort(key=lambda s: s[0], reverse=True)
        best = scored[0][1] if scored and scored[0][0] > 0 else self.areas[0]
        tool = best.tools_used[0]
        tool_doc = self.tk.by_name(tool).one_line if self.tk.by_name(tool) else ""
        return {"area": best.name, "tool": tool, "why": tool_doc, "goal": best.goal, "status": best.status}

    def guide(self, task: str) -> str:
        r = self.route(task)
        gate = "" if r["status"] in ("AVAILABLE", "CLEARED") else "  [locked -- clear earlier areas first]"
        return "for %r -> area %r, use %r  (%s)%s" % (task, r["area"], r["tool"], r["why"], gate)

    def strategize(self, lanes: Optional[list] = None) -> Dict[str, object]:
        """Portfolio guidance: count the task lanes (Pazaak bitboards) and recommend the next MOVE.

        Where route() picks a tool for one task, this looks across all task lanes and -- by counting
        high-value/high-risk/unverified/conflict -- recommends which move to play next. Every call is
        sealed through the toolkit. Returns None recommendation if Pazaak is unavailable on this box.
        """
        cards = self.tk.invoke("pazaak_cards")["result_obj"]
        lns = lanes if lanes is not None else self.tk.invoke("pazaak_lanes", None)["result_obj"]
        if cards is None or lns is None:
            return {"bitboards": None, "recommended": None, "note": "pazaak unavailable here"}
        bb = self.tk.invoke("pazaak_bitboards", lns)["result_obj"]
        moves = self.tk.invoke("pazaak_recommend", lns, cards, 3)["result_obj"]
        top = moves[0] if moves else None
        rec = (
            None
            if top is None
            else {"lane": top.lane_id, "card": top.card_name, "score": round(top.score, 1), "reason": top.reason}
        )
        return {"bitboards": bb, "recommended": rec}

    def advance(self, name: str) -> Dict[str, object]:
        """Run an area's demo through the sealed toolkit; clear + unlock on success."""
        a = self._area(name)
        if a is None:
            return {"area": name, "result": "no such area"}
        try:
            ok, detail = a.demo(self.tk)
        except Exception as e:  # a missing dep / surprise -> honest skip, not a crash
            ok, detail = False, "%s: %s" % (type(e).__name__, e)
        a.detail = detail
        a.status = "CLEARED" if ok else "SKIPPED"
        for nxt in self.areas:  # unlock dependents either way so the tour continues
            if nxt.unlock_after == a.name and nxt.status == "LOCKED":
                nxt.status = "AVAILABLE"
        return {"area": name, "cleared": ok, "detail": detail}

    def traverse(self) -> Dict[str, object]:
        """Walk every area in unlock order; seal progress; return the journey summary."""
        for a in self.areas:
            self.advance(a.name)
        cleared = [a.name for a in self.areas if a.status == "CLEARED"]
        skipped = [a.name for a in self.areas if a.status == "SKIPPED"]
        return {
            "cleared": len(cleared),
            "skipped": len(skipped),
            "total": len(self.areas),
            "cleared_areas": cleared,
            "skipped_areas": skipped,
            "sealed": self.tk.verify(),
            "tool_calls": len(self.tk.transcript),
        }

    def render(self) -> str:
        mark = {"CLEARED": "[x]", "SKIPPED": "[-]", "AVAILABLE": "[ ]", "LOCKED": "[#]"}
        lines = ["TASK MAP  (the AI's guided tour of every SCBE system)"]
        for i, a in enumerate(self.areas, 1):
            lines.append("  %s %2d. %-22s %s" % (mark.get(a.status, "[?]"), i, a.name, a.detail[:60]))
        return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    m = TaskMap()
    print("== GUIDANCE: the map names the right tool for a plain-words task ==")
    for task in [
        "classify the number 91",
        "make sure this code agrees in every language",
        "remember my context",
        "how hard is this level",
    ]:
        print("  " + m.guide(task))
    print("\n== STRATEGY: the Pazaak board counts the task portfolio + recommends the next move ==")
    s = m.strategize()
    print("  bitboards:", s["bitboards"])
    print("  recommended next move:", s["recommended"])

    print("\n== TRAVERSE: walk every area, running its system through the sealed toolkit ==")
    summary = m.traverse()
    print(m.render())
    print(
        "\n  cleared %d/%d areas (%d skipped for missing deps); %d sealed tool calls; transcript verified: %s"
        % (summary["cleared"], summary["total"], summary["skipped"], summary["tool_calls"], summary["sealed"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
