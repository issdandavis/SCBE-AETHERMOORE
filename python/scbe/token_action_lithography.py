"""Fail-closed token-to-action lithography over the existing semantic VM.

The EOT lattice supplies exact token identity and byte paths.  A caller must
explicitly bind selected token identities to the semantic opcode VM's closed
instruction vocabulary.  The resulting "mask" is assembled to bytes,
disassembled, and compared instruction-for-instruction before optional bounded
execution.  Geometry or model scores may propose a binding order; they never
grant execution authority.

This module reuses lithography as a compiler metaphor.  It does not invoke or
claim the physical Fourier-optics simulator in ``C:/dev/training-research``.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re
from typing import Any, Mapping, Sequence

from python.scbe.eot_token_lattice import (
    EOT_SYMBOL,
    validate_eot_lattice,
)
from python.scbe.semantic_opcode_vm import (
    TOKEN_TO_CONTRACT,
    Instruction,
    SemanticOpcodeError,
    assemble,
    disassemble,
    run_program,
)

TOKEN_ACTION_LITHOGRAPHY_SCHEMA = "scbe.token-action-lithography.v1"
MAX_ACTION_INSTRUCTIONS = 4096
MAX_EXECUTION_STEPS = 1_000_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class TokenActionLithographyError(ValueError):
    """A token mask, lattice binding, or compiler round trip was invalid."""


@dataclass(frozen=True, slots=True)
class ActionTokenBinding:
    """One exact lattice token explicitly assigned to one VM instruction."""

    table_id: str
    token_id: int | str
    byte_hex: str
    semantic_token: str
    operands: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.table_id, str) or not self.table_id.strip():
            raise ValueError("table_id must be non-empty text")
        if isinstance(self.token_id, bool) or not isinstance(self.token_id, (int, str)):
            raise ValueError("token_id must be an integer or string")
        try:
            raw = bytes.fromhex(self.byte_hex)
        except (TypeError, ValueError) as exc:
            raise ValueError("byte_hex must be hexadecimal") from exc
        if raw.hex() != self.byte_hex:
            raise ValueError("byte_hex must be canonical lowercase hexadecimal")
        if self.semantic_token not in TOKEN_TO_CONTRACT:
            raise ValueError("semantic_token must name an exact VM contract")
        if not isinstance(self.operands, tuple) or not all(
            isinstance(value, str) and value for value in self.operands
        ):
            raise ValueError("operands must be a tuple of non-empty strings")
        if any(
            any(character.isspace() or character in ";#" for character in value)
            for value in self.operands
        ):
            raise ValueError("operands cannot contain whitespace, ';', or '#'")


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return sha256(_canonical_json(value)).hexdigest()


def _typed_token_id(token_id: int | str) -> str:
    return f"{'int' if isinstance(token_id, int) else 'str'}:{token_id}"


def _require_projection_receipt(value: str | None) -> None:
    if value is not None and SHA256_RE.fullmatch(value) is None:
        raise TokenActionLithographyError(
            "projection_receipt_sha256 must be lowercase SHA-256"
        )


def _selected_path(
    lattice: Mapping[str, Any], binding: ActionTokenBinding
) -> Mapping[str, Any]:
    token_paths = lattice.get("token_paths")
    if not isinstance(token_paths, list):
        raise TokenActionLithographyError("lattice token_paths are unavailable")
    typed_token_id = _typed_token_id(binding.token_id)
    matches = [
        row
        for row in token_paths
        if isinstance(row, Mapping)
        and row.get("table_id") == binding.table_id
        and row.get("token_id") == binding.token_id
        and type(row.get("token_id")) is type(binding.token_id)
        and row.get("typed_token_id") == typed_token_id
        and row.get("byte_hex") == binding.byte_hex
    ]
    if len(matches) != 1:
        raise TokenActionLithographyError(
            "declared token identity must match exactly one lattice path"
        )
    path = matches[0]
    raw = bytes.fromhex(binding.byte_hex)
    symbols = [*raw, EOT_SYMBOL]
    route = path.get("node_route")
    steps = path.get("steps")
    if (
        path.get("symbols_with_eot") != symbols
        or not isinstance(route, list)
        or len(route) != len(raw) + 1
        or route[0] != 0
        or not isinstance(steps, list)
        or len(steps) != len(symbols)
        or path.get("active_probability_path") is not True
    ):
        raise TokenActionLithographyError("token path identity/topology is invalid")

    nodes = lattice.get("nodes")
    if not isinstance(nodes, list):
        raise TokenActionLithographyError("lattice nodes are unavailable")
    product = 1.0
    for depth, (symbol, step) in enumerate(zip(symbols, steps, strict=True)):
        node_id = route[depth]
        if (
            not isinstance(step, Mapping)
            or step.get("node_id") != node_id
            or step.get("symbol") != symbol
            or not isinstance(node_id, int)
            or not 0 <= node_id < len(nodes)
        ):
            raise TokenActionLithographyError("token step does not match its route")
        node = nodes[node_id]
        views = node.get("table_views") if isinstance(node, Mapping) else None
        if not isinstance(views, list):
            raise TokenActionLithographyError("token route has no table view")
        view = next(
            (
                row
                for row in views
                if isinstance(row, Mapping) and row.get("table_id") == binding.table_id
            ),
            None,
        )
        edges = view.get("edges") if isinstance(view, Mapping) else None
        edge = next(
            (
                row
                for row in edges or ()
                if isinstance(row, Mapping) and row.get("symbol") == symbol
            ),
            None,
        )
        if edge is None:
            raise TokenActionLithographyError("active token route lacks a live edge")
        probability = edge.get("conditional_probability")
        if (
            not isinstance(probability, (int, float))
            or isinstance(probability, bool)
            or not math.isfinite(probability)
            or probability <= 0.0
            or step.get("conditional_probability") != probability
            or step.get("positive_mass_edge_present") is not True
            or step.get("transition_function_sha256")
            != edge["transition_function"]["function_sha256"]
        ):
            raise TokenActionLithographyError("token route probability is invalid")
        product *= float(probability)
        if symbol != EOT_SYMBOL and route[depth + 1] != edge.get("child_node_id"):
            raise TokenActionLithographyError("token route child does not match edge")

    reconstructed = path.get("reconstructed_path_mass")
    exact = path.get("exact_byte_path_mass")
    if (
        not isinstance(reconstructed, (int, float))
        or not isinstance(exact, (int, float))
        or not math.isclose(product, float(reconstructed), rel_tol=1e-9, abs_tol=1e-12)
        or not math.isclose(
            float(reconstructed), float(exact), rel_tol=1e-9, abs_tol=1e-12
        )
    ):
        raise TokenActionLithographyError("token path mass does not telescope")
    return path


def compile_token_action_mask(
    lattice: Mapping[str, Any],
    bindings: Sequence[ActionTokenBinding],
    *,
    execute: bool = False,
    max_steps: int = 10_000,
    projection_receipt_sha256: str | None = None,
) -> dict[str, Any]:
    """Compile explicit token bindings through the existing semantic opcode VM."""

    validate_eot_lattice(lattice)
    _require_projection_receipt(projection_receipt_sha256)
    if not bindings or len(bindings) > MAX_ACTION_INSTRUCTIONS:
        raise TokenActionLithographyError(
            f"bindings must contain 1..{MAX_ACTION_INSTRUCTIONS} instructions"
        )
    if not all(isinstance(binding, ActionTokenBinding) for binding in bindings):
        raise TokenActionLithographyError("every binding must be ActionTokenBinding")
    if (
        isinstance(max_steps, bool)
        or not isinstance(max_steps, int)
        or not 1 <= max_steps <= MAX_EXECUTION_STEPS
    ):
        raise TokenActionLithographyError(
            f"max_steps must be in 1..{MAX_EXECUTION_STEPS}"
        )

    selected_paths = [_selected_path(lattice, binding) for binding in bindings]
    expected_instructions = [
        Instruction(binding.semantic_token, binding.operands) for binding in bindings
    ]
    source_lines = [
        " ".join((binding.semantic_token, *binding.operands)).strip()
        for binding in bindings
    ]
    source = "\n".join(source_lines)
    try:
        program = assemble(source)
        decoded = disassemble(program)
    except SemanticOpcodeError as exc:
        raise TokenActionLithographyError(str(exc)) from exc
    if decoded != expected_instructions:
        raise TokenActionLithographyError(
            "assembled program did not round-trip to declared instructions"
        )

    mask_rows = []
    for index, (binding, path) in enumerate(zip(bindings, selected_paths, strict=True)):
        contract = TOKEN_TO_CONTRACT[binding.semantic_token]
        row = {
            "instruction_index": index,
            "table_id": binding.table_id,
            "typed_token_id": _typed_token_id(binding.token_id),
            "source_byte_hex": binding.byte_hex,
            "source_path_sha256": _digest(path),
            "semantic_token": contract.token,
            "opcode": contract.opcode,
            "opcode_hex": f"{contract.opcode:02x}",
            "family": contract.family,
            "operands": list(binding.operands),
            "verification_rule": contract.verification_rule,
        }
        mask_rows.append({**row, "mask_cell_sha256": _digest(row)})

    execution_receipt = run_program(program, max_steps=max_steps) if execute else None
    body = {
        "schema": TOKEN_ACTION_LITHOGRAPHY_SCHEMA,
        "source_lattice_sha256": lattice["receipt_sha256"],
        "projection_receipt_sha256": projection_receipt_sha256,
        "mask": mask_rows,
        "mask_sha256": _digest(mask_rows),
        "program": {
            "isa_profile": "semantic-vm-v1",
            "instruction_count": len(bindings),
            "max_steps": max_steps,
            "source_lines": source_lines,
            "program_hex": program.hex(),
            "program_sha256": sha256(program).hexdigest(),
            "disassembly_roundtrip_exact": True,
        },
        "execution": execution_receipt,
        "authority": {
            "binding_mode": "explicit-declaration-only",
            "isa_selection_is_explicit": True,
            "arbitrary_token_bytes_are_executable": False,
            "geometry_or_weight_score_grants_authority": False,
            "execution_scope": "bounded-semantic-opcode-vm" if execute else "none",
            "external_os_or_shell_authority": False,
        },
        "claim_boundary": {
            "exact_lattice_token_paths_verified": True,
            "compiler_roundtrip_verified": True,
            "projection_receipt_is_provenance_not_permission": True,
            "physical_lithography_simulator_invoked": False,
            "neural_weights_trained": False,
        },
        "receipt_security": "unkeyed-corruption-detection-only",
    }
    return {**body, "receipt_sha256": _digest(body)}


def verify_token_action_mask(
    lattice: Mapping[str, Any],
    bindings: Sequence[ActionTokenBinding],
    receipt: Mapping[str, Any],
) -> bool:
    """Recompile an action mask and require byte-for-byte receipt equality."""

    try:
        program = receipt.get("program")
        if not isinstance(program, Mapping):
            return False
        rebuilt = compile_token_action_mask(
            lattice,
            bindings,
            execute=receipt.get("execution") is not None,
            max_steps=int(program.get("max_steps", 10_000)),
            projection_receipt_sha256=receipt.get("projection_receipt_sha256"),
        )
    except (
        TokenActionLithographyError,
        SemanticOpcodeError,
        TypeError,
        ValueError,
    ):
        return False
    return dict(receipt) == rebuilt


__all__ = [
    "TOKEN_ACTION_LITHOGRAPHY_SCHEMA",
    "ActionTokenBinding",
    "TokenActionLithographyError",
    "compile_token_action_mask",
    "verify_token_action_mask",
]
