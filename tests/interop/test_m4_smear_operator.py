import pytest

torch = pytest.importorskip("torch")

from src.m4mesh.mesh_graph import build_mesh_ops_grid2d
from src.m4mesh.smear import smear


def test_smear_identity_when_betas_only_beta0():
    ops = build_mesh_ops_grid2d(4, 4)
    u = torch.randn(ops.N, 10)

    out = smear(u, ops.A_norm, betas=[1.0, 0.0, 0.0], J=2)
    assert torch.allclose(out, u, atol=1e-7, rtol=0.0)


def test_smear_requires_beta_length_j_plus_one():
    ops = build_mesh_ops_grid2d(3, 3)
    u = torch.randn(ops.N, 4)
    with pytest.raises(ValueError):
        smear(u, ops.A_norm, betas=[1.0, 0.5], J=2)
