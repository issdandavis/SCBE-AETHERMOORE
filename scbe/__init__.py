"""
SCBE - Geometric AI Safety
==========================

Block adversarial AI behavior with math, not rules.

Quick Start:
    from scbe import guard

    # Wrap any LLM call
    response = guard(your_llm_call, "user input here")

    # Or check directly
    from scbe import is_safe
    if is_safe("ignore previous instructions"):
        # This won't run - blocked geometrically

Install:
    pip install scbe

Learn more: https://github.com/issdandavis/SCBE-AETHERMOORE
"""

__version__ = "0.1.0"
__author__ = "SCBE Team"

from .core import (
    guard,
    is_safe,
    evaluate,
    SCBEGuard,
    Decision,
)

__all__ = [
    "guard",
    "is_safe",
    "evaluate",
    "SCBEGuard",
    "Decision",
    "__version__",
]
