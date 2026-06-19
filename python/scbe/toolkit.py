"""toolkit: one governed, sealed registry over every real SCBE coding + math + control system.

This is the AI's toolbox. It catalogs the actual callable tools across the repo (coding, math,
geometry, control, governance, measurement, language, verification), and exposes ONE governed way to
call any of them: every invocation is allowlist/safety-screened, runs the destructive-command screen
(the never-delete rule), and is SHA-256 SEALED into a forward-chained transcript -- reusing the real
SHA-256 seal from desktop_access (the in-system "geoseal" layer; the security is the standard hash,
nothing exotic).

  * lazy + robust: a tool's module is imported only when first used; if a dependency is missing the
    tool is reported UNAVAILABLE, never crashing the toolbox.
  * governed: `safe` tools (pure computation) run freely; `guarded` tools (file/desktop/stateful, or
    anything that executes code) need a confirm reason; a destructive string in any argument is
    REFUSED outright.
  * sealed: each call appends {tool, args, result, decision, prev, result_hash, seal}; the seal binds
    the PRIOR seal + a digest of the result, so `verify()` catches mutation, insertion, reordering,
    AND a swapped composition payload. (A holder of the live Toolkit could recompute the chain -- for
    cross-boundary integrity, sign the final seal with an external key.)

    from python.scbe.toolkit import default_toolkit
    tk = default_toolkit()
    tk.invoke("is_prime", 97)             # -> sealed receipt, result True
    tk.invoke("recover", tk.invoke("place", [1, 2, 3])["result_obj"])   # tools compose
    tk.verify()                            # the whole session is tamper-evident
"""

from __future__ import annotations

import hashlib
import importlib
import secrets
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .desktop_access import _DESTRUCTIVE, _seal

_RESULT_CAP = 240  # how much of a result repr to keep in the sealed record


def _digest(obj: Any) -> str:
    """A stable SHA-256 digest of a (possibly unserializable) result, for sealing composition payloads."""
    try:
        return hashlib.sha256(repr(obj).encode("utf-8")).hexdigest()[:16]
    except Exception:
        return "?"


@dataclass(frozen=True)
class Tool:
    name: str
    module: str  # dotted import path
    callable: str  # attribute (may be "Class.method")
    domain: str
    one_line: str
    safety: str  # "safe" | "guarded"


