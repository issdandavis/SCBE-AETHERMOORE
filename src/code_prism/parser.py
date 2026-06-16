from __future__ import annotations

import ast
import re
from typing import List

from .models import PrismFunction, PrismModule


def parse_python_to_ir(source: str, module_name: str = "module") -> PrismModule:
    tree = ast.parse(source)
    functions: List[PrismFunction] = []

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        args = [arg.arg for arg in node.args.args]
        docstring = ast.get_docstring(node)
        body_lines = [
            ast.unparse(stmt)
            for stmt in node.body
            if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Constant)
        ]
        if not body_lines:
            body_lines = ["pass"]

        returns = ast.unparse(node.returns) if node.returns is not None else None
        functions.append(
            PrismFunction(
                name=node.name,
                args=args,
                body=body_lines,
                returns=returns,
                docstring=docstring,
                metadata={"source": "python_ast"},
            )
        )

    return PrismModule(
        module_name=module_name,
        source_language="python",
        functions=functions,
        metadata={"constructs": ["function_def"]},
    )


def _find_matching_brace(source: str, open_index: int) -> int:
    depth = 0
    in_string: str | None = None
    escaped = False

    for index in range(open_index, len(source)):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            continue
        if char in {"'", '"', "`"}:
            in_string = char
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("Unbalanced braces in TypeScript function body.")


def _normalise_ts_body(body: str) -> List[str]:
    lines: List[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        if line.endswith(";"):
            line = line[:-1].rstrip()
        lines.append(line)
    return lines


def parse_typescript_to_ir(source: str, module_name: str = "module") -> PrismModule:
    pattern = re.compile(
        r"(?:export\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*(?::\s*([^{]+))?\{",
        re.DOTALL,
    )
    functions: List[PrismFunction] = []

    for match in pattern.finditer(source):
        name = match.group(1)
        raw_args = match.group(2).strip()
        returns = match.group(3).strip() if match.group(3) else None
        close_index = _find_matching_brace(source, match.end() - 1)
        body = source[match.end() : close_index]
        args: List[str] = []
        if raw_args:
            for part in raw_args.split(","):
                token = part.strip()
                if not token:
                    continue
                arg_name = token.split(":")[0].strip()
                args.append(arg_name)
        functions.append(
            PrismFunction(
                name=name,
                args=args,
                body=_normalise_ts_body(body),
                returns=returns,
                metadata={"source": "typescript_regex", "body_source": "safe_subset"},
            )
        )

    return PrismModule(
        module_name=module_name,
        source_language="typescript",
        functions=functions,
        metadata={"constructs": ["function_def"]},
    )


def parse_source_to_ir(source: str, source_language: str, module_name: str = "module") -> PrismModule:
    lang = source_language.lower()
    if lang == "python":
        return parse_python_to_ir(source, module_name=module_name)
    if lang in {"typescript", "ts"}:
        return parse_typescript_to_ir(source, module_name=module_name)
    raise ValueError(f"Unsupported source language: {source_language}")
