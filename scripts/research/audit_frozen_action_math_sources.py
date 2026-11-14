"""Audit pinned math sources against Clay's exact action compiler.

This tool prepares evidence only. It does not build a training manifest, load a
model, start an optimizer, dispatch a tool, or authorize promotion.
"""

from __future__ import annotations

import argparse
import ast
from fractions import Fraction
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable, Iterable

SCHEMA = "clay.frozen-action-math-exact-compiler-audit.v1"
GSM8K_ANNOTATION = re.compile(r"<<([^<>]+)=([^<>]+)>>")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _fraction(value: object) -> Fraction:
    return Fraction(str(value).replace(",", "").strip())


def _evaluate(node: ast.AST) -> Fraction:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return _fraction(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _evaluate(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            return Fraction(left // right)
    raise ValueError(f"unsupported arithmetic node: {type(node).__name__}")


def _safe_value(expression: str) -> Fraction:
    return _evaluate(ast.parse(expression, mode="eval"))


def _fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _load_compiler(
    root: Path,
) -> tuple[Callable[[str], dict[str, Any]], dict[str, str]]:
    compiler_root = root.resolve(strict=True)
    worktree_root = compiler_root.parents[1]
    for candidate in (compiler_root, worktree_root):
        if str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
    module = importlib.import_module("action_compiler")
    source = Path(module.__file__).resolve(strict=True)
    compiler = module.ActionCompiler()
    return compiler.compile, {
        "module": str(source),
        "sha256": _sha256_file(source),
    }


def _source_rows(gsm8k: Path, svamp: Path) -> Iterable[dict[str, Any]]:
    with gsm8k.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            raw = json.loads(line)
            matches = GSM8K_ANNOTATION.findall(str(raw["answer"]))
            expression = matches[-1][0] if matches else None
            expected = matches[-1][1] if matches else None
            yield {
                "source": "openai-gsm8k",
                "source_row_id": f"gsm8k-train:{index}",
                "source_index": index,
                "prompt": str(raw["question"]),
                "source_expression": expression,
                "expected": expected,
            }

    payload = json.loads(svamp.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("SVAMP source must contain a JSON array")
    for index, raw in enumerate(payload):
        prompt = f"{str(raw['Body']).strip()} {str(raw['Question']).strip()}".strip()
        yield {
            "source": "arkilpatel-svamp",
            "source_row_id": f"svamp:{raw['ID']}",
            "source_index": index,
            "prompt": prompt,
            "source_expression": str(raw["Equation"]),
            "expected": raw["Answer"],
        }


def _audit_row(
    row: dict[str, Any],
    *,
    compile_action: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    source_expression = row["source_expression"]
    normalized = None if source_expression is None else str(source_expression).replace(",", "").strip()
    safe_value: Fraction | None = None
    value_consistent = False
    arithmetic_error: dict[str, str] | None = None
    if normalized is not None:
        try:
            safe_value = _safe_value(normalized)
            value_consistent = safe_value == _fraction(row["expected"])
        except (ValueError, ZeroDivisionError, SyntaxError) as error:
            arithmetic_error = {"type": type(error).__name__, "message": str(error)}

    compiler_receipt = None
    compiler_error: dict[str, str] | None = None
    if normalized is not None:
        try:
            compiled = compile_action(f"math :: {normalized}")
            compiler_receipt = str(compiled["receipt_sha256"])
        except Exception as error:  # The external exact compiler owns its error taxonomy.
            compiler_error = {"type": type(error).__name__, "message": str(error)}

    accepted = bool(value_consistent and compiler_receipt is not None)
    return {
        "accepted": accepted,
        "arithmetic_error": arithmetic_error,
        "compiler_error": compiler_error,
        "compiler_receipt_sha256": compiler_receipt,
        "expected": None if row["expected"] is None else str(row["expected"]),
        "normalized_expression": normalized,
        "prompt_sha256": _prompt_sha256(row["prompt"]),
        "safe_value": None if safe_value is None else _fraction_text(safe_value),
        "source": row["source"],
        "source_expression": source_expression,
        "source_index": row["source_index"],
        "source_row_id": row["source_row_id"],
        "value_consistent": value_consistent,
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [row for row in rows if row["accepted"]]
    rejected = [row for row in rows if not row["accepted"]]
    return {
        "accepted": len(accepted),
        "accepted_ledger_sha256": hashlib.sha256(
            "".join(_canonical_json(row) + "\n" for row in accepted).encode("utf-8")
        ).hexdigest(),
        "compiler_rejected": sum(row["compiler_error"] is not None for row in rows),
        "missing_expression": sum(row["normalized_expression"] is None for row in rows),
        "rejected": len(rejected),
        "rejected_row_ids": [row["source_row_id"] for row in rejected],
        "total": len(rows),
        "value_inconsistent": sum(
            row["normalized_expression"] is not None and not row["value_consistent"] for row in rows
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gsm8k", required=True, type=Path)
    parser.add_argument("--svamp", required=True, type=Path)
    parser.add_argument("--action-compiler-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ledger-output", type=Path)
    parser.add_argument("--limit-per-source", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gsm8k = args.gsm8k.resolve(strict=True)
    svamp = args.svamp.resolve(strict=True)
    compile_action, compiler_identity = _load_compiler(args.action_compiler_root)
    limit = args.limit_per_source
    if limit is not None and limit <= 0:
        raise ValueError("--limit-per-source must be positive")

    audited: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for row in _source_rows(gsm8k, svamp):
        source = str(row["source"])
        count = seen.get(source, 0)
        seen[source] = count + 1
        if limit is not None and count >= limit:
            continue
        audited.append(_audit_row(row, compile_action=compile_action))

    ledger_output = (args.ledger_output or args.output.with_suffix(".rows.jsonl")).resolve()
    ledger_text = "".join(_canonical_json(row) + "\n" for row in audited)
    _atomic_text(ledger_output, ledger_text)
    summaries = {
        source: _summarize([row for row in audited if row["source"] == source])
        for source in ("openai-gsm8k", "arkilpatel-svamp")
    }
    report = {
        "schema": SCHEMA,
        "status": "PARTIAL" if limit is not None else "COMPLETE_NO_ADMISSION",
        "authority": {
            "dataset_admission": "NONE",
            "launch": "NONE",
            "partial_unfreeze": "NONE",
            "promotion": "NONE",
            "tool_dispatch": "DISABLED",
        },
        "compiler": compiler_identity,
        "ledger": {
            "bytes": len(ledger_text.encode("utf-8")),
            "path": str(ledger_output),
            "rows": len(audited),
            "sha256": hashlib.sha256(ledger_text.encode("utf-8")).hexdigest(),
        },
        "limit_per_source": limit,
        "sources": {
            "openai-gsm8k": {
                "path": str(gsm8k),
                "sha256": _sha256_file(gsm8k),
                **summaries["openai-gsm8k"],
            },
            "arkilpatel-svamp": {
                "path": str(svamp),
                "sha256": _sha256_file(svamp),
                **summaries["arkilpatel-svamp"],
            },
        },
        "claim_boundary": (
            "This exact-compiler audit prepares candidate rows only. It does not create "
            "a source-authority ledger or material dataset and authorizes no training."
        ),
    }
    output = args.output.resolve()
    _atomic_text(output, json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        _canonical_json(
            {
                "ledger_sha256": report["ledger"]["sha256"],
                "output": str(output),
                "sources": summaries,
                "status": report["status"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
