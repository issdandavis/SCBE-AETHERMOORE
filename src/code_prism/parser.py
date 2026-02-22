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
            ast.unparse(stmt) for stmt in node.body if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Constant)
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


def parse_typescript_to_ir(source: str, module_name: str = "module") -> PrismModule:
    pattern = re.compile(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*\{", re.DOTALL)
    functions: List[PrismFunction] = []

    for match in pattern.finditer(source):
        name = match.group(1)
        raw_args = match.group(2).strip()
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
                body=["// TODO: translate implementation"],
                metadata={"source": "typescript_regex"},
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

