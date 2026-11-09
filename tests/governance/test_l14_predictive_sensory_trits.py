from src.symphonic_cipher.scbe_aethermoore.ai_brain.predictive_sensory_trits import (
    PredictiveSensoryTritRouter,
)
from src.symphonic_cipher.scbe_aethermoore.layer_contracts import (
    ObservationStatus,
    SpectralObservation,
)


def observation(status: ObservationStatus, score: float | None) -> SpectralObservation:
    return SpectralObservation(status, score, sample_rate_hz=16_000, cutoff_hz=4_000)


def test_missing_and_measured_silence_do_not_share_observation_semantics() -> None:
    router = PredictiveSensoryTritRouter()
    missing = router.process(observation(ObservationStatus.MISSING, None))
    silence = router.process(observation(ObservationStatus.SILENT, 0.0))
    assert missing.status is ObservationStatus.MISSING
    assert missing.observed is None
    assert silence.status is ObservationStatus.SILENT
    assert silence.observed == 0.0


def test_expected_omission_occupies_negative_mirror_trit() -> None:
    router = PredictiveSensoryTritRouter(prediction_alpha=0.1, omission_threshold=0.1)
    router.process(observation(ObservationStatus.OBSERVED, 0.8))
    omitted = router.process(observation(ObservationStatus.SILENT, 0.0))
    assert omitted.omission is True
    assert omitted.state.mirror == -1
    assert omitted.state.primary == -1
    assert omitted.route_score > 0


def test_repetition_builds_adaptation_without_becoming_unobserved() -> None:
    router = PredictiveSensoryTritRouter(adaptation_alpha=0.5)
    first = router.process(observation(ObservationStatus.OBSERVED, 0.6))
    second = router.process(observation(ObservationStatus.OBSERVED, 0.6))
    third = router.process(observation(ObservationStatus.OBSERVED, 0.6))
    assert first.adaptation == 0.0
    assert first.state.mirror == second.state.mirror == third.state.mirror == 1
    assert first.status is second.status is third.status is ObservationStatus.OBSERVED
    assert first.adaptation < second.adaptation < third.adaptation
    assert third.route_score < second.route_score


def test_signed_error_and_precision_are_separate_controls() -> None:
    router = PredictiveSensoryTritRouter(prediction_alpha=0.1, residual_threshold=0.05)
    router.process(observation(ObservationStatus.OBSERVED, 0.7))
    low = router.process(observation(ObservationStatus.OBSERVED, 0.2), precision=0.25)
    assert low.state.primary == -1
    assert low.state.mirror == 1
    assert low.precision == 0.25
