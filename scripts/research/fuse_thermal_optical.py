"""
Fusion example: Combining existing thermal-geometric channels
with the new Optical Laser (penetration/retention + dual wavelength) model.

Drop this into your scoring logic inside prime_fog_of_war_probe.py.

The idea:
- Keep your current best thermal profile (e.g. cold_spot=3, gradient_abs=5 or whatever the grid gives).
- Compute an additional "optical_laser_score" using the new module.
- Fuse them (simple weighted average or learned weights later).

This is a short-form integration demo.
"""

try:
    from scripts.research.optical_laser_prime_model import (
        apply_optical_laser,
        compute_log_transitions,
    )
except ModuleNotFoundError:  # Direct execution from scripts/research.
    from optical_laser_prime_model import (
        apply_optical_laser,
        compute_log_transitions,
    )


def fused_anchor_score(
    gaps: list[float],
    historical_gaps: list[float] | None = None,
    thermal_score: float = 0.5,
    cold_spot: float = 3.0,
    gradient_abs: float = 5.0,
    optical_weight: float = 0.35,
) -> float:
    """
    Returns a fused score in [0,1] for how likely the current window ends
    near an anchor event (|gap ratio| spike).

    Args:
        gaps: recent gap sequence (at least last 12)
        historical_gaps: earlier gaps for retention retrieval (can be subset)
        thermal_score: your existing thermal+instability+geo+cassette score
        cold_spot, gradient_abs: current thermal hyperparameters
        optical_weight: how much to trust the new optical laser channel
    """
    if len(gaps) < 3:
        return thermal_score

    # Build recent transitions
    recent_trans = compute_log_transitions(gaps)

    # Historical for retention (use earlier part of the sequence)
    hist_trans = []
    if historical_gaps and len(historical_gaps) > 10:
        hist_trans = compute_log_transitions(historical_gaps)

    # New optical laser score (includes depth, mode switch, dual wavelength, retention boost)
    optical_score = apply_optical_laser(
        window_trans=recent_trans,
        historical_trans=hist_trans,
        cold_spot=cold_spot,
        gradient_abs=gradient_abs,
    )

    # Simple fusion (you can make this more sophisticated later)
    fused = (1 - optical_weight) * thermal_score + optical_weight * optical_score
    return max(0.01, min(0.99, fused))


# Example usage inside your probe
if __name__ == "__main__":
    # Fake recent gaps (replace with real window from your probe)
    recent_gaps = [12, 18, 14, 22, 30, 28, 18, 42, 50, 36, 70, 90]
    # Earlier history for retention lookup
    hist_gaps = [8, 10, 14, 12, 20, 18, 30, 24, 16, 36, 42, 50, 28, 18, 66] * 5

    thermal = 0.62  # whatever your current model outputs for this window
    fused = fused_anchor_score(recent_gaps, hist_gaps, thermal_score=thermal)

    print(f"Thermal only : {thermal:.4f}")
    print(f"Fused (optical weight 0.35): {fused:.4f}")
