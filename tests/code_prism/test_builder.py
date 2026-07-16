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
        target_languages=["ruby"],
    )
    ruby = artifacts["ruby"]
    assert not ruby.valid
    assert ruby.issues
    assert ruby.issues[0].code == "unsupported_route"


def test_python_to_all_primary_code_prism_lanes():
    builder = CodePrismBuilder()
    artifacts = builder.translate(
        source_code=PY_SOURCE,
        source_language="python",
        target_languages=["typescript", "go", "rust", "c", "julia", "haskell"],
        module_name="primary_mod",
    )

    assert all(artifact.valid for artifact in artifacts.values())
    assert "export function add" in artifacts["typescript"].code
    assert "func Add" in artifacts["go"].code
    assert "pub fn add" in artifacts["rust"].code
    assert "double add" in artifacts["c"].code
    assert "function add" in artifacts["julia"].code
    assert "add a b =" in artifacts["haskell"].code


def test_rust_c_julia_haskell_parse_into_code_prism_ir():
    builder = CodePrismBuilder()
    samples = {
        "rust": "pub fn add(a: f64, b: f64) -> f64 { let total = a + b; return total; }",
        "c": "double add(double a, double b) { double total = a + b; return total; }",
        "julia": "function add(a, b)\n    total = a + b\n    return total\nend\n",
        "haskell": "add a b = a + b\n",
    }

    for language, source in samples.items():
        artifacts = builder.translate(source_code=source, source_language=language, target_languages=["python", "typescript"])
        assert artifacts["python"].valid, language
        assert artifacts["typescript"].valid, language
        assert "def add" in artifacts["python"].code
        assert "export function add" in artifacts["typescript"].code


def test_all_supported_sources_emit_all_supported_targets():
    builder = CodePrismBuilder()
    samples = {
        "python": "def add(a, b):\n    total = a + b\n    return total\n",
        "typescript": "export function add(a: number, b: number): number {\n  const total = a + b;\n  return total;\n}\n",
        "go": "func add(a float64, b float64) float64 {\n  total := a + b\n  return total\n}\n",
        "rust": "pub fn add(a: f64, b: f64) -> f64 { let total = a + b; return total; }",
        "c": "double add(double a, double b) { double total = a + b; return total; }",
        "julia": "function add(a, b)\n    total = a + b\n    return total\nend\n",
        "haskell": "add a b = a + b\n",
    }
    targets = list(samples)

    for source_language, source in samples.items():
        artifacts = builder.translate(
            source_code=source,
            source_language=source_language,
            target_languages=targets,
            module_name=f"{source_language}_mod",
        )
        invalid = {language: artifact.issues for language, artifact in artifacts.items() if not artifact.valid}
        assert not invalid, f"{source_language} produced invalid artifacts: {invalid}"
        assert "def add(a, b)" in artifacts["python"].code
        assert "export function add(a: any, b: any):" in artifacts["typescript"].code
        assert "func Add(a " in artifacts["go"].code and " b " in artifacts["go"].code
        assert "pub fn add(a:" in artifacts["rust"].code and "b:" in artifacts["rust"].code
        assert "add(double a, double b)" in artifacts["c"].code or "add(number a, number b)" in artifacts["c"].code
        assert "function add(a, b)" in artifacts["julia"].code
        assert "add a b =" in artifacts["haskell"].code
