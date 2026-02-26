import pytest

torch = pytest.importorskip("torch")

from src.m4mesh.scbe_graph import CONNECTOME, CORE_LIMBIC, RISK, build_phdm_mesh_ops


def test_phdm_mesh_ops_shape_and_row_stochastic():
    ops = build_phdm_mesh_ops()
    assert ops.N == 16

    row_sums = torch.sparse.sum(ops.A_norm, dim=1).to_dense()
    ones = torch.ones_like(row_sums)
    assert torch.allclose(row_sums, ones, atol=1e-6, rtol=0.0)


def test_core_to_risk_has_no_direct_edge_without_bridge():
    ops = build_phdm_mesh_ops()
    dense = ops.A_norm.to_dense()

    for i in CORE_LIMBIC:
        for j in RISK:
            assert dense[i, j] == 0.0

    # Connectome must bridge to risk.
    for c in CONNECTOME:
        for j in RISK:
            assert dense[c, j] > 0.0

