import pytest

torch = pytest.importorskip("torch")

from src.m4mesh.canonical_bridge import run_governance_pipeline
from src.m4mesh.manifest import FluxManifest


def test_run_governance_pipeline_emits_21d_state():
    torch.manual_seed(42)

    manifest = FluxManifest(
        alpha_C=0.4,
        alpha_K=0.35,
        alpha_T=0.25,
        smear_enabled=True,
        smear_betas=[0.6, 0.3, 0.1],
    )

    # 16-node canonical PHDM graph input.
    c = torch.randn(16, 6) * 0.1
    k = torch.randn(16, 6) * 0.1

    out = run_governance_pipeline(c, k, manifest)
    states = out["canonical_states"]

    assert states.shape == (16, 21)
    assert isinstance(out["manifest_hash"], str) and len(out["manifest_hash"]) == 64
    assert "validation" in out
    assert out["validation"]["max_u_norm"] < 1.0

