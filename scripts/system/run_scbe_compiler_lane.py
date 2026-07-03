#!/usr/bin/env python3
"""Run the SCBE compiler lane for a tiny CA program.

This is not a fake language face. It uses the existing CA opcode compiler and
STIB binary encoder:

  CA opcodes -> CompiledProgram -> STIB bytes -> source face -> Python exec

Default demo compiles `clamp(a,b,c)` from CA opcode 0x29 and executes it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(REPO / "python") not in sys.path:
    sys.path.insert(0, str(REPO / "python"))

from scbe.tongue_isa import compile_ca_tokens, disassemble, emit_compiled_program_source  # noqa: E402
from scbe.tongue_isa_binary import decode, encode, from_compiled  # noqa: E402


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_lane(opcodes: list[int], target: str, fn_name: str, arg_names: list[str], args: list[float]) -> dict[str, Any]:
    compiled = compile_ca_tokens(opcodes, target=target, fn_name=fn_name, arg_names=arg_names)
    stib = encode(from_compiled(compiled))
    stib_block = decode(stib)
    source = emit_compiled_program_source(compiled)
    recovered = disassemble(source)

    result: Any = None
    executed = False
    if target == "python":
        namespace: dict[str, Any] = {}
        exec(compile(source, f"<scbe-{fn_name}>", "exec"), namespace)  # noqa: S102 - explicit demo execution
        result = namespace[fn_name](*args)
        executed = True

    return {
        "schema": "scbe.compiler_lane.receipt.v1",
        "compiler_lane": "CA opcodes -> STIB -> Code Prism source -> execution",
        "target": target,
        "fn_name": fn_name,
        "arg_names": arg_names,
        "args": args,
        "opcodes_hex": [f"0x{x:02X}" for x in opcodes],
        "op_trace": [[op, name] for op, name in compiled.op_trace],
        "stib_hex": stib.hex(),
        "stib_sha256": _sha256(stib),
        "stib_decoded": {
            "tongue": stib_block.tongue,
            "fn_name": stib_block.fn_name,
            "arg_names": stib_block.arg_names,
            "opcodes_hex": [f"0x{x:02X}" for x in stib_block.opcodes],
        },
        "source_sha256": _sha256(source.encode("utf-8")),
        "source": source,
        "recovered_trace": [[op, name] for op, name in recovered],
        "round_trip_ok": recovered == compiled.op_trace and stib_block.opcodes == opcodes,
        "executed": executed,
        "result": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--opcodes", default="0x29", help="comma/space separated CA opcode bytes")
    parser.add_argument("--target", default="python")
    parser.add_argument("--fn", default="clamp_demo")
    parser.add_argument("--args", default="a,b,c")
    parser.add_argument("--values", default="12,0,10")
    parser.add_argument("--out", default="artifacts/ai_brain/compiler_lane_receipt.json")
    ns = parser.parse_args()

    opcodes = [int(x, 0) for x in ns.opcodes.replace(",", " ").split() if x.strip()]
    arg_names = [x.strip() for x in ns.args.split(",") if x.strip()]
    values = [float(x.strip()) for x in ns.values.split(",") if x.strip()]

    receipt = run_lane(opcodes, ns.target, ns.fn, arg_names, values)
    out = REPO / ns.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "receipt": str(out),
        "round_trip_ok": receipt["round_trip_ok"],
        "executed": receipt["executed"],
        "result": receipt["result"],
        "stib_sha256": receipt["stib_sha256"][:16],
        "source_sha256": receipt["source_sha256"][:16],
    }, indent=2, sort_keys=True))
    return 0 if receipt["round_trip_ok"] and (receipt["executed"] or ns.target != "python") else 2


if __name__ == "__main__":
    raise SystemExit(main())
