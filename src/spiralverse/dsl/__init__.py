"""
Spiralverse Programming DSL & Aethercode Esoteric Language

Two complementary DSLs for the Spiralverse:

1. Spiralverse DSL - Structured, Python-like syntax with @tongue decorators
2. Aethercode - Esoteric polyglot language with 6 Sacred Langues weaving

Example Spiralverse syntax:
```spiralverse
@tongue(KO)
define pattern HarmonicFlow:
    input signal: Wave
    output transformed: Wave
    let phase = signal.phase + π/6
    yield Wave(phase, signal.amplitude * φ)
```

Example Aethercode syntax:
```aethercode
f7b3e5a9: tharn Greeting {
  anvil message = veil("Hello from the 6 Langues!")
}
a3f7c2e1: 'vel thara'een drath-khar(true) {
  e4f1c8d7: lumenna("Hello from the 6 Langues!")
  keth'return "Harmony achieved"
}
```

@module spiralverse/dsl
@layer Layer 1, Layer 2, Layer 13
@version 1.1.0
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

# Aethercode - The Esoteric Language
from .aethercode import (
    Langue,
    LANGUE_CONFIG,
    ChantComposition,
    LatticePosition,
    RWP2Envelope,
    AethercodeInterpreter,
    run_aethercode,
    aethercode_hello_world,
    aethercode_fibonacci,
)

__all__ = [
    # Spiralverse DSL - Lexer
    "SpiralverseLexer",
    "Token",
    "TokenType",
    # Spiralverse DSL - Parser
    "SpiralverseParser",
    "ASTNode",
    # Spiralverse DSL - Interpreter
    "SpiralverseInterpreter",
    "ExecutionContext",
    # Spiralverse DSL - Types
    "SpiralverseType",
    "WaveType",
    "PositionType",
    "TongueType",
    "PatternType",
    "FlowType",
    # Aethercode - Esoteric Language
    "Langue",
    "LANGUE_CONFIG",
    "ChantComposition",
    "LatticePosition",
    "RWP2Envelope",
    "AethercodeInterpreter",
    "run_aethercode",
    "aethercode_hello_world",
    "aethercode_fibonacci",
]
