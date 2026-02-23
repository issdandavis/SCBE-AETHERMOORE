import pytest

torch = pytest.importorskip("torch")

from src.m4mesh.mesh_graph import build_mesh_ops_grid2d
from src.m4mesh.wave import damped_wave


def test_wave_is_deterministic():
    torch.manual_seed(123)
    ops = build_mesh_ops_grid2d(6, 6)
    z0 = torch.randn(ops.N, 12)

    out1 = damped_wave(z0, ops.L_norm, alpha=0.15, gamma=0.25, steps=6, physics_gate=None)

    torch.manual_seed(123)
    z0b = torch.randn(ops.N, 12)
    out2 = damped_wave(z0b, ops.L_norm, alpha=0.15, gamma=0.25, steps=6, physics_gate=None)

    assert torch.allclose(out1, out2, atol=0.0, rtol=0.0)
