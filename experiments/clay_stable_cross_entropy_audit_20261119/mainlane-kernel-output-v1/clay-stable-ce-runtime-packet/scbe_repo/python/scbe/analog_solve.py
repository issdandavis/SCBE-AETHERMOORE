"""analog_solve: inference WITHOUT a neural forward pass -- navigate a geometry maze of verified cases.

The maze (Issac's framing): the answer sits at the hidden angle of a geometry maze, and the cracks in
the walls are the hints at the path. Made literal with the spin-voxel math from
`docs/specs/QUASI_VECTOR_SPIN_VOXELS_MAZE_RND.md`:

  - every verified case is a normalized feature vector S (a "spin");
  - alignment(query, case) = S_q . S_c   -- the cosine ANGLE between two spins (1.0 = same direction);
  - disorder         = 1 - alignment      -- the doc's per-edge D_spin (a misaligned neighbor = a wall);
  - the CRACKS        = the best-aligned verified neighbors (they point down a likely path);
  - the WALLS         = execution verification (a candidate that fails the tests hit a wall);
  - the HIDDEN ANGLE  = the neighbor whose grafted solution actually PASSES -- found by navigating, not
                        by a model.

This is "analog inference for a non-inference model": no trained forward pass runs. A new problem is
SOLVED by INTERPOLATION (retrieve the best-aligned verified case) + COMPOSITION (graft its code, adapt
the entry point) + VERIFY (run the tests). It wins where the new problem is near something already
verified; on genuine novelty it returns unsolved and the caller falls back to a model.

HONEST LIMIT (learned the hard way -- an adversarial review caught it): a "solved" is only as trustworthy
as the tests it ran against. On a WEAK oracle (e.g. MBPP's 3 cherry-picked asserts) a grafted neighbor
can pass while being the wrong algorithm (a monotonic-array checker renamed to all_unique passed all 3).
So the lane does not emit code that fails the GIVEN tests, but "passes the tests" != "correct" -- the
caller MUST hold back tests it did not search on (see measure_mbpp's public-search / held-back-accept),
and the verifier strength is the real ceiling. That caveat IS the interpolate-and-check bet stated
honestly: cheap when the spec is strong, untrustworthy when the spec is weak.

    from python.scbe.analog_solve import Maze, analog_solve
    maze = Maze.from_solved([("add a and b", "def add(a,b): return a+b", ["assert add(2,3)==5"])])
    out = analog_solve("sum two numbers", ["assert total(2, 3) == 5"], maze)  # solved, 0 model calls
"""

from __future__ import annotations

import ast
import math
import re
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from python.helm import public_bench as pb
from python.helm.free_generator import strip_to_code

# --- the analog representation: text -> a normalized "spin" vector (deterministic, stdlib, $0) --------

_WORD = re.compile(r"[a-zA-Z_][a-zA-Z_0-9]*")


def featurize(text: str) -> Dict[str, float]:
    """Map text to an L2-normalized sparse spin vector. Features = lowercased word tokens + character
    3-grams (so 'sum'~'sums' and renamed variables still align). Deterministic -- no model, no network."""
    text = (text or "").lower()
    feats: Dict[str, float] = {}
    for w in _WORD.findall(text):
        feats["w:" + w] = feats.get("w:" + w, 0.0) + 1.0
    squashed = re.sub(r"\s+", " ", text)
    for i in range(len(squashed) - 2):
        g = squashed[i : i + 3]
        feats["g:" + g] = feats.get("g:" + g, 0.0) + 0.5
    norm = math.sqrt(sum(v * v for v in feats.values())) or 1.0
    return {k: v / norm for k, v in feats.items()}


def alignment(a: Dict[str, float], b: Dict[str, float]) -> float:
    """S_a . S_b -- the cosine angle between two spins (both already normalized). 1.0 = same direction."""
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    return sum(v * big.get(k, 0.0) for k, v in small.items())


def disorder(a: Dict[str, float], b: Dict[str, float]) -> float:
    """1 - alignment: the spin-voxel D_spin. High disorder = a wall between query and case."""
    return 1.0 - alignment(a, b)


# --- adapting a verified neighbor's code to the new problem's entry point (the COMPOSITION step) ------

