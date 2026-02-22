import re

from src.code_prism.builder import CodePrismBuilder


PY_SOURCE = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""


def _arg_count(signature_args: str) -> int:
    if not signature_args.strip():
        return 0
    return len([part for part in signature_args.split(",") if part.strip()])


def test_shape_parity_python_to_typescript_and_go():
    builder = CodePrismBuilder()
    artifacts = builder.translate(
        source_code=PY_SOURCE,
        source_language="python",
        target_languages=["typescript", "go"],
        module_name="parity_mod",
        tongue_combo="KO+CA",
    )

    ts_artifact = artifacts["typescript"]
    go_artifact = artifacts["go"]

    assert ts_artifact.valid
    assert go_artifact.valid

    ts_signatures = {
        name: _arg_count(args)
        for name, args in re.findall(r"export function ([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)", ts_artifact.code)
    }
    go_signatures = {
        name.lower(): _arg_count(args)
        for name, args in re.findall(r"func ([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)", go_artifact.code)
    }

    expected = {"add": 2, "subtract": 2}
    assert ts_signatures == expected
    assert go_signatures == expected
