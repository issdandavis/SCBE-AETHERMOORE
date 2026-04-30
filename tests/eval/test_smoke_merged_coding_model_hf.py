from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "eval" / "smoke_merged_coding_model_hf.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("smoke_merged_coding_model_hf", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_code_accepts_py_fence() -> None:
    module = _load_module()
    text = "```py\ndef fib(n):\n    return n\n```"

    assert module._extract_code(text) == "def fib(n):\n    return n"
