"""Build Six Sacred Tongues syntax-alignment SFT records.

The generator teaches a model that each coding concept has one semantic block
with six aligned surfaces. The immediate seed is the "custom programming
language" pattern of grammar -> AST -> lowering, plus first-class records,
enums, matrix values, explainable errors, and token-efficient boring syntax.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "sacred_tongue_syntax_alignment_v1"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "training-data" / "sft"
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "model_training" / "sacred_tongue_syntax_alignment_v1.json"

TRAIN_NAME = "sacred_tongue_syntax_alignment_v1_train.sft.jsonl"
HOLDOUT_NAME = "sacred_tongue_syntax_alignment_v1_holdout.sft.jsonl"
MANIFEST_NAME = "sacred_tongue_syntax_alignment_v1_manifest.json"

TONGUES: list[dict[str, str]] = [
    {
        "code": "KO",
        "full_name": "Kor'aelin",
        "coding_primary": "Python",
        "paradigm": "prefix control and orchestration",
    },
    {
        "code": "AV",
        "full_name": "Avali",
        "coding_primary": "TypeScript",
        "paradigm": "message-facing typed application code",
    },
    {
        "code": "RU",
        "full_name": "Runethic",
        "coding_primary": "Rust",
        "paradigm": "safety, ownership, and explicit failure",
    },
    {
        "code": "CA",
        "full_name": "Cassisivadan",
        "coding_primary": "Mathematica",
        "paradigm": "symbolic computation and matrix algebra",
    },
    {
        "code": "UM",
        "full_name": "Umbroth",
        "coding_primary": "Haskell",
        "paradigm": "pure functional transformation",
    },
    {
        "code": "DR",
        "full_name": "Draumric",
        "coding_primary": "Markdown",
        "paradigm": "literate specification and reproducible blocks",
    },
]

SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE coding alignment tutor. Teach the Six Sacred Tongues as full-name "
    "coding primaries: Kor'aelin with Python, Avali with TypeScript, Runethic with Rust, "
    "Cassisivadan with Mathematica, Umbroth with Haskell, and Draumric with Markdown. "
    "Preserve one concept id, one semantic AST, six aligned syntax surfaces, and deterministic invariants."
)


def _matrix_surfaces() -> dict[str, dict[str, str]]:
    return {
        "Kor'aelin": {
            "syntax": "matrix = [[1.0, 2.0], [3.0, 4.0]]",
            "type": "list[list[float]]",
            "lowering": "Python list of rows; optional NumPy lowering is np.array(matrix, dtype=float).",
        },
        "Avali": {
            "syntax": "const matrix: number[][] = [[1, 2], [3, 4]];",
            "type": "number[][]",
            "lowering": "TypeScript nested number arrays with explicit row-major intent.",
        },
        "Runethic": {
            "syntax": "let matrix: Vec<Vec<f64>> = vec![vec![1.0, 2.0], vec![3.0, 4.0]];",
            "type": "Vec<Vec<f64>>",
            "lowering": "Rust owned row vectors; invalid ragged rows must return an error.",
        },
        "Cassisivadan": {
            "syntax": "matrix = {{1., 2.}, {3., 4.}}",
            "type": "Matrix expression",
            "lowering": "Mathematica list-of-lists; Dimensions[matrix] is the shape witness.",
        },
        "Umbroth": {
            "syntax": "matrix :: [[Double]]\nmatrix = [[1.0, 2.0], [3.0, 4.0]]",
            "type": "[[Double]]",
            "lowering": "Haskell nested lists; pure functions validate rectangular shape before use.",
        },
        "Draumric": {
            "syntax": "```matrix\n1.0 2.0\n3.0 4.0\n```",
            "type": "Markdown fenced matrix block",
            "lowering": "Markdown table or fenced block with a declared row-major shape witness.",
        },
    }


def _shape_surfaces() -> dict[str, dict[str, str]]:
    return {
        "Kor'aelin": {
            "syntax": "shape = (len(matrix), len(matrix[0]) if matrix else 0)",
            "type": "tuple[int, int]",
            "lowering": "Python tuple rows, columns.",
        },
        "Avali": {
            "syntax": "const shape: [number, number] = [matrix.length, matrix[0]?.length ?? 0];",
            "type": "[number, number]",
            "lowering": "TypeScript tuple rows, columns.",
        },
        "Runethic": {
            "syntax": "let shape: (usize, usize) = (matrix.len(), matrix.first().map_or(0, |r| r.len()));",
            "type": "(usize, usize)",
            "lowering": "Rust tuple rows, columns.",
        },
        "Cassisivadan": {
            "syntax": "shape = Dimensions[matrix]",
            "type": "List[Integer, Integer]",
            "lowering": "Mathematica Dimensions returns rows and columns.",
        },
        "Umbroth": {
            "syntax": "shape m = (length m, if null m then 0 else length (head m))",
            "type": "[[a]] -> (Int, Int)",
            "lowering": "Haskell pure shape function.",
        },
        "Draumric": {
            "syntax": "shape: rows=2 columns=2",
            "type": "Markdown metadata line",
            "lowering": "Markdown shape witness attached to the fenced matrix block.",
        },
    }


def _matmul_surfaces() -> dict[str, dict[str, str]]:
    return {
        "Kor'aelin": {
            "syntax": "product = [[sum(a*b for a, b in zip(row, col)) for col in zip(*right)] for row in left]",
            "type": "list[list[float]]",
            "lowering": "Python pure fallback; NumPy lowering is left @ right when arrays are validated.",
        },
        "Avali": {
            "syntax": "const product = left.map(row => transpose(right).map(col => dot(row, col)));",
            "type": "number[][]",
            "lowering": "TypeScript map over rows and transposed columns.",
        },
        "Runethic": {
            "syntax": "let product = matmul(&left, &right)?;",
            "type": "Result<Vec<Vec<f64>>, MatrixError>",
            "lowering": "Rust checked call; dimension mismatch returns MatrixError.",
        },
        "Cassisivadan": {
            "syntax": "product = left . right",
            "type": "Matrix expression",
            "lowering": "Mathematica Dot after Dimensions[left][[2]] == Dimensions[right][[1]].",
        },
        "Umbroth": {
            "syntax": "product = [[sum (zipWith (*) row col) | col <- transpose right] | row <- left]",
            "type": "[[Double]]",
            "lowering": "Haskell list comprehension over rows and transposed columns.",
        },
        "Draumric": {
            "syntax": "matrix-product:\n  inputs: [left, right]\n  invariant: left.columns == right.rows",
            "type": "Markdown operation block",
            "lowering": "Markdown reproducible recipe with explicit dimension invariant.",
        },
    }


def _record_surfaces() -> dict[str, dict[str, str]]:
    return {
        "Kor'aelin": {
            "syntax": "class Listing(BaseModel):\n    price: float\n    beds: int",
            "type": "Pydantic model",
            "lowering": "Python validation model with explicit fields.",
        },
        "Avali": {
            "syntax": "interface Listing { price: number; beds: number }",
            "type": "TypeScript interface",
            "lowering": "TypeScript structural type.",
        },
        "Runethic": {
            "syntax": "struct Listing { price: f64, beds: u32 }",
            "type": "Rust struct",
            "lowering": "Rust owned record with typed fields.",
        },
        "Cassisivadan": {
            "syntax": "Listing[price_Real, beds_Integer]",
            "type": "Symbolic record pattern",
            "lowering": "Mathematica head with typed pattern constraints.",
        },
        "Umbroth": {
            "syntax": "data Listing = Listing { price :: Double, beds :: Int }",
            "type": "Haskell algebraic data type",
            "lowering": "Haskell named-field data constructor.",
        },
        "Draumric": {
            "syntax": "| field | type |\n| price | number |\n| beds | integer |",
            "type": "Markdown schema table",
            "lowering": "Markdown schema witness for generated code.",
        },
    }


def _enum_surfaces() -> dict[str, dict[str, str]]:
    return {
        "Kor'aelin": {
            "syntax": "class Gate(str, Enum):\n    ALLOW = 'ALLOW'\n    DENY = 'DENY'",
            "type": "Python Enum",
            "lowering": "Python string enum for stable serialization.",
        },
        "Avali": {
            "syntax": "type Gate = 'ALLOW' | 'DENY';",
            "type": "TypeScript literal union",
            "lowering": "TypeScript finite choice set.",
        },
        "Runethic": {
            "syntax": "enum Gate { Allow, Deny }",
            "type": "Rust enum",
            "lowering": "Rust closed sum type.",
        },
        "Cassisivadan": {
            "syntax": "Gate /: ValidGateQ[Gate['ALLOW' | 'DENY']] := True",
            "type": "Symbolic finite domain",
            "lowering": "Mathematica symbolic domain predicate.",
        },
        "Umbroth": {
            "syntax": "data Gate = Allow | Deny deriving (Eq, Show)",
            "type": "Haskell sum type",
            "lowering": "Haskell closed constructor set.",
        },
        "Draumric": {
            "syntax": "gate-values: [ALLOW, DENY]",
            "type": "Markdown enum list",
            "lowering": "Markdown finite-domain declaration.",
        },
    }


def _error_surfaces() -> dict[str, dict[str, str]]:
    return {
        "Kor'aelin": {
            "syntax": "raise MatrixError('dimension mismatch', expected='left.columns == right.rows')",
            "type": "Python exception",
            "lowering": "Python explainable error with expected invariant.",
        },
        "Avali": {
            "syntax": "throw new MatrixError('dimension mismatch', { expected: 'left.columns == right.rows' });",
            "type": "TypeScript Error",
            "lowering": "TypeScript structured error object.",
        },
        "Runethic": {
            "syntax": "return Err(MatrixError::DimensionMismatch { expected: 'left.columns == right.rows' });",
            "type": "Result error",
            "lowering": "Rust recoverable error path.",
        },
        "Cassisivadan": {
            "syntax": "Failure['DimensionMismatch', <|'Expected' -> 'left.columns == right.rows'|>]",
            "type": "Failure expression",
            "lowering": "Mathematica symbolic failure object.",
        },
        "Umbroth": {
            "syntax": "Left (DimensionMismatch 'left.columns == right.rows')",
            "type": "Either MatrixError a",
            "lowering": "Haskell typed failure value.",
        },
        "Draumric": {
            "syntax": "error:\n  reason: dimension mismatch\n  expected: left.columns == right.rows",
            "type": "Markdown diagnostic block",
            "lowering": "Markdown audit record for failed invariant.",
        },
    }


def _lsp_diagnostic_surfaces() -> dict[str, dict[str, str]]:
    return {
        "Kor'aelin": {
            "syntax": "diagnostic = {'range': span, 'severity': 'error', 'message': 'dimension mismatch'}",
            "type": "dict[str, object]",
            "lowering": "Python LSP-style diagnostic packet for orchestration and quick repair.",
        },
        "Avali": {
            "syntax": "const diagnostic: Diagnostic = { range, severity: DiagnosticSeverity.Error, message };",
            "type": "Language Server Protocol Diagnostic",
            "lowering": "TypeScript native LSP object shape for editor/tool integration.",
        },
        "Runethic": {
            "syntax": "Diagnostic { range, severity: Severity::Error, message }",
            "type": "Diagnostic struct",
            "lowering": "Rust typed diagnostic for fail-closed tooling.",
        },
        "Cassisivadan": {
            "syntax": "Diagnostic[<|'Range' -> span, 'Severity' -> 'Error', 'Message' -> message|>]",
            "type": "Symbolic diagnostic expression",
            "lowering": "Mathematica symbolic diagnostic used for rule-based verification.",
        },
        "Umbroth": {
            "syntax": "Diagnostic { range = span, severity = Error, message = msg }",
            "type": "Diagnostic record",
            "lowering": "Haskell record value passed through pure analysis functions.",
        },
        "Draumric": {
            "syntax": "diagnostic:\n  severity: error\n  message: dimension mismatch\n  range: line:column-span",
            "type": "Markdown diagnostic block",
            "lowering": "Markdown audit block that humans and agents can both read.",
        },
    }


def _vim_operator_motion_surfaces() -> dict[str, dict[str, str]]:
    return {
        "Kor'aelin": {
            "syntax": "edit = apply_operator('change', motion='inside_function', text=replacement)",
            "type": "EditorEdit",
            "lowering": "Python command object: operator plus motion plus payload.",
        },
        "Avali": {
            "syntax": "const edit = vim.operator('change').motion('insideFunction').text(replacement);",
            "type": "EditorEdit",
            "lowering": "TypeScript fluent command for compact editor actions.",
        },
        "Runethic": {
            "syntax": "Edit::new(Operator::Change, Motion::InsideFunction).with_text(replacement)",
            "type": "Edit",
            "lowering": "Rust enum-backed operator/motion command with explicit payload.",
        },
        "Cassisivadan": {
            "syntax": "Edit[Change, InsideFunction, Replacement -> replacement]",
            "type": "Symbolic edit expression",
            "lowering": "Mathematica symbolic edit that can be transformed or proven before apply.",
        },
        "Umbroth": {
            "syntax": "edit = Edit Change InsideFunction replacement",
            "type": "Edit",
            "lowering": "Haskell algebraic edit constructor.",
        },
        "Draumric": {
            "syntax": "edit:\n  operator: change\n  motion: inside-function\n  payload: replacement",
            "type": "Markdown edit intent block",
            "lowering": "Markdown operator/motion/action packet for review before apply.",
        },
    }


def _binary_wave_packet_surfaces() -> dict[str, dict[str, str]]:
    return {
        "Kor'aelin": {
            "syntax": "packet = pack_bits(op='diagnose', phase=0, lane='Kor\\'aelin', amplitude=1.0)",
            "type": "bytes",
            "lowering": "Python transport packet after semantic intent is validated.",
        },
        "Avali": {
            "syntax": "const packet = packBits({ op: 'diagnose', phase: 1, lane: 'Avali', amplitude: 1.618 });",
            "type": "Uint8Array",
            "lowering": "TypeScript byte packet for browser/editor transport.",
        },
        "Runethic": {
            "syntax": "let packet: Vec<u8> = pack_bits(BinaryWave { op, phase, lane, amplitude })?;",
            "type": "Vec<u8>",
            "lowering": "Rust checked binary packet with explicit error handling.",
        },
        "Cassisivadan": {
            "syntax": "packet = BinaryWaveEncode[<|'Op' -> op, 'Phase' -> phase, 'Amplitude' -> amplitude|>]",
            "type": "ByteArray",
            "lowering": "Mathematica symbolic packet encoded only after invariant checks.",
        },
        "Umbroth": {
            "syntax": "packet = packBits BinaryWave { op = Diagnose, phase = phase, amplitude = amp }",
            "type": "ByteString",
            "lowering": "Haskell pure binary encoder for validated wave state.",
        },
        "Draumric": {
            "syntax": "binary-wave:\n  op: diagnose\n  phase: 0\n  amplitude: 1.000\n  transport: byte-packet",
            "type": "Markdown transport receipt",
            "lowering": "Markdown receipt explaining the binary packet without hiding intent.",
        },
    }


SYNTAX_BLOCKS: list[dict[str, Any]] = [
    {
        "concept_id": "matrix_literal",
        "title": "First-class matrix literal",
        "semantic_ast": {
            "node": "MatrixLiteral",
            "shape": [2, 2],
            "row_major_values": [[1.0, 2.0], [3.0, 4.0]],
        },
        "invariants": ["rectangular", "row_major", "numeric_cells", "same_shape_across_tongues"],
        "surfaces": _matrix_surfaces(),
    },
    {
        "concept_id": "matrix_shape",
        "title": "Matrix shape witness",
        "semantic_ast": {"node": "MatrixShape", "input": "matrix", "output": ["rows", "columns"]},
        "invariants": ["rows >= 0", "columns >= 0", "empty_matrix_columns_zero"],
        "surfaces": _shape_surfaces(),
    },
    {
        "concept_id": "matrix_multiply",
        "title": "Checked matrix multiplication",
        "semantic_ast": {"node": "MatrixMultiply", "left": "left", "right": "right"},
        "invariants": ["left.columns == right.rows", "output.rows == left.rows", "output.columns == right.columns"],
        "surfaces": _matmul_surfaces(),
    },
    {
        "concept_id": "record_type",
        "title": "Record type",
        "semantic_ast": {"node": "RecordType", "name": "Listing", "fields": {"price": "number", "beds": "integer"}},
        "invariants": ["field_names_stable", "field_types_explicit", "serializable"],
        "surfaces": _record_surfaces(),
    },
    {
        "concept_id": "enum_type",
        "title": "Finite enum type",
        "semantic_ast": {"node": "EnumType", "name": "Gate", "values": ["ALLOW", "DENY"]},
        "invariants": ["closed_value_set", "stable_wire_values", "invalid_values_rejected"],
        "surfaces": _enum_surfaces(),
    },
    {
        "concept_id": "explainable_error",
        "title": "Explainable error object",
        "semantic_ast": {
            "node": "ExplainableError",
            "error": "DimensionMismatch",
            "expected": "left.columns == right.rows",
        },
        "invariants": ["machine_readable_reason", "human_readable_expected_condition", "no_silent_failure"],
        "surfaces": _error_surfaces(),
    },
    {
        "concept_id": "lsp_diagnostic",
        "title": "Language Server Protocol diagnostic",
        "semantic_ast": {
            "node": "LanguageServerProtocolDiagnostic",
            "range": "source span",
            "severity": "error",
            "message": "dimension mismatch",
        },
        "invariants": ["range_required", "severity_required", "message_required", "no_apply_without_diagnostic_gate"],
        "surfaces": _lsp_diagnostic_surfaces(),
    },
    {
        "concept_id": "vim_operator_motion",
        "title": "Vim-style operator motion edit",
        "semantic_ast": {
            "node": "EditorOperatorMotion",
            "operator": "change",
            "motion": "inside_function",
            "payload": "replacement",
        },
        "invariants": ["operator_required", "motion_required", "payload_required_for_change", "review_before_apply"],
        "surfaces": _vim_operator_motion_surfaces(),
    },
    {
        "concept_id": "binary_wave_tool_packet",
        "title": "Binary wave tool packet",
        "semantic_ast": {
            "node": "BinaryWaveToolPacket",
            "op": "diagnose",
            "phase": "tongue phase",
            "amplitude": "phi-weighted lane strength",
        },
        "invariants": [
            "semantic_intent_precedes_transport",
            "phase_is_bounded",
            "amplitude_is_non_negative",
            "binary_packet_has_markdown_receipt",
        ],
        "surfaces": _binary_wave_packet_surfaces(),
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_blocks(blocks: list[dict[str, Any]] = SYNTAX_BLOCKS) -> None:
    full_names = {tongue["full_name"] for tongue in TONGUES}
    for block in blocks:
        surfaces = block.get("surfaces", {})
        if set(surfaces) != full_names:
            missing = sorted(full_names - set(surfaces))
            extra = sorted(set(surfaces) - full_names)
            raise ValueError(f"{block['concept_id']} surface mismatch missing={missing} extra={extra}")
        for tongue in TONGUES:
            surface = surfaces[tongue["full_name"]]
            for field in ("syntax", "type", "lowering"):
                if not str(surface.get(field, "")).strip():
                    raise ValueError(f"{block['concept_id']} {tongue['full_name']} missing {field}")


def _assistant_payload(block: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "six_sacred_tongues_syntax_alignment",
        "source_inspiration": {
            "video_title": "I Built My Own Programming Language",
            "channel": "youniss",
            "url": "https://www.youtube.com/watch?v=XGINo_KUqBg",
            "transferable_lessons": [
                "grammar to abstract syntax tree to lowering",
                "first-class matrix type backed by an optimized runtime",
                "records and enums as explicit model-facing types",
                "boring opinionated syntax to reduce token ambiguity",
                "explainable errors as feedback for humans and language models",
            ],
        },
        "tongue_map": TONGUES,
        "concept_id": block["concept_id"],
        "title": block["title"],
        "semantic_ast": block["semantic_ast"],
        "invariants": block["invariants"],
        "surfaces": block["surfaces"],
        "alignment_rule": (
            "A model may change the surface syntax for one Sacred Tongue only if the semantic_ast and invariants "
            "still round-trip across Kor'aelin, Avali, Runethic, Cassisivadan, Umbroth, and Draumric."
        ),
    }


def build_records(blocks: list[dict[str, Any]] = SYNTAX_BLOCKS) -> list[dict[str, Any]]:
    validate_blocks(blocks)
    records = []
    for block in blocks:
        assistant = _assistant_payload(block)
        user_content = (
            "Align this coding concept across all Six Sacred Tongues. Return one semantic AST, invariants, "
            "and six syntax surfaces using full tongue names.\n\n"
            f"CONCEPT_ID: {block['concept_id']}\nTITLE: {block['title']}"
        )
        records.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": _json_dumps(assistant)},
                ],
                "meta": {
                    "schema_version": SCHEMA_VERSION,
                    "source_family": "sacred_tongue_syntax_alignment",
                    "source_script": "scripts/training_data/build_sacred_tongue_syntax_alignment_sft.py",
                    "concept_id": block["concept_id"],
                    "record_type": "syntax_alignment",
                    "split": "holdout" if block["concept_id"] in {"matrix_multiply"} else "train",
                    "tongue_full_names": [tongue["full_name"] for tongue in TONGUES],
                    "coding_primaries": {tongue["full_name"]: tongue["coding_primary"] for tongue in TONGUES},
                    "goal_sha256": _sha256_text(user_content),
                    "assistant_sha256": _sha256_text(_json_dumps(assistant)),
                },
            }
        )
    return records


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(_json_dumps(row) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def write_outputs(
    records: list[dict[str, Any]],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> dict[str, str]:
    output_dir = output_dir if output_dir.is_absolute() else REPO_ROOT / output_dir
    config_path = config_path if config_path.is_absolute() else REPO_ROOT / config_path
    train = [row for row in records if row["meta"]["split"] == "train"]
    holdout = [row for row in records if row["meta"]["split"] == "holdout"]
    train_path = output_dir / TRAIN_NAME
    holdout_path = output_dir / HOLDOUT_NAME
    manifest_path = output_dir / MANIFEST_NAME

    _write_jsonl(train_path, train)
    _write_jsonl(holdout_path, holdout)

    config_payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "tongues": TONGUES,
        "syntax_blocks": SYNTAX_BLOCKS,
        "source_inspiration": {
            "title": "I Built My Own Programming Language",
            "channel": "youniss",
            "url": "https://www.youtube.com/watch?v=XGINo_KUqBg",
        },
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config_payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "record_count": len(records),
        "train_count": len(train),
        "holdout_count": len(holdout),
        "train_path": str(train_path.relative_to(REPO_ROOT)),
        "holdout_path": str(holdout_path.relative_to(REPO_ROOT)),
        "config_path": str(config_path.relative_to(REPO_ROOT)),
        "concept_ids": [row["meta"]["concept_id"] for row in records],
        "verification": ["python -m pytest tests/training_data/test_build_sacred_tongue_syntax_alignment_sft.py -q"],
        "notes": [
            "This is an experimental eval-only alignment set until every surface has production adapter evidence.",
            "Cassisivadan is aligned to Mathematica for symbolic computation and matrix algebra.",
            "Every record keeps the full Sacred Tongue names visible.",
            "Matrix syntax is treated as a first-class aligned block, not a decorative example.",
        ],
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "train": str(train_path),
        "holdout": str(holdout_path),
        "manifest": str(manifest_path),
        "config": str(config_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--config-path", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    records = build_records(deepcopy(SYNTAX_BLOCKS))
    paths = write_outputs(records, args.output_dir, args.config_path)
    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": SCHEMA_VERSION,
                "record_count": len(records),
                "train_count": sum(1 for row in records if row["meta"]["split"] == "train"),
                "holdout_count": sum(1 for row in records if row["meta"]["split"] == "holdout"),
                "paths": paths,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