# --- the catalog: every real, callable tool the inventory confirmed exists --------------------
CATALOG: List[Tool] = [
    Tool(
        "classify_number_task",
        "python.scbe.sieve_calc",
        "classify_number_task",
        "math",
        "prime sieve decides primality + factor count; model only labels",
        "safe",
    ),
    Tool(
        "run_stepwise",
        "python.scbe.stepwise",
        "run_stepwise",
        "control",
        "walk a task's steps, rewind on missteps, stop at the ceiling",
        "safe",
    ),
    Tool(
        "scripted_proposer",
        "python.scbe.stepwise",
        "scripted_proposer",
        "control",
        "a deterministic proposer that replays a fixed answer sequence",
        "safe",
    ),
    Tool("is_prime", "src.numtheory", "is_prime", "math", "deterministic Miller-Rabin primality test", "safe"),
    Tool("factorization", "src.numtheory", "factorization", "math", "prime factorization as {prime: exponent}", "safe"),
    Tool(
        "PrimeCategories",
        "src.prime_category",
        "PrimeCategories",
        "math",
        "categories as primes; membership = divisibility; code = product",
        "safe",
    ),
    Tool(
        "parse",
        "python.scbe.loomflow",
        "parse",
        "coding",
        "parse branching/looping scalar assembly into instructions",
        "safe",
    ),
    Tool(
        "interpret",
        "python.scbe.loomflow",
        "interpret",
        "control",
        "run a scalar IR via the reference interpreter; return prints",
        "safe",
    ),
    Tool(
        "emit",
        "python.scbe.loomflow",
        "emit",
        "coding",
        "emit a loomflow program as a dispatch loop in py/js/rust/c",
        "safe",
    ),
    Tool(
        "verify",
        "python.scbe.loomflow",
        "verify",
        "verify",
        "run reference + every face; report AGREE/DISAGREE per face",
        "safe",
    ),
    Tool(
        "parse_fn",
        "python.scbe.loomfn",
        "parse",
        "coding",
        "parse loomfn assembly (arrays, functions, strings)",
        "safe",
    ),
    Tool(
        "verify_fn", "python.scbe.loomfn", "verify", "verify", "run loomfn reference + faces; compare honestly", "safe"
    ),
    Tool(
        "emit_fn",
        "python.scbe.loomfn",
        "emit",
        "coding",
        "emit a loomfn program (functions + arrays) in py/js/rust",
        "safe",
    ),
    Tool(
        "from_tongue",
        "python.scbe.loomtongue",
        "from_tongue",
        "language",
        "translate a conlang program into a loomflow program",
        "safe",
    ),
    Tool(
        "to_tongue",
        "python.scbe.loomtongue",
        "to_tongue",
        "language",
        "read a loomflow program back out as conlang text (bijective)",
        "safe",
    ),
    Tool(
        "verify_tongue",
        "python.scbe.loomtongue",
        "verify_tongue",
        "verify",
        "translate + run + verify the conlang song round-trips",
        "safe",
    ),
    Tool("to_cube", "python.scbe.board", "to_cube", "coding", "split a 6-bit opcode into 4x4x4 cube coords", "safe"),
    Tool("from_cube", "python.scbe.board", "from_cube", "coding", "bijective inverse of to_cube", "safe"),
    Tool("place", "python.scbe.board", "place", "coding", "program -> ordered stones on the token board", "safe"),
    Tool(
        "recover", "python.scbe.board", "recover", "verify", "bijective inverse of place (board is reversible)", "safe"
    ),
    Tool(
        "is_reversible",
        "python.scbe.board",
        "is_reversible",
        "verify",
        "test a program round-trips through place/recover",
        "safe",
    ),
    Tool("rgb", "python.scbe.board", "rgb", "coding", "opcode byte -> RGB color via its cube axes", "safe"),
    Tool(
        "opcode_note",
        "python.scbe.board",
        "opcode_note",
        "language",
        "opcode -> pitch (scale degree) + note name",
        "safe",
    ),
    Tool(
        "emit_polyglot",
        "python.scbe.polyglot",
        "emit",
        "coding",
        "emit a CA opcode program as source in any registered language",
        "safe",
    ),
    Tool("program_bytes", "python.scbe.polyglot", "program_bytes", "coding", "op names -> CA opcode bytes", "safe"),
    Tool(
        "languages",
        "python.scbe.polyglot",
        "languages",
        "coding",
        "list registered language faces available for emission",
        "safe",
    ),
    Tool(
        "play",
        "python.scbe.instrument",
        "play",
        "language",
        "play a song -> ops -> a language face, run + verify round-trip",
        "safe",
    ),
    Tool(
        "notes_to_ops",
        "python.scbe.instrument",
        "notes_to_ops",
        "language",
        "map a note song to CA op names via a mode's scale",
        "safe",
    ),
    Tool(
        "emit_all",
        "python.scbe.instrument",
        "emit_all",
        "coding",
        "emit one song into every registered language face",
        "safe",
    ),
    Tool(
        "keyspace",
        "python.scbe.instrument",
        "keyspace",
        "language",
        "multisensory key for an opcode (pitch, midi, light, rgb)",
        "safe",
    ),
    Tool(
        "rosetta",
        "python.scbe.rosetta",
        "rosetta",
        "measurement",
        "manifest a song into every face, run + verify cross-face",
        "safe",
    ),
    Tool(
        "bytes_to_bits",
        "python.scbe.bit_spine",
        "bytes_to_bits",
        "coding",
        "encode bytes as a reversible binary string",
        "safe",
    ),
    Tool(
        "bits_to_bytes",
        "python.scbe.bit_spine",
        "bits_to_bytes",
        "coding",
        "bijective inverse of bytes_to_bits",
        "safe",
    ),
    Tool(
        "run_bf",
        "python.scbe.bit_spine",
        "run_bf",
        "coding",
        "run a Brainfuck-class program on the finite-safe tape",
        "safe",
    ),
    Tool(
        "pack_ops",
        "python.scbe.bit_spine",
        "pack_ops",
        "coding",
        "pack 3-bit opcodes with a hash-checked header",
        "safe",
    ),
    Tool(
        "verify_dna",
        "python.scbe.bijective_dna",
        "verify",
        "verify",
        "run every strand check on a program (faces, rc, midpoints, seal)",
        "safe",
    ),
    Tool(
        "faces_agree",
        "python.scbe.bijective_dna",
        "faces_agree",
        "verify",
        "emit to every face + decode back; all must equal the program",
        "safe",
    ),
    Tool(
        "seekable",
        "python.scbe.bijective_dna",
        "seekable",
        "verify",
        "assembly from every midpoint reconstructs the build",
        "safe",
    ),
    Tool(
        "seal_dna",
        "python.scbe.bijective_dna",
        "seal",
        "verify",
        "scramble (position, opcode) through an invertible permutation",
        "safe",
    ),
    Tool(
        "forge",
        "python.codeforge",
        "forge",
        "coding",
        "run the workflow machine on plain English -> tamper-evident build",
        "guarded",
    ),
    Tool(
        "inscribe",
        "python.inscribe.ratios",
        "inscribe",
        "measurement",
        "encode a float as a compact continued-fraction ratio",
        "safe",
    ),
    Tool(
        "extrapolate",
        "python.inscribe.extrapolate",
        "extrapolate",
        "measurement",
        "fit the minimal polynomial through points + predict",
        "safe",
    ),
    Tool(
        "emit_python",
        "src.code_prism.emitter",
        "emit_python",
        "coding",
        "emit a PrismModule IR as valid Python source",
        "safe",
    ),
    Tool(
        "emit_from_ir",
        "src.code_prism.emitter",
        "emit_from_ir",
        "coding",
        "convert a PrismModule IR to py/ts/go",
        "safe",
    ),
    Tool(
        "analyze_formula",
        "python.scbe.chemistry_dimensions",
        "analyze_formula",
        "math",
        "chemical formula -> atom + subatomic dimensional totals",
        "safe",
    ),
    Tool(
        "to_dna",
        "python.scbe.dna_parse",
        "to_dna",
        "math",
        "bijective hex<->DNA codec (1 hex digit -> 2 bases)",
        "safe",
    ),
    Tool(
        "positions",
        "src.scbe_aethermoore.geometry",
        "positions",
        "geometry",
        "region positions as points in the Poincare disk",
        "safe",
    ),
    Tool(
        "route_intent",
        "src.scbe_aethermoore.geometry",
        "route_intent",
        "routing",
        "project an intent point onto the nearest rail; flag drift",
        "safe",
    ),
    Tool(
        "valid_edge",
        "src.scbe_aethermoore.geometry",
        "valid_edge",
        "routing",
        "is a transition a valid consecutive pair on a rail",
        "safe",
    ),
    Tool(
        "finsler_distance",
        "python.scbe.geometric_router",
        "finsler_distance",
        "geometry",
        "tongue-weighted (Finsler) hyperbolic distance",
        "safe",
    ),
    Tool(
        "route_fleet",
        "python.scbe.geometric_router",
        "route_fleet",
        "routing",
        "assign tasks to agents by the Finsler metric + pressure",
        "safe",
    ),
    Tool(
        "round_robin",
        "python.scbe.geometric_router",
        "round_robin",
        "routing",
        "flat-parallel baseline for comparison vs geometric routing",
        "safe",
    ),
    Tool(
        "build_registry",
        "python.scbe.phdm_polyhedra",
        "build_registry",
        "geometry",
        "build the 16-polyhedra registry with zones + phi weights",
        "safe",
    ),
    Tool(
        "self_test",
        "python.scbe.phdm_polyhedra",
        "self_test",
        "geometry",
        "run the polyhedra registry self-tests",
        "safe",
    ),
    Tool(
        "encode",
        "python.scbe.phdm_embedding",
        "encode",
        "geometry",
        "encode text into 21D Poincare ball coordinates",
        "safe",
    ),
    Tool(
        "get_trust_ring",
        "python.scbe.phdm_embedding",
        "get_trust_ring",
        "geometry",
        "radial distance -> trust ring (CORE/INNER/OUTER/WALL)",
        "safe",
    ),
    Tool(
        "play_governed",
        "python.scbe.game_board",
        "play_governed",
        "control",
        "play a game to its end with a referee + sealed moves",
        "guarded",
    ),
    Tool(
        "run_level",
        "python.scbe.level_slice",
        "run_level",
        "control",
        "clear a governed file-normalization level end-to-end",
        "guarded",
    ),
    Tool(
        "invoke",
        "python.scbe.desktop_access",
        "ActionRegistry.invoke",
        "governance",
        "invoke a desktop action through the allowlist + screen, sealed",
        "guarded",
    ),
    Tool(
        "verify_registry",
        "python.scbe.desktop_access",
        "ActionRegistry.verify",
        "governance",
        "verify every SHA-256 seal in an action transcript",
        "safe",
    ),
    Tool(
        "play_cube",
        "python.scbe.desktop_access",
        "play_cube",
        "control",
        "play a cube twist sequence as governed desktop actions",
        "guarded",
    ),
    Tool(
        "access_points",
        "python.scbe.desktop_access",
        "ActionRegistry.access_points",
        "routing",
        "one action through verb + DOM + pixels channels",
        "safe",
    ),
    Tool(
        "mcp_tools",
        "python.scbe.desktop_access",
        "ActionRegistry.mcp_tools",
        "routing",
        "the registry's actions as MCP tool schemas",
        "safe",
    ),
    Tool(
        "run_loop",
        "python.scbe.pair_loop",
        "run_loop",
        "control",
        "run a template: fixed tokens free, blanks routed by capability",
        "safe",
    ),
    Tool(
        "ledger_run",
        "python.scbe.context_ledger",
        "Ledger.run",
        "control",
        "execute one ledger command; append a sealed event",
        "safe",
    ),
    Tool(
        "recall",
        "python.scbe.context_ledger",
        "Ledger.recall",
        "control",
        "return the working context as compact text",
        "safe",
    ),
    Tool(
        "pack",
        "python.scbe.context_ledger",
        "Ledger.pack",
        "control",
        "forward attention-heavy context in shorthand; drop stale",
        "safe",
    ),
    Tool(
        "verify_ledger",
        "python.scbe.context_ledger",
        "Ledger.verify",
        "verify",
        "the ledger event log is tamper-evident",
        "safe",
    ),
    Tool(
        "evaluate_semantic_gate",
        "python.scbe.semantic_gate",
        "evaluate_semantic_gate",
        "governance",
        "provenance separation -> deterministic ALLOW/QUARANTINE/DENY",
        "safe",
    ),
    Tool(
        "hyperbolic_distance",
        "src.geoseal",
        "hyperbolic_distance",
        "geometry",
        "hyperbolic distance in the Poincare ball (arcosh)",
        "safe",
    ),
    Tool(
        "run_swarm",
        "src.geoseal",
        "run_swarm",
        "control",
        "run GeoSeal swarm steps; track per-agent suspicion",
        "guarded",
    ),
    Tool(
        "compute_metrics",
        "src.geoseal",
        "compute_metrics",
        "measurement",
        "GeoSeal metrics: isolation time, boundary norm, consensus",
        "safe",
    ),
    Tool(
        "difficulty",
        "python.helm.leveling",
        "difficulty",
        "measurement",
        "level rank -> difficulty (0..100) under a slope shape",
        "safe",
    ),
    Tool(
        "track",
        "python.helm.leveling",
        "track",
        "measurement",
        "flatten a tiered curriculum into one ranked track",
        "safe",
    ),
    Tool(
        "ride",
        "python.helm.leveling",
        "ride",
        "measurement",
        "climb a curriculum with continuous difficulty scoring",
        "safe",
    ),
    Tool(
        "skill_capped_generator",
        "python.helm.leveling",
        "skill_capped_generator",
        "measurement",
        "a synthetic rider with a known skill ceiling",
        "safe",
    ),
    Tool(
        "run_curriculum",
        "python.helm.curriculum",
        "run_curriculum",
        "measurement",
        "score a climber on the 5-tier graded ladder",
        "safe",
    ),
    Tool(
        "run_public_bench",
        "python.helm.public_bench",
        "run_public_bench",
        "measurement",
        "run problems vs a generator; verify hidden asserts in a subprocess",
        "guarded",  # executes candidate code in a subprocess
    ),
    Tool(
        "climb_on_board",
        "python.helm.substrate_climber",
        "climb_on_board",
        "measurement",
        "climb the numeric loomfn ladder, cross-face verified",
        "safe",
    ),
    Tool(
        "conformance",
        "python.scbe.polyglot_conformance",
        "conformance",
        "measurement",
        "compile + run a program across every polyglot backend",
        "guarded",  # compiles + executes generated code in external toolchains
    ),
    Tool(
        "benchmark",
        "python.scbe.rosetta",
        "benchmark",
        "measurement",
        "run songs across all faces; report Rosetta coverage",
        "safe",
    ),
    Tool(
        "pazaak_cards",
        "scripts.system.agentic_pazaak_board",
        "load_cards",
        "control",
        "load the Pazaak deck (+1/-1/+0 risk/value cards)",
        "safe",
    ),
    Tool(
        "pazaak_lanes",
        "scripts.system.agentic_pazaak_board",
        "load_lanes",
        "control",
        "load task lanes (value/risk/verified/blocked/conflict)",
        "safe",
    ),
    Tool(
        "pazaak_bitboards",
        "scripts.system.agentic_pazaak_board",
        "bitboards",
        "measurement",
        "count task lanes into bitboards (high_value/risk/unverified/conflict)",
        "safe",
    ),
    Tool(
        "pazaak_recommend",
        "scripts.system.agentic_pazaak_board",
        "recommend_moves",
        "control",
        "recommend scored card moves across the task lanes (Pazaak counting)",
        "safe",
    ),
]

