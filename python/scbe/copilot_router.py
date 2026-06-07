"""Deterministic route cards for weak coding agents.

The route card turns a small coding intent into mechanical handles:

    op names -> CA opcodes -> ordered prime tape -> STIB bytes
             -> semantic abacus receipt -> next safe commands

The LLM does not need to remember compiler syntax. It can ask for a route card,
then follow the command hints and receipts.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Sequence

from src.geoseed.prime_coordinate_abacus import build_prime_coordinate
from src.geoseed.semantic_abacus import build_semantic_abacus_receipt

from .prime_ir import prime_plan_from_ops
from .tongue_isa import SUPPORTED_TARGETS, supported_ca_ops
from .tongue_isa_binary import STIBBlock, encode as encode_stib

SCHEMA_VERSION = "scbe_agentic_copilot_route_v1"


@dataclass(frozen=True)
class CopilotOpRoute:
    """One opcode route row with both slot and prime coordinates."""

    step: int
    op_name: str
    opcode: int
    op_hex: str
    prime: int
    family: str
    route_lane: str
    opcode_slot_coordinate: dict[str, object]
    prime_coordinate: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CopilotRouteCard:
    """A deterministic command card a weak model can follow."""

    schema: str
    ops: tuple[str, ...]
    opcodes: tuple[int, ...]
    hex_sequence: tuple[str, ...]
    prime_sequence: tuple[int, ...]
    prime_tape: str
    target: str
    fn_name: str
    arg_names: tuple[str, ...]
    compile_supported: bool
    route_rows: tuple[CopilotOpRoute, ...]
    stib_sha256: str
    stib_semantic_abacus: dict[str, object]
    next_commands: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "ops": list(self.ops),
            "opcodes": list(self.opcodes),
            "hex_sequence": list(self.hex_sequence),
            "prime_sequence": list(self.prime_sequence),
            "prime_tape": self.prime_tape,
            "target": self.target,
            "fn_name": self.fn_name,
            "arg_names": list(self.arg_names),
            "compile_supported": self.compile_supported,
            "route_rows": [row.to_dict() for row in self.route_rows],
            "stib_sha256": self.stib_sha256,
            "stib_semantic_abacus": self.stib_semantic_abacus,
            "next_commands": [dict(command) for command in self.next_commands],
        }


def build_copilot_route_card(
    op_names: Sequence[str],
    *,
    target: str = "python",
    fn_name: str = "tongue_fn",
    arg_names: Sequence[str] = (),
) -> CopilotRouteCard:
    """Build a no-LLM route card for a CA opcode program."""
    if target not in SUPPORTED_TARGETS:
        raise ValueError(
            f"unsupported target {target!r}; pick one of {SUPPORTED_TARGETS}"
        )

    normalized_ops = tuple(name.strip().lower() for name in op_names if name.strip())
    if not normalized_ops:
        raise ValueError("at least one op is required")

    prime_plan = prime_plan_from_ops(normalized_ops)
    opcodes = tuple(int(opcode) for opcode in prime_plan["opcodes"])
    hex_sequence = tuple(str(value) for value in prime_plan["hex_sequence"])
    prime_sequence = tuple(int(prime) for prime in prime_plan["prime_sequence"])
    prime_tape = str(prime_plan["prime_tape"])
    args = tuple(arg.strip() for arg in arg_names if arg.strip())
    supported_ops = set(supported_ca_ops())
    compile_supported = all(name in supported_ops for name in normalized_ops)

    stib_bytes = encode_stib(
        STIBBlock(
            tongue="CA",
            fn_name=fn_name,
            arg_names=list(args),
            opcodes=list(opcodes),
        )
    )
    stib_receipt = build_semantic_abacus_receipt(
        stib_bytes,
        payload_label="stib-copilot-route",
        goal="account deterministic coding route",
        expected_tool="metrics.read",
    )

    rows = tuple(
        _build_route_row(step, name, opcode, prime)
        for step, (name, opcode, prime) in enumerate(
            zip(normalized_ops, opcodes, prime_sequence)
        )
    )
    return CopilotRouteCard(
        schema=SCHEMA_VERSION,
        ops=normalized_ops,
        opcodes=opcodes,
        hex_sequence=hex_sequence,
        prime_sequence=prime_sequence,
        prime_tape=prime_tape,
        target=target,
        fn_name=fn_name,
        arg_names=args,
        compile_supported=compile_supported,
        route_rows=rows,
        stib_sha256=hashlib.sha256(stib_bytes).hexdigest(),
        stib_semantic_abacus=_receipt_summary(stib_receipt.to_dict()),
        next_commands=_next_commands(
            prime_tape=prime_tape,
            target=target,
            fn_name=fn_name,
            arg_names=args,
            compile_supported=compile_supported,
        ),
    )


def _build_route_row(
    step: int, op_name: str, opcode: int, prime: int
) -> CopilotOpRoute:
    family = _opcode_family(opcode)
    slot_coordinate = build_prime_coordinate(opcode + 1).to_dict()
    prime_coordinate = build_prime_coordinate(prime).to_dict()
    lane = f"{family}.mod30:{prime_coordinate['residues']['mod30']}"
    return CopilotOpRoute(
        step=step,
        op_name=op_name,
        opcode=opcode,
        op_hex=f"0x{opcode:02X}",
        prime=prime,
        family=family,
        route_lane=lane,
        opcode_slot_coordinate=slot_coordinate,
        prime_coordinate=prime_coordinate,
    )


def _opcode_family(opcode: int) -> str:
    if 0x00 <= opcode <= 0x0F:
        return "arithmetic"
    if 0x10 <= opcode <= 0x1F:
        return "logic"
    if 0x20 <= opcode <= 0x2F:
        return "comparison"
    if 0x30 <= opcode <= 0x3F:
        return "aggregation"
    return "unknown"


def _receipt_summary(receipt: dict[str, object]) -> dict[str, object]:
    composition = receipt["composition"]
    assert isinstance(composition, dict)
    return {
        "schema_version": receipt["schema_version"],
        "payload_label": receipt["payload_label"],
        "payload_sha256": receipt["payload_sha256"],
        "byte_count": receipt["byte_count"],
        "bit_count": receipt["bit_count"],
        "prime_weighted_total": composition["prime_weighted_total"],
        "decision": receipt["decision"],
        "allowed": receipt["allowed"],
        "abacus_layer": receipt["abacus_layer"],
    }


def _next_commands(
    *,
    prime_tape: str,
    target: str,
    fn_name: str,
    arg_names: Sequence[str],
    compile_supported: bool,
) -> tuple[dict[str, object], ...]:
    args_spec = ",".join(arg_names)
    commands: list[dict[str, object]] = [
        {
            "name": "inspect-prime-route",
            "tool": "scbe_code copilot-route",
            "purpose": "rebuild this deterministic route card",
            "safe": True,
        }
    ]
    if compile_supported:
        commands.append(
            {
                "name": "compile-prime",
                "tool": "scbe_code compile-prime",
                "purpose": "emit target-language source from the ordered prime tape",
                "safe": True,
                "argv": [
                    "compile-prime",
                    "--primes",
                    prime_tape,
                    "--target",
                    target,
                    "--fn",
                    fn_name,
                    "--args",
                    args_spec,
                    "--json",
                ],
            }
        )
        commands.append(
            {
                "name": "lint-prime-shape",
                "tool": "scbe_code lint-prime-shape",
                "purpose": "verify emitted source still carries the same prime opcode shape",
                "safe": True,
                "argv": [
                    "lint-prime-shape",
                    "--expected-primes",
                    prime_tape,
                    "--json",
                ],
            }
        )
    else:
        commands.append(
            {
                "name": "compile-prime",
                "tool": "scbe_code compile-prime",
                "purpose": "blocked until every op has a target-language template",
                "safe": False,
                "reason": "route includes CA ops without compiler templates",
            }
        )
    return tuple(commands)


def known_expression_ops(expr: str) -> list[str]:
    """Resolve the small expression aliases a weak model can reliably ask for."""
    key = expr.strip().lower().replace(" ", "")
    known = {
        "abs_add": ["abs", "abs", "add"],
        "abs(a)+abs(b)": ["abs", "abs", "add"],
        "|a|+|b|": ["abs", "abs", "add"],
        "abs(left)+abs(right)": ["abs", "abs", "add"],
    }
    if key not in known:
        raise ValueError(f"unknown CA expression {expr!r}; use explicit op names")
    return known[key]


__all__ = [
    "SCHEMA_VERSION",
    "CopilotOpRoute",
    "CopilotRouteCard",
    "build_copilot_route_card",
    "known_expression_ops",
]
