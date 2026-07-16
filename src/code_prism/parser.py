from __future__ import annotations

import ast
import re
from typing import List

from .models import PrismFunction, PrismModule

LANG_ALIASES = {
    "ts": "typescript",
    "js": "typescript",
    "javascript": "typescript",
    "rs": "rust",
    "c99": "c",
    "jl": "julia",
    "hs": "haskell",
    "golang": "go",
}


def _lang(source_language: str) -> str:
    lang = source_language.lower()
    return LANG_ALIASES.get(lang, lang)


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
        for keyword in ("const ", "let ", "var "):
            if line.startswith(keyword):
                line = line[len(keyword) :].strip()
                break
        lines.append(line)
    return lines


def _strip_line_comments(line: str, language: str) -> str:
    if language in {"rust", "go", "c", "typescript"} and "//" in line:
        return line.split("//", 1)[0].rstrip()
    if language == "haskell" and "--" in line:
        return line.split("--", 1)[0].rstrip()
    return line


def _normalise_assignment(line: str, language: str) -> str:
    line = line.strip()
    if not line:
        return line
    if language == "go" and ":=" in line:
        name, value = line.split(":=", 1)
        return f"{name.strip()} = {value.strip()}"
    if language == "rust":
        line = re.sub(r"^let\s+mut\s+", "", line)
        line = re.sub(r"^let\s+", "", line)
    if language == "julia":
        line = re.sub(r"^local\s+", "", line)
    if language == "c":
        line = re.sub(
            r"^(?:const\s+)?(?:unsigned\s+|signed\s+)?(?:int|long|float|double|bool|char|size_t)\s+\*?\s*",
            "",
            line,
        )
    if language == "go":
        line = re.sub(r"^var\s+", "", line)
    return line.strip()


def _normalise_c_family_body(body: str, language: str) -> List[str]:
    normalised: List[str] = []
    raw_statements: List[str] = []
    for raw_line in body.replace(";", ";\n").splitlines():
        line = _strip_line_comments(raw_line.strip(), language)
        if not line:
            continue
        for part in [piece.strip() for piece in line.split(";") if piece.strip()]:
            raw_statements.append(part)

    for index, statement in enumerate(raw_statements):
        line = _normalise_assignment(statement, language)
        if not line:
            continue
        if line.startswith("return "):
            normalised.append(line)
            continue
        if language == "rust" and index == len(raw_statements) - 1 and "=" not in line:
            normalised.append(f"return {line}")
            continue
        normalised.append(line)
    return normalised or ["pass"]


def _arg_name(arg: str, language: str = "") -> str:
    token = arg.strip()
    if not token:
        return ""
    if ":" in token:
        token = token.split(":", 1)[0].strip()
    token = token.replace("*", " ").strip()
    parts = token.split()
    if language == "go" and parts:
        return parts[0]
    return parts[-1] if parts else ""


def _parse_braced_functions(
    source: str,
    *,
    language: str,
    pattern: re.Pattern,
    module_name: str,
    name_group: int = 1,
    args_group: int = 2,
    returns_group: int | None = None,
) -> PrismModule:
    functions: List[PrismFunction] = []
    for match in pattern.finditer(source):
        name = match.group(name_group)
        raw_args = match.group(args_group).strip()
        returns = match.group(returns_group).strip() if returns_group and match.group(returns_group) else None
        close_index = _find_matching_brace(source, match.end() - 1)
        body = source[match.end() : close_index]
        args = [_arg_name(part, language) for part in raw_args.split(",") if _arg_name(part, language)]
        functions.append(
            PrismFunction(
                name=name,
                args=args,
                body=_normalise_c_family_body(body, language),
                returns=returns,
                metadata={"source": f"{language}_safe_subset"},
            )
        )
    return PrismModule(
        module_name=module_name,
        source_language=language,
        functions=functions,
        metadata={"constructs": ["function_def"]},
    )


def parse_rust_to_ir(source: str, module_name: str = "module") -> PrismModule:
    pattern = re.compile(
        r"(?:pub\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*(?:->\s*([^{]+))?\{",
        re.DOTALL,
    )
    return _parse_braced_functions(
        source,
        language="rust",
        pattern=pattern,
        module_name=module_name,
        returns_group=3,
    )


def parse_c_to_ir(source: str, module_name: str = "module") -> PrismModule:
    pattern = re.compile(
        r"(?:static\s+|inline\s+|extern\s+)*([A-Za-z_][A-Za-z0-9_\s\*]*?)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*\{",
        re.DOTALL,
    )
    return _parse_braced_functions(
        source,
        language="c",
        pattern=pattern,
        module_name=module_name,
        name_group=2,
        args_group=3,
        returns_group=1,
    )


def parse_go_to_ir(source: str, module_name: str = "module") -> PrismModule:
    pattern = re.compile(
        r"func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*([A-Za-z_][A-Za-z0-9_\[\]\*]*)?\s*\{",
        re.DOTALL,
    )
    return _parse_braced_functions(
        source,
        language="go",
        pattern=pattern,
        module_name=module_name,
        returns_group=3,
    )


def parse_julia_to_ir(source: str, module_name: str = "module") -> PrismModule:
    pattern = re.compile(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*\n(.*?)\nend", re.DOTALL)
    functions: List[PrismFunction] = []
    for match in pattern.finditer(source):
        args = [_arg_name(part, "julia") for part in match.group(2).split(",") if _arg_name(part, "julia")]
        body = []
        for raw_line in match.group(3).splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            body.append(_normalise_assignment(line, "julia"))
        functions.append(
            PrismFunction(
                name=match.group(1),
                args=args,
                body=body or ["pass"],
                metadata={"source": "julia_safe_subset"},
            )
        )
    return PrismModule(
        module_name=module_name,
        source_language="julia",
        functions=functions,
        metadata={"constructs": ["function_def"]},
    )


def parse_haskell_to_ir(source: str, module_name: str = "module") -> PrismModule:
    functions: List[PrismFunction] = []
    for raw_line in source.splitlines():
        line = _strip_line_comments(raw_line.strip(), "haskell")
        if not line or "::" in line or "=" not in line:
            continue
        left, expr = line.split("=", 1)
        parts = left.split()
        if not parts:
            continue
        name, args = parts[0], parts[1:]
        if not re.match(r"^[a-z_][A-Za-z0-9_']*$", name):
            continue
        functions.append(
            PrismFunction(
                name=name.replace("'", "_prime"),
                args=args,
                body=[f"return {expr.strip()}"],
                metadata={"source": "haskell_safe_subset"},
            )
        )
    return PrismModule(
        module_name=module_name,
        source_language="haskell",
        functions=functions,
        metadata={"constructs": ["function_def"]},
    )


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
    lang = _lang(source_language)
    if lang == "python":
        return parse_python_to_ir(source, module_name=module_name)
    if lang == "typescript":
        return parse_typescript_to_ir(source, module_name=module_name)
    if lang == "go":
        return parse_go_to_ir(source, module_name=module_name)
    if lang == "rust":
        return parse_rust_to_ir(source, module_name=module_name)
    if lang == "c":
        return parse_c_to_ir(source, module_name=module_name)
    if lang == "julia":
        return parse_julia_to_ir(source, module_name=module_name)
    if lang == "haskell":
        return parse_haskell_to_ir(source, module_name=module_name)
    raise ValueError(f"Unsupported source language: {source_language}")
