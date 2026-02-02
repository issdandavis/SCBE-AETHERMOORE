"""
Spiralverse DSL Parser

Parses tokens into an Abstract Syntax Tree (AST).

@module spiralverse/dsl/parser
@version 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Union
from .lexer import Token, TokenType

# ============================================================================
# AST Node Types
# ============================================================================

class NodeType(Enum):
    """Types of AST nodes."""
    # Program structure
    PROGRAM = auto()
    PATTERN_DEF = auto()
    FLOW_DEF = auto()
    AGENT_DEF = auto()
    IMPORT_STMT = auto()

    # Statements
    BLOCK = auto()
    LET_STMT = auto()
    YIELD_STMT = auto()
    RETURN_STMT = auto()
    IF_STMT = auto()
    WHILE_STMT = auto()
    FOR_STMT = auto()
    MATCH_STMT = auto()
    EXPR_STMT = auto()

    # Expressions
    BINARY_EXPR = auto()
    UNARY_EXPR = auto()
    CALL_EXPR = auto()
    MEMBER_EXPR = auto()
    INDEX_EXPR = auto()
    PIPE_EXPR = auto()

    # Literals
    NUMBER_LIT = auto()
    STRING_LIT = auto()
    IDENTIFIER = auto()
    CONSTANT = auto()
    GLYPH_LIT = auto()

    # Type annotations
    TYPE_ANNOTATION = auto()
    PARAM = auto()

    # Decorators
    DECORATOR = auto()
    TONGUE_DECORATOR = auto()
    GLYPH_DECORATOR = auto()


# ============================================================================
# AST Nodes
# ============================================================================

@dataclass
class ASTNode:
    """Base AST node."""
    node_type: NodeType
    line: int = 0
    column: int = 0


@dataclass
class ProgramNode(ASTNode):
    """Root program node."""
    definitions: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = NodeType.PROGRAM


@dataclass
class PatternDefNode(ASTNode):
    """Pattern definition."""
    name: str = ""
    tongue: Optional[str] = None
    decorators: List[ASTNode] = field(default_factory=list)
    inputs: List[ASTNode] = field(default_factory=list)
    outputs: List[ASTNode] = field(default_factory=list)
    body: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = NodeType.PATTERN_DEF


@dataclass
class FlowDefNode(ASTNode):
    """Flow definition."""
    name: str = ""
    tongue: Optional[str] = None
    decorators: List[ASTNode] = field(default_factory=list)
    stages: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = NodeType.FLOW_DEF


@dataclass
class AgentDefNode(ASTNode):
    """Agent definition."""
    name: str = ""
    tongue: Optional[str] = None
    decorators: List[ASTNode] = field(default_factory=list)
    body: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = NodeType.AGENT_DEF


@dataclass
class LetStmtNode(ASTNode):
    """Let statement (variable binding)."""
    name: str = ""
    type_annotation: Optional[ASTNode] = None
    value: Optional[ASTNode] = None

    def __post_init__(self):
        self.node_type = NodeType.LET_STMT


@dataclass
class YieldStmtNode(ASTNode):
    """Yield statement."""
    value: Optional[ASTNode] = None

    def __post_init__(self):
        self.node_type = NodeType.YIELD_STMT


@dataclass
class ReturnStmtNode(ASTNode):
    """Return statement."""
    value: Optional[ASTNode] = None

    def __post_init__(self):
        self.node_type = NodeType.RETURN_STMT


@dataclass
class IfStmtNode(ASTNode):
    """If statement."""
    condition: Optional[ASTNode] = None
    then_branch: List[ASTNode] = field(default_factory=list)
    else_branch: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = NodeType.IF_STMT


@dataclass
class WhileStmtNode(ASTNode):
    """While loop."""
    condition: Optional[ASTNode] = None
    body: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = NodeType.WHILE_STMT


@dataclass
class ForStmtNode(ASTNode):
    """For loop."""
    variable: str = ""
    iterable: Optional[ASTNode] = None
    body: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = NodeType.FOR_STMT


@dataclass
class BinaryExprNode(ASTNode):
    """Binary expression."""
    left: Optional[ASTNode] = None
    operator: str = ""
    right: Optional[ASTNode] = None

    def __post_init__(self):
        self.node_type = NodeType.BINARY_EXPR


@dataclass
class UnaryExprNode(ASTNode):
    """Unary expression."""
    operator: str = ""
    operand: Optional[ASTNode] = None

    def __post_init__(self):
        self.node_type = NodeType.UNARY_EXPR


@dataclass
class CallExprNode(ASTNode):
    """Function/pattern call."""
    callee: Optional[ASTNode] = None
    arguments: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = NodeType.CALL_EXPR


@dataclass
class MemberExprNode(ASTNode):
    """Member access (a.b)."""
    object: Optional[ASTNode] = None
    property: str = ""

    def __post_init__(self):
        self.node_type = NodeType.MEMBER_EXPR


@dataclass
class PipeExprNode(ASTNode):
    """Pipe expression (a | b)."""
    stages: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = NodeType.PIPE_EXPR


@dataclass
class NumberLitNode(ASTNode):
    """Numeric literal."""
    value: float = 0.0
    is_integer: bool = True

    def __post_init__(self):
        self.node_type = NodeType.NUMBER_LIT


@dataclass
class StringLitNode(ASTNode):
    """String literal."""
    value: str = ""

    def __post_init__(self):
        self.node_type = NodeType.STRING_LIT


@dataclass
class IdentifierNode(ASTNode):
    """Identifier."""
    name: str = ""

    def __post_init__(self):
        self.node_type = NodeType.IDENTIFIER


@dataclass
class ConstantNode(ASTNode):
    """Mathematical constant (φ, π, e)."""
    name: str = ""
    value: float = 0.0

    def __post_init__(self):
        self.node_type = NodeType.CONSTANT


@dataclass
class GlyphLitNode(ASTNode):
    """Glyph symbol literal."""
    symbols: str = ""

    def __post_init__(self):
        self.node_type = NodeType.GLYPH_LIT


@dataclass
class DecoratorNode(ASTNode):
    """Generic decorator."""
    name: str = ""
    arguments: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = NodeType.DECORATOR


@dataclass
class ParamNode(ASTNode):
    """Parameter definition."""
    name: str = ""
    type_annotation: Optional[ASTNode] = None
    default_value: Optional[ASTNode] = None

    def __post_init__(self):
        self.node_type = NodeType.PARAM


@dataclass
class TypeAnnotationNode(ASTNode):
    """Type annotation."""
    type_name: str = ""
    type_params: List[ASTNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = NodeType.TYPE_ANNOTATION


# ============================================================================
# Parser
# ============================================================================

class SpiralverseParser:
    """
    Parser for Spiralverse DSL.

    Converts a token stream into an Abstract Syntax Tree.
    """

    # Mathematical constants
    CONSTANTS = {
        "φ": 1.618033988749895,
        "π": 3.141592653589793,
        "e": 2.718281828459045,
    }

    def __init__(self, tokens: List[Token]):
        """
        Initialize parser.

        Args:
            tokens: Token stream from lexer
        """
        self.tokens = tokens
        self.pos = 0
        self.current_tongue: Optional[str] = None

    def parse(self) -> ProgramNode:
        """
        Parse the token stream.

        Returns:
            AST root node
        """
        program = ProgramNode(definitions=[])

        while not self._is_at_end():
            # Skip newlines between definitions
            self._skip_newlines()
            if self._is_at_end():
                break

            definition = self._parse_definition()
            if definition:
                program.definitions.append(definition)

        return program

    def _parse_definition(self) -> Optional[ASTNode]:
        """Parse a top-level definition."""
        decorators = self._parse_decorators()

        if self._check(TokenType.DEFINE):
            return self._parse_pattern_or_flow(decorators)
        elif self._check(TokenType.IMPORT):
            return self._parse_import()

        raise SyntaxError(
            f"Expected definition at line {self._current().line}"
        )

    def _parse_decorators(self) -> List[ASTNode]:
        """Parse decorator list."""
        decorators = []

        while self._check(TokenType.AT):
            self._advance()  # consume @
            decorator = self._parse_decorator()
            decorators.append(decorator)
            self._skip_newlines()

        return decorators

    def _parse_decorator(self) -> ASTNode:
        """Parse a single decorator."""
        name_token = self._advance()

        # @tongue(KO)
        if name_token.type == TokenType.TONGUE:
            self._expect(TokenType.LPAREN)
            tongue_token = self._advance()
            self._expect(TokenType.RPAREN)
            self.current_tongue = tongue_token.value
            return DecoratorNode(
                name="tongue",
                arguments=[IdentifierNode(name=tongue_token.value)],
                line=name_token.line,
                column=name_token.column,
            )

        # @glyph(●→○)
        if name_token.type == TokenType.GLYPH or name_token.value == "glyph":
            self._expect(TokenType.LPAREN)
            glyph_token = self._advance()
            self._expect(TokenType.RPAREN)
            return DecoratorNode(
                name="glyph",
                arguments=[GlyphLitNode(symbols=glyph_token.value)],
                line=name_token.line,
                column=name_token.column,
            )

        # Generic decorator
        arguments = []
        if self._check(TokenType.LPAREN):
            self._advance()
            if not self._check(TokenType.RPAREN):
                arguments = self._parse_argument_list()
            self._expect(TokenType.RPAREN)

        return DecoratorNode(
            name=name_token.value,
            arguments=arguments,
            line=name_token.line,
            column=name_token.column,
        )

    def _parse_pattern_or_flow(self, decorators: List[ASTNode]) -> ASTNode:
        """Parse pattern or flow definition."""
        self._advance()  # consume 'define'

        keyword_token = self._advance()

        if keyword_token.type == TokenType.PATTERN:
            return self._parse_pattern(decorators)
        elif keyword_token.type == TokenType.FLOW:
            return self._parse_flow(decorators)
        elif keyword_token.type == TokenType.AGENT:
            return self._parse_agent(decorators)

        raise SyntaxError(
            f"Expected 'pattern', 'flow', or 'agent' at line {keyword_token.line}"
        )

    def _parse_pattern(self, decorators: List[ASTNode]) -> PatternDefNode:
        """Parse pattern definition."""
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.COLON)
        self._skip_newlines()
        self._expect(TokenType.INDENT)

        inputs = []
        outputs = []
        body = []

        while not self._check(TokenType.DEDENT) and not self._is_at_end():
            self._skip_newlines()

            if self._check(TokenType.INPUT):
                self._advance()
                param = self._parse_param()
                inputs.append(param)
            elif self._check(TokenType.OUTPUT):
                self._advance()
                param = self._parse_param()
                outputs.append(param)
            else:
                stmt = self._parse_statement()
                if stmt:
                    body.append(stmt)

            self._skip_newlines()

        if self._check(TokenType.DEDENT):
            self._advance()

        return PatternDefNode(
            name=name_token.value,
            tongue=self.current_tongue,
            decorators=decorators,
            inputs=inputs,
            outputs=outputs,
            body=body,
            line=name_token.line,
            column=name_token.column,
        )

    def _parse_flow(self, decorators: List[ASTNode]) -> FlowDefNode:
        """Parse flow definition."""
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.COLON)
        self._skip_newlines()
        self._expect(TokenType.INDENT)

        stages = []

        while not self._check(TokenType.DEDENT) and not self._is_at_end():
            self._skip_newlines()
            stage = self._parse_expression()
            if stage:
                stages.append(stage)
            self._skip_newlines()

        if self._check(TokenType.DEDENT):
            self._advance()

        return FlowDefNode(
            name=name_token.value,
            tongue=self.current_tongue,
            decorators=decorators,
            stages=stages,
            line=name_token.line,
            column=name_token.column,
        )

    def _parse_agent(self, decorators: List[ASTNode]) -> AgentDefNode:
        """Parse agent definition."""
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.COLON)
        self._skip_newlines()
        self._expect(TokenType.INDENT)

        body = []

        while not self._check(TokenType.DEDENT) and not self._is_at_end():
            self._skip_newlines()
            stmt = self._parse_statement()
            if stmt:
                body.append(stmt)
            self._skip_newlines()

        if self._check(TokenType.DEDENT):
            self._advance()

        return AgentDefNode(
            name=name_token.value,
            tongue=self.current_tongue,
            decorators=decorators,
            body=body,
            line=name_token.line,
            column=name_token.column,
        )

    def _parse_import(self) -> ASTNode:
        """Parse import statement."""
        self._advance()  # consume 'import'
        # Simplified: just parse identifier
        name = self._expect(TokenType.IDENTIFIER)
        return IdentifierNode(name=name.value, line=name.line, column=name.column)

    def _parse_param(self) -> ParamNode:
        """Parse a parameter."""
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.COLON)
        type_anno = self._parse_type_annotation()

        return ParamNode(
            name=name_token.value,
            type_annotation=type_anno,
            line=name_token.line,
            column=name_token.column,
        )

    def _parse_type_annotation(self) -> TypeAnnotationNode:
        """Parse a type annotation."""
        type_token = self._advance()
        return TypeAnnotationNode(
            type_name=type_token.value,
            line=type_token.line,
            column=type_token.column,
        )

    def _parse_statement(self) -> Optional[ASTNode]:
        """Parse a statement."""
        # Decorators for statements
        decorators = []
        if self._check(TokenType.AT):
            decorators = self._parse_decorators()

        if self._check(TokenType.LET):
            return self._parse_let_stmt()
        elif self._check(TokenType.YIELD):
            return self._parse_yield_stmt()
        elif self._check(TokenType.RETURN):
            return self._parse_return_stmt()
        elif self._check(TokenType.IF):
            return self._parse_if_stmt()
        elif self._check(TokenType.WHILE):
            return self._parse_while_stmt()
        elif self._check(TokenType.FOR):
            return self._parse_for_stmt()
        elif self._check(TokenType.NEWLINE):
            self._advance()
            return None

        # Expression statement
        expr = self._parse_expression()
        return expr

    def _parse_let_stmt(self) -> LetStmtNode:
        """Parse let statement."""
        self._advance()  # consume 'let'
        name_token = self._expect(TokenType.IDENTIFIER)

        type_anno = None
        if self._check(TokenType.COLON):
            self._advance()
            type_anno = self._parse_type_annotation()

        self._expect(TokenType.ASSIGN)
        value = self._parse_expression()

        return LetStmtNode(
            name=name_token.value,
            type_annotation=type_anno,
            value=value,
            line=name_token.line,
            column=name_token.column,
        )

    def _parse_yield_stmt(self) -> YieldStmtNode:
        """Parse yield statement."""
        token = self._advance()
        value = self._parse_expression()
        return YieldStmtNode(
            value=value,
            line=token.line,
            column=token.column,
        )

    def _parse_return_stmt(self) -> ReturnStmtNode:
        """Parse return statement."""
        token = self._advance()
        value = None
        if not self._check(TokenType.NEWLINE) and not self._check(TokenType.DEDENT):
            value = self._parse_expression()
        return ReturnStmtNode(
            value=value,
            line=token.line,
            column=token.column,
        )

    def _parse_if_stmt(self) -> IfStmtNode:
        """Parse if statement."""
        token = self._advance()
        condition = self._parse_expression()
        self._expect(TokenType.COLON)
        self._skip_newlines()
        self._expect(TokenType.INDENT)

        then_branch = []
        while not self._check(TokenType.DEDENT) and not self._is_at_end():
            self._skip_newlines()
            stmt = self._parse_statement()
            if stmt:
                then_branch.append(stmt)

        if self._check(TokenType.DEDENT):
            self._advance()

        else_branch = []
        if self._check(TokenType.ELSE):
            self._advance()
            self._expect(TokenType.COLON)
            self._skip_newlines()
            self._expect(TokenType.INDENT)

            while not self._check(TokenType.DEDENT) and not self._is_at_end():
                self._skip_newlines()
                stmt = self._parse_statement()
                if stmt:
                    else_branch.append(stmt)

            if self._check(TokenType.DEDENT):
                self._advance()

        return IfStmtNode(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            line=token.line,
            column=token.column,
        )

    def _parse_while_stmt(self) -> WhileStmtNode:
        """Parse while loop."""
        token = self._advance()
        condition = self._parse_expression()
        self._expect(TokenType.COLON)
        self._skip_newlines()
        self._expect(TokenType.INDENT)

        body = []
        while not self._check(TokenType.DEDENT) and not self._is_at_end():
            self._skip_newlines()
            stmt = self._parse_statement()
            if stmt:
                body.append(stmt)

        if self._check(TokenType.DEDENT):
            self._advance()

        return WhileStmtNode(
            condition=condition,
            body=body,
            line=token.line,
            column=token.column,
        )

    def _parse_for_stmt(self) -> ForStmtNode:
        """Parse for loop."""
        token = self._advance()
        var_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.IN)
        iterable = self._parse_expression()
        self._expect(TokenType.COLON)
        self._skip_newlines()
        self._expect(TokenType.INDENT)

        body = []
        while not self._check(TokenType.DEDENT) and not self._is_at_end():
            self._skip_newlines()
            stmt = self._parse_statement()
            if stmt:
                body.append(stmt)

        if self._check(TokenType.DEDENT):
            self._advance()

        return ForStmtNode(
            variable=var_token.value,
            iterable=iterable,
            body=body,
            line=token.line,
            column=token.column,
        )

    def _parse_expression(self) -> Optional[ASTNode]:
        """Parse an expression."""
        return self._parse_pipe_expr()

    def _parse_pipe_expr(self) -> Optional[ASTNode]:
        """Parse pipe expression (a | b | c)."""
        left = self._parse_or_expr()

        if self._check(TokenType.PIPE):
            stages = [left]
            while self._check(TokenType.PIPE):
                self._advance()
                stages.append(self._parse_or_expr())
            return PipeExprNode(stages=stages)

        return left

    def _parse_or_expr(self) -> Optional[ASTNode]:
        """Parse logical OR."""
        left = self._parse_and_expr()

        while self._check(TokenType.OR) or self._check(TokenType.DOUBLE_PIPE):
            op = self._advance()
            right = self._parse_and_expr()
            left = BinaryExprNode(left=left, operator="or", right=right)

        return left

    def _parse_and_expr(self) -> Optional[ASTNode]:
        """Parse logical AND."""
        left = self._parse_comparison()

        while self._check(TokenType.AND):
            self._advance()
            right = self._parse_comparison()
            left = BinaryExprNode(left=left, operator="and", right=right)

        return left

    def _parse_comparison(self) -> Optional[ASTNode]:
        """Parse comparison expression."""
        left = self._parse_additive()

        while self._check_any([
            TokenType.EQUALS, TokenType.NOT_EQUALS,
            TokenType.LESS_THAN, TokenType.GREATER_THAN,
            TokenType.LESS_EQUAL, TokenType.GREATER_EQUAL,
        ]):
            op = self._advance()
            right = self._parse_additive()
            left = BinaryExprNode(left=left, operator=op.value, right=right)

        return left

    def _parse_additive(self) -> Optional[ASTNode]:
        """Parse additive expression (+, -)."""
        left = self._parse_multiplicative()

        while self._check(TokenType.PLUS) or self._check(TokenType.MINUS):
            op = self._advance()
            right = self._parse_multiplicative()
            left = BinaryExprNode(left=left, operator=op.value, right=right)

        return left

    def _parse_multiplicative(self) -> Optional[ASTNode]:
        """Parse multiplicative expression (*, /, %)."""
        left = self._parse_power()

        while self._check_any([TokenType.STAR, TokenType.SLASH, TokenType.PERCENT]):
            op = self._advance()
            right = self._parse_power()
            left = BinaryExprNode(left=left, operator=op.value, right=right)

        return left

    def _parse_power(self) -> Optional[ASTNode]:
        """Parse power expression (**)."""
        left = self._parse_unary()

        if self._check(TokenType.POWER):
            self._advance()
            right = self._parse_power()  # Right associative
            return BinaryExprNode(left=left, operator="**", right=right)

        return left

    def _parse_unary(self) -> Optional[ASTNode]:
        """Parse unary expression."""
        if self._check(TokenType.MINUS) or self._check(TokenType.NOT):
            op = self._advance()
            operand = self._parse_unary()
            return UnaryExprNode(operator=op.value, operand=operand)

        return self._parse_call()

    def _parse_call(self) -> Optional[ASTNode]:
        """Parse call and member access."""
        expr = self._parse_primary()

        while True:
            if self._check(TokenType.LPAREN):
                self._advance()
                args = []
                if not self._check(TokenType.RPAREN):
                    args = self._parse_argument_list()
                self._expect(TokenType.RPAREN)
                expr = CallExprNode(callee=expr, arguments=args)
            elif self._check(TokenType.DOT):
                self._advance()
                name = self._expect(TokenType.IDENTIFIER)
                expr = MemberExprNode(object=expr, property=name.value)
            else:
                break

        return expr

    def _parse_argument_list(self) -> List[ASTNode]:
        """Parse function argument list."""
        args = [self._parse_expression()]

        while self._check(TokenType.COMMA):
            self._advance()
            args.append(self._parse_expression())

        return args

    def _parse_primary(self) -> Optional[ASTNode]:
        """Parse primary expression."""
        if self._check(TokenType.INTEGER):
            token = self._advance()
            return NumberLitNode(
                value=int(token.value),
                is_integer=True,
                line=token.line,
                column=token.column,
            )

        if self._check(TokenType.FLOAT):
            token = self._advance()
            return NumberLitNode(
                value=float(token.value),
                is_integer=False,
                line=token.line,
                column=token.column,
            )

        if self._check(TokenType.STRING):
            token = self._advance()
            return StringLitNode(
                value=token.value,
                line=token.line,
                column=token.column,
            )

        if self._check(TokenType.IDENTIFIER):
            token = self._advance()
            return IdentifierNode(
                name=token.value,
                line=token.line,
                column=token.column,
            )

        if self._check(TokenType.PHI):
            token = self._advance()
            return ConstantNode(name="φ", value=self.CONSTANTS["φ"])

        if self._check(TokenType.PI):
            token = self._advance()
            return ConstantNode(name="π", value=self.CONSTANTS["π"])

        if self._check(TokenType.GLYPH_SYMBOL):
            token = self._advance()
            return GlyphLitNode(symbols=token.value)

        if self._check(TokenType.LPAREN):
            self._advance()
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN)
            return expr

        # Tongue identifiers
        for tongue_type in [TokenType.KO, TokenType.AV, TokenType.RU,
                           TokenType.CA, TokenType.UM, TokenType.DR]:
            if self._check(tongue_type):
                token = self._advance()
                return IdentifierNode(name=token.value)

        return None

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _current(self) -> Token:
        """Get current token."""
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        """Consume and return current token."""
        token = self.tokens[self.pos]
        if not self._is_at_end():
            self.pos += 1
        return token

    def _check(self, token_type: TokenType) -> bool:
        """Check if current token is of given type."""
        if self._is_at_end():
            return False
        return self._current().type == token_type

    def _check_any(self, types: List[TokenType]) -> bool:
        """Check if current token is any of given types."""
        return any(self._check(t) for t in types)

    def _expect(self, token_type: TokenType) -> Token:
        """Consume token of expected type or raise error."""
        if self._check(token_type):
            return self._advance()
        raise SyntaxError(
            f"Expected {token_type.name} but got {self._current().type.name} "
            f"at line {self._current().line}"
        )

    def _is_at_end(self) -> bool:
        """Check if at end of tokens."""
        return self._current().type == TokenType.EOF

    def _skip_newlines(self) -> None:
        """Skip newline tokens."""
        while self._check(TokenType.NEWLINE):
            self._advance()
