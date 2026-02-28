"""Tests for hybrid_encoder.pipeline -- the full 7-module integration."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.hybrid_encoder import TernaryHybridEncoder, EncoderInput


def test_encode_from_raw_signal():
    enc = TernaryHybridEncoder(chemistry_threat_level=3)
    result = enc.encode(EncoderInput(raw_signal=0.5))
    assert result.decision in ("ALLOW", "QUARANTINE", "DENY")
    assert len(result.tongue_trits) == 6
    assert len(result.state_21d_used) == 21
    assert len(result.audit_trail) > 0


def test_encode_from_21d_state():
    enc = TernaryHybridEncoder(chemistry_threat_level=3)
    state = [0.1] * 21
    result = enc.encode(EncoderInput(state_21d=state))
    assert result.decision in ("ALLOW", "QUARANTINE", "DENY")


def test_encode_from_code_text():
    enc = TernaryHybridEncoder(chemistry_threat_level=3)
    code = "import os\ndef hello():\n    if True:\n        return 42"
    result = enc.encode(EncoderInput(code_text=code))
    assert result.decision in ("ALLOW", "QUARANTINE", "DENY")
    assert len(result.molecular_bonds) > 0


def test_molecular_bonds_from_code():
    enc = TernaryHybridEncoder(chemistry_threat_level=3)
    code = "import json\nclass Foo:\n    pass"
    result = enc.encode(EncoderInput(code_text=code))
    tongues = {b.tongue_affinity for b in result.molecular_bonds}
    assert "AV" in tongues or "DR" in tongues


def test_hybrid_representation():
    enc = TernaryHybridEncoder(chemistry_threat_level=3)
    result = enc.encode(EncoderInput(raw_signal=0.5))
    h = result.hybrid
    assert h.ternary_int == h.binary_int  # Both encode the same integer
    assert h.tongue_polarity in ("KO", "AV", "RU")


def test_negative_space_complement():
    enc = TernaryHybridEncoder(chemistry_threat_level=3)
    result = enc.encode(EncoderInput(raw_signal=0.5))
    ns = result.negative_space
    # Complement should have opposite signs
    for orig, comp in zip(result.tongue_trits, ns.complement_trits):
        assert orig == -comp


def test_gate_state_valid():
    enc = TernaryHybridEncoder(chemistry_threat_level=3)
    result = enc.encode(EncoderInput(raw_signal=0.5))
    gs = result.gate_state
    assert hasattr(gs, "t1")
    assert hasattr(gs, "t2")
    assert hasattr(gs, "t3")
    for t in [gs.t1, gs.t2, gs.t3]:
        assert t in (-1, 0, 1)


def test_hamiltonian_replay_detection():
    enc = TernaryHybridEncoder(chemistry_threat_level=3)
    r1 = enc.encode(EncoderInput(raw_signal=0.5))
    assert r1.traversal_valid is True

    # Same input again should trigger replay detection
    r2 = enc.encode(EncoderInput(raw_signal=0.5))
    assert r2.traversal_valid is False


def test_audit_trail_complete():
    enc = TernaryHybridEncoder(chemistry_threat_level=3)
    result = enc.encode(EncoderInput(raw_signal=0.5))
    steps = [a["step"] for a in result.audit_trail]
    assert "state_adapter" in steps
    assert "dual_ternary" in steps
    assert "tongue_trits" in steps
    assert "hamiltonian" in steps
    assert "gate_swap" in steps
    assert "quasicrystal" in steps
    assert "chemistry" in steps
    assert "governance" in steps
    assert "complete" in steps


def test_encode_count():
    enc = TernaryHybridEncoder(chemistry_threat_level=3)
    assert enc.encode_count == 0
    enc.encode(EncoderInput(raw_signal=0.5))
    assert enc.encode_count == 1
    enc.encode(EncoderInput(raw_signal=0.3))
    assert enc.encode_count == 2


def test_diagnostics():
    enc = TernaryHybridEncoder(chemistry_threat_level=3)
    enc.encode(EncoderInput(raw_signal=0.5))
    diag = enc.get_diagnostics()
    assert diag["encode_count"] == 1
    assert diag["hamiltonian_unique"] >= 1
    assert "chemistry_state" in diag


def test_reset():
    enc = TernaryHybridEncoder(chemistry_threat_level=3)
    enc.encode(EncoderInput(raw_signal=0.5))
    enc.reset()
    assert enc.encode_count == 0
    diag = enc.get_diagnostics()
    assert diag["hamiltonian_unique"] == 0


def test_governance_summary_structure():
    enc = TernaryHybridEncoder(chemistry_threat_level=3)
    result = enc.encode(EncoderInput(raw_signal=0.5))
    gs = result.governance_summary
    assert "decisions" in gs
    assert "allow" in gs
    assert "deny" in gs
    assert "consensus" in gs
