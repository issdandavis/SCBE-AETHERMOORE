from agents.multi_model_modal_matrix import MultiModelModalMatrix


def test_reduce_allow_when_models_agree():
    m = MultiModelModalMatrix()
    for model_id in ("ko", "ru", "dr"):
        for modality_id in ("navigation", "content", "threat"):
            m.ingest(
                model_id=model_id,
                modality_id=modality_id,
                prediction="ALLOW",
                confidence=0.92,
                latency_ms=120.0,
                risk=0.08,
            )
    out = m.reduce()
    assert out.decision == "ALLOW"
    assert out.confidence > 0.6
    assert out.signals["overall_agreement"] == 1.0


def test_reduce_deny_when_models_agree_on_deny():
    m = MultiModelModalMatrix()
    for model_id in ("ko", "ru", "dr"):
        for modality_id in ("navigation", "content", "threat"):
            m.ingest(
                model_id=model_id,
                modality_id=modality_id,
                prediction="DENY",
                confidence=0.95,
                latency_ms=80.0,
                risk=0.9,
            )
    out = m.reduce()
    assert out.decision == "DENY"


def test_conflicting_votes_quarantine_or_deny():
    m = MultiModelModalMatrix()
    # Same modality disagreement across models.
    m.ingest(model_id="ko", modality_id="content", prediction="ALLOW", confidence=0.9, latency_ms=100, risk=0.15)
    m.ingest(model_id="ru", modality_id="content", prediction="QUARANTINE", confidence=0.9, latency_ms=100, risk=0.4)
    m.ingest(model_id="dr", modality_id="content", prediction="DENY", confidence=0.9, latency_ms=100, risk=0.7)
    # Add a second modality to avoid trivial structure.
    m.ingest(model_id="ko", modality_id="threat", prediction="ALLOW", confidence=0.7, latency_ms=120, risk=0.2)
    m.ingest(model_id="ru", modality_id="threat", prediction="QUARANTINE", confidence=0.8, latency_ms=120, risk=0.45)
    m.ingest(model_id="dr", modality_id="threat", prediction="DENY", confidence=0.8, latency_ms=120, risk=0.75)
    out = m.reduce()
    assert out.decision in {"QUARANTINE", "DENY"}
    assert out.signals["conflict_mass"] > 0.0


def test_reduce_empty_matrix_raises():
    m = MultiModelModalMatrix()
    try:
        _ = m.reduce()
        assert False, "expected ValueError"
    except ValueError:
        pass