_DEF = re.compile(r"^\s*def\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*\(", re.M)


def target_name(checks: Sequence[str]) -> Optional[str]:
    """The function the tests call, e.g. 'total' from `assert total(2, 3) == 5`. The maze must produce a
    callable by THIS name even if the neighbor it borrows from named it something else."""
    for c in checks:
        m = re.search(r"\b([a-zA-Z_][a-zA-Z_0-9]*)\s*\(", c.split("assert", 1)[-1])
        if m:
            return m.group(1)
    return None


def adapt(code: str, checks: Sequence[str]) -> str:
    """Graft a neighbor's solution onto the new problem: if the tests call a name the code doesn't
    define, and the code has exactly one top-level def, rename that def to the target. Conservative on
    purpose -- a bad graft just hits a wall (fails verify), it never ships unverified."""
    code = strip_to_code(code)
    want = target_name(checks)
    if not want:
        return code
    defined = _DEF.findall(code)
    if want in defined or len(defined) != 1:
        return code
    return re.sub(r"(\bdef\s+)" + re.escape(defined[0]) + r"(\s*\()", r"\g<1>" + want + r"\2", code, count=1)


# --- adapt BASIS: a tiny execution-gated code-transform alphabet (Icecuber's "small basis, compose,
#     verify"). Every candidate is still run against the walls, so a wrong transform just hits a wall --
#     BUT it amplifies a weak oracle (more candidates = more chances to overfit few tests), so the caller
#     MUST verify accepted code against held-back tests it did not search on (see measure_mbpp). ---------

_BINOP_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv, ast.FloorDiv: ast.Mult, ast.Div: ast.Mult}
_CMP_SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
_NUM = re.compile(r"(?<![\w.])\d+(?![\w.])")


class _OpSwapper(ast.NodeTransformer):
    """Swap exactly the `target`-th swappable operator (post-order). target=-1 swaps nothing (counts)."""

    def __init__(self, target: int) -> None:
        self.target = target
        self.count = 0

    def visit_BinOp(self, node: ast.AST) -> ast.AST:
        self.generic_visit(node)
        if type(node.op) in _BINOP_SWAP:
            if self.count == self.target:
                node.op = _BINOP_SWAP[type(node.op)]()
            self.count += 1
        return node

    def visit_Compare(self, node: ast.AST) -> ast.AST:
        self.generic_visit(node)
        if len(node.ops) == 1 and type(node.ops[0]) in _CMP_SWAP:
            if self.count == self.target:
                node.ops = [_CMP_SWAP[type(node.ops[0])]()]
            self.count += 1
        return node


def _op_swap_variants(code: str) -> List[str]:
    """One-operator-flipped variants (AST-safe), e.g. n // 2 -> n * 2 (half -> double)."""
    try:
        ast.parse(code)
    except SyntaxError:
        return []
    counter = _OpSwapper(-1)
    counter.visit(ast.parse(code))
    out: List[str] = []
    for i in range(counter.count):
        tree = ast.parse(code)
        _OpSwapper(i).visit(tree)
        try:
            out.append(ast.unparse(ast.fix_missing_locations(tree)))
        except Exception:
            pass
    return out


def _const_variants(code: str, checks: Sequence[str]) -> List[str]:
    """Rebind a numeric literal in the body to one that appears in the spec/tests."""
    code_nums = list(dict.fromkeys(_NUM.findall(code)))
    targets = [t for t in dict.fromkeys(n for c in checks for n in _NUM.findall(c)) if t not in set(code_nums)]
    out: List[str] = []
    for cn in code_nums:
        for tn in targets:
            out.append(_NUM.sub(lambda m, cn=cn, tn=tn: tn if m.group(0) == cn else m.group(0), code))
    return out


