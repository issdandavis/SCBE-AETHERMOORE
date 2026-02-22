from pathlib import Path

from src.code_prism.matrix import load_interoperability_matrix


def test_matrix_loads_and_has_core_languages():
    matrix = load_interoperability_matrix()
    assert {"python", "typescript", "go"}.issubset(matrix.languages)
    assert matrix.can_translate("python", "typescript")
    assert matrix.can_translate("typescript", "go")


def test_matrix_file_exists():
    matrix_path = Path("config/code_prism/interoperability_matrix.json")
    assert matrix_path.exists()

