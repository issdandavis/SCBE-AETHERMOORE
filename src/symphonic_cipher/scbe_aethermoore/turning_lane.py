from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from .cli_toolkit import CrossTokenizer, Lexicons, TongueTokenizer

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np

from python.scbe.atomic_tokenization import TONGUES as ATOMIC_TONGUES
from python.scbe.chemical_fusion import FusionParams
from python.scbe.history_reducer import reduce_atomic_history

DEFAULT_TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
DEFAULT_MODES = ("byte", "semantic")
SAFE_COMMAND_FAMILIES = ("echo", "python-script", "pytest-targeted")
SAFE_SCRIPT_ROOTS = (REPO_ROOT / "scripts", REPO_ROOT / "tools")
SAFE_PYTEST_ROOT = REPO_ROOT / "tests"
ATOMIC_TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_.:/-]*|\d+")
SEMANTIC_CLASS_IDS = {
    "INERT_WITNESS": 0,
    "ACTION": 1,
    "ENTITY": 2,
    "NEGATION": 3,
    "MODIFIER": 4,
    "RELATION": 5,
    "TEMPORAL": 6,
}
FAMILY_ATOMIC_CONTEXT = {
    "echo": {"language": "en", "context_class": "operator"},
    "python-script": {"language": None, "context_class": "operator"},
    "pytest-targeted": {"language": None, "context_class": "safety"},
}
FAMILY_GOVERNANCE_PROTOS = {
    "echo": np.array([0.0, 0.0, 0.25, 0.0, 0.0, 0.0], dtype=float),
    "python-script": np.array([0.3, 0.2, 0.6, 0.5, 0.1, 0.2], dtype=float),
    "pytest-targeted": np.array([0.15, 0.35, 0.75, 0.2, -0.1, 0.45], dtype=float),
}


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    max_abs = float(np.max(np.abs(vector))) if vector.size else 0.0
    if max_abs <= 0.0:
        return vector.astype(float)
    return vector.astype(float) / max_abs


def _atomicize_arg_token(value: str) -> list[str]:
    raw = value.strip()
    if not raw:
        return []
    candidate = Path(raw)
    if candidate.exists():
        parts = []
        try:
            rel = candidate.resolve().relative_to(REPO_ROOT.resolve())
            parts.extend(rel.parts)
        except ValueError:
            parts.extend(candidate.parts[-3:])
        text = " ".join(parts)
    else:
        text = raw
    return [token.lower() for token in ATOMIC_TOKEN_PATTERN.findall(text)]


def _packet_semantic_tokens(packet: dict) -> list[str]:
    tokens = [packet["family"].replace("-", "_")]
    argv = packet.get("argv", [])
    for value in argv[1:]:
        tokens.extend(_atomicize_arg_token(str(value)))
    return tokens[:64]


def _build_atomic_feature_row(state) -> list[float]:
    return [
        state.element.Z,
        state.element.group,
        state.element.period,
        state.element.valence,
        state.element.electronegativity,
        state.band_flag,
        -1 if state.dual_state is None else state.dual_state,
        0,
    ]


def _build_periodic_view(states) -> np.ndarray:
    if not states:
        return np.zeros(6, dtype=float)
    witness_ratio = sum(1 for state in states if state.element.witness_stable) / len(states)
    mean_z = sum(state.element.Z for state in states) / len(states)
    mean_group = sum(state.element.group for state in states) / len(states)
    mean_period = sum(state.element.period for state in states) / len(states)
    mean_valence = sum(state.element.valence for state in states) / len(states)
    mean_chi = sum(state.element.electronegativity for state in states) / len(states)
    vector = np.array(
        [
            (mean_group - 9.5) / 9.5,
            (mean_period - 2.5) / 2.5,
            ((mean_z % 7.0) - 3.0) / 3.0,
            (mean_valence - 2.0) / 2.0,
            (mean_chi - 2.0) / 2.0,
            (witness_ratio * 2.0) - 1.0,
        ],
        dtype=float,
    )
    return np.clip(vector, -1.0, 1.0)