def adapt_basis(code: str, checks: Sequence[str], max_candidates: int = 24) -> List[str]:
    """A small basis of cheap, deterministic grafts over ONE neighbor's code: rename-entry (cheapest,
    first), as-is, then one-operator-swaps and constant-rebinds, each re-renamed to the target entry.
    Bounded by `max_candidates`. The first that passes the walls wins -- so the cheapest graft is tried
    first, and a richer graft only fires when the simple one cannot bridge the gap."""
    base = strip_to_code(code)
    seen: List[str] = []

    def push(c: Optional[str]) -> None:
        if c and c not in seen and len(seen) < max_candidates:
            seen.append(c)

    push(adapt(base, checks))  # cheapest: rename entry to the target -- tried first (preserves old behavior)
    push(base)
    for b in list(seen):
        for v in _op_swap_variants(b):
            push(adapt(v, checks))
        for v in _const_variants(b, checks):
            push(adapt(v, checks))
        if len(seen) >= max_candidates:
            break
    return seen[:max_candidates]


# --- the maze: a case base of verified (problem, solution) pairs as spin vectors ----------------------


class Case:
    """One verified node in the maze: a problem, a solution known to pass, and the problem's spin."""

    __slots__ = ("cid", "problem", "code", "spin", "source")

    def __init__(self, cid: str, problem: str, code: str, source: str = "corpus") -> None:
        self.cid = cid
        self.problem = problem
        self.code = strip_to_code(code)
        self.spin = featurize(problem + " " + self.code)
        self.source = source


class Maze:
    """The geometry maze: verified cases positioned by their spin. `cracks` ranks them by alignment to a
    query -- the hints at the path. No case enters unless its code is real (the caller vouches it)."""

    def __init__(self, cases: Optional[List[Case]] = None) -> None:
        self.cases: List[Case] = cases or []

    def add(self, problem: str, code: str, cid: Optional[str] = None, source: str = "corpus") -> "Maze":
        self.cases.append(Case(cid or ("case_%d" % len(self.cases)), problem, code, source))
        return self

    def learn(self, problem: str, code: str, checks: Optional[Sequence[str]] = None, cid: Optional[str] = None) -> bool:
        """Add a freshly-VERIFIED solve back into the maze -- the SOAR/Stitch abstraction-library move the
        ARC winners use: the library grows with use, so RECURRENCE (not a frozen corpus) drives the hit
        rate. This is the honest answer to '0% on all-distinct MBPP': don't expect a static library to
        cover novel work -- let it accrete what gets solved, so the second time a shape recurs it is free.
        If `checks` are given the code must pass them first (only verified cases enter); returns admitted."""
        code = strip_to_code(code)
        if checks is not None and not pb._verify(code, list(checks), [], [])["public_passed"]:
            return False
        self.add(problem, code, cid=cid, source="learned")
        return True

    def cracks(self, query: str) -> List[Tuple[float, Case]]:
        """Neighbors ranked by alignment (high = a crack pointing that way). Returns (alignment, case)."""
        q = featurize(query)
        ranked = [(alignment(q, c.spin), c) for c in self.cases]
        ranked.sort(key=lambda t: t[0], reverse=True)
        return ranked

    @classmethod
    def from_solved(cls, triples: Sequence[Tuple[str, str, Sequence[str]]]) -> "Maze":
        """Build from (problem, code, checks) triples -- only cases whose code ACTUALLY passes its checks
        get in (the walls vouch for every node; an unverified pair is silently dropped)."""
        m = cls()
        for i, (problem, code, checks) in enumerate(triples):
            if pb._verify(strip_to_code(code), list(checks), [], [])["public_passed"]:
                m.add(problem, code, cid="solved_%d" % i, source="solved")
        return m

    @classmethod
    def from_corpus(cls, records: Sequence[Dict[str, Any]]) -> "Maze":
        """Build from {messages, meta} VTC records: problem = first user turn, solution = last assistant
        turn. The corpus is already execution-verified upstream, so we trust its codes here."""
        m = cls()
        for i, r in enumerate(records):
            msgs = r.get("messages", [])
            problem = next((x["content"] for x in msgs if x.get("role") == "user"), "")
            code = next((x["content"] for x in reversed(msgs) if x.get("role") == "assistant"), "")
            if problem and code:
                cid = str(r.get("meta", {}).get("task_id", "rec_%d" % i))
                m.add(problem, code, cid=cid, source="corpus")
        return m


# --- the solver: navigate the maze, no neural forward pass ------------------------------------------


