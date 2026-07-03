"""Mixed expression coding lane (SCBE prototype).

This script builds a weighted mixed-expression packet. It is a staging layer for
programs that use several SCBE tongues / host languages in one intent:
Python for readable state, Haskell for pure transforms, C-family snippets for
edge kernels, and custom binary/STIB-like speckles for tiny exact gaps.

State: batter, not baked. It emits a receipt packet only. A product claim starts
only after the packet is lowered to a real target and compiled/run.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PY_SRC = ROOT / "python"
if str(PY_SRC) not in sys.path:
    sys.path.insert(0, str(PY_SRC))

FALLBACK_CODE_LANE_REGISTRY: dict[str, dict[str, str]] = {
    "computational_isomorphism": {
        "KO": "lisp",
        "AV": "python",
        "RU": "forth",
        "CA": "sql",
        "UM": "assembly",
        "DR": "make",
    },
    "opcode_runtime": {
        "CA": "c",
    },
}

try:
    from scbe.tongue_code_lanes import CODE_LANE_REGISTRY  # type: ignore
except Exception:  # pragma: no cover - keeps the lane usable before packaging.
    CODE_LANE_REGISTRY = FALLBACK_CODE_LANE_REGISTRY

SUPPORTED_ISA_TARGETS = [
    "python",
    "typescript",
    "go",
    "rust",
    "c",
    "julia",
    "haskell",
    "zig",
]


@dataclass(frozen=True)
class MixedSegment:
    """One brush stroke in a mixed-expression program."""

    id: str
    tongue: str
    language: str
    role: str
    weight: float
    text: str
    source: str = "human_or_agent"
    compiler_target: str = ""
    opcodes: list[str] = field(default_factory=list)
    binary_hex: str = ""
    constraints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MixedExpression:
    """Weighted conlang/code packet before lowering to executable code."""

    id: str
    intent: str
    segments: list[MixedSegment]
    contract: dict[str, Any]
    oven: dict[str, Any]

    def normalized_weights(self) -> dict[str, float]:
        total = sum(max(0.0, segment.weight) for segment in self.segments) or 1.0
        return {
            segment.id: round(max(0.0, segment.weight) / total, 6)
            for segment in self.segments
        }

    def code_lane_ledger(self) -> dict[str, Any]:
        ledger: dict[str, Any] = {}
        for segment in self.segments:
            ledger[segment.id] = {
                "tongue": segment.tongue,
                "language": segment.language,
                "role": segment.role,
                "weight": segment.weight,
                "canonical_lanes": canonical_tongue_lanes(segment.tongue),
                "compiler_target": segment.compiler_target,
                "baked": False,
            }
        return ledger

    def to_packet(self) -> dict[str, Any]:
        return {
            "schema": "scbe.mixed_expression.v1",
            "status": "batter",
            "id": self.id,
            "intent": self.intent,
            "normalized_weights": self.normalized_weights(),
            "segments": [asdict(segment) for segment in self.segments],
            "contract": self.contract,
            "oven": self.oven,
            "code_lane_ledger": self.code_lane_ledger(),
            "rule": "No release claim until lower -> compile -> run -> receipt.",
        }


def canonical_tongue_lanes(tongue: str) -> list[dict[str, str]]:
    lanes: list[dict[str, str]] = []
    registry = CODE_LANE_REGISTRY if isinstance(CODE_LANE_REGISTRY, dict) else {}
    for family, mapping in registry.items():
        if not isinstance(mapping, dict) or tongue not in mapping:
            continue
        lane = mapping[tongue]
        if isinstance(lane, str):
            lanes.append({"family": str(family), "lane": lane})
        elif isinstance(lane, (list, tuple, set)):
            for item in lane:
                lanes.append({"family": str(family), "lane": str(item)})
        else:
            lanes.append({"family": str(family), "lane": str(lane)})
    return lanes


def stib_staging_hex(tongue: str, label: str, bitstring: str) -> str:
    """Build a tiny STIB-like staging marker.

    This deliberately does not pretend to be the official STIB encoder. The
    official path should route through scbe.tongue_isa_binary once the lowering
    step is wired and tested.
    """

    compact_bits = "".join(ch for ch in bitstring if ch in "01")
    payload = f"{tongue}:{label}:{compact_bits}".encode("ascii")
    return (b"STIB" + len(payload).to_bytes(2, "big") + payload).hex()


def build_demo_expression() -> MixedExpression:
    segments = [
        MixedSegment(
            id="av_python_bootstrap",
            tongue="AV",
            language="python",
            role="human_readable_state_shape",
            weight=0.34,
            text="raw_value = request.get('value')\nvalue = normalize(raw_value)",
            compiler_target="python",
            constraints=["readable", "debuggable", "safe_to_show_user"],
        ),
        MixedSegment(
            id="ca_haskell_fold_view",
            tongue="CA",
            language="haskell",
            role="pure_transform_view",
            weight=0.26,
            text="score xs = foldl caAdd 0 xs",
            compiler_target="haskell",
            opcodes=["CA_ADD", "CA_FOLD"],
            constraints=["pure", "side_effect_free", "must_match_ca_opcode_semantics"],
        ),
        MixedSegment(
            id="um_cpp_corner_kernel",
            tongue="UM",
            language="cpp_style",
            role="fast_edge_kernel",
            weight=0.20,
            text=(
                "double clamp_corner(double v) { "
                "return v < 0.0 ? 0.0 : (v > 1.0 ? 1.0 : v); }"
            ),
            compiler_target="c_family_unbaked",
            constraints=[
                "official_tongue_isa_has_c_not_cpp_yet",
                "must_lower_before_execution",
            ],
        ),
        MixedSegment(
            id="ca_binary_speckle",
            tongue="CA",
            language="stib_staging_hex",
            role="micro_gap_exactness",
            weight=0.20,
            text="bits: 10100101 00010011",
            compiler_target="stib_binary_unbaked",
            opcodes=["ROUND_ULP", "CLAMP_EDGE"],
            binary_hex=stib_staging_hex("CA", "rounding-corner-v1", "10100101 00010011"),
            constraints=[
                "tiny_gap_fill",
                "must_route_to_official_stib_encoder_before_release",
            ],
        ),
    ]
    return MixedExpression(
        id="mixed_expression_demo_001",
        intent=(
            "Normalize a request value, fold a score, clamp tiny numerical "
            "corners, and preserve the binary speckle needed for exactness."
        ),
        segments=segments,
        contract={
            "input": "request.value plus a numeric list xs",
            "output": "normalized value plus clamped score",
            "must_preserve": [
                "human readable state",
                "pure transform semantics",
                "edge kernel intent",
                "binary rounding/corner marker",
            ],
        },
        oven={
            "status": "batter",
            "required_next_steps": [
                "lower mixed packet to shared_ir.RouteIR",
                "lower CA opcodes through tongue_isa",
                "replace stib_staging_hex with tongue_isa_binary output",
                "compile target program",
                "run executable check and emit receipt",
            ],
            "supported_isa_targets_now": SUPPORTED_ISA_TARGETS,
            "release_gate": "compile_and_run_receipt_required",
        },
    )


def emit_human_brief(expression: MixedExpression) -> str:
    weights = expression.normalized_weights()
    lines = [
        f"Mixed expression: {expression.id}",
        f"Intent: {expression.intent}",
        "Segments:",
    ]
    for segment in expression.segments:
        lines.append(
            f"- {segment.id}: {segment.tongue}/{segment.language} "
            f"weight={weights[segment.id]} role={segment.role}"
        )
    lines.append("Status: batter. It still needs the oven: lower, compile, run, receipt.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit an SCBE mixed-expression packet.")
    parser.add_argument("--out", help="Write JSON packet to this path.")
    parser.add_argument("--brief", action="store_true", help="Print a compact human brief.")
    args = parser.parse_args(argv)

    expression = build_demo_expression()
    if args.brief:
        output = emit_human_brief(expression) + "\n"
    else:
        output = json.dumps(expression.to_packet(), indent=2, sort_keys=True) + "\n"

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
