"""
Spiralverse DSL Lexer

Tokenizes Spiralverse source code into tokens for parsing.

@module spiralverse/dsl/lexer
@version 1.0.0
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Iterator
import re

# ============================================================================
# Token Types
# ============================================================================

class TokenType(Enum):
    """Token types in Spiralverse DSL."""

    # Literals
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    IDENTIFIER = auto()

    # Keywords
    DEFINE = auto()
    PATTERN = auto()
    FLOW = auto()
    AGENT = auto()
    INPUT = auto()
    OUTPUT = auto()
    LET = auto()
    YIELD = auto()
    RETURN = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    MATCH = auto()
    CASE = auto()
    IMPORT = auto()
    FROM = auto()
    AS = auto()

    # Tongue keywords
    TONGUE = auto()
    KO = auto()
    AV = auto()
    RU = auto()
    CA = auto()
    UM = auto()
    DR = auto()

    # Type keywords
    WAVE = auto()
    POSITION = auto()
    SIGNAL = auto()
    VECTOR = auto()

    # Decorators
    AT = auto()
    GLYPH = auto()
    AXIOM = auto()
    ORACLE = auto()
    CHARM = auto()
    LEDGER = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    POWER = auto()
    ASSIGN = auto()
    EQUALS = auto()
    NOT_EQUALS = auto()
    LESS_THAN = auto()
    GREATER_THAN = auto()
    LESS_EQUAL = auto()
    GREATER_EQUAL = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    ARROW = auto()
    FAT_ARROW = auto()
    PIPE = auto()
    DOUBLE_PIPE = auto()

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    COLON = auto()
    DOT = auto()
    SEMICOLON = auto()

    # Special
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()

    # Constants
    PHI = auto()      # φ (golden ratio)
    PI = auto()       # π
    EULER = auto()    # e

    # Glyph symbols (from polyglot alphabets)
    GLYPH_SYMBOL = auto()


# Keywords mapping
KEYWORDS = {
    "define": TokenType.DEFINE,
    "pattern": TokenType.PATTERN,
    "flow": TokenType.FLOW,
    "agent": TokenType.AGENT,
    "input": TokenType.INPUT,
    "output": TokenType.OUTPUT,
    "let": TokenType.LET,
    "yield": TokenType.YIELD,
    "return": TokenType.RETURN,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "match": TokenType.MATCH,
    "case": TokenType.CASE,
    "import": TokenType.IMPORT,
    "from": TokenType.FROM,
    "as": TokenType.AS,
    # Tongues
    "tongue": TokenType.TONGUE,
    "KO": TokenType.KO,
    "AV": TokenType.AV,
    "RU": TokenType.RU,
    "CA": TokenType.CA,
    "UM": TokenType.UM,
    "DR": TokenType.DR,
    # Types
    "Wave": TokenType.WAVE,
    "Position": TokenType.POSITION,
    "Signal": TokenType.SIGNAL,
    "Vector": TokenType.VECTOR,
    # Decorators
    "glyph": TokenType.GLYPH,
    "axiom": TokenType.AXIOM,
    "oracle": TokenType.ORACLE,
    "charm": TokenType.CHARM,
    "ledger": TokenType.LEDGER,
    # Logical
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
}


# Glyph symbols (subset from polyglot alphabets)
GLYPH_SYMBOLS = set("●○◉◎▲△▼▽■□★☆✓✗→←↔⇒⇐⊲⊳")


# ============================================================================
# Token
# ============================================================================

@dataclass
class Token:
    """A single token from lexical analysis."""
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"


# ============================================================================
# Lexer
# ============================================================================

class SpiralverseLexer:
    """
    Lexer for Spiralverse DSL.

    Handles:
    - Indentation-based scoping (Python-like)
    - Unicode glyph symbols
    - Mathematical constants (φ, π, e)
    """

    def __init__(self, source: str):
        """
        Initialize lexer with source code.

        Args:
            source: Spiralverse source code
        """
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.indent_stack = [0]
        self.tokens: List[Token] = []
        self._at_line_start = True

    def tokenize(self) -> List[Token]:
        """
        Tokenize the source code.

        Returns:
            List of tokens
        """
        self.tokens = []
        self.pos = 0
        self.line = 1
        self.column = 1
        self.indent_stack = [0]
        self._at_line_start = True

        while self.pos < len(self.source):
            self._scan_token()

        # Handle remaining dedents
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(TokenType.DEDENT, "", self.line, self.column))

        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens

    def _scan_token(self) -> None:
        """Scan and emit the next token."""
        # Handle line start (indentation)
        if self._at_line_start:
            self._handle_indentation()
            self._at_line_start = False
            return

        # Skip whitespace (but not newlines)
        if self._peek() in " \t" and not self._at_line_start:
            self._advance()
            return

        # Newline
        if self._peek() == "\n":
            self._advance()
            self.line += 1
            self.column = 1
            self._at_line_start = True
            self.tokens.append(Token(TokenType.NEWLINE, "\\n", self.line - 1, self.column))
            return

        # Skip carriage return
        if self._peek() == "\r":
            self._advance()
            return

        # Comments
        if self._peek() == "#":
            self._skip_comment()
            return

        # String literals
        if self._peek() in '"\'':
            self._scan_string()
            return

        # Numbers
        if self._peek().isdigit() or (self._peek() == "." and self._peek_next().isdigit()):
            self._scan_number()
            return

        # Identifiers and keywords
        if self._peek().isalpha() or self._peek() == "_":
            self._scan_identifier()
            return

        # Mathematical constants
        if self._peek() in "φπe":
            self._scan_constant()
            return

        # Glyph symbols
        if self._peek() in GLYPH_SYMBOLS:
            self._scan_glyph()
            return

        # Operators and delimiters
        self._scan_operator()

    def _handle_indentation(self) -> None:
        """Handle indentation at line start."""
        indent = 0

        while self.pos < len(self.source) and self._peek() in " \t":
            if self._peek() == " ":
                indent += 1
            else:  # tab
                indent += 4
            self._advance()

        # Skip empty lines and comments
        if self._peek() in "\n\r#":
            self._at_line_start = False
            return

        current_indent = self.indent_stack[-1]

        if indent > current_indent:
            self.indent_stack.append(indent)
            self.tokens.append(Token(TokenType.INDENT, str(indent), self.line, 1))
        elif indent < current_indent:
            while self.indent_stack and self.indent_stack[-1] > indent:
                self.indent_stack.pop()
                self.tokens.append(Token(TokenType.DEDENT, "", self.line, 1))

    def _skip_comment(self) -> None:
        """Skip a comment until end of line."""
        while self.pos < len(self.source) and self._peek() != "\n":
            self._advance()

    def _scan_string(self) -> None:
        """Scan a string literal."""
        quote = self._advance()
        start_line = self.line
        start_col = self.column - 1
        value = ""

        while self.pos < len(self.source) and self._peek() != quote:
            if self._peek() == "\\":
                self._advance()
                if self.pos < len(self.source):
                    escape = self._advance()
                    if escape == "n":
                        value += "\n"
                    elif escape == "t":
                        value += "\t"
                    elif escape == "\\":
                        value += "\\"
                    elif escape == quote:
                        value += quote
                    else:
                        value += escape
            elif self._peek() == "\n":
                raise SyntaxError(f"Unterminated string at line {start_line}")
            else:
                value += self._advance()

        if self.pos >= len(self.source):
            raise SyntaxError(f"Unterminated string at line {start_line}")

        self._advance()  # closing quote
        self.tokens.append(Token(TokenType.STRING, value, start_line, start_col))

    def _scan_number(self) -> None:
        """Scan a numeric literal."""
        start_col = self.column
        value = ""
        is_float = False

        while self.pos < len(self.source) and (self._peek().isdigit() or self._peek() == "."):
            if self._peek() == ".":
                if is_float:
                    break
                is_float = True
            value += self._advance()

        # Scientific notation
        if self.pos < len(self.source) and self._peek() in "eE":
            is_float = True
            value += self._advance()
            if self._peek() in "+-":
                value += self._advance()
            while self.pos < len(self.source) and self._peek().isdigit():
                value += self._advance()

        token_type = TokenType.FLOAT if is_float else TokenType.INTEGER
        self.tokens.append(Token(token_type, value, self.line, start_col))

    def _scan_identifier(self) -> None:
        """Scan an identifier or keyword."""
        start_col = self.column
        value = ""

        while self.pos < len(self.source) and (
            self._peek().isalnum() or self._peek() == "_"
        ):
            value += self._advance()

        # Check for keyword
        token_type = KEYWORDS.get(value, TokenType.IDENTIFIER)
        self.tokens.append(Token(token_type, value, self.line, start_col))

    def _scan_constant(self) -> None:
        """Scan a mathematical constant."""
        start_col = self.column
        char = self._advance()

        if char == "φ":
            self.tokens.append(Token(TokenType.PHI, "φ", self.line, start_col))
        elif char == "π":
            self.tokens.append(Token(TokenType.PI, "π", self.line, start_col))
        elif char == "e":
            self.tokens.append(Token(TokenType.EULER, "e", self.line, start_col))

    def _scan_glyph(self) -> None:
        """Scan a glyph symbol sequence."""
        start_col = self.column
        value = ""

        while self.pos < len(self.source) and self._peek() in GLYPH_SYMBOLS:
            value += self._advance()

        self.tokens.append(Token(TokenType.GLYPH_SYMBOL, value, self.line, start_col))

    def _scan_operator(self) -> None:
        """Scan an operator or delimiter."""
        start_col = self.column
        char = self._advance()

        # Two-character operators
        if char == "=" and self._peek() == "=":
            self._advance()
            self.tokens.append(Token(TokenType.EQUALS, "==", self.line, start_col))
        elif char == "!" and self._peek() == "=":
            self._advance()
            self.tokens.append(Token(TokenType.NOT_EQUALS, "!=", self.line, start_col))
        elif char == "<" and self._peek() == "=":
            self._advance()
            self.tokens.append(Token(TokenType.LESS_EQUAL, "<=", self.line, start_col))
        elif char == ">" and self._peek() == "=":
            self._advance()
            self.tokens.append(Token(TokenType.GREATER_EQUAL, ">=", self.line, start_col))
        elif char == "-" and self._peek() == ">":
            self._advance()
            self.tokens.append(Token(TokenType.ARROW, "->", self.line, start_col))
        elif char == "=" and self._peek() == ">":
            self._advance()
            self.tokens.append(Token(TokenType.FAT_ARROW, "=>", self.line, start_col))
        elif char == "|" and self._peek() == "|":
            self._advance()
            self.tokens.append(Token(TokenType.DOUBLE_PIPE, "||", self.line, start_col))
        elif char == "*" and self._peek() == "*":
            self._advance()
            self.tokens.append(Token(TokenType.POWER, "**", self.line, start_col))

        # Single-character operators
        elif char == "+":
            self.tokens.append(Token(TokenType.PLUS, "+", self.line, start_col))
        elif char == "-":
            self.tokens.append(Token(TokenType.MINUS, "-", self.line, start_col))
        elif char == "*":
            self.tokens.append(Token(TokenType.STAR, "*", self.line, start_col))
        elif char == "/":
            self.tokens.append(Token(TokenType.SLASH, "/", self.line, start_col))
        elif char == "%":
            self.tokens.append(Token(TokenType.PERCENT, "%", self.line, start_col))
        elif char == "=":
            self.tokens.append(Token(TokenType.ASSIGN, "=", self.line, start_col))
        elif char == "<":
            self.tokens.append(Token(TokenType.LESS_THAN, "<", self.line, start_col))
        elif char == ">":
            self.tokens.append(Token(TokenType.GREATER_THAN, ">", self.line, start_col))
        elif char == "|":
            self.tokens.append(Token(TokenType.PIPE, "|", self.line, start_col))
        elif char == "@":
            self.tokens.append(Token(TokenType.AT, "@", self.line, start_col))

        # Delimiters
        elif char == "(":
            self.tokens.append(Token(TokenType.LPAREN, "(", self.line, start_col))
        elif char == ")":
            self.tokens.append(Token(TokenType.RPAREN, ")", self.line, start_col))
        elif char == "[":
            self.tokens.append(Token(TokenType.LBRACKET, "[", self.line, start_col))
        elif char == "]":
            self.tokens.append(Token(TokenType.RBRACKET, "]", self.line, start_col))
        elif char == "{":
            self.tokens.append(Token(TokenType.LBRACE, "{", self.line, start_col))
        elif char == "}":
            self.tokens.append(Token(TokenType.RBRACE, "}", self.line, start_col))
        elif char == ",":
            self.tokens.append(Token(TokenType.COMMA, ",", self.line, start_col))
        elif char == ":":
            self.tokens.append(Token(TokenType.COLON, ":", self.line, start_col))
        elif char == ".":
            self.tokens.append(Token(TokenType.DOT, ".", self.line, start_col))
        elif char == ";":
            self.tokens.append(Token(TokenType.SEMICOLON, ";", self.line, start_col))

        else:
            raise SyntaxError(
                f"Unexpected character '{char}' at line {self.line}, column {start_col}"
            )

    def _peek(self) -> str:
        """Peek at current character."""
        if self.pos >= len(self.source):
            return "\0"
        return self.source[self.pos]

    def _peek_next(self) -> str:
        """Peek at next character."""
        if self.pos + 1 >= len(self.source):
            return "\0"
        return self.source[self.pos + 1]

    def _advance(self) -> str:
        """Consume and return current character."""
        char = self.source[self.pos]
        self.pos += 1
        self.column += 1
        return char
