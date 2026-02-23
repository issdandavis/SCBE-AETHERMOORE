import pytest

torch = pytest.importorskip("torch")

from src.m4mesh.cvl import BlockLayout
from src.m4mesh.manifest import FluxManifest
from src.m4mesh.mesh_graph import build_mesh_ops_grid2d
from src.m4mesh.pipeline import M4Subsystem
from src.m4mesh.tie_kb import TIEKB


def test_visibility_output_isolated_from_tie_block_under_ck_gate():
    torch.manual_seed(7)

    ops = build_mesh_ops_grid2d(4, 4)
    layout = BlockLayout(D_C=8, D_K=8, D_T=8)
    manifest = FluxManifest(
        alpha_C=0.4,
        alpha_K=0.3,
        alpha_T=0.3,
        smear_enabled=False,
        smear_betas=[1.0, 0.0, 0.0],
    )
    subsystem = M4Subsystem.build(ops, layout, manifest)

    C = torch.randn(ops.N, layout.D_C)
    K = torch.randn(ops.N, layout.D_K)

    tie_a = TIEKB(kb=torch.randn(32, layout.D_T))
    tie_b = TIEKB(kb=torch.randn(32, layout.D_T) * 10.0)

    y_a = subsystem.run(C, K, tie_a)["y"]
    y_b = subsystem.run(C, K, tie_b)["y"]

    # Hidden T path should not materially affect visible C|K output.
    assert torch.allclose(y_a, y_b, atol=1e-6, rtol=0.0)
