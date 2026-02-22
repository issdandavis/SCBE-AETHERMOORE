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
    lang = language.lower()
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
            issues.append(ValidationIssue(code="ts_missing_export_function", message="No exported function found."))
        if not _balanced_braces(source, "{", "}"):
            issues.append(ValidationIssue(code="ts_unbalanced_braces", message="Unbalanced braces in TypeScript output."))
        return issues

    if lang == "go":
        if "package " not in source:
            issues.append(ValidationIssue(code="go_missing_package", message="Missing package declaration."))
        if "func " not in source:
            issues.append(ValidationIssue(code="go_missing_function", message="No Go function emitted."))
        if not _balanced_braces(source, "{", "}"):
            issues.append(ValidationIssue(code="go_unbalanced_braces", message="Unbalanced braces in Go output."))
        return issues

    issues.append(ValidationIssue(code="unsupported_language", message=f"Unsupported language {language}."))
    return issues

