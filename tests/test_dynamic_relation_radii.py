from __future__ import annotations

from collections import deque

from src.symphonic_cipher.scbe_aethermoore.axiom_grouped import dynamic_relation_radii as dr
from src.symphonic_cipher.scbe_aethermoore.axiom_grouped import polyhedral_flow as pf


def _warm_history(axis: str, *, slope: float = -0.5):
    return {
        axis: deque(
            ((float(i), 1.0 + slope * float(i)) for i in range(pf._RHO_LOG_MIN_SAMPLES)),
            maxlen=pf._RHO_LOG_WINDOW,
        )
    }


def test_dynamic_radii_falls_back_until_axis_is_warm() -> None:
    distances = {"KO": 0.25}

    out = dr.composite_harmonic_wall_dynamic(distances, history={"KO": deque(maxlen=pf._RHO_LOG_WINDOW)})

    assert out["mode"] == "static_fallback"
    assert out["radii"] is None
    assert "h_composite" in out


def test_compute_dynamic_radii_uses_warm_rho_signal() -> None:
    radii = dr.compute_dynamic_radii({"KO": 0.25}, history=_warm_history("KO"), epsilon=0.1)

    assert radii is not None
    assert set(radii) == {"KO"}
    assert 0.0 <= radii["KO"] < pf.TONGUE_WEIGHTS["KO"]


def test_dynamic_wall_reports_weighted_mean_and_radii() -> None:
    distances = {"KO": 0.25}

    out = dr.composite_harmonic_wall_dynamic(distances, history=_warm_history("KO"), epsilon=0.1)

    assert out["mode"] == "dynamic"
    assert out["radii"] is not None
    assert out["weighted_mean_d"] == distances["KO"]
    assert 0.0 < out["h_composite"] <= 1.0