_BY_NAME: Dict[str, Tool] = {t.name: t for t in CATALOG}


def _resolve(tool: Tool) -> Optional[Callable[..., Any]]:
    """Lazily import the tool's module and resolve its callable (None if unavailable)."""
    try:
        obj: Any = importlib.import_module(tool.module)
        for part in tool.callable.split("."):
            obj = getattr(obj, part)
        return obj
    except Exception:
        return None


@dataclass
class Toolkit:
    """The governed, sealed toolbox: list, resolve, and invoke any cataloged tool."""

    tools: List[Tool] = field(default_factory=lambda: list(CATALOG))
    transcript: List[dict] = field(default_factory=list)
    nonce: str = field(default_factory=lambda: secrets.token_hex(8))  # binds this session's seal chain

    def by_name(self, name: str) -> Optional[Tool]:
        return next((t for t in self.tools if t.name == name), None)

    def list(self, domain: Optional[str] = None) -> List[Tool]:
        return [t for t in self.tools if domain is None or t.domain == domain]

    def domains(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for t in self.tools:
            out[t.domain] = out.get(t.domain, 0) + 1
        return out

    def available(self) -> Dict[str, bool]:
        """Which tools actually import on this box (deps present)."""
        return {t.name: _resolve(t) is not None for t in self.tools}

    def invoke(self, name: str, *args: Any, confirm: Optional[str] = None, **kwargs: Any) -> dict:
        """Call a tool through the gate; seal the receipt. Tools compose: pass result_obj along."""
        tool = self.by_name(name)
        rec: dict = {
            "hop": len(self.transcript) + 1,
            "tool": name,
            "args": (repr(args) + (" " + repr(kwargs) if kwargs else ""))[:_RESULT_CAP],
            "decision": "",
            "result": "",
        }
        result_obj: Any = None
        fn = _resolve(tool) if tool else None
        text = " ".join(str(a) for a in args) + " " + " ".join(str(v) for v in kwargs.values())
        if tool is None:
            rec.update(decision="NO_TOOL", result="no tool %r" % name)
        elif fn is None:
            rec.update(decision="UNAVAILABLE", result="module %s not importable here" % tool.module)
        elif _DESTRUCTIVE.search(text):
            rec.update(decision="REFUSED", result="destructive content in args blocked")
        elif tool.safety == "guarded" and not confirm:
            rec.update(decision="NEEDS_CONFIRM", result="guarded tool; pass confirm='<reason>'")
        else:
            try:
                result_obj = fn(*args, **kwargs)
                rec.update(decision="ALLOWED", result=repr(result_obj)[:_RESULT_CAP])
            except Exception as e:  # a tool that errors is reported, never silently 'ok'
                rec.update(decision="ERROR", result="%s: %s" % (type(e).__name__, e))
        # forward-chain: each seal binds the prior seal (or the session nonce) + a digest of the
        # composition payload, so fabricating, reordering, or mutating any record fails verify().
        rec["prev"] = self.transcript[-1]["seal"] if self.transcript else self.nonce
        rec["result_hash"] = _digest(result_obj) if result_obj is not None else ""
        rec["seal"] = _seal(rec)
        self.transcript.append(rec)
        rec["result_obj"] = result_obj  # the live payload (its digest is sealed; the object itself is not)
        return rec

    def verify(self) -> bool:
        """Tamper-evident: the seal chain detects mutation, insertion, reordering, AND a swapped
        result_obj (its digest is sealed). A holder of the live Toolkit could recompute the chain --
        for cross-boundary integrity, sign the final seal with an external key."""
        prev = self.nonce
        for r in self.transcript:
            body = {k: v for k, v in r.items() if k not in ("seal", "result_obj")}
            if r.get("seal") != _seal(body):
                return False  # record mutated
            if r.get("prev") != prev:
                return False  # inserted / reordered / fabricated
            if "result_obj" in r and r["result_obj"] is not None and r.get("result_hash") != _digest(r["result_obj"]):
                return False  # composition payload swapped
            prev = r["seal"]
        return True

    def _safe_alternative(self, domain: Optional[str], exclude: str) -> Optional[str]:
        """A different SAFE, importable tool in the same domain -- a recovery suggestion."""
        avail = self.available()
        for t in self.tools:
            if t.domain == domain and t.name != exclude and t.safety == "safe" and avail.get(t.name):
                return t.name
        return None

    def diagnose(self, record: dict) -> dict:
        """Classify why a tool call failed and recommend the next SAFE move; seal the diagnosis.

        Governance/environment failures are classified by the gate decision; a confirmation-required
        failure is NEVER auto-retried (retry_safe=False) -- it surfaces the confirm requirement. The
        diagnosis is appended to the same sealed chain, so the failure + its diagnosis are auditable.
        """
        decision = record.get("decision")
        tool = record.get("tool", "")
        domain = self.by_name(tool).domain if self.by_name(tool) else None
        if decision == "NEEDS_CONFIRM":
            cause, retry_safe = "needs_confirm", False
            recovery = (
                "guarded tool: re-invoke %r WITH confirm='<reason>'. Do NOT auto-retry -- surface to a human/policy."
                % tool
            )
        elif decision == "REFUSED":
            cause, retry_safe = "refused_destructive", False
            recovery = "blocked by the never-delete screen. Remove the destructive content; do NOT retry."
        elif decision == "UNAVAILABLE":
            alt = self._safe_alternative(domain, tool)
            cause, retry_safe = "unavailable_dependency", bool(alt)
            recovery = (
                ("dependency missing here; use a same-domain available tool: %r" % alt)
                if alt
                else "no available same-domain alternative; install the dep or pick another domain."
            )
        elif decision == "NO_TOOL":
            cause, retry_safe = "unknown_tool", False
            recovery = "no tool named %r; consult toolkit.list() for the catalog." % tool
        elif decision == "ERROR":
            alt = self._safe_alternative(domain, tool)
            cause, retry_safe = "tool_error", False
            recovery = "the tool raised (%s). Check args; or try %r." % (str(record.get("result", ""))[:70], alt)
        else:
            ro = record.get("result_obj")
            if isinstance(ro, dict) and ro.get("completed") is False and ro.get("stuck_at"):
                cause, retry_safe = "step_drift", False
                recovery = (
                    "stepwise drifted at step %r -- offload that step to a deterministic calc tool "
                    "(sieve_calc) so the model only judges." % ro.get("stuck_at")
                )
            else:
                cause, retry_safe, recovery = "none", True, "no failure"
        diag = {
            "hop": len(self.transcript) + 1,
            "diagnose": tool,
            "from_decision": decision,
            "cause": cause,
            "recovery": recovery,
            "retry_safe": retry_safe,
            "prev": self.transcript[-1]["seal"] if self.transcript else self.nonce,
        }
        diag["seal"] = _seal(diag)
        self.transcript.append(diag)
        return diag


def default_toolkit() -> Toolkit:
    return Toolkit()


def main(argv: Optional[List[str]] = None) -> int:
    tk = default_toolkit()
    avail = tk.available()
    n_ok = sum(1 for v in avail.values() if v)
    print("TOOLKIT  %d tools across %d domains; %d importable on this box\n" % (len(tk.tools), len(tk.domains()), n_ok))
    print("  domains:", tk.domains())
    print("\n  sample governed + sealed calls:")
    for name, args, kw in [("is_prime", (97,), {}), ("factorization", (360,), {}), ("place", ([1, 2, 3],), {})]:
        r = tk.invoke(name, *args, **kw)
        print("    %-14s %-10s %s" % (name, r["decision"], r["result"]))
    # a guarded tool without confirm, and a destructive arg
    print("    %-14s %-10s %s" % ("run_level*", tk.invoke("run_level", [])["decision"], "(needs confirm)"))
    print("    %-14s %-10s %s" % ("is_prime+rm", tk.invoke("is_prime", "rm -rf /")["decision"], "(destructive arg)"))
    print("\n  transcript sealed + tamper-evident:", tk.verify())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
