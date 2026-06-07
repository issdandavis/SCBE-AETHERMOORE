"""
tier2_parser.py — Expression and statement parser → Tier 2 AST.

Bridges the gap between human-readable expressions (any notation, any syntax)
and the Tier 2 node types in tier2_composer.py. Once a string is parsed into a
Tier 2 AST, it can be:
  - Evaluated:  eval_node(ast, env)
  - Emitted:    emit_node(ast, tongue)  → Python / TypeScript / Rust / C / Julia / Haskell
  - Compiled:   AtomProgram.from_text() → Sacred Tongue byte stream

Grammar (informal):
    prog     = stmt* EOF
    stmt     = let | while | if | return | expr
    let      = ('let'|'var') IDENT '=' expr  |  IDENT '=' expr
    while    = 'while' expr ':' block  |  'while' expr '{' block '}'
    if       = 'if' expr ':' block ['else' ':' block]
             | 'if' '(' expr ')' '{' block '}' ['else' '{' block '}']
    return   = 'return' expr
    block    = stmt+  (dedented or '}')
    expr     = Pratt operator-precedence parser
    call     = IDENT '(' args ')'
    args     = expr (',' expr)*
    lit      = NUMBER | STRING
    NUMBER   = basen_normalizer — binary / hex / ternary / octal / decimal

Supported operators (grouped by binding power):
    Assignment-like:  =  (not parsed as expr, only in let)
    Logical:  or  and  not
    Comparison:  ==  !=  <  >  <=  >=
    Bitwise:  |  ^  &  <<  >>
    Additive:  +  -
    Multiplicative:  *  /  //  %
    Exponential:  **  ^^ (power)
    Unary prefix:  -  not  ~
    Call / subscript:  f(...)

Op name mapping to Tier 2 OpNode names (from tier2_composer.py):
    +  → add      -  → sub      *  → mul      /  → div
    // → div      %  → mod      ** → pow      & → and
    |  → or       ^  → xor      << → shl      >> → shr
    == → eq       != → neq      <  → lt       >  → gt
    <= → lte      >= → gte      not → not     ~  → not
    (unary -)     → neg

Named function calls map to known Tier 2 ops:
    sqrt, log, exp, abs, ceil, floor, round, popcount,
    inc, dec, reduce, fold, scan, filter, map, accum,
    factorial (built-in macro), lucas_lehmer (built-in macro),
    mersenne (built-in macro)

Built-in macros (return SeqNode ready to evaluate):
    factorial(n)          — iterative factorial via WhileNode
    lucas_lehmer(p)       — Lucas-Lehmer primality test for 2^p - 1
    mersenne(p)           — returns the Mersenne number 2^p - 1
    gcd(a, b)             — iterative GCD via WhileNode
    euclid_perfect(p)     — 2^(p-1) * (2^p - 1) perfect number formula
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.cli.tier2_composer import (
    LitNode,
    VarNode,
    OpNode,
    LetNode,
    IfNode,
    WhileNode,
    SeqNode,
    CallNode,
    DefNode,
)
from src.cli.basen_normalizer import parse_literal


# Re-export parse error type
class ParseError(Exception):
    pass


# ─────────────────────────────────────────────────────────────────────────────
#  Tokenizer
# ─────────────────────────────────────────────────────────────────────────────


class TK(Enum):
    NUM = auto()
    IDENT = auto()
    OP = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    COLON = auto()
    SEMI = auto()
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()


@dataclass
class Token:
    kind: TK
    text: str
    pos: int


_TOKEN_PATTERNS = [
    (
        TK.NUM,
        r"0[bB][01][01_]*|0[xX][0-9A-Fa-f][0-9A-Fa-f_]*|0[tT][012][012_]*"
        r"|0[oO][0-7][0-7_]*|[0-9][0-9_]*(?:\.[0-9][0-9_]*)?(?:[eE][+-]?[0-9]+)?"
        r"|[0-9A-Fa-f]+[hH]|\$[0-9A-Fa-f]+|%[01]+",
    ),
    (TK.IDENT, r"[A-Za-z_][A-Za-z0-9_]*"),
    (TK.OP, r"<<=|>>=|<<|>>|<=|>=|==|!=|\*\*|\^{2}|//|&&|\|\||->|[-+*//%^&|<>=!~]"),
    (TK.LPAREN, r"\("),
    (TK.RPAREN, r"\)"),
    (TK.LBRACE, r"\{"),
    (TK.RBRACE, r"\}"),
    (TK.COMMA, r","),
    (TK.COLON, r":"),
    (TK.SEMI, r";"),
    (TK.NEWLINE, r"\n"),
]

_MASTER = re.compile(
    "|".join(f"(?P<g{i}>{pat})" for i, (_, pat) in enumerate(_TOKEN_PATTERNS))
    + r"|(?P<ws>[ \t\r]+)"
    + r"|(?P<comment>#[^\n]*)"
)


def tokenize(text: str) -> List[Token]:
    """Tokenize source text. Skips whitespace and comments."""
    tokens: List[Token] = []
    for m in _MASTER.finditer(text):
        if m.lastgroup in ("ws", "comment"):
            continue
        for i, (tk, _) in enumerate(_TOKEN_PATTERNS):
            grp = f"g{i}"
            if m.lastgroup == grp:
                tokens.append(Token(kind=tk, text=m.group(), pos=m.start()))
                break
    tokens.append(Token(kind=TK.EOF, text="", pos=len(text)))
    return tokens


# ─────────────────────────────────────────────────────────────────────────────
#  Operator binding powers and Tier 2 op name mapping
# ─────────────────────────────────────────────────────────────────────────────

# (left binding power, right binding power, tier2 op name)
_INFIX: Dict[str, tuple] = {
    "or": (10, 10, "or"),
    "and": (20, 20, "and"),
    "|": (25, 25, "or"),
    "^": (30, 30, "xor"),
    "&": (35, 35, "and"),
    "==": (40, 40, "eq"),
    "!=": (40, 40, "neq"),
    "<": (50, 50, "lt"),
    ">": (50, 50, "gt"),
    "<=": (50, 50, "lte"),
    ">=": (50, 50, "gte"),
    "<<": (60, 60, "shl"),
    ">>": (60, 60, "shr"),
    "+": (70, 70, "add"),
    "-": (70, 70, "sub"),
    "*": (80, 80, "mul"),
    "/": (80, 80, "div"),
    "//": (80, 80, "div"),
    "%": (80, 80, "mod"),
    "**": (90, 89, "pow"),  # right-associative
    "^^": (90, 89, "pow"),
}

_PREFIX_OPS: Dict[str, str] = {
    "-": "neg",
    "not": "not",
    "~": "not",
}

# Known single-argument ops mapping function names → tier2 op names
_UNARY_FUNCS: Dict[str, str] = {
    "sqrt": "sqrt",
    "log": "log",
    "exp": "exp",
    "abs": "abs",
    "ceil": "ceil",
    "floor": "floor",
    "round": "round",
    "popcount": "popcount",
    "inc": "inc",
    "dec": "dec",
    "neg": "neg",
}

# Binary function names → tier2 op names
_BINARY_FUNCS: Dict[str, str] = {
    "add": "add",
    "sub": "sub",
    "mul": "mul",
    "div": "div",
    "mod": "mod",
    "pow": "pow",
    "gcd_step": "mod",
    "shl": "shl",
    "shr": "shr",
    "eq": "eq",
    "neq": "neq",
    "lt": "lt",
    "gt": "gt",
    "max": "max",
    "min": "min",
}

# Ternary function names → tier2 op names
_TERNARY_FUNCS: Dict[str, str] = {
    "clamp": "clamp",
    "within": "within",
}

_KEYWORDS = frozenset(
    [
        "let",
        "var",
        "if",
        "else",
        "while",
        "for",
        "return",
        "def",
        "fn",
        "func",
        "not",
        "and",
        "or",
        "true",
        "false",
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
#  Built-in macros — return Tier 2 ASTs for compound operations
# ─────────────────────────────────────────────────────────────────────────────


def build_factorial(n_expr) -> SeqNode:
    """Iterative factorial via WhileNode.

    Equivalent to:
        acc = 1; n_var = n
        while n_var > 1: acc *= n_var; n_var -= 1
    Returns final value of acc.
    """
    return SeqNode(
        nodes=[
            LetNode("__acc", LitNode(1)),
            LetNode("__n", n_expr),
            WhileNode(
                cond=OpNode("gt", {"a": VarNode("__n"), "b": LitNode(1)}),
                body=SeqNode(
                    nodes=[
                        LetNode(
                            "__acc",
                            OpNode("mul", {"a": VarNode("__acc"), "b": VarNode("__n")}),
                        ),
                        LetNode("__n", OpNode("dec", {"a": VarNode("__n")})),
                    ]
                ),
                max_iterations=200_000,
            ),
            VarNode("__acc"),
        ]
    )


def build_mersenne(p_expr) -> SeqNode:
    """Compute 2^p - 1.

    Returns SeqNode that evaluates to the Mersenne number.
    """
    return SeqNode(
        nodes=[
            LetNode("__p", p_expr),
            LetNode(
                "__M",
                OpNode(
                    "sub",
                    {
                        "a": OpNode("shl", {"a": LitNode(1), "b": VarNode("__p")}),
                        "b": LitNode(1),
                    },
                ),
            ),
            VarNode("__M"),
        ]
    )


def build_lucas_lehmer(p_expr) -> SeqNode:
    """Lucas-Lehmer primality test for 2^p - 1.

    Equivalent to:
        M = (1 << p) - 1
        s = 4
        i = 0
        while i < p - 2:
            s = (s * s - 2) % M
            i = i + 1
        result = (s == 0)

    Special case: p==2 → 2^2-1=3 is prime, but the standard loop runs 0
    iterations and leaves s=4, so we return 1 (True) by direct check.

    Returns True (1) if 2^p - 1 is prime, False (0) otherwise.
    WARNING: for large p this runs p-2 iterations — use only for small exponents
    in the interactive CLI. The prime_fog_of_war_probe.py uses native Python for
    large exponents.
    """
    return SeqNode(
        nodes=[
            LetNode("__p", p_expr),
            # p==2 edge case: 2^2-1=3 is prime; the loop runs 0 times so s stays 4.
            # Inject the result as 1 when p==2.
            LetNode("__ll_p2", OpNode("eq", {"a": VarNode("__p"), "b": LitNode(2)})),
            # M = (1 << p) - 1
            LetNode(
                "__M",
                OpNode(
                    "sub",
                    {
                        "a": OpNode("shl", {"a": LitNode(1), "b": VarNode("__p")}),
                        "b": LitNode(1),
                    },
                ),
            ),
            LetNode("__s", LitNode(4)),
            LetNode("__i", LitNode(0)),
            # limit = p - 2
            LetNode("__limit", OpNode("sub", {"a": VarNode("__p"), "b": LitNode(2)})),
            WhileNode(
                cond=OpNode("lt", {"a": VarNode("__i"), "b": VarNode("__limit")}),
                body=SeqNode(
                    nodes=[
                        LetNode(
                            "__s",
                            OpNode(
                                "mod",
                                {
                                    "a": OpNode(
                                        "sub",
                                        {
                                            "a": OpNode(
                                                "mul",
                                                {
                                                    "a": VarNode("__s"),
                                                    "b": VarNode("__s"),
                                                },
                                            ),
                                            "b": LitNode(2),
                                        },
                                    ),
                                    "b": VarNode("__M"),
                                },
                            ),
                        ),
                        LetNode(
                            "__i", OpNode("add", {"a": VarNode("__i"), "b": LitNode(1)})
                        ),
                    ]
                ),
                max_iterations=500_000,
            ),
            # result: p==2 → 1; otherwise s==0
            LetNode("__ll_s0", OpNode("eq", {"a": VarNode("__s"), "b": LitNode(0)})),
            # OR: if either p==2 or s==0, it's prime
            OpNode("or", {"a": VarNode("__ll_p2"), "b": VarNode("__ll_s0")}),
        ]
    )


def build_gcd(a_expr, b_expr) -> SeqNode:
    """Iterative GCD via Euclidean algorithm.

    while b != 0: t = b; b = a % b; a = t
    return a
    """
    return SeqNode(
        nodes=[
            LetNode("__a", a_expr),
            LetNode("__b", b_expr),
            WhileNode(
                cond=OpNode("neq", {"a": VarNode("__b"), "b": LitNode(0)}),
                body=SeqNode(
                    nodes=[
                        LetNode("__t", VarNode("__b")),
                        LetNode(
                            "__b",
                            OpNode("mod", {"a": VarNode("__a"), "b": VarNode("__b")}),
                        ),
                        LetNode("__a", VarNode("__t")),
                    ]
                ),
                max_iterations=200,
            ),
            VarNode("__a"),
        ]
    )


def build_euclid_perfect(p_expr) -> SeqNode:
    """Euclid-Euler perfect number: 2^(p-1) * (2^p - 1).

    Only meaningful when 2^p - 1 is a Mersenne prime.
    """
    return SeqNode(
        nodes=[
            LetNode("__p", p_expr),
            LetNode("__pm1", OpNode("sub", {"a": VarNode("__p"), "b": LitNode(1)})),
            LetNode(
                "__mersenne",
                OpNode(
                    "sub",
                    {
                        "a": OpNode("shl", {"a": LitNode(1), "b": VarNode("__p")}),
                        "b": LitNode(1),
                    },
                ),
            ),
            LetNode(
                "__result",
                OpNode(
                    "mul",
                    {
                        "a": OpNode("shl", {"a": LitNode(1), "b": VarNode("__pm1")}),
                        "b": VarNode("__mersenne"),
                    },
                ),
            ),
            VarNode("__result"),
        ]
    )


_MACROS = {
    "factorial": (1, lambda args: build_factorial(args[0])),
    "mersenne": (1, lambda args: build_mersenne(args[0])),
    "lucas_lehmer": (1, lambda args: build_lucas_lehmer(args[0])),
    "gcd": (2, lambda args: build_gcd(args[0], args[1])),
    "euclid_perfect": (1, lambda args: build_euclid_perfect(args[0])),
}


# ─────────────────────────────────────────────────────────────────────────────
#  Parser
# ─────────────────────────────────────────────────────────────────────────────


class Parser:
    """Pratt top-down operator precedence parser.

    Converts a token stream into a Tier 2 AST. The AST can be passed
    directly to eval_node() or emit_node() from tier2_composer.py.
    """

    def __init__(self, tokens: List[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> Token:
        while self._pos < len(self._tokens) and self._tokens[self._pos].kind in (
            TK.NEWLINE,
            TK.SEMI,
        ):
            self._pos += 1
        if self._pos >= len(self._tokens):
            return Token(TK.EOF, "", -1)
        return self._tokens[self._pos]

    def _peek_raw(self) -> Token:
        if self._pos >= len(self._tokens):
            return Token(TK.EOF, "", -1)
        return self._tokens[self._pos]

    def _consume(self, kind: Optional[TK] = None, text: Optional[str] = None) -> Token:
        tok = self._peek()
        if kind is not None and tok.kind != kind:
            raise ParseError(
                f"Expected token {kind.name}, got {tok.kind.name!r} ({tok.text!r}) at pos {tok.pos}"
            )
        if text is not None and tok.text != text:
            raise ParseError(f"Expected {text!r}, got {tok.text!r} at pos {tok.pos}")
        self._pos += 1
        return tok

    def _skip_newlines(self) -> None:
        while self._pos < len(self._tokens) and self._tokens[self._pos].kind in (
            TK.NEWLINE,
            TK.SEMI,
        ):
            self._pos += 1

    def _at_end(self) -> bool:
        return self._peek().kind == TK.EOF

    # ── Expression (Pratt) ────────────────────────────────────────────────

    def parse_expr(self, min_bp: int = 0):
        """Parse an expression with binding power >= min_bp."""
        tok = self._peek()

        # Prefix
        if tok.kind == TK.NUM:
            self._pos += 1
            left = self._parse_number(tok.text)
        elif tok.kind == TK.IDENT and tok.text in ("true", "True"):
            self._pos += 1
            left = LitNode(1)
        elif tok.kind == TK.IDENT and tok.text in ("false", "False"):
            self._pos += 1
            left = LitNode(0)
        elif tok.kind == TK.IDENT and tok.text == "not":
            # logical NOT: emit as (expr == 0) so it works in boolean context
            self._pos += 1
            operand = self.parse_expr(min_bp=15)
            left = OpNode("eq", {"a": operand, "b": LitNode(0)})
        elif tok.kind == TK.IDENT and tok.text in _PREFIX_OPS:
            self._pos += 1
            operand = self.parse_expr(min_bp=85)
            left = OpNode(_PREFIX_OPS[tok.text], {"a": operand})
        elif tok.kind == TK.OP and tok.text == "-":
            self._pos += 1
            operand = self.parse_expr(min_bp=85)
            left = OpNode("neg", {"a": operand})
        elif tok.kind == TK.OP and tok.text == "~":
            self._pos += 1
            operand = self.parse_expr(min_bp=85)
            left = OpNode("not", {"a": operand})
        elif tok.kind == TK.IDENT:
            self._pos += 1
            # Look-ahead for function call
            if self._peek_raw().kind == TK.LPAREN:
                left = self._parse_call(tok.text)
            else:
                left = VarNode(tok.text)
        elif tok.kind == TK.LPAREN:
            self._pos += 1
            left = self.parse_expr(0)
            self._consume(TK.RPAREN)
        else:
            raise ParseError(
                f"Unexpected token {tok.kind.name!r} ({tok.text!r}) at pos {tok.pos}"
            )

        # Infix
        while True:
            op_tok = self._peek()
            if op_tok.kind == TK.EOF:
                break
            # Ident keywords as infix operators (and, or)
            if op_tok.kind == TK.IDENT and op_tok.text in _INFIX:
                info = _INFIX[op_tok.text]
            elif op_tok.kind == TK.OP and op_tok.text in _INFIX:
                info = _INFIX[op_tok.text]
            else:
                break

            lbp, rbp, op_name = info
            if lbp <= min_bp:
                break
            self._pos += 1
            right = self.parse_expr(rbp)
            left = OpNode(op_name, {"a": left, "b": right})

        return left

    def _parse_number(self, text: str):
        """Parse a numeric literal, handling floats and any base."""
        if "." in text or "e" in text.lower():
            return LitNode(float(text))
        try:
            p = parse_literal(text)
            return LitNode(p.value)
        except ValueError:
            return LitNode(int(text))

    def _parse_call(self, name: str):
        """Parse a function call. May expand to a macro."""
        self._consume(TK.LPAREN)
        args = []
        while self._peek().kind != TK.RPAREN and not self._at_end():
            args.append(self.parse_expr(0))
            if self._peek().kind == TK.COMMA:
                self._pos += 1
        self._consume(TK.RPAREN)

        # Macro expansion
        if name in _MACROS:
            arity, builder = _MACROS[name]
            if len(args) != arity:
                raise ParseError(
                    f"Macro {name!r} expects {arity} args, got {len(args)}"
                )
            return builder(args)

        # Unary named function
        if name in _UNARY_FUNCS and len(args) == 1:
            return OpNode(_UNARY_FUNCS[name], {"a": args[0]})

        # Binary named function
        if name in _BINARY_FUNCS and len(args) == 2:
            return OpNode(_BINARY_FUNCS[name], {"a": args[0], "b": args[1]})

        # Ternary named function
        if name in _TERNARY_FUNCS and len(args) == 3:
            return OpNode(
                _TERNARY_FUNCS[name], {"a": args[0], "b": args[1], "c": args[2]}
            )

        # Unknown: emit as CallNode
        return CallNode(
            func_name=name,
            kwargs={f"arg{i}": a for i, a in enumerate(args)},
        )

    # ── Statements ────────────────────────────────────────────────────────

    def parse_stmt(self):
        """Parse one statement."""
        self._skip_newlines()
        tok = self._peek()

        if tok.kind == TK.EOF:
            return None

        # let / var binding
        if tok.kind == TK.IDENT and tok.text in ("let", "var"):
            self._pos += 1
            name_tok = self._consume(TK.IDENT)
            self._consume(TK.OP, "=")
            expr = self.parse_expr(0)
            return LetNode(name_tok.text, expr)

        # return
        if tok.kind == TK.IDENT and tok.text == "return":
            self._pos += 1
            expr = self.parse_expr(0)
            return expr  # just the expression value

        # while
        if tok.kind == TK.IDENT and tok.text == "while":
            return self._parse_while()

        # if
        if tok.kind == TK.IDENT and tok.text == "if":
            return self._parse_if()

        # def / fn / func
        if tok.kind == TK.IDENT and tok.text in ("def", "fn", "func"):
            return self._parse_def()

        # Assignment: IDENT = expr  (only if next is =, not ==)
        if tok.kind == TK.IDENT and tok.text not in _KEYWORDS:
            peek_next = (
                self._tokens[self._pos + 1]
                if self._pos + 1 < len(self._tokens)
                else None
            )
            if peek_next and peek_next.kind == TK.OP and peek_next.text == "=":
                self._pos += 2  # skip name and =
                expr = self.parse_expr(0)
                return LetNode(tok.text, expr)

        # Expression statement
        return self.parse_expr(0)

    def _parse_block(self) -> SeqNode:
        """Parse a block — either `{ stmts }` or a Python-style indent block."""
        self._skip_newlines()
        if self._peek().kind == TK.LBRACE:
            self._pos += 1  # consume {
            stmts = []
            while self._peek().kind != TK.RBRACE and not self._at_end():
                s = self.parse_stmt()
                if s is not None:
                    stmts.append(s)
            self._consume(TK.RBRACE)
            return SeqNode(stmts)

        # Python-style: parse one statement after the `:` already consumed
        s = self.parse_stmt()
        stmts = [s] if s is not None else []
        return SeqNode(stmts)

    def _parse_while(self) -> WhileNode:
        self._pos += 1  # consume 'while'
        cond = self.parse_expr(0)
        # optional colon or opening brace handled by _parse_block
        if self._peek().kind == TK.COLON:
            self._pos += 1
        block = self._parse_block()
        return WhileNode(cond=cond, body=block)

    def _parse_if(self) -> IfNode:
        self._pos += 1  # consume 'if'
        cond = self.parse_expr(0)
        if self._peek().kind == TK.COLON:
            self._pos += 1
        then_block = self._parse_block()
        else_block = None
        self._skip_newlines()
        if self._peek().kind == TK.IDENT and self._peek().text == "else":
            self._pos += 1
            if self._peek().kind == TK.COLON:
                self._pos += 1
            else_block = self._parse_block()
        return IfNode(cond=cond, then_body=then_block, else_body=else_block)

    def _parse_def(self) -> DefNode:
        self._pos += 1  # consume 'def'/'fn'
        name_tok = self._consume(TK.IDENT)
        self._consume(TK.LPAREN)
        params = []
        while self._peek().kind != TK.RPAREN and not self._at_end():
            params.append(self._consume(TK.IDENT).text)
            if self._peek().kind == TK.COMMA:
                self._pos += 1
        self._consume(TK.RPAREN)
        if self._peek().kind == TK.COLON:
            self._pos += 1
        body = self._parse_block()
        # return_var: last expression in the body
        return DefNode(name=name_tok.text, params=params, body=body, return_var=None)

    def parse_program(self) -> SeqNode:
        """Parse a full program (sequence of statements)."""
        stmts = []
        while not self._at_end():
            s = self.parse_stmt()
            if s is not None:
                stmts.append(s)
        return SeqNode(stmts)


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────


def parse(text: str):
    """Parse an expression or program string into a Tier 2 AST node.

    Single-expression inputs return the expression node directly.
    Multi-statement inputs return a SeqNode.

    Examples:
        parse("3 + 4")              → OpNode("add", {a: LitNode(3), b: LitNode(4)})
        parse("factorial(5)")       → SeqNode([LetNode("__acc", ...), WhileNode(...), VarNode])
        parse("x = 5\\nx * 2")      → SeqNode([LetNode("x", 5), OpNode("mul", ...)])
        parse("lucas_lehmer(13)")   → SeqNode([...WhileNode...])
    """
    tokens = tokenize(text.strip())
    parser = Parser(tokens)
    prog = parser.parse_program()
    # If there's exactly one node in the sequence, unwrap it
    if len(prog.nodes) == 1:
        return prog.nodes[0]
    return prog


def parse_expr(text: str):
    """Parse a single expression (no statements)."""
    tokens = tokenize(text.strip())
    parser = Parser(tokens)
    return parser.parse_expr(0)


# ─────────────────────────────────────────────────────────────────────────────
#  Self-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys as _sys

    _sys.path.insert(0, str(_root))
    from src.cli.tier2_composer import eval_node, emit_node, VarEnv

    tests = [
        ("3 + 4", 7, "add"),
        ("2 ** 10", 1024, "power"),
        ("factorial(5)", 120, "factorial via WhileNode"),
        ("factorial(10)", 3628800, "factorial 10"),
        ("gcd(48, 18)", 6, "GCD iterative"),
        ("gcd(1071, 462)", 21, "GCD larger"),
        ("mersenne(5)", 31, "2^5 - 1"),
        ("mersenne(7)", 127, "2^7 - 1"),
        ("lucas_lehmer(2)", 1, "LL(2)=True"),
        ("lucas_lehmer(3)", 1, "LL(3)=True"),
        ("lucas_lehmer(5)", 1, "LL(5)=True"),
        ("lucas_lehmer(7)", 1, "LL(7)=True"),
        ("lucas_lehmer(11)", 0, "LL(11)=False (2^11-1 composite)"),
        ("lucas_lehmer(13)", 1, "LL(13)=True"),
        ("x = 5\nx * 3", 15, "variable assignment"),
        ("if 3 > 2: 99 else: 0", 99, "if-else true branch"),
        ("if 1 > 2: 99 else: 0", 0, "if-else false branch"),
        ("0xFF", 255, "hex literal"),
        ("0b1010", 10, "binary literal"),
        ("abs(-7)", 7, "unary abs"),
        ("not 0", 1, "not false"),
    ]

    passed = failed = 0
    for src, expected, label in tests:
        env = VarEnv()
        try:
            ast = parse(src)
            result = eval_node(ast, env)
            ok = result == expected
        except Exception as exc:
            ok = False
            result = repr(exc)
        sym = "✓" if ok else "✗"
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"  {sym}  {label:40s}  expected={expected!r}  got={result!r}")

    print(f"\n  Parser self-test: {passed}/{passed+failed} passed")

    # Emit factorial(5) in three tongues
    print("\n  factorial(5) emitted across tongues:")
    ast = parse("factorial(5)")
    for tongue in ["KO", "RU", "CA"]:
        code = emit_node(ast, tongue)
        print(f"    [{tongue}]  {code[:100]}")
