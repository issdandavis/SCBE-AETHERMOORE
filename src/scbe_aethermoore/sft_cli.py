"""Dependency-light launcher for the JSONL-to-SFT conversion command.

The historical implementation lives below ``symphonic_cipher``.  Importing
that package executes its numerical facade and therefore requires NumPy even
though the converter itself uses only the Python standard library.  Loading
the leaf module from its installed path keeps the default scanner/converter
wheel dependency-free without duplicating the conversion implementation.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_converter() -> ModuleType:
    implementation = (
        Path(__file__).resolve().parent.parent / "symphonic_cipher" / "scbe_aethermoore" / "convert_to_sft.py"
    )
    if not implementation.is_file():
        raise RuntimeError("SCBE SFT converter implementation is missing from this installation")

    spec = importlib.util.spec_from_file_location("_scbe_aethermoore_convert_to_sft", implementation)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load SCBE SFT converter from {implementation}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    """Run the standard-library SFT converter without importing NumPy modules."""

    _load_converter().main()


__all__ = ["main"]
