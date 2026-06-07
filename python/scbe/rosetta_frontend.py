"""Python-source front-end for the Rosetta bounded-control mail room.

This is a deliberately narrow ingress compiler:

    Python subset -> canonical Tier-2 program -> Rosetta control tape

It accepts scalar, side-effect-free function bodies with assignments,
conditionals, while loops, range-for loops, arithmetic/comparison expressions,
and a small set of pure calls. It refuses unsupported Python constructs instead
of guessing.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .rosetta_control import (
    CONTROL_TARGETS,
    RosettaControlNode,
    build_rosetta_control_node,
)


class LoweringError(ValueError):
    """Raised when Python source is outside the supported Rosetta subset."""


@dataclass(frozen=True)
class PythonControlFrontend:
    """Result of lowering Python source into the Rosetta control system."""

    schema: str
    function_name: str
    source_hash: str
    canonical_program: str
    constants: tuple[tuple[str, int], ...]
    control_node: RosettaControlNode

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "function_name": self.function_name,
            "source_hash": self.source_hash,
            "canonical_program": self.canonical_program,
            "constants": [
                {"name": name, "value": value} for name, value in self.constants
            ],
            "control_node": self.control_node.to_dict(),
        }


def compile_python_control_source(
    source: str,
    *,
    constants: Mapping[str, int] | None = None,
    fn_name: str | None = None,
    targets: Sequence[str] = CONTROL_TARGETS,
    output_fn: str | None = None,
    run: bool = False,
) -> PythonControlFrontend:
    """Lower one supported Python function into a Rosetta control node."""
    function = _single_function(source, fn_name=fn_name)
    lowered = _PythonLowerer(constants or {}).lower_function(function)
    canonical_program = lowered.canonical_program
    control = build_rosetta_control_node(
        canonical_program,
        targets=targets,
        fn_name=output_fn or function.name,
        run=run,
    )
    return PythonControlFrontend(
        schema="scbe_rosetta_python_frontend_v1",
        function_name=function.name,
        source_hash=_source_hash(source),
        canonical_program=canonical_program,
        constants=tuple(
            sorted((name, int(value)) for name, value in (constants or {}).items())
        ),
        control_node=control,
    )


@dataclass(frozen=True)
class _LoweredFunction:
    canonical_program: str


class _PythonLowerer:
    def __init__(self, constants: Mapping[str, int]) -> None:
        self.constants = {str(name): int(value) for name, value in constants.items()}
        self.names: dict[str, str] = {}
        self.arg_names: set[str] = set()
        self.local_count = 0

    def lower_function(self, function: ast.FunctionDef) -> _LoweredFunction:
        statements: list[str] = []
        for index, arg in enumerate(function.args.args):
            if arg.arg not in self.constants:
                raise LoweringError(
                    f"missing constant for function argument {arg.arg!r}"
                )
            canonical = f"arg{index}"
            self.names[arg.arg] = canonical
            self.arg_names.add(arg.arg)
            statements.append(f"{canonical} = {self.constants[arg.arg]}")

        body = self._lower_block(function.body, allow_return=True)
        statements.extend(body)
        if not statements:
            raise LoweringError("function body is empty")
        return _LoweredFunction(canonical_program="\n".join(statements))

    def _lower_block(
        self, statements: Sequence[ast.stmt], *, allow_return: bool
    ) -> list[str]:
        out: list[str] = []
        for index, statement in enumerate(statements):
            is_last = index == len(statements) - 1
            if isinstance(statement, ast.Return):
                if not allow_return or not is_last:
                    raise LoweringError(
                        "return is supported only as the last statement in a block"
                    )
                if statement.value is None:
                    raise LoweringError("bare return is not supported")
                out.append(self._expr(statement.value))
                continue
            if isinstance(statement, ast.Pass):
                continue
            if isinstance(statement, ast.Assign):
                out.extend(self._assign(statement))
                continue
            if isinstance(statement, ast.AugAssign):
                out.append(self._aug_assign(statement))
                continue
            if isinstance(statement, ast.If):
                out.append(self._if(statement))
                continue
            if isinstance(statement, ast.While):
                out.append(self._while(statement))
                continue
            if isinstance(statement, ast.For):
                out.extend(self._for_range(statement))
                continue
            if isinstance(statement, ast.Expr):
                out.append(self._expr(statement.value))
                continue
            raise LoweringError(f"unsupported statement: {type(statement).__name__}")
        return out

    def _assign(self, statement: ast.Assign) -> list[str]:
        if len(statement.targets) != 1 or not isinstance(
            statement.targets[0], ast.Name
        ):
            raise LoweringError("only single-name assignment is supported")
        name = self._bind_name(statement.targets[0].id)
        return [f"{name} = {self._expr(statement.value)}"]

    def _aug_assign(self, statement: ast.AugAssign) -> str:
        if not isinstance(statement.target, ast.Name):
            raise LoweringError("augmented assignment target must be a name")
        name = self._name(statement.target.id)
        op = _bin_op(statement.op)
        return f"{name} = {op}({name}, {self._expr(statement.value)})"

    def _if(self, statement: ast.If) -> str:
        cond = self._expr(statement.test)
        then_body = self._brace_block(statement.body, allow_return=True)
        if statement.orelse:
            else_body = self._brace_block(statement.orelse, allow_return=True)
            return f"if {cond} {{ {then_body} }} else {{ {else_body} }}"
        return f"if {cond} {{ {then_body} }}"

    def _while(self, statement: ast.While) -> str:
        if statement.orelse:
            raise LoweringError("while-else is not supported")
        cond = self._expr(statement.test)
        body = self._brace_block(statement.body, allow_return=False)
        return f"while {cond} {{ {body} }}"

    def _for_range(self, statement: ast.For) -> list[str]:
        if statement.orelse:
            raise LoweringError("for-else is not supported")
        if not isinstance(statement.target, ast.Name):
            raise LoweringError("range-for target must be a name")
        range_args = self._range_args(statement.iter)
        target = self._bind_name(statement.target.id)
        start, stop = range_args
        body = self._lower_block(statement.body, allow_return=False)
        body.append(f"{target} = add({target}, 1)")
        return [
            f"{target} = {start}",
            f"while lt({target}, {stop}) {{ {'; '.join(body)} }}",
        ]

    def _range_args(self, node: ast.AST) -> tuple[str, str]:
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "range"
        ):
            raise LoweringError("for loops support only range(...)")
        if node.keywords:
            raise LoweringError("range keyword arguments are not supported")
        if len(node.args) == 1:
            return "0", self._expr(node.args[0])
        if len(node.args) == 2:
            return self._expr(node.args[0]), self._expr(node.args[1])
        if len(node.args) == 3:
            step = self._literal_int(node.args[2])
            if step != 1:
                raise LoweringError("range step is supported only when it is 1")
            return self._expr(node.args[0]), self._expr(node.args[1])
        raise LoweringError("range expects one, two, or three arguments")

    def _brace_block(
        self, statements: Sequence[ast.stmt], *, allow_return: bool
    ) -> str:
        lowered = self._lower_block(statements, allow_return=allow_return)
        if not lowered:
            raise LoweringError("empty blocks are not supported")
        return "; ".join(lowered)

    def _expr(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "1" if node.value else "0"
            if isinstance(node.value, int):
                return str(node.value)
            raise LoweringError(f"unsupported literal: {node.value!r}")
        if isinstance(node, ast.Name):
            return self._name(node.id)
        if isinstance(node, ast.BinOp):
            return (
                f"{_bin_op(node.op)}({self._expr(node.left)}, {self._expr(node.right)})"
            )
        if isinstance(node, ast.UnaryOp):
            return self._unary(node)
        if isinstance(node, ast.Compare):
            return self._compare(node)
        if isinstance(node, ast.BoolOp):
            return self._bool_op(node)
        if isinstance(node, ast.Call):
            return self._call(node)
        if isinstance(node, (ast.List, ast.Tuple, ast.Subscript, ast.Dict, ast.Set)):
            raise LoweringError(f"{type(node).__name__} is not supported in control v1")
        raise LoweringError(f"unsupported expression: {type(node).__name__}")

    def _unary(self, node: ast.UnaryOp) -> str:
        value = self._expr(node.operand)
        if isinstance(node.op, ast.USub):
            return f"neg({value})"
        if isinstance(node.op, ast.Not):
            return f"eq({value}, 0)"
        raise LoweringError(f"unsupported unary operator: {type(node.op).__name__}")

    def _compare(self, node: ast.Compare) -> str:
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise LoweringError("chained comparisons are not supported")
        op_name = _cmp_op(node.ops[0])
        return f"{op_name}({self._expr(node.left)}, {self._expr(node.comparators[0])})"

    def _bool_op(self, node: ast.BoolOp) -> str:
        if len(node.values) < 2:
            raise LoweringError("boolean op needs at least two values")
        op = "and" if isinstance(node.op, ast.And) else "or"
        expr = self._expr(node.values[0])
        for value in node.values[1:]:
            expr = f"{op}({expr}, {self._expr(value)})"
        return expr

    def _call(self, node: ast.Call) -> str:
        if not isinstance(node.func, ast.Name):
            raise LoweringError("only simple function calls are supported")
        if node.keywords:
            raise LoweringError("keyword arguments are not supported")
        name = node.func.id
        if name not in {"abs", "min", "max"}:
            raise LoweringError(f"unsupported call: {name}")
        rendered = ", ".join(self._expr(arg) for arg in node.args)
        return f"{name}({rendered})"

    def _literal_int(self, node: ast.AST) -> int:
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return int(node.value)
        raise LoweringError("expected integer literal")

    def _bind_name(self, source_name: str) -> str:
        if source_name in self.names:
            return self.names[source_name]
        canonical = f"v{self.local_count}"
        self.local_count += 1
        self.names[source_name] = canonical
        return canonical

    def _name(self, source_name: str) -> str:
        if source_name not in self.names:
            raise LoweringError(f"name {source_name!r} is not bound")
        return self.names[source_name]


def _single_function(source: str, *, fn_name: str | None) -> ast.FunctionDef:
    try:
        module = ast.parse(source)
    except SyntaxError as exc:
        raise LoweringError(f"invalid Python source: {exc}") from exc
    functions = [node for node in module.body if isinstance(node, ast.FunctionDef)]
    if not functions:
        raise LoweringError("source must contain one function")
    if len(functions) != len(module.body):
        raise LoweringError(
            "module-level statements other than functions are not supported"
        )
    if fn_name is not None:
        matches = [function for function in functions if function.name == fn_name]
        if not matches:
            raise LoweringError(f"function {fn_name!r} not found")
        function = matches[0]
    elif len(functions) == 1:
        function = functions[0]
    else:
        raise LoweringError("multiple functions require --fn")
    if function.decorator_list:
        raise LoweringError("decorated functions are not supported")
    if (
        function.args.posonlyargs
        or function.args.kwonlyargs
        or function.args.kwarg
        or function.args.vararg
    ):
        raise LoweringError("only positional scalar arguments are supported")
    if function.args.defaults or function.args.kw_defaults:
        raise LoweringError("default arguments are not supported")
    return function


def _bin_op(op: ast.operator) -> str:
    if isinstance(op, ast.Add):
        return "add"
    if isinstance(op, ast.Sub):
        return "sub"
    if isinstance(op, ast.Mult):
        return "mul"
    if isinstance(op, (ast.Div, ast.FloorDiv)):
        return "div"
    if isinstance(op, ast.Mod):
        return "mod"
    if isinstance(op, ast.Pow):
        return "pow"
    if isinstance(op, ast.LShift):
        return "shl"
    if isinstance(op, ast.RShift):
        return "shr"
    raise LoweringError(f"unsupported binary operator: {type(op).__name__}")


def _cmp_op(op: ast.cmpop) -> str:
    if isinstance(op, ast.Eq):
        return "eq"
    if isinstance(op, ast.NotEq):
        return "neq"
    if isinstance(op, ast.Lt):
        return "lt"
    if isinstance(op, ast.LtE):
        return "lte"
    if isinstance(op, ast.Gt):
        return "gt"
    if isinstance(op, ast.GtE):
        return "gte"
    raise LoweringError(f"unsupported comparison operator: {type(op).__name__}")


def _source_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def parse_constants(values: Sequence[str]) -> dict[str, int]:
    """Parse CLI constants of the form name=value."""
    out: dict[str, int] = {}
    for raw in values:
        if "=" not in raw:
            raise LoweringError(f"constant must be name=value, got {raw!r}")
        name, value = raw.split("=", 1)
        name = name.strip()
        if not name:
            raise LoweringError(f"constant name is empty in {raw!r}")
        out[name] = int(value.strip(), 0)
    return out


def frontend_summary(frontend: PythonControlFrontend) -> str:
    """Small text summary for non-JSON CLI output."""
    tape = frontend.control_node.control_tape.to_dict()["prime_tape"]
    return "\n".join(
        [
            f"function: {frontend.function_name}",
            f"value: {frontend.control_node.value}",
            f"canonical_program: {frontend.canonical_program}",
            f"prime_tape: {tape}",
        ]
    )
