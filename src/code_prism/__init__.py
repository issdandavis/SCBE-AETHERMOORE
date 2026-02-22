"""
Code Prism
==========

Language-interoperability scaffold for SCBE systems.

This package translates a safe subset of source code into a language-neutral
IR and emits target-language code with validation metadata.
"""

from .builder import CodePrismBuilder, TranslationArtifact
from .matrix import InteroperabilityMatrix, load_interoperability_matrix

__all__ = [
    "CodePrismBuilder",
    "InteroperabilityMatrix",
    "TranslationArtifact",
    "load_interoperability_matrix",
]

