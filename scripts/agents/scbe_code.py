#!/usr/bin/env python3
"""SCBE local code-generation CLI — bijective, sandbox-safe, no-network by default.

Three operating modes, no LLM required for the first two:

1. ``tongue``  — Compile CA opcode bytes (the Cassisivadan stack-machine ISA)
   into source code for a target language using ``python.scbe.tongue_isa``.
   Bijective via the trailing ``# opname (0xHH)`` trace comments and the
   STIB binary canonical form.

2. ``lookup``  — Render a single 64-op lexicon entry from
   ``artifacts/cross_language_lookup/full_cross_language_lookup.json`` for any
   tongue (KO/AV/RU/CA/UM/DR) or extra target (GO/ZI). No model load.

3. ``llm``     — Optional. Loads a small instruct model (default
   ``Qwen/Qwen2.5-Coder-1.5B-Instruct``) only when explicitly invoked, only
   if torch+transformers are importable, and ALWAYS routes prompts whose id
   matches a known stage6 kind through the production
   ``src/governance/stage6_constrained_decoding.py`` shim. If the import
   fails, ``llm`` mode degrades to printing the forced-prefix manifest a
   downstream tool could feed any external model.

Subcommands
-----------
- ``compile-ca``       bytes → source (tongue mode)
- ``ca-plan``          op names / known expressions → exact CA opcode bytes
- ``render-op``        op-name + args → lexicon template (lookup mode)
- ``manifest``         emit stage6 forced-prefix manifest as JSON (no model)
- ``generate``         run llm-mode generation OR fall back to manifest
- ``apply``            pipe a unified diff through ``safe_apply.py``

The ``apply`` subcommand is the ONLY path that mutates the working tree, and
it does so via the sandbox harness (worktree + smoke + replay). Nothing here
auto-applies generated output — you have to ask for ``apply`` explicitly.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
LOOKUP_PATH = (
    REPO_ROOT
    / "artifacts"
    / "cross_language_lookup"
    / "full_cross_language_lookup.json"
)

# Make repo importable for ``python.scbe.*`` and ``src.governance.*``.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Mode 1 — tongue: CA opcode bytes → source via tongue_isa dispatcher.
# ---------------------------------------------------------------------------


def _parse_opcode_bytes(spec: str) -> List[int]:
    """Parse a comma/whitespace separated list of bytes; supports 0x.. and decimal."""
    out: List[int] = []
    for raw in spec.replace(",", " ").split():
        token = raw.strip()
        if not token:
            continue
        base = 16 if token.lower().startswith("0x") else 10
        value = int(token, base)
        if not 0 <= value <= 0xFF:
            raise ValueError(f"opcode byte out of range: {token}")
        out.append(value)
    return out


def _wrap_program_source(program) -> str:
    """Wrap a CompiledProgram's body lines in the target language's function syntax.

    Single source of truth for every target so compile-ca and compile-prime stay
    in lockstep (python/typescript/go imperative; c imperative array stack;
    haskell let/in over the threaded pure-transform bindings).
    """
    from python.scbe.tongue_isa import wrap_program_source

    return wrap_program_source(program)


def cmd_compile_ca(args: argparse.Namespace) -> int:
    from python.scbe.tongue_isa import compile_ca_tokens, disassemble

    tokens = _parse_opcode_bytes(args.opcodes)
    arg_names = [a for a in (args.args or "").split(",") if a.strip()]
    program = compile_ca_tokens(
        tokens,
        target=args.target,
        fn_name=args.fn,
        arg_names=arg_names or None,
    )
    source = _wrap_program_source(program)

    bijection = disassemble(source)
    payload = {
        "target": args.target,
        "fn_name": program.fn_name,
        "arg_names": program.arg_names,
        "op_trace": program.op_trace,
        "round_trip_ok": [op for op, _ in program.op_trace]
        == [op for op, _ in bijection],
        "source": source,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(source, end="")
        if not payload["round_trip_ok"]:
            print("# WARN: bijection round-trip mismatch", file=sys.stderr)
            return 2
    return 0


def _ca_name_index() -> Dict[str, int]:
    from python.scbe.ca_opcode_table import OP_TABLE

    return {entry.name.lower(): op_id for op_id, entry in OP_TABLE.items()}


def _parse_ca_ops(spec: str) -> List[str]:
    return [
        token.strip().lower()
        for token in spec.replace(",", " ").split()
        if token.strip()
    ]


def _ops_for_expression(expr: str) -> List[str]:
    key = expr.strip().lower().replace(" ", "")
    known = {
        "abs_add": ["abs", "abs", "add"],
        "abs(a)+abs(b)": ["abs", "abs", "add"],
        "|a|+|b|": ["abs", "abs", "add"],
        "abs(left)+abs(right)": ["abs", "abs", "add"],
    }
    if key not in known:
        raise ValueError(
            f"unknown CA expression {expr!r}; use --ops for explicit op names"
        )
    return known[key]


def cmd_ca_plan(args: argparse.Namespace) -> int:
    """Resolve CA operation names to canonical opcode bytes without model recall."""
    names = _ops_for_expression(args.expr) if args.expr else _parse_ca_ops(args.ops)
    if not names:
        print("provide --ops or --expr", file=sys.stderr)
        return 2

    index = _ca_name_index()
    unknown = [name for name in names if name not in index]
    if unknown:
        print(f"unknown CA op(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    opcodes = [index[name] for name in names]
    hex_sequence = [f"0x{op:02X}" for op in opcodes]
    payload = {
        "tongue": "CA",
        "ops": names,
        "opcodes": opcodes,
        "hex_sequence": hex_sequence,
        "hex": ", ".join(hex_sequence),
        "compile_hint": f"compile-ca --opcodes \"{' '.join(hex_sequence)}\" --args a,b",
        "source": "python.scbe.ca_opcode_table.OP_TABLE",
    }
    print(json.dumps(payload, indent=2) if args.json else payload["hex"])
    return 0


def cmd_prime_plan(args: argparse.Namespace) -> int:
    """Resolve CA operation names to canonical prime-coded IR."""
    from python.scbe.prime_ir import prime_plan_from_ops

    names = _ops_for_expression(args.expr) if args.expr else _parse_ca_ops(args.ops)
    if not names:
        print("provide --ops or --expr", file=sys.stderr)
        return 2

    try:
        payload = prime_plan_from_ops(names)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    payload["compile_prime_hint"] = (
        f"compile-prime --primes \"{payload['prime_tape']}\" --args a,b"
    )
    payload["compile_ca_hint"] = (
        f"compile-ca --opcodes \"{' '.join(payload['hex_sequence'])}\" --args a,b"
    )
    print(json.dumps(payload, indent=2) if args.json else payload["prime_tape"])
    return 0


def cmd_compile_prime(args: argparse.Namespace) -> int:
    """Compile a prime-coded CA program into target-language source."""
    from python.scbe.prime_ir import decode_primes_to_opcodes, parse_prime_sequence

    try:
        primes = parse_prime_sequence(args.primes)
        opcodes = decode_primes_to_opcodes(primes)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    ca_args = argparse.Namespace(
        opcodes=" ".join(f"0x{op:02X}" for op in opcodes),
        target=args.target,
        fn=args.fn,
        args=args.args,
        json=args.json,
    )
    if not args.json:
        return cmd_compile_ca(ca_args)

    from python.scbe.tongue_isa import compile_ca_tokens, disassemble

    arg_names = [a for a in (args.args or "").split(",") if a.strip()]
    program = compile_ca_tokens(
        opcodes,
        target=args.target,
        fn_name=args.fn,
        arg_names=arg_names or None,
    )
    source = _wrap_program_source(program)

    payload = {
        "target": args.target,
        "fn_name": program.fn_name,
        "arg_names": program.arg_names,
        "prime_sequence": primes,
        "opcodes": opcodes,
        "hex_sequence": [f"0x{op:02X}" for op in opcodes],
        "op_trace": program.op_trace,
        "round_trip_ok": [op for op, _ in program.op_trace]
        == [op for op, _ in disassemble(source)],
        "source": source,
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["round_trip_ok"] else 2


def cmd_copilot_route(args: argparse.Namespace) -> int:
    """Return a deterministic route card for weak coding agents."""
    from python.scbe.copilot_router import build_copilot_route_card

    names = _ops_for_expression(args.expr) if args.expr else _parse_ca_ops(args.ops)
    if not names:
        print("provide --ops or --expr", file=sys.stderr)
        return 2

    arg_names = [arg for arg in (args.args or "").split(",") if arg.strip()]
    try:
        card = build_copilot_route_card(
            names,
            target=args.target,
            fn_name=args.fn,
            arg_names=arg_names,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    payload = card.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            "\n".join(
                command["name"]
                + ": "
                + (
                    " ".join(str(part) for part in command["argv"])
                    if "argv" in command
                    else str(command["purpose"])
                )
                for command in payload["next_commands"]
            )
        )
    return 0


def cmd_lint_prime_shape(args: argparse.Namespace) -> int:
    """Require source to carry a valid prime-opcode shape witness."""
    from python.scbe.prime_shape_gate import audit_prime_opcode_shape

    if args.source_file:
        source = Path(args.source_file).read_text(encoding="utf-8")
    else:
        source = args.content if args.content is not None else sys.stdin.read()
    audit = audit_prime_opcode_shape(
        source, expected_primes=args.expected_primes or None
    )
    if args.json:
        print(json.dumps(audit.to_dict(), indent=2))
    else:
        print(f"{audit.verdict}: {'ok' if audit.ok else '; '.join(audit.problems)}")
    return 0 if audit.ok else 1


def cmd_lint_rosetta_control_shape(args: argparse.Namespace) -> int:
    """Require bounded-control source to match its compiler-owned scaffold."""
    from python.scbe.rosetta_control_gate import audit_rosetta_control_shape

    if args.source_file:
        source = Path(args.source_file).read_text(encoding="utf-8")
    else:
        source = args.content if args.content is not None else sys.stdin.read()
    audit = audit_rosetta_control_shape(
        source,
        expression=args.expr,
        target=args.target or None,
        fn_name=args.fn or None,
        expected_primes=args.expected_primes or None,
    )
    if args.json:
        print(json.dumps(audit.to_dict(), indent=2))
    else:
        print(f"{audit.verdict}: {'ok' if audit.ok else '; '.join(audit.problems)}")
    return 0 if audit.ok else 1


def cmd_ingest_rosetta_control_source(args: argparse.Namespace) -> int:
    """Ingress generated bounded-control source back into the shared control tape."""
    from python.scbe.rosetta_control_ingress import ingest_rosetta_control_source

    if args.source_file:
        source = Path(args.source_file).read_text(encoding="utf-8")
    else:
        source = args.content if args.content is not None else sys.stdin.read()
    ingress = ingest_rosetta_control_source(
        source,
        expected_primes=args.expected_primes or None,
    )
    if args.json:
        print(json.dumps(ingress.to_dict(), indent=2))
    else:
        print(
            f"{ingress.verdict}: "
            f"{ingress.to_dict()['prime_tape'] if ingress.ok else '; '.join(ingress.problems)}"
        )
    return 0 if ingress.ok else 1


def cmd_compile_python_control(args: argparse.Namespace) -> int:
    """Lower supported Python source into the shared Rosetta control tape."""
    from python.scbe.rosetta_frontend import (
        LoweringError,
        compile_python_control_source,
        frontend_summary,
        parse_constants,
    )

    if args.source_file:
        source = Path(args.source_file).read_text(encoding="utf-8")
    else:
        source = args.content if args.content is not None else sys.stdin.read()
    targets = [
        target.strip()
        for target in (args.targets or "").replace(";", ",").split(",")
        if target.strip()
    ]
    try:
        frontend = compile_python_control_source(
            source,
            constants=parse_constants(args.const or []),
            fn_name=args.fn or None,
            targets=targets,
            output_fn=args.output_fn or None,
            run=args.run,
        )
    except LoweringError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(frontend.to_dict(), indent=2))
    else:
        print(frontend_summary(frontend))
    return 0 if not frontend.control_node.problems else 1


def cmd_rosetta_node(args: argparse.Namespace) -> int:
    """Compile one canonical CA/prime route into many language lenses."""
    from python.scbe.prime_ir import decode_primes_to_opcodes, parse_prime_sequence
    from python.scbe.rosetta_compiler import build_rosetta_node

    try:
        if args.primes:
            opcodes = decode_primes_to_opcodes(parse_prime_sequence(args.primes))
        else:
            names = (
                _ops_for_expression(args.expr) if args.expr else _parse_ca_ops(args.ops)
            )
            if not names:
                print("provide --primes, --ops, or --expr", file=sys.stderr)
                return 2
            index = _ca_name_index()
            unknown = [name for name in names if name not in index]
            if unknown:
                print(f"unknown CA op(s): {', '.join(unknown)}", file=sys.stderr)
                return 2
            opcodes = [index[name] for name in names]
        targets = [
            target.strip()
            for target in (args.targets or "").replace(";", ",").split(",")
            if target.strip()
        ]
        arg_names = [arg.strip() for arg in (args.args or "").split(",") if arg.strip()]
        run_values = None
        if args.run:
            run_values = _parse_numeric_values(args.values)
            if len(run_values) != len(arg_names):
                print(
                    f"--values count ({len(run_values)}) must match --args count ({len(arg_names)})",
                    file=sys.stderr,
                )
                return 2
        node = build_rosetta_node(
            opcodes,
            targets=targets,
            fn_name=args.fn,
            arg_names=arg_names,
            run_values=run_values,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(node.to_dict(), indent=2))
    else:
        print(f"prime_tape: {' '.join(str(prime) for prime in node.prime_sequence)}")
        print(f"shortest_target: {node.shortest_target}")
        print(f"shortest_runnable_target: {node.shortest_runnable_target}")
        for artifact in node.artifacts:
            print(
                f"{artifact.target}: chars={artifact.source_chars} "
                f"round_trip={artifact.round_trip_ok} runtime={artifact.runtime.status}"
            )
    return 0 if not node.problems else 1


def cmd_rosetta_control_node(args: argparse.Namespace) -> int:
    """Compile a bounded Tier-2 program across control-capable language lenses."""
    from python.scbe.rosetta_control import build_rosetta_control_node

    targets = [
        target.strip()
        for target in (args.targets or "").replace(";", ",").split(",")
        if target.strip()
    ]
    try:
        node = build_rosetta_control_node(
            args.expr,
            targets=targets,
            fn_name=args.fn,
            run=args.run,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(node.to_dict(), indent=2))
    else:
        print(f"value: {node.value}")
        print(f"prime_tape: {node.control_tape.to_dict()['prime_tape']}")
        print(f"runtime_consensus_ok: {node.runtime_consensus_ok}")
        for artifact in node.artifacts:
            print(
                f"{artifact.target}: chars={artifact.source_chars} "
                f"runtime={artifact.runtime.status}"
            )
    return 0 if not node.problems else 1


def cmd_chem_code(args: argparse.Namespace) -> int:
    """Run the bounded ChemCode research language."""
    from python.scbe.chem_code import run_chem_code

    if args.source_file:
        source = Path(args.source_file).read_text(encoding="utf-8")
    else:
        source = args.content if args.content is not None else sys.stdin.read()

    result = run_chem_code(
        source,
        fuel=args.fuel,
        compile_control=not args.no_control_projection,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"verdict: {result.safety_verdict}")
        print(f"ok: {result.ok}")
        if result.problems:
            print(f"problems: {'; '.join(result.problems)}")
        print(f"events: {len(result.events)}")
        print(f"fuel: {result.fuel_used}/{result.fuel_limit}")
        print(f"control_prime_tape: {result.control_prime_tape}")
    return 0 if result.ok else 1


def _parse_numeric_values(spec: str) -> List[float]:
    values = [
        token.strip() for token in spec.replace(",", " ").split() if token.strip()
    ]
    if not values:
        raise ValueError("--run requires --values")
    return [float(value) for value in values]


# ---------------------------------------------------------------------------
# Mode 2 — lookup: render a single lexicon entry (no model).
# ---------------------------------------------------------------------------


def _load_lookup() -> Dict[str, Any]:
    if not LOOKUP_PATH.exists():
        raise FileNotFoundError(f"missing lookup artifact: {LOOKUP_PATH}")
    with LOOKUP_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _find_op(lookup: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    """Locate an op by name (case-insensitive) or hex/decimal id."""
    needle = key.strip()
    if needle.lower().startswith("0x"):
        op_id = int(needle, 16)
        return next((e for e in lookup["lexicon"] if e["op_id"] == op_id), None)
    if needle.isdigit():
        op_id = int(needle, 10)
        return next((e for e in lookup["lexicon"] if e["op_id"] == op_id), None)
    lower = needle.lower()
    return next((e for e in lookup["lexicon"] if e["name"].lower() == lower), None)


def cmd_render_op(args: argparse.Namespace) -> int:
    lookup = _load_lookup()
    entry = _find_op(lookup, args.op)
    if entry is None:
        print(f"unknown op {args.op!r}", file=sys.stderr)
        return 2
    code_map = entry.get("code", {})
    target = args.target.upper()
    template = code_map.get(target)
    if template is None:
        valid = sorted(k for k in code_map if not k.endswith("_inherits_from"))
        print(
            f"target {target!r} not in lexicon entry; valid: {valid}", file=sys.stderr
        )
        return 2

    a = args.a
    b = args.b if args.b is not None else "_"
    rendered = template.replace("{a}", str(a)).replace("{b}", str(b))

    payload = {
        "op_id": entry["op_id"],
        "op_hex": entry["op_hex"],
        "name": entry["name"],
        "band": entry.get("band"),
        "target": target,
        "template": template,
        "rendered": rendered,
        "note": entry.get("note", ""),
    }
    print(json.dumps(payload, indent=2) if args.json else rendered)
    return 0


# ---------------------------------------------------------------------------
# Mode 3 — manifest: stage6 forced-prefix prompt manifest (no model).
# ---------------------------------------------------------------------------


def cmd_manifest(args: argparse.Namespace) -> int:
    from src.governance.stage6_constrained_decoding import (
        PREFIX_ORDER,
        SYSTEM_PROMPT,
        build_prefix,
        kind_from_id,
    )

    if args.kind:
        if args.kind not in PREFIX_ORDER:
            print(
                f"unknown stage6 kind {args.kind!r}; valid: {sorted(PREFIX_ORDER)}",
                file=sys.stderr,
            )
            return 2
        kinds = [args.kind]
    elif args.prompt_id:
        detected = kind_from_id(args.prompt_id)
        if detected is None:
            print(f"no stage6 kind matched id {args.prompt_id!r}", file=sys.stderr)
            return 2
        kinds = [detected]
    else:
        kinds = sorted(PREFIX_ORDER)

    manifest = {
        "system_prompt": SYSTEM_PROMPT,
        "kinds": [
            {
                "kind": k,
                "tokens": list(PREFIX_ORDER[k]),
                "forced_prefix": build_prefix(k),
            }
            for k in kinds
        ],
    }
    print(json.dumps(manifest, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Mode 3' — generate: lazy-load LLM, route stage6 ids through the shim.
# ---------------------------------------------------------------------------


def _try_load_llm(model_id: str):
    """Return (model, tokenizer) or raise; imports are local on purpose."""
    try:
        import torch  # noqa: F401
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as e:
        raise RuntimeError(f"LLM deps not available: {e}") from e

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto")
    return model, tokenizer


def cmd_generate(args: argparse.Namespace) -> int:
    """Optional LLM mode. Falls back to manifest if model can't load.

    Use ``SCBE_CODE_MODEL`` to override the default model id, or pass
    ``--model``. Prompt ids matching a stage6 kind get the production
    forced-prefix shim; everything else gets a plain chat-template call.
    """
    from src.governance.stage6_constrained_decoding import (
        kind_from_id,
        stage6_constrained_response,
    )

    model_id = args.model or os.environ.get(
        "SCBE_CODE_MODEL", "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    )
    if args.no_llm:
        print(json.dumps({"ok": False, "skipped": True, "reason": "no_llm"}, indent=2))
        return 0

    try:
        model, tokenizer = _try_load_llm(model_id)
    except RuntimeError as e:
        # Graceful degrade: still emit the stage6 manifest the caller can use.
        from src.governance.stage6_constrained_decoding import (
            PREFIX_ORDER,
            build_prefix,
        )

        kind = kind_from_id(args.prompt_id or "")
        payload = {
            "ok": False,
            "model_loaded": False,
            "model_id": model_id,
            "error": str(e),
            "fallback_manifest": {
                "kind": kind,
                "forced_prefix": build_prefix(kind) if kind else None,
                "available_kinds": sorted(PREFIX_ORDER),
            },
        }
        print(json.dumps(payload, indent=2))
        return 0

    prompt_id = args.prompt_id or ""
    user_prompt = args.prompt or ""
    kind = kind_from_id(prompt_id)
    if kind is not None:
        verdict = stage6_constrained_response(
            model,
            tokenizer,
            {"id": prompt_id, "prompt": user_prompt, "required": [], "forbidden": []},
            max_new_tokens=args.max_new_tokens,
        )
        print(json.dumps(verdict, indent=2, ensure_ascii=False))
        return 0 if verdict.get("ok") else 1

    # Non-stage6: plain chat template, greedy.
    msgs = [{"role": "user", "content": user_prompt}]
    text = tokenizer.apply_chat_template(
        msgs, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    out = model.generate(
        **inputs,
        max_new_tokens=args.max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )
    n_in = inputs["input_ids"].shape[1]
    response = tokenizer.decode(out[0][n_in:], skip_special_tokens=True)
    print(
        json.dumps(
            {"ok": True, "model_id": model_id, "kind": None, "response": response},
            indent=2,
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Mode 4 — apply: explicit gate, never auto.
# ---------------------------------------------------------------------------


def cmd_apply(args: argparse.Namespace) -> int:
    from scripts.agents.safe_apply import apply_patch_safely

    if args.patch_file:
        patch_text = Path(args.patch_file).read_text(encoding="utf-8")
    else:
        patch_text = sys.stdin.read()
    if not patch_text.strip():
        print(json.dumps({"ok": False, "error": "empty patch"}, indent=2))
        return 2

    result = apply_patch_safely(
        patch_text,
        smoke_cmd=args.smoke,
        smoke_timeout=args.smoke_timeout,
    )
    if args.dry_run and result.ok:
        result.applied = False
        result.error = "dry-run: smoke passed but main-tree apply skipped"
    print(result.to_json())
    return 0 if result.ok else 1


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scbe_code", description=__doc__.splitlines()[0]
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ca = sub.add_parser("compile-ca", help="CA opcode bytes -> source")
    p_ca.add_argument("--opcodes", required=True, help='e.g. "0x00 0x0B 0x09"')
    p_ca.add_argument(
        "--target",
        choices=["python", "typescript", "go", "c", "haskell"],
        default="python",
    )
    p_ca.add_argument("--fn", default="tongue_fn")
    p_ca.add_argument("--args", default="", help="comma-separated arg names")
    p_ca.add_argument("--json", action="store_true")
    p_ca.set_defaults(func=cmd_compile_ca)

    p_ca_plan = sub.add_parser(
        "ca-plan", help="CA op names / known expressions -> exact opcode bytes"
    )
    p_ca_plan.add_argument(
        "--ops", default="", help='comma/space-separated names, e.g. "abs,abs,add"'
    )
    p_ca_plan.add_argument(
        "--expr",
        default="",
        help='known expression alias, e.g. "abs(a)+abs(b)" or "abs_add"',
    )
    p_ca_plan.add_argument("--json", action="store_true")
    p_ca_plan.set_defaults(func=cmd_ca_plan)

    p_prime_plan = sub.add_parser(
        "prime-plan", help="CA op names / known expressions -> prime-coded IR"
    )
    p_prime_plan.add_argument(
        "--ops", default="", help='comma/space-separated names, e.g. "abs,abs,add"'
    )
    p_prime_plan.add_argument(
        "--expr",
        default="",
        help='known expression alias, e.g. "abs(a)+abs(b)" or "abs_add"',
    )
    p_prime_plan.add_argument("--json", action="store_true")
    p_prime_plan.set_defaults(func=cmd_prime_plan)

    p_compile_prime = sub.add_parser(
        "compile-prime", help="prime-coded CA program -> source"
    )
    p_compile_prime.add_argument(
        "--primes", required=True, help='ordered prime tape, e.g. "29 29 2"'
    )
    p_compile_prime.add_argument(
        "--target",
        choices=["python", "typescript", "go", "c", "haskell"],
        default="python",
    )
    p_compile_prime.add_argument("--fn", default="tongue_fn")
    p_compile_prime.add_argument("--args", default="", help="comma-separated arg names")
    p_compile_prime.add_argument("--json", action="store_true")
    p_compile_prime.set_defaults(func=cmd_compile_prime)

    p_copilot_route = sub.add_parser(
        "copilot-route",
        help="op names / known expressions -> route card for weak coding agents",
    )
    p_copilot_route.add_argument(
        "--ops", default="", help='comma/space-separated names, e.g. "abs,abs,add"'
    )
    p_copilot_route.add_argument(
        "--expr",
        default="",
        help='known expression alias, e.g. "abs(a)+abs(b)" or "abs_add"',
    )
    p_copilot_route.add_argument(
        "--target",
        choices=["python", "typescript", "go", "c", "haskell"],
        default="python",
    )
    p_copilot_route.add_argument("--fn", default="tongue_fn")
    p_copilot_route.add_argument("--args", default="", help="comma-separated arg names")
    p_copilot_route.add_argument("--json", action="store_true")
    p_copilot_route.set_defaults(func=cmd_copilot_route)

    p_lint_prime = sub.add_parser(
        "lint-prime-shape", help="validate source opcode trace -> prime tape shape"
    )
    p_lint_prime.add_argument(
        "--source-file", help="source file to inspect; stdin if omitted"
    )
    p_lint_prime.add_argument("--content", help="inline source text")
    p_lint_prime.add_argument(
        "--expected-primes",
        default="",
        help='ordered expected prime tape, e.g. "29 29 2"',
    )
    p_lint_prime.add_argument("--json", action="store_true")
    p_lint_prime.set_defaults(func=cmd_lint_prime_shape)

    p_lint_control = sub.add_parser(
        "lint-rosetta-control-shape",
        help="validate bounded-control source against its expression-owned scaffold",
    )
    p_lint_control.add_argument(
        "--expr",
        required=True,
        help='Tier-2 expression/program, e.g. "factorial(5)" or "gcd(48,18)"',
    )
    p_lint_control.add_argument(
        "--source-file", help="source file to inspect; stdin if omitted"
    )
    p_lint_control.add_argument("--content", help="inline source text")
    p_lint_control.add_argument(
        "--target",
        choices=["python", "typescript", "go", "c"],
        default="",
        help="optional control target; inferred from source if omitted",
    )
    p_lint_control.add_argument("--fn", default="", help="optional function name")
    p_lint_control.add_argument(
        "--expected-primes",
        default="",
        help="ordered expected control prime tape",
    )
    p_lint_control.add_argument("--json", action="store_true")
    p_lint_control.set_defaults(func=cmd_lint_rosetta_control_shape)

    p_ingest_control = sub.add_parser(
        "ingest-rosetta-control-source",
        help="validate generated bounded-control source and return its shared tape",
    )
    p_ingest_control.add_argument(
        "--source-file", help="source file to inspect; stdin if omitted"
    )
    p_ingest_control.add_argument("--content", help="inline source text")
    p_ingest_control.add_argument(
        "--expected-primes",
        default="",
        help="optional ordered expected control prime tape",
    )
    p_ingest_control.add_argument("--json", action="store_true")
    p_ingest_control.set_defaults(func=cmd_ingest_rosetta_control_source)

    p_python_control = sub.add_parser(
        "compile-python-control",
        help="lower a supported Python function into a Rosetta control node",
    )
    p_python_control.add_argument(
        "--source-file", help="Python source file; stdin if omitted"
    )
    p_python_control.add_argument("--content", help="inline Python source text")
    p_python_control.add_argument(
        "--fn", default="", help="function name when the source has multiple functions"
    )
    p_python_control.add_argument(
        "--const",
        action="append",
        default=[],
        help="specialize a scalar argument, e.g. --const n=5",
    )
    p_python_control.add_argument(
        "--targets",
        default="python,typescript,go,c",
        help="comma-separated control targets: python,typescript,go,c",
    )
    p_python_control.add_argument(
        "--output-fn",
        default="",
        help="generated output function name; defaults to the source function name",
    )
    p_python_control.add_argument(
        "--run", action="store_true", help="execute available runtime lanes"
    )
    p_python_control.add_argument("--json", action="store_true")
    p_python_control.set_defaults(func=cmd_compile_python_control)

    p_rosetta = sub.add_parser(
        "rosetta-node",
        help="compile one CA/prime program across language lenses and optionally run it",
    )
    p_rosetta.add_argument(
        "--primes", default="", help='ordered prime tape, e.g. "29 29 2"'
    )
    p_rosetta.add_argument(
        "--ops", default="", help='comma/space-separated names, e.g. "abs,abs,add"'
    )
    p_rosetta.add_argument(
        "--expr", default="", help='known expression alias, e.g. "abs(a)+abs(b)"'
    )
    p_rosetta.add_argument(
        "--targets",
        default="python,typescript,go,c,haskell",
        help="comma-separated targets: python,typescript,go,c,haskell",
    )
    p_rosetta.add_argument("--fn", default="tongue_fn")
    p_rosetta.add_argument("--args", default="", help="comma-separated arg names")
    p_rosetta.add_argument(
        "--values", default="", help="comma/space-separated runtime values"
    )
    p_rosetta.add_argument(
        "--run", action="store_true", help="execute available runtime lanes"
    )
    p_rosetta.add_argument("--json", action="store_true")
    p_rosetta.set_defaults(func=cmd_rosetta_node)

    p_rosetta_control = sub.add_parser(
        "rosetta-control-node",
        help="compile bounded Tier-2 branch/loop programs across language lenses",
    )
    p_rosetta_control.add_argument(
        "--expr",
        required=True,
        help='Tier-2 expression/program, e.g. "factorial(5)" or "gcd(48,18)"',
    )
    p_rosetta_control.add_argument(
        "--targets",
        default="python,typescript,go,c",
        help="comma-separated control targets: python,typescript,go,c",
    )
    p_rosetta_control.add_argument("--fn", default="control_fn")
    p_rosetta_control.add_argument(
        "--run", action="store_true", help="execute available runtime lanes"
    )
    p_rosetta_control.add_argument("--json", action="store_true")
    p_rosetta_control.set_defaults(func=cmd_rosetta_control_node)

    p_chem_code = sub.add_parser(
        "chem-code",
        help="run bounded Turing-complete ChemCode research programs",
    )
    p_chem_code.add_argument(
        "--source-file", help="ChemCode source file; stdin if omitted"
    )
    p_chem_code.add_argument("--content", help="inline ChemCode source text")
    p_chem_code.add_argument(
        "--fuel", type=int, default=200, help="max ChemCode statement fuel"
    )
    p_chem_code.add_argument(
        "--no-control-projection",
        action="store_true",
        help="skip Rosetta control prime-tape projection",
    )
    p_chem_code.add_argument("--json", action="store_true")
    p_chem_code.set_defaults(func=cmd_chem_code)

    p_op = sub.add_parser("render-op", help="render single lexicon op for a tongue")
    p_op.add_argument("--op", required=True, help="op name (e.g. add) or id (5 / 0x05)")
    p_op.add_argument(
        "--target",
        default="KO",
        help="KO|AV|RU|CA|UM|DR|GO|ZI (case-insensitive)",
    )
    p_op.add_argument("--a", default="a")
    p_op.add_argument("--b", default=None)
    p_op.add_argument("--json", action="store_true")
    p_op.set_defaults(func=cmd_render_op)

    p_man = sub.add_parser(
        "manifest", help="emit stage6 forced-prefix manifest (no model)"
    )
    p_man.add_argument("--kind", help="stage6 kind (e.g. resource_jump_cancel)")
    p_man.add_argument("--prompt-id", help="prompt id whose suffix selects a kind")
    p_man.set_defaults(func=cmd_manifest)

    p_gen = sub.add_parser("generate", help="optional LLM call; degrades to manifest")
    p_gen.add_argument("--prompt", default="", help="user prompt text")
    p_gen.add_argument("--prompt-id", default="", help="prompt id for stage6 routing")
    p_gen.add_argument("--model", default="", help="overrides $SCBE_CODE_MODEL")
    p_gen.add_argument("--max-new-tokens", type=int, default=240)
    p_gen.add_argument("--no-llm", action="store_true", help="skip model load entirely")
    p_gen.set_defaults(func=cmd_generate)

    p_app = sub.add_parser("apply", help="sandbox-apply a unified diff (explicit gate)")
    p_app.add_argument("--patch-file", help="patch path; stdin if omitted")
    p_app.add_argument("--smoke", help="smoke command run inside worktree")
    p_app.add_argument("--smoke-timeout", type=int, default=60)
    p_app.add_argument("--dry-run", action="store_true", help="never replay on main")
    p_app.set_defaults(func=cmd_apply)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