def analog_solve(
    problem: str,
    checks: Sequence[str],
    maze: Maze,
    imports: Sequence[str] = (),
    rounds: int = 5,
    min_alignment: float = 0.05,
) -> Dict[str, Any]:
    """Solve by navigating the maze: follow the best-aligned cracks, graft + adapt each neighbor's code,
    and verify against the walls (the tests). Returns the first graft that PASSES -- the hidden-angle
    answer -- with the path it walked. If no crack within `min_alignment` produces a passing graft,
    returns solved=False (honest: the caller falls back to a model). Zero model calls either way.

    The result carries `path` (the cracks tried: cid, angle, disorder, passed) so the navigation is
    inspectable, and `solver='analog'` so a router can record that geometry -- not a model -- solved it.
    """
    path: List[Dict[str, Any]] = []
    tried_code: set = set()
    for angle, case in maze.cracks(problem)[: max(rounds, 1)]:
        if angle < min_alignment:
            break  # the remaining neighbors are walls, not cracks -- stop, don't guess
        for candidate in adapt_basis(case.code, checks):  # try the cheap graft, then the small basis
            if candidate in tried_code:
                continue  # same wall already hit -- skip (the prune)
            tried_code.add(candidate)
            if pb._verify(candidate, list(checks), [], list(imports))["public_passed"]:
                path.append(
                    {"cid": case.cid, "angle": round(angle, 4), "disorder": round(1.0 - angle, 4), "passed": True}
                )
                return {
                    "solved": True,
                    "code": candidate,
                    "via": case.cid,
                    "angle": round(angle, 4),
                    "rounds_used": len(path) + 1,
                    "path": path,
                    "solver": "analog",
                }
        path.append({"cid": case.cid, "angle": round(angle, 4), "disorder": round(1.0 - angle, 4), "passed": False})
    return {"solved": False, "code": None, "via": None, "rounds_used": len(path), "path": path, "solver": "analog"}


def analog_solver(maze: Maze) -> Callable[[Any], str]:
    """A run_step-compatible solver: given a spec dict with `check`, return the top-aligned graft as a
    candidate string (AetherDesk.run_step then verifies it against the walls). Lets a router route a step
    to the maze exactly like it routes to a block or a model -- analog inference as a first-class lane."""

    def solve(spec: Any) -> str:
        problem = spec.get("spec", "") if isinstance(spec, dict) else str(spec)
        checks = spec.get("check", []) if isinstance(spec, dict) else []
        ranked = maze.cracks(problem)
        if not ranked:
            return ""
        return adapt(ranked[0][1].code, checks)

    return solve


def render(out: Dict[str, Any]) -> str:
    """One-screen summary of a navigation: the path of cracks walked and where it exited."""
    lines = ["ANALOG SOLVE  (%s)" % ("SOLVED via %s" % out["via"] if out["solved"] else "no crack -> fall back")]
    for step in out["path"]:
        mark = "OK " if step["passed"] else "wall"
        lines.append("  %-12s angle=%.3f disorder=%.3f  %s" % (step["cid"], step["angle"], step["disorder"], mark))
    if out["solved"]:
        lines.append("  hidden-angle answer: %s" % out["code"].splitlines()[0])
    return "\n".join(lines)


def demo() -> Dict[str, Any]:
    """Two honest outcomes, no model in the loop:
    1. a renamed/near-duplicate of a verified case -> SOLVED by geometry alone (interpolation win);
    2. a genuinely novel problem with no aligned crack -> solved=False (the honest fallback, not a guess).
    """
    maze = Maze.from_solved(
        [
            ("add two numbers a and b", "def add(a, b):\n    return a + b", ["assert add(2, 3) == 5"]),
            ("multiply a and b", "def mul(a, b):\n    return a * b", ["assert mul(2, 3) == 6"]),
            ("reverse a string s", "def rev(s):\n    return s[::-1]", ["assert rev('ab') == 'ba'"]),
        ]
    )
    # 1. "sum two numbers" calls total(): no case names it, but 'add' aligns -> graft + rename -> passes.
    hit = analog_solve("sum / total of two numbers a and b", ["assert total(2, 3) == 5"], maze)
    # 2. nothing in the maze is about prime factorization -> no crack clears min_alignment -> fall back.
    miss = analog_solve("compute the nth Fibonacci number recursively", ["assert fib(10) == 55"], maze)
    return {"interpolation_solved": hit["solved"], "novel_fell_back": not miss["solved"], "hit": hit, "miss": miss}


