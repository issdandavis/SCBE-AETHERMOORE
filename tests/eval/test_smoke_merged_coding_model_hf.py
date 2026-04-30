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


def test_compile_and_run_allows_common_type_checks() -> None:
    module = _load_module()
    code = """def depth2_keys(obj: dict) -> list[str]:
    keys = []
    for value in obj.values():
        if isinstance(value, dict):
            keys.extend(value.keys())
    return sorted(keys)
"""

    verdict = module._compile_and_run(
        code,
        "depth2_keys",
        ((({"a": {"x": 1, "y": {"z": 2}}, "b": 3, "c": {"m": 4}},), ["m", "x", "y"]),),
    )

    assert verdict == {"ok": True, "failures": []}
