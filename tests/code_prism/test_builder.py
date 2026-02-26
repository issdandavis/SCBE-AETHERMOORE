from src.code_prism.builder import CodePrismBuilder


PY_SOURCE = """
def add(a, b):
    return a + b
"""


def test_python_to_typescript_and_go_translation():
    builder = CodePrismBuilder()
    artifacts = builder.translate(
        source_code=PY_SOURCE,
        source_language="python",
        target_languages=["typescript", "go"],
        module_name="math_mod",
        tongue_combo="KO+CA",
    )

    ts = artifacts["typescript"]
    go = artifacts["go"]

    assert ts.valid
    assert go.valid
    assert "export function add" in ts.code
    assert "func Add" in go.code
    assert ts.metadata["tongue_combo"] == "KO+CA"


def test_unsupported_route_returns_issue():
    builder = CodePrismBuilder()
    artifacts = builder.translate(
        source_code=PY_SOURCE,
        source_language="python",
        target_languages=["rust"],
    )
    rust = artifacts["rust"]
    assert not rust.valid
    assert rust.issues
    assert rust.issues[0].code == "unsupported_route"

