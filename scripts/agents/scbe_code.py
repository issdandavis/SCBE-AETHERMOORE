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
LOOKUP_PATH = REPO_ROOT / "artifacts" / "cross_language_lookup" / "full_cross_language_lookup.json"

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
    source_lines = []
    if args.target == "python":
        sig = f"def {program.fn_name}({', '.join(program.arg_names)}):"
        source_lines.append(sig)
        for line in program.body_lines:
            source_lines.append("    " + line)
    elif args.target == "typescript":
        sig = f"export function {program.fn_name}({', '.join(a + ': number' for a in program.arg_names)}): number | null {{"
        source_lines.append(sig)
        for line in program.body_lines:
            source_lines.append("  " + line)
        source_lines.append("}")
    else:  # go
        sig = f"func {program.fn_name}({', '.join(a + ' float64' for a in program.arg_names)}) interface{{}} {{"
        source_lines.append(sig)
        for line in program.body_lines:
            source_lines.append("\t" + line)
        source_lines.append("}")
    source = "\n".join(source_lines) + "\n"

    bijection = disassemble(source)
    payload = {
        "target": args.target,
        "fn_name": program.fn_name,
        "arg_names": program.arg_names,
        "op_trace": program.op_trace,
        "round_trip_ok": [op for op, _ in program.op_trace] == [op for op, _ in bijection],
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
    return [token.strip().lower() for token in spec.replace(",", " ").split() if token.strip()]


def _ops_for_expression(expr: str) -> List[str]:
    key = expr.strip().lower().replace(" ", "")
    known = {
        "abs_add": ["abs", "abs", "add"],
        "abs(a)+abs(b)": ["abs", "abs", "add"],
        "|a|+|b|": ["abs", "abs", "add"],
        "abs(left)+abs(right)": ["abs", "abs", "add"],
    }
    if key not in known:
        raise ValueError(f"unknown CA expression {expr!r}; use --ops for explicit op names")
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
        "compile_hint": f"compile-ca --opcodes \"{' '.join(hex_sequence)}\"",
        "source": "python.scbe.ca_opcode_table.OP_TABLE",
    }
    print(json.dumps(payload, indent=2) if args.json else payload["hex"])
    return 0


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
        print(f"target {target!r} not in lexicon entry; valid: {valid}", file=sys.stderr)
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
            print(f"unknown stage6 kind {args.kind!r}; valid: {sorted(PREFIX_ORDER)}", file=sys.stderr)
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
            {"kind": k, "tokens": list(PREFIX_ORDER[k]), "forced_prefix": build_prefix(k)} for k in kinds
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

    model_id = args.model or os.environ.get("SCBE_CODE_MODEL", "Qwen/Qwen2.5-Coder-1.5B-Instruct")
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
    text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    out = model.generate(
        **inputs,
        max_new_tokens=args.max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )
    n_in = inputs["input_ids"].shape[1]
    response = tokenizer.decode(out[0][n_in:], skip_special_tokens=True)
    print(json.dumps({"ok": True, "model_id": model_id, "kind": None, "response": response}, indent=2))
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
    parser = argparse.ArgumentParser(prog="scbe_code", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ca = sub.add_parser("compile-ca", help="CA opcode bytes -> source")
    p_ca.add_argument("--opcodes", required=True, help='e.g. "0x00 0x0B 0x09"')
    p_ca.add_argument("--target", choices=["python", "typescript", "go"], default="python")
    p_ca.add_argument("--fn", default="tongue_fn")
    p_ca.add_argument("--args", default="", help="comma-separated arg names")
    p_ca.add_argument("--json", action="store_true")
    p_ca.set_defaults(func=cmd_compile_ca)

    p_ca_plan = sub.add_parser("ca-plan", help="CA op names / known expressions -> exact opcode bytes")
    p_ca_plan.add_argument("--ops", default="", help='comma/space-separated names, e.g. "abs,abs,add"')
    p_ca_plan.add_argument("--expr", default="", help='known expression alias, e.g. "abs(a)+abs(b)" or "abs_add"')
    p_ca_plan.add_argument("--json", action="store_true")
    p_ca_plan.set_defaults(func=cmd_ca_plan)

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

    p_man = sub.add_parser("manifest", help="emit stage6 forced-prefix manifest (no model)")
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
