"""
Spiralverse DSL Interpreter

Executes Spiralverse AST nodes.

@module spiralverse/dsl/interpreter
@version 1.0.0
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
import math

from .parser import (
    ASTNode, NodeType, ProgramNode, PatternDefNode, FlowDefNode,
    AgentDefNode, LetStmtNode, YieldStmtNode, ReturnStmtNode,
    IfStmtNode, WhileStmtNode, ForStmtNode, BinaryExprNode,
    UnaryExprNode, CallExprNode, MemberExprNode, PipeExprNode,
    NumberLitNode, StringLitNode, IdentifierNode, ConstantNode,
    GlyphLitNode, DecoratorNode, ParamNode, TypeAnnotationNode,
)
from .types import (
    SpiralverseType, WaveType, PositionType, TongueType,
    PatternType, FlowType, SignalType, VectorType, NumericType,
    PHI, PI, E,
)


# ============================================================================
# Execution Context
# ============================================================================

@dataclass
class ExecutionContext:
    """
    Execution context for Spiralverse interpreter.

    Manages scopes, variables, and patterns.
    """
    parent: Optional["ExecutionContext"] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    patterns: Dict[str, PatternType] = field(default_factory=dict)
    flows: Dict[str, FlowType] = field(default_factory=dict)
    current_tongue: Optional[TongueType] = None
    return_value: Any = None
    yielded_values: List[Any] = field(default_factory=list)
    should_return: bool = False

    def get(self, name: str) -> Any:
        """Get variable from scope chain."""
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(f"Undefined variable: {name}")

    def set(self, name: str, value: Any) -> None:
        """Set variable in current scope."""
        self.variables[name] = value

    def define_pattern(self, pattern: PatternType) -> None:
        """Define a pattern."""
        self.patterns[pattern.name] = pattern

    def get_pattern(self, name: str) -> Optional[PatternType]:
        """Get pattern from scope chain."""
        if name in self.patterns:
            return self.patterns[name]
        if self.parent:
            return self.parent.get_pattern(name)
        return None

    def child(self) -> "ExecutionContext":
        """Create child context."""
        return ExecutionContext(
            parent=self,
            current_tongue=self.current_tongue,
        )


# ============================================================================
# Built-in Functions
# ============================================================================

def builtin_print(*args) -> None:
    """Print values."""
    print(*args)


def builtin_len(value) -> int:
    """Get length of collection."""
    if isinstance(value, (list, str)):
        return len(value)
    if isinstance(value, VectorType):
        return value.dim
    if isinstance(value, SignalType):
        return len(value.samples)
    raise TypeError(f"Cannot get length of {type(value)}")


def builtin_range(*args) -> List[int]:
    """Generate range."""
    return list(range(*args))


def builtin_abs(value) -> float:
    """Absolute value."""
    if isinstance(value, NumericType):
        return abs(value.value)
    return abs(value)


def builtin_sin(value) -> float:
    """Sine function."""
    if isinstance(value, NumericType):
        return math.sin(value.value)
    return math.sin(value)


def builtin_cos(value) -> float:
    """Cosine function."""
    if isinstance(value, NumericType):
        return math.cos(value.value)
    return math.cos(value)


def builtin_sqrt(value) -> float:
    """Square root."""
    if isinstance(value, NumericType):
        return math.sqrt(value.value)
    return math.sqrt(value)


def builtin_log(value) -> float:
    """Natural logarithm."""
    if isinstance(value, NumericType):
        return math.log(value.value)
    return math.log(value)


def builtin_Wave(**kwargs) -> WaveType:
    """Create a Wave."""
    return WaveType(**kwargs)


def builtin_Position(**kwargs) -> PositionType:
    """Create a Position."""
    return PositionType(**kwargs)


def builtin_Signal(**kwargs) -> SignalType:
    """Create a Signal."""
    return SignalType(**kwargs)


def builtin_Vector(*args) -> VectorType:
    """Create a Vector."""
    if len(args) == 1 and isinstance(args[0], list):
        return VectorType(values=args[0])
    return VectorType(values=list(args))


BUILTINS: Dict[str, Callable] = {
    "print": builtin_print,
    "len": builtin_len,
    "range": builtin_range,
    "abs": builtin_abs,
    "sin": builtin_sin,
    "cos": builtin_cos,
    "sqrt": builtin_sqrt,
    "log": builtin_log,
    "Wave": builtin_Wave,
    "Position": builtin_Position,
    "Signal": builtin_Signal,
    "Vector": builtin_Vector,
}


# ============================================================================
# Interpreter
# ============================================================================

class SpiralverseInterpreter:
    """
    Interpreter for Spiralverse DSL.

    Executes AST nodes and manages execution context.
    """

    def __init__(self):
        """Initialize interpreter."""
        self.global_context = ExecutionContext()
        self._setup_builtins()

    def _setup_builtins(self) -> None:
        """Setup built-in functions and constants."""
        for name, func in BUILTINS.items():
            self.global_context.variables[name] = func

        # Mathematical constants
        self.global_context.variables["φ"] = PHI
        self.global_context.variables["phi"] = PHI
        self.global_context.variables["π"] = PI
        self.global_context.variables["pi"] = PI
        self.global_context.variables["e"] = E

        # Tongue constructors
        for tongue in ["KO", "AV", "RU", "CA", "UM", "DR"]:
            self.global_context.variables[tongue] = TongueType(tongue)

    def execute(self, ast: ASTNode) -> Any:
        """
        Execute an AST node.

        Args:
            ast: Root AST node

        Returns:
            Execution result
        """
        return self._eval(ast, self.global_context)

    def _eval(self, node: ASTNode, ctx: ExecutionContext) -> Any:
        """Evaluate an AST node."""
        if node is None:
            return None

        method_name = f"_eval_{node.node_type.name.lower()}"
        method = getattr(self, method_name, None)

        if method is None:
            raise NotImplementedError(f"No evaluator for {node.node_type}")

        return method(node, ctx)

    # ========================================================================
    # Program Structure
    # ========================================================================

    def _eval_program(self, node: ProgramNode, ctx: ExecutionContext) -> Any:
        """Evaluate program."""
        result = None
        for definition in node.definitions:
            result = self._eval(definition, ctx)
        return result

    def _eval_pattern_def(self, node: PatternDefNode, ctx: ExecutionContext) -> PatternType:
        """Evaluate pattern definition."""
        tongue = TongueType(node.tongue) if node.tongue else None

        pattern = PatternType(
            name=node.name,
            tongue=tongue,
            input_types=[p.type_annotation.type_name for p in node.inputs if p.type_annotation],
            output_types=[p.type_annotation.type_name for p in node.outputs if p.type_annotation],
            body=node.body,
        )

        # Store input/output param names
        pattern._input_params = [p.name for p in node.inputs]
        pattern._output_params = [p.name for p in node.outputs]

        ctx.define_pattern(pattern)
        return pattern

    def _eval_flow_def(self, node: FlowDefNode, ctx: ExecutionContext) -> FlowType:
        """Evaluate flow definition."""
        tongue = TongueType(node.tongue) if node.tongue else None

        # Evaluate stages as expressions
        stages = []
        for stage in node.stages:
            evaluated = self._eval(stage, ctx)
            if isinstance(evaluated, PatternType):
                stages.append(evaluated)
            elif callable(evaluated):
                # Wrap callable as pattern
                stages.append(PatternType(name=str(evaluated), body=evaluated))

        flow = FlowType(
            name=node.name,
            tongue=tongue,
            stages=stages,
        )

        ctx.flows[node.name] = flow
        return flow

    def _eval_agent_def(self, node: AgentDefNode, ctx: ExecutionContext) -> Dict[str, Any]:
        """Evaluate agent definition."""
        agent_ctx = ctx.child()
        if node.tongue:
            agent_ctx.current_tongue = TongueType(node.tongue)

        result = None
        for stmt in node.body:
            result = self._eval(stmt, agent_ctx)
            if agent_ctx.should_return:
                break

        return {
            "name": node.name,
            "tongue": node.tongue,
            "result": result,
            "yields": agent_ctx.yielded_values,
        }

    # ========================================================================
    # Statements
    # ========================================================================

    def _eval_let_stmt(self, node: LetStmtNode, ctx: ExecutionContext) -> None:
        """Evaluate let statement."""
        value = self._eval(node.value, ctx) if node.value else None
        ctx.set(node.name, value)

    def _eval_yield_stmt(self, node: YieldStmtNode, ctx: ExecutionContext) -> Any:
        """Evaluate yield statement."""
        value = self._eval(node.value, ctx)
        ctx.yielded_values.append(value)
        return value

    def _eval_return_stmt(self, node: ReturnStmtNode, ctx: ExecutionContext) -> Any:
        """Evaluate return statement."""
        value = self._eval(node.value, ctx) if node.value else None
        ctx.return_value = value
        ctx.should_return = True
        return value

    def _eval_if_stmt(self, node: IfStmtNode, ctx: ExecutionContext) -> Any:
        """Evaluate if statement."""
        condition = self._eval(node.condition, ctx)

        if self._is_truthy(condition):
            for stmt in node.then_branch:
                self._eval(stmt, ctx)
                if ctx.should_return:
                    break
        else:
            for stmt in node.else_branch:
                self._eval(stmt, ctx)
                if ctx.should_return:
                    break

        return None

    def _eval_while_stmt(self, node: WhileStmtNode, ctx: ExecutionContext) -> None:
        """Evaluate while loop."""
        while self._is_truthy(self._eval(node.condition, ctx)):
            for stmt in node.body:
                self._eval(stmt, ctx)
                if ctx.should_return:
                    return
        return None

    def _eval_for_stmt(self, node: ForStmtNode, ctx: ExecutionContext) -> None:
        """Evaluate for loop."""
        iterable = self._eval(node.iterable, ctx)

        for item in iterable:
            ctx.set(node.variable, item)
            for stmt in node.body:
                self._eval(stmt, ctx)
                if ctx.should_return:
                    return
        return None

    # ========================================================================
    # Expressions
    # ========================================================================

    def _eval_binary_expr(self, node: BinaryExprNode, ctx: ExecutionContext) -> Any:
        """Evaluate binary expression."""
        left = self._eval(node.left, ctx)
        right = self._eval(node.right, ctx)

        # Unwrap NumericType
        if isinstance(left, NumericType):
            left = left.value
        if isinstance(right, NumericType):
            right = right.value

        op = node.operator

        # Arithmetic
        if op == "+":
            if isinstance(left, VectorType) and isinstance(right, VectorType):
                return left + right
            return left + right
        elif op == "-":
            if isinstance(left, VectorType) and isinstance(right, VectorType):
                return left - right
            return left - right
        elif op == "*":
            if isinstance(left, VectorType):
                return left * right
            return left * right
        elif op == "/":
            return left / right
        elif op == "%":
            return left % right
        elif op == "**":
            return left ** right

        # Comparison
        elif op == "==":
            return left == right
        elif op == "!=":
            return left != right
        elif op == "<":
            return left < right
        elif op == ">":
            return left > right
        elif op == "<=":
            return left <= right
        elif op == ">=":
            return left >= right

        # Logical
        elif op == "and":
            return self._is_truthy(left) and self._is_truthy(right)
        elif op == "or":
            return self._is_truthy(left) or self._is_truthy(right)

        raise ValueError(f"Unknown operator: {op}")

    def _eval_unary_expr(self, node: UnaryExprNode, ctx: ExecutionContext) -> Any:
        """Evaluate unary expression."""
        operand = self._eval(node.operand, ctx)

        if isinstance(operand, NumericType):
            operand = operand.value

        if node.operator == "-":
            return -operand
        elif node.operator == "not":
            return not self._is_truthy(operand)

        raise ValueError(f"Unknown unary operator: {node.operator}")

    def _eval_call_expr(self, node: CallExprNode, ctx: ExecutionContext) -> Any:
        """Evaluate function/pattern call."""
        callee = self._eval(node.callee, ctx)
        args = [self._eval(arg, ctx) for arg in node.arguments]

        # Built-in function
        if callable(callee):
            return callee(*args)

        # Pattern call
        if isinstance(callee, PatternType):
            return self._call_pattern(callee, args, ctx)

        raise TypeError(f"Cannot call {type(callee)}")

    def _call_pattern(self, pattern: PatternType, args: List[Any], ctx: ExecutionContext) -> Any:
        """Call a pattern with arguments."""
        # Create new scope
        pattern_ctx = ctx.child()

        # Bind arguments to input parameters
        input_params = getattr(pattern, "_input_params", [])
        for i, param_name in enumerate(input_params):
            if i < len(args):
                pattern_ctx.set(param_name, args[i])

        # Execute body
        for stmt in pattern.body or []:
            self._eval(stmt, pattern_ctx)
            if pattern_ctx.should_return:
                return pattern_ctx.return_value

        # Return yielded values or last result
        if pattern_ctx.yielded_values:
            return pattern_ctx.yielded_values[-1]

        return None

    def _eval_member_expr(self, node: MemberExprNode, ctx: ExecutionContext) -> Any:
        """Evaluate member access."""
        obj = self._eval(node.object, ctx)

        # Wave properties
        if isinstance(obj, WaveType):
            if node.property == "phase":
                return obj.phase
            elif node.property == "amplitude":
                return obj.amplitude
            elif node.property == "frequency":
                return obj.frequency

        # Position properties
        if isinstance(obj, PositionType):
            return getattr(obj, node.property)

        # Vector properties
        if isinstance(obj, VectorType):
            if node.property == "dim":
                return obj.dim
            elif node.property == "magnitude":
                return obj.magnitude()

        # Generic attribute access
        return getattr(obj, node.property)

    def _eval_pipe_expr(self, node: PipeExprNode, ctx: ExecutionContext) -> Any:
        """Evaluate pipe expression (a | b | c)."""
        result = self._eval(node.stages[0], ctx)

        for stage in node.stages[1:]:
            stage_value = self._eval(stage, ctx)

            if isinstance(stage_value, PatternType):
                result = self._call_pattern(stage_value, [result], ctx)
            elif callable(stage_value):
                result = stage_value(result)
            else:
                raise TypeError(f"Cannot pipe through {type(stage_value)}")

        return result

    # ========================================================================
    # Literals
    # ========================================================================

    def _eval_number_lit(self, node: NumberLitNode, ctx: ExecutionContext) -> float:
        """Evaluate number literal."""
        return node.value

    def _eval_string_lit(self, node: StringLitNode, ctx: ExecutionContext) -> str:
        """Evaluate string literal."""
        return node.value

    def _eval_identifier(self, node: IdentifierNode, ctx: ExecutionContext) -> Any:
        """Evaluate identifier."""
        name = node.name

        # Check for pattern
        pattern = ctx.get_pattern(name)
        if pattern:
            return pattern

        # Check for variable
        return ctx.get(name)

    def _eval_constant(self, node: ConstantNode, ctx: ExecutionContext) -> float:
        """Evaluate mathematical constant."""
        return node.value

    def _eval_glyph_lit(self, node: GlyphLitNode, ctx: ExecutionContext) -> str:
        """Evaluate glyph literal."""
        return node.symbols

    def _eval_decorator(self, node: DecoratorNode, ctx: ExecutionContext) -> Dict[str, Any]:
        """Evaluate decorator (returns metadata)."""
        return {
            "name": node.name,
            "arguments": [self._eval(arg, ctx) for arg in node.arguments],
        }

    def _eval_param(self, node: ParamNode, ctx: ExecutionContext) -> Dict[str, Any]:
        """Evaluate parameter definition."""
        return {
            "name": node.name,
            "type": self._eval(node.type_annotation, ctx) if node.type_annotation else None,
        }

    def _eval_type_annotation(self, node: TypeAnnotationNode, ctx: ExecutionContext) -> str:
        """Evaluate type annotation."""
        return node.type_name

    # ========================================================================
    # Helpers
    # ========================================================================

    def _is_truthy(self, value: Any) -> bool:
        """Check if value is truthy."""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, list):
            return len(value) > 0
        if isinstance(value, NumericType):
            return value.value != 0
        return True


# ============================================================================
# Convenience Functions
# ============================================================================

def run_spiralverse(source: str) -> Any:
    """
    Parse and execute Spiralverse source code.

    Args:
        source: Spiralverse source code

    Returns:
        Execution result
    """
    from .lexer import SpiralverseLexer
    from .parser import SpiralverseParser

    lexer = SpiralverseLexer(source)
    tokens = lexer.tokenize()

    parser = SpiralverseParser(tokens)
    ast = parser.parse()

    interpreter = SpiralverseInterpreter()
    return interpreter.execute(ast)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "ExecutionContext",
    "SpiralverseInterpreter",
    "run_spiralverse",
    "BUILTINS",
]
