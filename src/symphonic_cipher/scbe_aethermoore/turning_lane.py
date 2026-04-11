from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from .cli_toolkit import CrossTokenizer, Lexicons, TongueTokenizer

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
DEFAULT_MODES = ("byte", "semantic")
SAFE_COMMAND_FAMILIES = ("echo", "python-script", "pytest-targeted")
SAFE_SCRIPT_ROOTS = (REPO_ROOT / "scripts", REPO_ROOT / "tools")
SAFE_PYTEST_ROOT = REPO_ROOT / "tests"


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _default_witnesses(source_tongue: str) -> List[str]:
    src = source_tongue.upper()
    return [tongue for tongue in DEFAULT_TONGUES if tongue != src]


def _load_vm():
    from tools.stvm.vm import SacredTongueVM

    return SacredTongueVM


def _run_vm_program(program: Sequence[int], max_steps: int = 10000) -> List[int]:
    vm_cls = _load_vm()
    vm = vm_cls([int(byte) & 0xFF for byte in program])
    sink = io.StringIO()
    with redirect_stdout(sink):
        return vm.run(max_steps=max_steps)


@dataclass(frozen=True)
class TurningProgramCase:
    name: str
    program: List[int]
    expected_output: List[int]
    max_steps: int = 10000


def _build_add_program() -> List[int]:
    return [
        0x05, 0x00, 0x05, 0x00,  # set R0, 5
        0x05, 0x01, 0x08, 0x00,  # set R1, 8
        0x10, 0x02, 0x00, 0x01,  # add R2, R0, R1
        0x07, 0x02, 0x00, 0x00,  # print R2
        0x01, 0x00, 0x00, 0x00,  # halt
    ]


def _build_branch_program() -> List[int]:
    return [
        0x05, 0x00, 0x05, 0x00,  # set R0, 5
        0x05, 0x01, 0x05, 0x00,  # set R1, 5
        0x17, 0x02, 0x00, 0x01,  # cmp_eq R2, R0, R1
        0x03, 0x02, 0x06, 0x00,  # jz R2, pc=6
        0x05, 0x03, 0x63, 0x00,  # set R3, 99
        0x07, 0x03, 0x00, 0x00,  # print R3
        0x01, 0x00, 0x00, 0x00,  # halt
    ]


def _build_fib_program() -> List[int]:
    return [
        0x05, 0x00, 0x00, 0x00,  # set R0, 0
        0x05, 0x01, 0x01, 0x00,  # set R1, 1
        0x05, 0x02, 0x05, 0x00,  # set R2, 5 (iterations)
        0x05, 0x05, 0x01, 0x00,  # set R5, 1
        0x10, 0x03, 0x00, 0x01,  # add R3, R0, R1
        0x06, 0x00, 0x01, 0x00,  # mov R0, R1
        0x06, 0x01, 0x03, 0x00,  # mov R1, R3
        0x11, 0x02, 0x02, 0x05,  # sub R2, R2, R5
        0x04, 0x02, 0x04, 0x00,  # jnz R2, pc=4
        0x07, 0x01, 0x00, 0x00,  # print R1
        0x01, 0x00, 0x00, 0x00,  # halt
    ]


TURNING_CASES = (
    TurningProgramCase("add-13", _build_add_program(), [13]),
    TurningProgramCase("branch-99", _build_branch_program(), [99]),
    TurningProgramCase("fib-6", _build_fib_program(), [8]),
)


def prove_transport_mesh(
    payload: bytes,
    source_tongue: str = "KO",
    witness_tongues: Iterable[str] | None = None,
    modes: Iterable[str] = DEFAULT_MODES,
) -> dict:
    src = source_tongue.upper()
    witnesses = [tongue.upper() for tongue in (witness_tongues or _default_witnesses(src))]
    selected_modes = tuple(mode for mode in modes if mode in {"byte", "semantic"})
    if not selected_modes:
        raise ValueError("At least one transport mode is required.")

    lex = Lexicons()
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)

    packet_sha256 = hashlib.sha256(payload).hexdigest()
    src_tokens = tok.encode_bytes(src, payload)
    src_roundtrip = tok.decode_tokens(src, src_tokens)
    routes = [
        {
            "route": f"{src}->{src}",
            "mode": "direct",
            "matched": src_roundtrip == payload,
            "sha256": hashlib.sha256(src_roundtrip).hexdigest(),
            "token_count": len(src_tokens),
        }
    ]

    for dst in witnesses:
        for mode in selected_modes:
            dst_tokens, attest = xt.retokenize(src, dst, " ".join(src_tokens), mode=mode)
            roundtrip = tok.decode_tokens(dst, dst_tokens)
            routes.append(
                {
                    "route": f"{src}->{dst}",
                    "mode": mode,
                    "matched": roundtrip == payload,
                    "sha256": hashlib.sha256(roundtrip).hexdigest(),
                    "token_count": len(dst_tokens),
                    "attestation": {
                        "phase_delta": attest.phase_delta,
                        "weight_ratio": attest.weight_ratio,
                        "sha256_bytes": attest.sha256_bytes,
                    },
                }
            )

    matched = sum(1 for route in routes if route["matched"] and route["sha256"] == packet_sha256)
    convergence_score = matched / len(routes)

    return {
        "packet_sha256": packet_sha256,
        "source_tongue": src,
        "witness_tongues": witnesses,
        "modes": list(selected_modes),
        "route_count": len(routes),
        "matched_routes": matched,
        "convergence_score": convergence_score,
        "routes": routes,
        "source_tokens": src_tokens,
    }


