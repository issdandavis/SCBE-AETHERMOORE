from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import List


@dataclass
class ValidationIssue:
    code: str
    message: str


def _balanced_braces(source: str, open_char: str, close_char: str) -> bool:
    count = 0
    for ch in source:
        if ch == open_char:
            count += 1
        elif ch == close_char:
            count -= 1
            if count < 0:
                return False
    return count == 0


def validate_generated_code(source: str, language: str) -> List[ValidationIssue]:
    aliases = {
        "ts": "typescript",
        "js": "typescript",
        "javascript": "typescript",
        "rs": "rust",
        "jl": "julia",
        "hs": "haskell",
        "golang": "go",
    }
    lang = aliases.get(language.lower(), language.lower())
    issues: List[ValidationIssue] = []

    if lang == "python":
        try:
            ast.parse(source)
        except SyntaxError as exc:
            issues.append(
                ValidationIssue(
                    code="python_syntax_error",
                    message=f"SyntaxError line {exc.lineno}: {exc.msg}",
                )
            )
        return issues

    if lang in {"typescript", "ts"}:
        if "export function" not in source:
            issues.append(
                ValidationIssue(
                    code="ts_missing_export_function",
                    message="No exported function found.",
                )
            )
        if not _balanced_braces(source, "{", "}"):
            issues.append(
                ValidationIssue(
                    code="ts_unbalanced_braces",
                    message="Unbalanced braces in TypeScript output.",
                )
            )
        return issues

    if lang == "go":
        if "package " not in source:
            issues.append(ValidationIssue(code="go_missing_package", message="Missing package declaration."))
        if "func " not in source:
            issues.append(ValidationIssue(code="go_missing_function", message="No Go function emitted."))
        if not _balanced_braces(source, "{", "}"):
            issues.append(
                ValidationIssue(
                    code="go_unbalanced_braces",
                    message="Unbalanced braces in Go output.",
                )
            )
        return issues

    if lang == "rust":
        if "fn " not in source:
            issues.append(ValidationIssue(code="rust_missing_function", message="No Rust function emitted."))
        if not _balanced_braces(source, "{", "}"):
            issues.append(ValidationIssue(code="rust_unbalanced_braces", message="Unbalanced braces in Rust output."))
        return issues

    if lang == "c":
        if "(" not in source or ")" not in source:
            issues.append(ValidationIssue(code="c_missing_function", message="No C function emitted."))
        if not _balanced_braces(source, "{", "}"):
            issues.append(ValidationIssue(code="c_unbalanced_braces", message="Unbalanced braces in C output."))
        return issues

    if lang == "julia":
        if "function " not in source:
            issues.append(ValidationIssue(code="julia_missing_function", message="No Julia function emitted."))
        if source.count("function ") != source.count("\nend"):
            issues.append(ValidationIssue(code="julia_unbalanced_function", message="Julia function/end mismatch."))
        return issues

    if lang == "haskell":
        if "=" not in source:
            issues.append(ValidationIssue(code="haskell_missing_definition", message="No Haskell definition emitted."))
        return issues

    issues.append(ValidationIssue(code="unsupported_language", message=f"Unsupported language {language}."))
    return issues