def measure_mbpp(
    train_k: int = 120,
    eval_m: int = 80,
    public_k: int = 1,
    min_alignment: float = 0.05,
    rounds: int = 3,
    confident_angle: float = 0.6,
) -> Dict[str, Any]:
    """Honest capability test with the oracle hole FIXED. The maze is MBPP[:train_k] reference solutions
    (each execution-verified). For each disjoint held-out problem, the lane searches on only the PUBLIC
    tests (first `public_k`) and a solve is then re-checked on the HELD-BACK tests it never searched on:

      - genuine            : solved on public AND passes the held-back tests AND the neighbor is close
                             (angle >= confident_angle) -- the best the lane can honestly claim;
      - overfit            : passed public, FAILED the held-back tests -> caught, NOT a solve;
      - weak_oracle_suspect: passed every test but via a DISTANT neighbor (angle < confident_angle) -- the
                             283<-monotonic kind of coincidental pass the adversarial review found; the
                             tests are too weak to prove it correct, so it is NOT counted as solved.

    The earlier 'false_positives=0 by construction' was wrong: it used all tests for BOTH search and
    acceptance, so a graft that overfits a 3-assert oracle counted as solved. This split is the fix; the
    residual truth is that MBPP's tiny oracle still cannot prove correctness, so genuine is a CEILING, not
    a guarantee.
    """
    ps = pb.pull_mbpp()
    train, ev = ps[:train_k], ps[train_k : train_k + eval_m]
    maze = Maze()
    for p in train:
        tests, imps = p.get("test_list", []), p.get("test_imports", [])
        if tests and pb._verify(p["code"], [], tests, imps)["hidden_passed"]:
            maze.add(p["prompt"], p["code"], cid=str(p["task_id"]), source="mbpp")
    rows: List[Dict[str, Any]] = []
    for p in ev:
        tests, imps = list(p.get("test_list", [])), p.get("test_imports", [])
        public, held = tests[:public_k], tests[public_k:]
        out = analog_solve(p["prompt"], public, maze, imports=imps, min_alignment=min_alignment, rounds=rounds)
        cls = "fallback"
        if out["solved"]:
            held_ok = (not held) or pb._verify(out["code"], [], held, imps)["hidden_passed"]
            cls = (
                "overfit" if not held_ok else ("genuine" if out["angle"] >= confident_angle else "weak_oracle_suspect")
            )
        rows.append(
            {"task_id": p["task_id"], "cls": cls, "via": out["via"], "angle": out["angle"] if out["solved"] else 0.0}
        )
    counts = {
        k: sum(1 for r in rows if r["cls"] == k) for k in ("genuine", "weak_oracle_suspect", "overfit", "fallback")
    }
    n = len(rows) or 1
    return {
        "n_train_cases": len(maze.cases),
        "n_eval": len(rows),
        "public_k": public_k,
        **counts,
        "genuine_rate": round(counts["genuine"] / n, 4),
        "genuine_rows": [r for r in rows if r["cls"] == "genuine"],
        "suspect_rows": [r for r in rows if r["cls"] == "weak_oracle_suspect"],
    }


def render_measure(m: Dict[str, Any]) -> str:
    lines = [
        "ANALOG LIBRARY LANE on held-out MBPP (0 model calls, public_k=%d search / held-back accept)" % m["public_k"],
        "  maze cases (verified) : %d" % m["n_train_cases"],
        "  held-out evaluated    : %d" % m["n_eval"],
        "  GENUINE (pass held-back, close neighbor): %d  (%.1f%%)" % (m["genuine"], 100 * m["genuine_rate"]),
        "  weak-oracle suspect (pass weak tests, distant neighbor): %d   <- NOT counted (likely coincidence)"
        % m["weak_oracle_suspect"],
        "  overfit (passed public, FAILED held-back): %d   <- caught, not a solve" % m["overfit"],
        "  honest fallback       : %d" % m["fallback"],
    ]
    for r in (m["genuine_rows"] + m["suspect_rows"])[:8]:
        lines.append("    %-18s task %s via case %s  angle=%.3f" % (r["cls"], r["task_id"], r["via"], r["angle"]))
    return "\n".join(lines)


