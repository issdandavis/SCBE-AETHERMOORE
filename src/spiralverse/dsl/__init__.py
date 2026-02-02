"""
Spiralverse Programming DSL

A domain-specific language for expressing swarm behaviors in the
Sacred Tongues coordinate system.

Example syntax:
```spiralverse
@tongue(KO)
define pattern HarmonicFlow:
    input signal: Wave
    output transformed: Wave

    let phase = signal.phase + π/6
    let amplitude = signal.amplitude * φ

    @glyph(●→○→◎)
    yield Wave(phase, amplitude)
```

@module spiralverse/dsl
@layer Layer 1, Layer 2, Layer 13
@version 1.0.0
@since 2026-02-02
"""

from .lexer import SpiralverseLexer, Token, TokenType
from .parser import SpiralverseParser, ASTNode
from .interpreter import SpiralverseInterpreter, ExecutionContext
from .types import (
    SpiralverseType,
    WaveType,
    PositionType,
    TongueType,
    PatternType,
    FlowType,
)

__all__ = [
    # Lexer
    "SpiralverseLexer",
    "Token",
    "TokenType",
    # Parser
    "SpiralverseParser",
    "ASTNode",
    # Interpreter
    "SpiralverseInterpreter",
    "ExecutionContext",
    # Types
    "SpiralverseType",
    "WaveType",
    "PositionType",
    "TongueType",
    "PatternType",
    "FlowType",
]