def build_atomic_execution_bundle(packet: dict) -> dict:
    family = packet["family"]
    tokens = _packet_semantic_tokens(packet)
    if not tokens:
        return {
            "status": "REJECT",
            "reason": "No semantic tokens were derived from the execution packet.",
            "tokens": [],
            "token_count": 0,
        }

    context = FAMILY_ATOMIC_CONTEXT.get(family, {"language": None, "context_class": "operator"})
    governance_proto = FAMILY_GOVERNANCE_PROTOS.get(family, np.zeros(6, dtype=float))
    _, history_result = reduce_atomic_history(
        tokens,
        language=context["language"],
        context_class=context["context_class"],
        params=FusionParams(rho_default=0.08),
        governance_proto=governance_proto,
    )
    states = history_result.states
    fusion = history_result.fusion
    rhombic_energy = history_result.rhombic_energy
    rhombic_value = history_result.rhombic_score
    tau_vectors = np.array([state.tau.as_tuple() for state in states], dtype=float)
    x_vector = np.mean(tau_vectors, axis=0)
    audio_vector = _normalize_vector(
        np.array([fusion.reconstruction_votes[tongue] for tongue in ATOMIC_TONGUES], dtype=float)
    )
    vision_vector = _build_periodic_view(states)

    if rhombic_value < 0.0002:
        advisory_status = "REJECT"
        advisory_reason = "Atomic/rhombic consistency fell below the execution floor."
    elif rhombic_value < 0.001:
        advisory_status = "WARN"
        advisory_reason = "Atomic/rhombic consistency is weak; packet may drift."
    else:
        advisory_status = "PASS"
        advisory_reason = "Atomic/rhombic consistency is stable."

    return {
        "status": advisory_status,
        "reason": advisory_reason,
        "family": family,
        "language": context["language"],
        "context_class": context["context_class"],
        "token_count": len(tokens),
        "tokens": tokens,
        "atomic_features": [_build_atomic_feature_row(state) for state in states],
        "trit_vectors": [list(state.tau.as_tuple()) for state in states],
        "semantic_classes": [state.semantic_class for state in states],
        "negative_states": [state.negative_state for state in states],
        "dual_states": [state.dual_state for state in states],
        "chemical_fusion": {
            "tau_hat": fusion.tau_hat,
            "reconstruction_votes": fusion.reconstruction_votes,
            "signed_edge_tension": fusion.signed_edge_tension,
            "coherence_penalty": fusion.coherence_penalty,
            "valence_pressure": fusion.valence_pressure,
        },
        "rhombic": {
            "energy": rhombic_energy,
            "score": rhombic_value,
            "governance_proto": governance_proto.tolist(),
            "x_vector": x_vector.tolist(),
            "audio_vector": audio_vector.tolist(),
            "vision_vector": vision_vector.tolist(),
        },
        "history_reducer": {
            "trust_level": history_result.trust_level,
            "trust_factor": history_result.trust_factor,
            "betrayal_delta": history_result.betrayal_delta,
            "negative_ratio": history_result.negative_ratio,
            "dual_state": history_result.dual_state,
            "lane_alignment": history_result.lane_alignment,
            "drift_norm": history_result.drift_norm,
            "drift_components": history_result.drift_components,
            "checkpoint": history_result.checkpoint,
        },
    }


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
        0x05,
        0x00,
        0x05,
        0x00,  # set R0, 5
        0x05,
        0x01,
        0x08,
        0x00,  # set R1, 8
        0x10,
        0x02,
        0x00,
        0x01,  # add R2, R0, R1
        0x07,
        0x02,
        0x00,
        0x00,  # print R2
        0x01,
        0x00,
        0x00,
        0x00,  # halt
    ]


def _build_branch_program() -> List[int]:
    return [
        0x05,
        0x00,
        0x05,
        0x00,  # set R0, 5
        0x05,
        0x01,
        0x05,
        0x00,  # set R1, 5
        0x17,
        0x02,
        0x00,
        0x01,  # cmp_eq R2, R0, R1
        0x03,
        0x02,
        0x06,
        0x00,  # jz R2, pc=6
        0x05,
        0x03,
        0x63,
        0x00,  # set R3, 99
        0x07,
        0x03,
        0x00,
        0x00,  # print R3
        0x01,
        0x00,
        0x00,
        0x00,  # halt
    ]


def _build_fib_program() -> List[int]:
    return [
        0x05,
        0x00,
        0x00,
        0x00,  # set R0, 0
        0x05,
        0x01,
        0x01,
        0x00,  # set R1, 1
        0x05,
        0x02,
        0x05,
        0x00,  # set R2, 5 (iterations)
        0x05,
        0x05,
        0x01,
        0x00,  # set R5, 1
        0x10,
        0x03,
        0x00,
        0x01,  # add R3, R0, R1
        0x06,
        0x00,
        0x01,
        0x00,  # mov R0, R1
        0x06,
        0x01,
        0x03,
        0x00,  # mov R1, R3
        0x11,
        0x02,
        0x02,
        0x05,  # sub R2, R2, R5
        0x04,
        0x02,
        0x04,
        0x00,  # jnz R2, pc=4
        0x07,
        0x01,
        0x00,
        0x00,  # print R1
        0x01,
        0x00,
        0x00,
        0x00,  # halt
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
        raise ValueError(f"Unsupported command family '{family}'. Allowed families: {', '.join(SAFE_COMMAND_FAMILIES)}")
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
    atomic_bundle = build_atomic_execution_bundle(packet)
    proof_status = "PASS" if mesh["convergence_score"] == 1.0 and atomic_bundle["status"] != "REJECT" else "FAIL"
    return {
        "status": proof_status,
        "family": packet["family"],
        "packet_sha256": packet["packet_sha256"],
        "transport": mesh,
        "atomic_precheck": atomic_bundle,
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
