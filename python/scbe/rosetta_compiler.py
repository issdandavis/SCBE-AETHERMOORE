"""Rosetta compiler node for prime-coded cross-language programs.

This is the mail-room layer for coding:

    operation names / prime tape
    -> CA opcode route
    -> per-language source lenses
    -> optional runtime deliveries

The canonical identity is the ordered opcode/prime tape. Language source is a
delivery envelope. Runtime execution is attempted only for toolchains available
on the current machine.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .ca_opcode_table import OP_TABLE
from .prime_ir import decode_primes_to_opcodes, encode_opcodes_to_primes
from .tongue_isa import (
    SUPPORTED_TARGETS,
    compile_ca_tokens,
    disassemble,
    wrap_program_source,
)

DEFAULT_TARGETS = ("python", "typescript", "go", "c", "haskell")
RUNTIME_SKIPPED = "SKIPPED_NO_RUNTIME"
RUNTIME_NOT_REQUESTED = "NOT_REQUESTED"
RUNTIME_PASS = "PASS"
RUNTIME_FAIL = "FAIL"


@dataclass(frozen=True)
class RuntimeResult:
    """Result from attempting to execute one target lens."""

    status: str
    value: float | None = None
    error: str = ""
    command: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "value": self.value,
            "error": self.error,
            "command": list(self.command),
        }


@dataclass(frozen=True)
class RosettaArtifact:
    """One target-language envelope for the same canonical program."""

    target: str
    source: str
    source_chars: int
    round_trip_ok: bool
    runtime: RuntimeResult = field(
        default_factory=lambda: RuntimeResult(status=RUNTIME_NOT_REQUESTED)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "source_chars": self.source_chars,
            "round_trip_ok": self.round_trip_ok,
            "runtime": self.runtime.to_dict(),
            "source": self.source,
        }


@dataclass(frozen=True)
class RosettaNode:
    """A cross-language compiler node bound to one prime/opcode identity."""

    schema: str
    fn_name: str
    arg_names: tuple[str, ...]
    run_values: tuple[float, ...] | None
    opcodes: tuple[int, ...]
    op_names: tuple[str, ...]
    prime_sequence: tuple[int, ...]
    artifacts: tuple[RosettaArtifact, ...]
    shortest_target: str | None
    shortest_runnable_target: str | None
    runtime_consensus_ok: bool | None
    problems: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "fn_name": self.fn_name,
            "arg_names": list(self.arg_names),
            "run_values": None if self.run_values is None else list(self.run_values),
            "opcodes": list(self.opcodes),
            "op_names": list(self.op_names),
            "prime_sequence": list(self.prime_sequence),
            "prime_tape": " ".join(str(prime) for prime in self.prime_sequence),
            "shortest_target": self.shortest_target,
            "shortest_runnable_target": self.shortest_runnable_target,
            "runtime_consensus_ok": self.runtime_consensus_ok,
            "problems": list(self.problems),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }


def build_rosetta_node(
    opcodes: Sequence[int],
    *,
    targets: Sequence[str] = DEFAULT_TARGETS,
    fn_name: str = "tongue_fn",
    arg_names: Sequence[str] | None = None,
    run_values: Sequence[float] | None = None,
) -> RosettaNode:
    """Compile one canonical opcode route into many target-language envelopes."""
    normalized_targets = _normalize_targets(targets)
    args = tuple(arg_names or ())
    values = None if run_values is None else tuple(float(value) for value in run_values)
    opcodes_tuple = tuple(int(opcode) for opcode in opcodes)
    prime_sequence = tuple(encode_opcodes_to_primes(opcodes_tuple))
    op_names = tuple(OP_TABLE[opcode].name for opcode in opcodes_tuple)

    artifacts: list[RosettaArtifact] = []
    problems: list[str] = []
    for target in normalized_targets:
        try:
            program = compile_ca_tokens(
                opcodes_tuple,
                target=target,
                fn_name=fn_name,
                arg_names=args,
            )
            source = wrap_program_source(program)
            round_trip_ok = [op for op, _ in program.op_trace] == [
                op for op, _ in disassemble(source)
            ]
            runtime = (
                _run_target(target, source, fn_name, values)
                if values is not None
                else RuntimeResult(status=RUNTIME_NOT_REQUESTED)
            )
            artifacts.append(
                RosettaArtifact(
                    target=target,
                    source=source,
                    source_chars=len(source),
                    round_trip_ok=round_trip_ok,
                    runtime=runtime,
                )
            )
        except (KeyError, ValueError) as exc:
            problems.append(f"{target}: {exc}")

    shortest_target = None
    if artifacts:
        shortest_target = min(
            artifacts, key=lambda artifact: artifact.source_chars
        ).target
    runnable = [
        artifact for artifact in artifacts if artifact.runtime.status == RUNTIME_PASS
    ]
    shortest_runnable_target = None
    if runnable:
        shortest_runnable_target = min(
            runnable, key=lambda artifact: artifact.source_chars
        ).target

    return RosettaNode(
        schema="scbe_rosetta_compiler_node_v1",
        fn_name=fn_name,
        arg_names=args,
        run_values=values,
        opcodes=opcodes_tuple,
        op_names=op_names,
        prime_sequence=prime_sequence,
        artifacts=tuple(artifacts),
        shortest_target=shortest_target,
        shortest_runnable_target=shortest_runnable_target,
        runtime_consensus_ok=_runtime_consensus(artifacts, values is not None),
        problems=tuple(problems),
    )


def build_rosetta_node_from_primes(
    primes: Sequence[int],
    *,
    targets: Sequence[str] = DEFAULT_TARGETS,
    fn_name: str = "tongue_fn",
    arg_names: Sequence[str] | None = None,
    run_values: Sequence[float] | None = None,
) -> RosettaNode:
    """Build a Rosetta node from an ordered prime tape."""
    return build_rosetta_node(
        decode_primes_to_opcodes(primes),
        targets=targets,
        fn_name=fn_name,
        arg_names=arg_names,
        run_values=run_values,
    )


def _normalize_targets(targets: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(target.strip().lower() for target in targets if target.strip())
    if not normalized:
        raise ValueError("at least one target is required")
    unknown = [target for target in normalized if target not in SUPPORTED_TARGETS]
    if unknown:
        raise ValueError(f"unsupported target(s): {', '.join(unknown)}")
    return normalized


def _run_target(
    target: str, source: str, fn_name: str, values: Sequence[float]
) -> RuntimeResult:
    if target == "python":
        return _run_python(source, fn_name, values)
    if target == "typescript":
        return _run_typescript_node(source, fn_name, values)
    if target == "c":
        return _run_c(source, fn_name, values)
    if target == "haskell":
        return _run_haskell(source, fn_name, values)
    if target == "go":
        return _run_go(source, fn_name, values)
    return RuntimeResult(
        status=RUNTIME_SKIPPED, error=f"no runtime adapter for {target}"
    )


def _run_python(source: str, fn_name: str, values: Sequence[float]) -> RuntimeResult:
    namespace: dict[str, Any] = {"__builtins__": {"abs": abs}}
    try:
        exec(source, namespace)  # noqa: S102 -- generated scaffold only
        value = namespace[fn_name](*values)
        return RuntimeResult(status=RUNTIME_PASS, value=float(value))
    except Exception as exc:  # pragma: no cover - defensive path
        return RuntimeResult(status=RUNTIME_FAIL, error=str(exc))


def _run_typescript_node(
    source: str, fn_name: str, values: Sequence[float]
) -> RuntimeResult:
    node = shutil.which("node")
    if not node:
        return RuntimeResult(status=RUNTIME_SKIPPED, error="node not found")
    javascript = _typescript_to_javascript(source, fn_name, values)
    return _run_temp_file((node,), ".js", javascript)


def _typescript_to_javascript(
    source: str, fn_name: str, values: Sequence[float]
) -> str:
    js = re.sub(
        r"export\s+function\s+([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\):\s*number\s*\|\s*null\s*\{",
        lambda match: f"function {match.group(1)}({_strip_ts_args(match.group(2))}) {{",
        source,
        count=1,
    )
    js = js.replace("const _stack: number[]", "const _stack")
    js = js.replace(".pop()!", ".pop()")
    call = ", ".join(_number_literal(value) for value in values)
    return js + f"\nconsole.log(JSON.stringify({fn_name}({call})));\n"


def _strip_ts_args(args: str) -> str:
    names = []
    for raw in args.split(","):
        token = raw.strip()
        if token:
            names.append(token.split(":", 1)[0].strip())
    return ", ".join(names)


def _run_c(source: str, fn_name: str, values: Sequence[float]) -> RuntimeResult:
    gcc = shutil.which("gcc")
    if not gcc:
        return RuntimeResult(status=RUNTIME_SKIPPED, error="gcc not found")
    call = ", ".join(_number_literal(value) for value in values)
    code = (
        "#include <math.h>\n#include <stdio.h>\n"
        f"{source}\n"
        f'int main(void) {{ printf("%.17g\\n", {fn_name}({call})); return 0; }}\n'
    )
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "probe.c"
        exe = Path(tmp) / "probe.exe"
        src.write_text(code, encoding="utf-8")
        compile_cmd = (gcc, str(src), "-lm", "-o", str(exe))
        compiled = subprocess.run(
            compile_cmd, capture_output=True, text=True, timeout=10
        )
        if compiled.returncode != 0:
            return RuntimeResult(
                status=RUNTIME_FAIL,
                error=(compiled.stderr or compiled.stdout).strip(),
                command=compile_cmd,
            )
        return _run_command((str(exe),))


def _run_haskell(source: str, fn_name: str, values: Sequence[float]) -> RuntimeResult:
    runner = shutil.which("runghc")
    if not runner:
        return RuntimeResult(status=RUNTIME_SKIPPED, error="runghc not found")
    call = " ".join(_haskell_number_literal(value) for value in values)
    code = source + f"\nmain = print ({fn_name} {call})\n"
    return _run_temp_file((runner,), ".hs", code)


def _run_go(source: str, fn_name: str, values: Sequence[float]) -> RuntimeResult:
    go = shutil.which("go")
    if not go:
        return RuntimeResult(status=RUNTIME_SKIPPED, error="go not found")
    call = ", ".join(_number_literal(value) for value in values)
    imports = ['"fmt"']
    if "math." in source:
        imports.append('"math"')
    import_block = (
        "import " + imports[0]
        if len(imports) == 1
        else "import (\n\t" + "\n\t".join(imports) + "\n)"
    )
    code = (
        "package main\n\n"
        f"{import_block}\n\n"
        "func caPop1(stack []float64) (float64, []float64) {\n"
        "\treturn stack[len(stack)-1], stack[:len(stack)-1]\n"
        "}\n"
        "func caPop2(stack []float64) (float64, float64, []float64) {\n"
        "\tb := stack[len(stack)-1]\n"
        "\ta := stack[len(stack)-2]\n"
        "\treturn a, b, stack[:len(stack)-2]\n"
        "}\n\n"
        f"{source}\n"
        f'func main() {{ fmt.Printf("%.17g\\n", {fn_name}({call})) }}\n'
    )
    return _run_temp_file((go, "run"), ".go", code)


def _run_temp_file(
    command_prefix: Sequence[str], suffix: str, content: str
) -> RuntimeResult:
    with tempfile.NamedTemporaryFile(
        "w", suffix=suffix, delete=False, encoding="utf-8"
    ) as handle:
        handle.write(content)
        path = handle.name
    try:
        return _run_command(tuple(command_prefix) + (path,))
    finally:
        Path(path).unlink(missing_ok=True)


def _run_command(command: Sequence[str]) -> RuntimeResult:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return RuntimeResult(
            status=RUNTIME_FAIL, error=str(exc), command=tuple(command)
        )
    if result.returncode != 0:
        return RuntimeResult(
            status=RUNTIME_FAIL,
            error=(result.stderr or result.stdout).strip(),
            command=tuple(command),
        )
    try:
        return RuntimeResult(
            status=RUNTIME_PASS,
            value=float(json.loads(result.stdout.strip())),
            command=tuple(command),
        )
    except (ValueError, json.JSONDecodeError) as exc:
        return RuntimeResult(
            status=RUNTIME_FAIL,
            error=f"could not parse runtime output {result.stdout!r}: {exc}",
            command=tuple(command),
        )


def _runtime_consensus(
    artifacts: Sequence[RosettaArtifact], run_requested: bool
) -> bool | None:
    if not run_requested:
        return None
    values = [
        artifact.runtime.value
        for artifact in artifacts
        if artifact.runtime.status == RUNTIME_PASS
        and artifact.runtime.value is not None
    ]
    if len(values) < 2:
        return None
    first = values[0]
    return all(
        math.isclose(first, value, rel_tol=1e-9, abs_tol=1e-9) for value in values[1:]
    )


def _number_literal(value: float) -> str:
    return repr(float(value))


def _haskell_number_literal(value: float) -> str:
    if value < 0:
        return f"({repr(float(value))})"
    return repr(float(value))