def _reword(prompt: str) -> str:
    """A mild deterministic paraphrase (keeps most words so alignment stays high -- a realistic recurrence,
    not a byte-identical repeat)."""
    p = (prompt or "").strip()
    return "Implement the following. " + (p[0].lower() + p[1:] if p else p)


def _rename(text: str, old: str, new: str) -> str:
    return re.sub(r"\b" + re.escape(old) + r"\b", new, text)


def measure_recurrence(base_k: int = 40, public_k: int = 1) -> Dict[str, Any]:
    """Honest demo of the self-growing library (the answer to 0%-on-all-distinct). A stream where each
    base problem RECURS once as a paraphrase (reworded prompt + renamed function). Processed in order:
    the library is tried first; a miss is solved 'expensively' (via the reference, simulating a model) and
    -- with learning ON -- LEARNED back. A later paraphrase of a learned problem is then sunk for FREE.
    Compares learning ON vs OFF. Every free hit is accepted only on HELD-BACK tests (no weak-oracle pass),
    and the paraphrase's renamed reference is the correct algorithm, so a hit is genuine. The 50% recurrence
    here is constructed -- the real free-hit rate tracks YOUR workload's recurrence, which is the point."""
    ps = pb.pull_mbpp()
    base = [
        p
        for p in ps[: base_k * 3]
        if p.get("test_list") and pb._verify(p["code"], [], p["test_list"], p.get("test_imports", []))["hidden_passed"]
    ][:base_k]

    def run(learning: bool) -> Dict[str, int]:
        maze = Maze()
        free = recur_free = expensive = 0
        for p in base:
            old = target_name(p["test_list"]) or "f"
            new = old + "_v2"
            items = [
                ("orig", p["prompt"], list(p["test_list"]), old),
                ("para", _reword(p["prompt"]), [_rename(t, old, new) for t in p["test_list"]], new),
            ]
            for kind, prompt, tests, name in items:
                imps = p.get("test_imports", [])
                public, held = tests[:public_k], tests[public_k:]
                out = analog_solve(prompt, public, maze, imports=imps)
                hit = out["solved"] and ((not held) or pb._verify(out["code"], [], held, imps)["hidden_passed"])
                if hit:
                    free += 1
                    recur_free += kind == "para"
                else:
                    expensive += 1
                    if learning:  # solve it via the reference (the expensive club), then keep it
                        maze.learn(prompt, adapt(p["code"], tests), checks=tests, cid="%s_%s" % (p["task_id"], kind))
        return {"free": free, "recurrence_free": recur_free, "expensive": expensive, "stream": 2 * len(base)}

    on, off = run(True), run(False)
    return {
        "base_k": len(base),
        "with_learning": on,
        "without_learning": off,
        "amortized_free": on["free"] - off["free"],
    }


def render_recurrence(m: Dict[str, Any]) -> str:
    on, off = m["with_learning"], m["without_learning"]
    return "\n".join(
        [
            "SELF-GROWING LIBRARY on a constructed 50%%-recurrence stream (%d base, %d items)"
            % (m["base_k"], on["stream"]),
            "  WITH learning : %d/%d sunk FREE by the library (%d of them recurrences)"
            % (on["free"], on["stream"], on["recurrence_free"]),
            "  WITHOUT       : %d/%d free  <- a frozen library can't amortize" % (off["free"], off["stream"]),
            "  amortized free solves: %d   <- recurrence the growing library bought back" % m["amortized_free"],
        ]
    )


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if "--measure" in argv:
        print(render_measure(measure_mbpp()))
        return 0
    if "--recurrence" in argv:
        print(render_recurrence(measure_recurrence()))
        return 0
    out = demo()
    print("ANALOG INFERENCE (no neural forward pass)")
    print()
    print(render(out["hit"]))
    print()
    print(render(out["miss"]))
    print()
    print(
        "interpolation solved (0 model calls): %s   |   novel honestly fell back: %s"
        % (out["interpolation_solved"], out["novel_fell_back"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
