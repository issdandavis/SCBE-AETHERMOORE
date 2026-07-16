#!/usr/bin/env python3
"""Build a receipted map across Code Prism, STIB, hex, and conlang tokenizers.

This is an orientation artifact, not a new compiler. It answers:

- Which Sacred Tongue primary languages are wired into Code Prism today?
- Which languages can be reached through the CA opcode/STIB compiler lane?
- Which tokenizer/conlang face owns reversible token orientation?
- Which projections are actually reversible, and which are one-way scaffolds?
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from python.scbe.bit_spine import BitSpine  # noqa: E402
from python.scbe.cube_token import CubeToken, LANGUAGE_FORMATIONS, TONGUE_LANGUAGE  # noqa: E402
from python.scbe.tongue_code_lanes import CODE_LANE_REGISTRY  # noqa: E402
from python.scbe.tongue_isa import SUPPORTED_TARGETS, compile_ca_tokens, emit_compiled_program_source, supported_ca_ops  # noqa: E402
from python.scbe.tongue_isa_binary import decode as stib_decode  # noqa: E402
from python.scbe.tongue_isa_binary import encode as stib_encode  # noqa: E402
from python.scbe.tongue_isa_binary import from_compiled  # noqa: E402
from src.cli.cross_build_ir import TIER1_PARTICIPATING_OPS, cross_build  # noqa: E402
from src.code_prism.matrix import load_interoperability_matrix  # noqa: E402


PRIMARY_LANGUAGE_BY_TONGUE = {
    "KO": "python",
    "AV": "typescript",
    "RU": "rust",
    "CA": "c",
    "UM": "julia",
    "DR": "haskell",
}

TONGUE_NAMES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}

CODE_PRISM_SOURCE_LANGUAGES = {"python", "typescript", "go", "rust", "c", "julia", "haskell"}
CODE_PRISM_EMIT_LANGUAGES = {"python", "typescript", "go", "rust", "c", "julia", "haskell"}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_map_hash(payload: dict[str, Any]) -> str:
    stable = {key: value for key, value in payload.items() if key not in {"generated_at", "map_sha256"}}
    return _sha256_text(json.dumps(stable, sort_keys=True))


def _load_matrix_routes() -> dict[str, list[str]]:
    matrix = load_interoperability_matrix()
    return {language: list(targets) for language, targets in matrix.transpilers.items()}


def _bit_spine_receipt(sample: str) -> dict[str, Any]:
    spine = BitSpine(sample.encode("utf-8"))
    recovered_from_hex = BitSpine.from_hex(spine.hex()).data.decode("utf-8")
    recovered_from_bits = BitSpine.from_bits(spine.bits()).data.decode("utf-8")
    recovered_from_trits = BitSpine.from_trits(spine.trits()).data.decode("utf-8")
    return {
        "schema": "scbe_bit_spine_orientation_receipt_v1",
        "sample": sample,
        "byte_len": len(spine.data),
        "sha256": spine.digest(),
        "hex": spine.hex(),
        "binary_prefix": spine.bits()[:64],
        "trit_count": len(spine.trits()),
        "roundtrip": {
            "hex": recovered_from_hex == sample,
            "binary": recovered_from_bits == sample,
            "trits": recovered_from_trits == sample,
        },
    }


def _stib_receipt() -> dict[str, Any]:
    compiled = compile_ca_tokens([0x29], target="python", fn_name="clamp_demo", arg_names=["a", "b", "c"])
    stib = stib_encode(from_compiled(compiled))
    decoded = stib_decode(stib)
    source = emit_compiled_program_source(compiled)
    return {
        "schema": "scbe_stib_orientation_receipt_v1",
        "lane": "CA opcodes -> STIB bytes -> Code Prism module source",
        "opcodes_hex": [f"0x{op:02X}" for op in decoded.opcodes],
        "stib_hex": stib.hex(),
        "stib_sha256": hashlib.sha256(stib).hexdigest(),
        "source_sha256": _sha256_text(source),
        "roundtrip_ok": decoded.opcodes == [0x29] and decoded.tongue == "CA",
    }


def _cube_token_receipts(sample: str) -> dict[str, Any]:
    cube = CubeToken(sample)
    faces = {}
    for tongue in PRIMARY_LANGUAGE_BY_TONGUE:
        encoded = cube.face(tongue)
        recovered = CubeToken.from_face(tongue, encoded).token
        faces[tongue] = {
            "tokens": encoded,
            "recovered": recovered,
            "roundtrip_ok": recovered == sample,
        }
    return {
        "schema": "scbe_cube_token_orientation_receipt_v1",
        "sample": sample,
        "all_faces_roundtrip": cube.is_bijective(),
        "faces": faces,
    }


def _code_prism_status(language: str, matrix_routes: dict[str, list[str]]) -> dict[str, Any]:
    lang = language.lower()
    return {
        "parser_supported": lang in CODE_PRISM_SOURCE_LANGUAGES,
        "emitter_supported": lang in CODE_PRISM_EMIT_LANGUAGES,
        "matrix_language": lang in matrix_routes,
        "matrix_targets": matrix_routes.get(lang, []),
        "full_source_status": "active_safe_subset"
        if lang in CODE_PRISM_SOURCE_LANGUAGES
        else ("target_only_safe_subset" if lang in CODE_PRISM_EMIT_LANGUAGES else "not_full_source_prism_today"),
    }


def _orientation_rows(sample: str, matrix_routes: dict[str, list[str]]) -> list[dict[str, Any]]:
    cube = CubeToken(sample)
    language_family = CODE_LANE_REGISTRY.get("language_family", {})
    rows = []
    for tongue, primary_language in PRIMARY_LANGUAGE_BY_TONGUE.items():
        cube_face_language = TONGUE_LANGUAGE.get(tongue)
        family = LANGUAGE_FORMATIONS.get(tongue, {})
        face_tokens = cube.face(tongue)
        rows.append(
            {
                "tongue": tongue,
                "tongue_name": TONGUE_NAMES[tongue],
                "primary_language": primary_language,
                "language_family_profile": list(language_family.get(tongue, ())),
                "cube_token_face_language": cube_face_language,
                "cube_token_formation": {
                    "paradigm": family.get("paradigm"),
                    "language_count": len(family.get("languages", [])),
                    "sample_languages": list(family.get("languages", []))[:8],
                },
                "code_prism_primary": _code_prism_status(primary_language, matrix_routes),
                "code_prism_cube_face": _code_prism_status(cube_face_language or "", matrix_routes),
                "ca_stib_target_supported": primary_language in SUPPORTED_TARGETS,
                "conlang_tokenizer": {
                    "runtime": "python.scbe.cube_token.CubeToken",
                    "sample_face_tokens": face_tokens,
                    "reverse_from_face_ok": CubeToken.from_face(tongue, face_tokens).token == sample,
                },
            }
        )
    return rows


def build_map(sample: str = "compile") -> dict[str, Any]:
    matrix_routes = _load_matrix_routes()
    cross_sample = cross_build("(x + y)", "KO", "RU")
    bit_receipt = _bit_spine_receipt(sample)
    stib_receipt = _stib_receipt()
    cube_receipt = _cube_token_receipts(sample)
    rows = _orientation_rows(sample, matrix_routes)
    payload: dict[str, Any] = {
        "schema": "scbe_code_prism_binary_conlang_orientation_map_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample": sample,
        "objective": "orient Code Prism, STIB/binary/hex, and conlang tokenizers into one reversible map",
        "code_prism": {
            "matrix_languages": sorted(matrix_routes),
            "parser_supported_sources": sorted(CODE_PRISM_SOURCE_LANGUAGES),
            "emitter_supported_targets": sorted(CODE_PRISM_EMIT_LANGUAGES),
            "matrix_routes": matrix_routes,
            "safe_subset_boundary": (
                "function definitions, arguments, return statements, basic assignments, "
                "and simple expressions across Python/TypeScript/Go/Rust/C/Julia/Haskell"
            ),
        },
        "ca_isa_stib": {
            "supported_targets": list(SUPPORTED_TARGETS),
            "supported_opcode_templates": len(supported_ca_ops()),
            "stib": stib_receipt,
        },
        "bit_spine_hex": bit_receipt,
        "conlang_tokenizers": {
            "python_cube_token": cube_receipt,
            "typescript_ss1": {
                "path": "src/tokenizer/ss1.ts",
                "role": "package tokenizer protocol; keep distinct from scbe.py direct CLI tables",
                "boundary": "same tongue labels, separate implementation surface; do not mix decoders without receipt",
            },
        },
        "cross_build_lattice": {
            "tier1_participating_ops": len(TIER1_PARTICIPATING_OPS),
            "sample": {
                "source": cross_sample.src_code,
                "source_tongue": cross_sample.src_tongue,
                "source_language": cross_sample.src_language,
                "target": cross_sample.dst_code,
                "target_tongue": cross_sample.dst_tongue,
                "target_language": cross_sample.dst_language,
                "op": cross_sample.ir.op_name,
            },
            "reversibility": "lexicon-bounded snippets lift to one LatticeOp and emit back to any participating tongue",
        },
        "orientation_rows": rows,
        "reversibility_contracts": [
            {
                "lane": "bit_spine",
                "path": "bytes -> binary/hex/trits -> bytes",
                "status": "exact_reversible",
                "receipt_key": "bit_spine_hex.roundtrip",
            },
            {
                "lane": "stib",
                "path": "CA opcodes -> STIB hex -> decoded opcodes",
                "status": "exact_reversible_for_v1_opcode_payloads",
                "receipt_key": "ca_isa_stib.stib.roundtrip_ok",
            },
            {
                "lane": "cube_token",
                "path": "raw token -> tongue face tokens -> raw token",
                "status": "exact_reversible_per_face",
                "receipt_key": "conlang_tokenizers.python_cube_token.all_faces_roundtrip",
            },
            {
                "lane": "code_prism",
                "path": "safe-subset source -> PrismModule IR -> target source",
                "status": "orientation_and_translation_scaffold_not_exact_source_bijection",
                "receipt_key": "code_prism",
            },
            {
                "lane": "cross_build_lattice",
                "path": "lexicon snippet -> LatticeOp -> lexicon snippet",
                "status": "reversible_inside_64_op_lexicon_boundary",
                "receipt_key": "cross_build_lattice.tier1_participating_ops",
            },
        ],
        "warnings": [
            "Primary language mapping and CubeToken face mapping are related but not identical; this map records both.",
            "scbe.py and src/tokenizer/ss1.ts are separate Sacred Tongue surfaces; use a receipt before crossing them.",
            "Code Prism is now full across primary lanes at safe-subset function level; classes, macros, generics, async, reflection, and arbitrary modules remain outside this lane.",
        ],
    }
    payload["map_sha256"] = _stable_map_hash(payload)
    return payload


def write_outputs(payload: dict[str, Any], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    latest_json = out_dir / "latest.json"
    latest_md = out_dir / "latest.md"
    latest_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest_md.write_text(render_markdown(payload), encoding="utf-8")
    return {"latest_json": str(latest_json), "latest_markdown": str(latest_md)}


def render_markdown(payload: dict[str, Any]) -> str:
    rows = payload["orientation_rows"]
    lines = [
        "# Code Prism / Binary / Conlang Orientation Map",
        "",
        f"Generated: {payload['generated_at']}",
        f"Sample token: `{payload['sample']}`",
        f"Map SHA-256: `{payload['map_sha256']}`",
        "",
        "## Current Status",
        "",
        f"- Code Prism parser sources: {', '.join(payload['code_prism']['parser_supported_sources'])}",
        f"- Code Prism emit targets: {', '.join(payload['code_prism']['emitter_supported_targets'])}",
        f"- CA/STIB targets: {', '.join(payload['ca_isa_stib']['supported_targets'])}",
        f"- CA opcode templates: {payload['ca_isa_stib']['supported_opcode_templates']}",
        f"- Cross-build Tier 1 ops: {payload['cross_build_lattice']['tier1_participating_ops']}",
        "",
        "## Tongue Rows",
        "",
        "| Tongue | Primary | Code Prism Primary | CA/STIB Target | Cube Face | Reversible Face |",
        "|---|---:|---|---|---|---|",
    ]
    for row in rows:
        prism_status = row["code_prism_primary"]["full_source_status"]
        reversible = "yes" if row["conlang_tokenizer"]["reverse_from_face_ok"] else "no"
        ca_target = "yes" if row["ca_stib_target_supported"] else "no"
        lines.append(
            f"| {row['tongue']} | {row['primary_language']} | {prism_status} | {ca_target} | "
            f"{row['cube_token_face_language']} | {reversible} |"
        )
    lines.extend(
        [
            "",
            "## Reversibility Contracts",
            "",
        ]
    )
    for contract in payload["reversibility_contracts"]:
        lines.append(f"- {contract['lane']}: {contract['status']} (`{contract['path']}`)")
    lines.extend(
        [
            "",
            "## Receipts",
            "",
            f"- Bit spine hex: `{payload['bit_spine_hex']['hex']}`",
            f"- Bit spine roundtrip: `{payload['bit_spine_hex']['roundtrip']}`",
            f"- STIB roundtrip: `{payload['ca_isa_stib']['stib']['roundtrip_ok']}`",
            f"- Cube token all faces roundtrip: `{payload['conlang_tokenizers']['python_cube_token']['all_faces_roundtrip']}`",
            "",
            "## Warnings",
            "",
        ]
    )
    for warning in payload["warnings"]:
        lines.append(f"- {warning}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Map Code Prism, binary/hex, and conlang tokenizer orientation.")
    parser.add_argument("--sample", default="compile", help="sample token/text used for reversible receipts")
    parser.add_argument("--out-dir", default="artifacts/code_prism_binary_conlang_map")
    parser.add_argument("--json", action="store_true", help="print full JSON payload")
    parser.add_argument("--check", action="store_true", help="fail if core reversibility receipts fail")
    args = parser.parse_args(argv)

    payload = build_map(sample=args.sample)
    outputs = write_outputs(payload, REPO / args.out_dir)
    payload["artifacts"] = {key: str(Path(value).relative_to(REPO)).replace("\\", "/") for key, value in outputs.items()}

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            json.dumps(
                {
                    "schema": payload["schema"],
                    "map_sha256": payload["map_sha256"][:16],
                    "code_prism_sources": payload["code_prism"]["parser_supported_sources"],
                    "code_prism_targets": payload["code_prism"]["emitter_supported_targets"],
                    "ca_stib_targets": payload["ca_isa_stib"]["supported_targets"],
                    "cube_faces_roundtrip": payload["conlang_tokenizers"]["python_cube_token"]["all_faces_roundtrip"],
                    "stib_roundtrip": payload["ca_isa_stib"]["stib"]["roundtrip_ok"],
                    "artifacts": payload["artifacts"],
                },
                indent=2,
                sort_keys=True,
            )
        )

    if args.check:
        bit_ok = all(payload["bit_spine_hex"]["roundtrip"].values())
        stib_ok = bool(payload["ca_isa_stib"]["stib"]["roundtrip_ok"])
        cube_ok = bool(payload["conlang_tokenizers"]["python_cube_token"]["all_faces_roundtrip"])
        return 0 if bit_ok and stib_ok and cube_ok else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
