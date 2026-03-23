import pytest

torch = pytest.importorskip("torch")
if not hasattr(torch, "randn"):
    pytest.skip("torch stub installed without tensor support", allow_module_level=True)

from src.m4mesh.geometry import BlockGate
from src.m4mesh.metrics import leakage_sensitivity


def test_leakage_sensitivity_hidden_only_perturbation():
    D_C, D_K, D_T = 4, 4, 4
    total = D_C + D_K + D_T

    vis_gate = BlockGate(D_C, D_K, D_T, keep_C=True, keep_K=True, keep_T=False)
    tie_gate = BlockGate(D_C, D_K, D_T, keep_C=False, keep_K=False, keep_T=True)

    x0 = torch.randn(12, total)
    delta = torch.randn_like(x0)

    # Visibility-only readout should be insensitive to T-only perturbation.
    sens = leakage_sensitivity(lambda x: vis_gate.apply(x), x0, tie_gate, delta)
    assert sens < 1e-8
