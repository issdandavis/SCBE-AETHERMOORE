import numpy as np

from src.kernel.tetris_embedder import _build_rotation_matrix, sacred_rotate


def test_rotation_matrix_matches_requested_dimension():
    rot_384 = _build_rotation_matrix("KO", 384)
    rot_768 = _build_rotation_matrix("KO", 768)

    assert rot_384.shape == (384, 384)
    assert rot_768.shape == (768, 768)


def test_sacred_rotate_supports_multiple_embedding_dimensions():
    vec_384 = np.linspace(-1.0, 1.0, 384, dtype=np.float64)
    vec_768 = np.linspace(-1.0, 1.0, 768, dtype=np.float64)

    out_384 = sacred_rotate(vec_384, "AV")
    out_768 = sacred_rotate(vec_768, "AV")

    assert out_384.shape == vec_384.shape
    assert out_768.shape == vec_768.shape
    assert np.isclose(np.linalg.norm(out_384), 1.0)
    assert np.isclose(np.linalg.norm(out_768), 1.0)