def run_turning_suite() -> dict:
    suite_rows = []
    route_count = 0
    route_matched = 0
    suite_pass = True

    for case in TURNING_CASES:
        payload = bytes(case.program)
        mesh = prove_transport_mesh(payload)
        route_count += mesh["route_count"]
        route_matched += mesh["matched_routes"]

        outputs = {}
        for tongue in DEFAULT_TONGUES:
            tokens = mesh["source_tokens"] if tongue == mesh["source_tongue"] else None
            if tokens is None:
                lex = Lexicons()
                tok = TongueTokenizer(lex)
                tokens = tok.encode_bytes(tongue, payload)
                decoded = tok.decode_tokens(tongue, tokens)
            else:
                decoded = payload
            outputs[tongue] = _run_vm_program(decoded, max_steps=case.max_steps)

        case_pass = all(output == case.expected_output for output in outputs.values())
        suite_pass = suite_pass and case_pass and mesh["convergence_score"] == 1.0
        suite_rows.append(
            {
                "name": case.name,
                "expected_output": case.expected_output,
                "outputs": outputs,
                "transport": {
                    "route_count": mesh["route_count"],
                    "matched_routes": mesh["matched_routes"],
                    "convergence_score": mesh["convergence_score"],
                },
                "status": "PASS" if case_pass and mesh["convergence_score"] == 1.0 else "FAIL",
            }
        )

    return {
        "status": "PASS" if suite_pass else "FAIL",
        "program_count": len(TURNING_CASES),
        "route_count": route_count,
        "matched_routes": route_matched,
        "convergence_score": route_matched / route_count if route_count else 0.0,
        "programs": suite_rows,
    }


def _validate_command_family(family: str) -> str:
    normalized = family.strip().lower()
    if normalized not in SAFE_COMMAND_FAMILIES:
        raise ValueError(
            f"Unsupported command family '{family}'. Allowed families: {', '.join(SAFE_COMMAND_FAMILIES)}"
        )
    return normalized


def _resolve_python_script(path_str: str) -> Path:
    path = (REPO_ROOT / path_str).resolve() if not os.path.isabs(path_str) else Path(path_str).resolve()
    if path.suffix.lower() != ".py":
        raise ValueError("python-script family only supports .py files")
    if not any(_is_within(path, root) for root in SAFE_SCRIPT_ROOTS):
        raise ValueError("python-script path must live under scripts/ or tools/")
    if not path.exists():
        raise ValueError(f"python-script path does not exist: {path}")
    return path


def _resolve_pytest_target(path_str: str) -> Path:
    path = (REPO_ROOT / path_str).resolve() if not os.path.isabs(path_str) else Path(path_str).resolve()
    if not _is_within(path, SAFE_PYTEST_ROOT):
        raise ValueError("pytest-targeted path must live under tests/")
    if not path.exists():
        raise ValueError(f"pytest target does not exist: {path}")
    return path


def prepare_execution_packet(family: str, args: Sequence[str]) -> dict:
    family_name = _validate_command_family(family)

    if family_name == "echo":
        text = " ".join(args)
        argv = [sys.executable, "-c", "import sys; print(sys.argv[1])", text]
    elif family_name == "python-script":
        if not args:
            raise ValueError("python-script family requires a script path")
        script_path = _resolve_python_script(args[0])
        argv = [sys.executable, str(script_path)] + list(args[1:])
    elif family_name == "pytest-targeted":
        if not args:
            raise ValueError("pytest-targeted family requires a test path")
        target = _resolve_pytest_target(args[0])
        argv = ["pytest", str(target), "-q"] + list(args[1:])
    else:
        raise ValueError(f"Unhandled family '{family_name}'")

    packet = {
        "family": family_name,
        "argv": argv,
        "cwd": str(REPO_ROOT),
        "version": "turning-exec-v1",
    }
    packet_text = _canonical_json(packet)
    packet_bytes = packet_text.encode("utf-8")
    packet["packet_text"] = packet_text
    packet["packet_sha256"] = hashlib.sha256(packet_bytes).hexdigest()
    return packet


def prove_execution_packet(
    packet: dict,
    source_tongue: str = "KO",
    witness_tongues: Iterable[str] | None = None,
    modes: Iterable[str] = DEFAULT_MODES,
) -> dict:
    packet_bytes = packet["packet_text"].encode("utf-8")
    mesh = prove_transport_mesh(
        payload=packet_bytes,
        source_tongue=source_tongue,
        witness_tongues=witness_tongues,
        modes=modes,
    )
    return {
        "status": "PASS" if mesh["convergence_score"] == 1.0 else "FAIL",
        "family": packet["family"],
        "packet_sha256": packet["packet_sha256"],
        "transport": mesh,
    }


def execute_command_family(packet: dict, timeout: int = 30) -> dict:
    proof = prove_execution_packet(packet)
    if proof["status"] != "PASS":
        raise RuntimeError("Execution packet failed convergence proof.")

    completed = subprocess.run(
        packet["argv"],
        cwd=packet["cwd"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "family": packet["family"],
        "argv": packet["argv"],
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "packet_sha256": packet["packet_sha256"],
        "proof": proof,
    }
