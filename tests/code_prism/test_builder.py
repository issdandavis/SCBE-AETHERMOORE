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
    assert "func Add(a float64, b float64) float64" in go.code
    assert "return a + b;" in ts.code
    assert "return a + b" in go.code
    assert "TODO" not in ts.code
    assert "TODO" not in go.code
    assert ts.metadata["tongue_combo"] == "KO+CA"


def test_typescript_body_round_trips_with_real_ir_body():
    builder = CodePrismBuilder()
    artifacts = builder.translate(
        source_code="""
export function add(a: number, b: number): number {
  const total = a + b;
  return total;
}
""",
        source_language="typescript",
        target_languages=["go"],
        module_name="ts_mod",
    )

    go = artifacts["go"]
    assert go.valid
    assert "func Add(a float64, b float64) float64" in go.code
    assert "total := a + b" in go.code
    assert "return total" in go.code
    assert "TODO" not in go.code


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
