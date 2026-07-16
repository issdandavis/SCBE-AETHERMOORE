"""STISA-backed opcode typewriter for Loom programs.

Loom's five core instructions are intentionally tiny.  This optional bridge
turns each instruction into a deterministic Cassisivadan/STISA lookup record so
an orchestration loop can be routed, inspected, and hash-receipted one
"keystroke" at a time without weakening Loom's standalone machine core.

The CA 64-op table and Loom control overlay share byte positions for some
control verbs.  Those collisions are namespaced and reported honestly: INC and
DEC are exact CA opcode matches, while JMP/OUT/HALT are Loom control overlays.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Mapping

from . import equiv
from . import machine as M

LOOM_TO_FLOW = {
    "inc": "inc",
    "dec": "dec",
    "jmp": "jmp",
    "out": "print",
    "halt": "halt",
}


@dataclass(frozen=True, slots=True)
class TypewriterKey:
    index: int
    loom_op: str
    flow_op: str
    opcode: int
    opcode_hex: str
    token: str
    namespace: str
    ca_name: str
    ca_aligned: bool
    register: str | None
    target: int | None
    trit: tuple[int, ...]
    features: tuple[float, ...]


def _tables():
    # Optional sibling bridge: machine.py remains dependency-free and standalone.
    from ..scbe.ca_opcode_table import get_ca_opcode
    from ..scbe.loomtongue import WORD_FOR_OP, _BYTE

    return get_ca_opcode, WORD_FOR_OP, _BYTE


def encode_typewriter(program: M.Program) -> tuple[TypewriterKey, ...]:
    """Encode a parsed Loom program as stable STISA/Cassisivadan keystrokes."""

    get_ca_opcode, word_for_op, flow_bytes = _tables()
    keys: list[TypewriterKey] = []
    for index, instruction in enumerate(program.instrs):
        flow_op = LOOM_TO_FLOW[instruction.op]
        opcode = int(flow_bytes[flow_op])
        ca_entry = get_ca_opcode(opcode)
        aligned = ca_entry.name == flow_op
        namespace = "ca-opcode" if aligned else "loom-control-overlay"
        keys.append(
            TypewriterKey(
                index=index,
                loom_op=instruction.op,
                flow_op=flow_op,
                opcode=opcode,
                opcode_hex=f"0x{opcode:02X}",
                token=word_for_op[flow_op],
                namespace=namespace,
                ca_name=ca_entry.name,
                ca_aligned=aligned,
                register=instruction.reg,
                target=instruction.target,
                trit=tuple(int(value) for value in ca_entry.trit.tolist()),
                features=tuple(float(value) for value in ca_entry.feat.tolist()),
            )
        )
    return tuple(keys)


def typewriter_receipt(
    source: str,
    init: Mapping[str, int] | None = None,
    *,
    max_steps: int = 100_000,
) -> dict:
    """Run and encode one Loom source, returning a hash-bound route receipt."""

    program = M.parse(source)
    run = M.run(program, dict(init or {}), max_steps=max_steps)
    keys = encode_typewriter(program)
    payload = [asdict(key) for key in keys]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    route_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "schema": "scbe.loom-typewriter.v1",
        "status": run.status,
        "steps": run.steps,
        "output": run.output,
        "registers": run.registers,
        "route_sha256": route_sha256,
        "keystroke_count": len(keys),
        "keystrokes": payload,
        "mirror": equiv.mirror_check(source, inits=[dict(init or {})]),
        "claim_boundary": (
            "STISA/CA features describe the underlying byte-table entry. "
            "Records in loom-control-overlay are namespaced semantic overlays, "
            "not claims that the CA opcode has the same operation name."
        ),
    }


def validate_typewriter_table() -> tuple[bool, list[str]]:
    """Validate coverage, byte uniqueness, and the two exact CA alignments."""

    get_ca_opcode, _word_for_op, flow_bytes = _tables()
    errors: list[str] = []
    if set(LOOM_TO_FLOW) != {"inc", "dec", "jmp", "out", "halt"}:
        errors.append("Loom core opcode coverage is incomplete")
    opcodes = [int(flow_bytes[name]) for name in LOOM_TO_FLOW.values()]
    if len(opcodes) != len(set(opcodes)):
        errors.append("Loom typewriter byte assignments collide")
    for op in ("inc", "dec"):
        entry = get_ca_opcode(int(flow_bytes[op]))
        if entry.name != op:
            errors.append(f"{op} must align with its CA opcode entry")
    return not errors, errors


__all__ = [
    "LOOM_TO_FLOW",
    "TypewriterKey",
    "encode_typewriter",
    "typewriter_receipt",
    "validate_typewriter_table",
]
