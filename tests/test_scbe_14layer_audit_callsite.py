import numpy as np

from src.scbe_14layer_reference import scbe_14layer_pipeline


def test_pipeline_emits_state21_audit_event():
    t = np.array([0.4, 0.2, 0.1, 0.3, 0.5, 0.6, 0.0, 0.2, 0.4, 0.6, 0.8, 1.0], dtype=float)
    result = scbe_14layer_pipeline(t=t, D=6)

    assert "state21_v1" in result
    assert "audit_event" in result
    assert len(result["state21_v1"]) == 21
    assert result["audit_event"]["schema"] == "state21_v1"
    assert result["audit_event"]["decision"] in {"ALLOW", "QUARANTINE", "DENY"}
