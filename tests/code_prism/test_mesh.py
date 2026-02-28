from src.code_prism.matrix import load_interoperability_matrix
from src.code_prism.mesh import CodeMeshBuilder


PY_SIMPLE = """
def add(a, b):
    return a + b
"""


PY_DEFERRED = """
class Worker:
    def run(self, x):
        return x
"""


def test_matrix_native_system_resolution():
    matrix = load_interoperability_matrix()
    assert matrix.resolve_native_language("node_runtime") == "typescript"
    assert matrix.resolve_native_language("go_runtime") == "go"
    assert matrix.resolve_native_language("typescript") == "typescript"
    assert matrix.default_tongue_combo("node_runtime").count("+") >= 1


def test_mesh_builder_allow_on_clean_route():
    builder = CodeMeshBuilder()
    artifacts = builder.translate_to_native(
        source_code=PY_SIMPLE,
        source_language="python",
        target_systems=["node_runtime"],
        module_name="mesh_mod",
    )
    out = artifacts["node_runtime"]

    assert out.decision_record is not None
    assert out.decision_record.action == "ALLOW"
    assert out.valid is True
    assert out.target_language == "typescript"
    assert len(out.state_vector) == 21
    assert out.mesh_overlay_230_bits == 230
    assert len(out.mesh_overlay_230_hex) == 58


def test_mesh_builder_quarantine_on_deferred_constructs():
    builder = CodeMeshBuilder()
    artifacts = builder.translate_to_native(
        source_code=PY_DEFERRED,
        source_language="python",
        target_systems=["node_runtime"],
        module_name="mesh_mod",
    )
    out = artifacts["node_runtime"]

    assert out.decision_record is not None
    assert out.decision_record.action == "QUARANTINE"
    assert out.gate_report["G3_deferred_safe"] is False
    assert "classes" in out.metadata["deferred_construct_hits"]


def test_mesh_builder_deny_unknown_target_system():
    builder = CodeMeshBuilder()
    artifacts = builder.translate_to_native(
        source_code=PY_SIMPLE,
        source_language="python",
        target_systems=["unknown_runtime"],
        module_name="mesh_mod",
    )
    out = artifacts["unknown_runtime"]

    assert out.decision_record is not None
    assert out.decision_record.action == "DENY"
    assert out.valid is False
