"""Tests for hybrid_encoder.state_adapter."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.hybrid_encoder.state_adapter import StateAdapter
from src.hybrid_encoder.types import EncoderInput


def test_adapt_empty_input():
    sa = StateAdapter()
    state = sa.adapt(EncoderInput())
    assert len(state) == 21
    assert all(v == 0.0 for v in state)


def test_adapt_raw_signal():
    sa = StateAdapter()
    state = sa.adapt(EncoderInput(raw_signal=0.5))
    assert len(state) == 21
    assert state[0] != 0.0  # KO (default) gets the signal


def test_adapt_raw_signal_with_tongue_hint():
    sa = StateAdapter()
    state = sa.adapt(EncoderInput(raw_signal=0.5, tongue_hint="DR"))
    assert len(state) == 21
    assert state[5] != 0.0  # DR is index 5


def test_adapt_state_21d():
    sa = StateAdapter()
    original = [0.1 * i for i in range(21)]
    state = sa.adapt(EncoderInput(state_21d=original))
    assert len(state) == 21
    assert all(-1.0 <= v <= 1.0 for v in state)


def test_adapt_state_short_padded():
    sa = StateAdapter()
    state = sa.adapt(EncoderInput(state_21d=[0.5, 0.3]))
    assert len(state) == 21
    assert state[0] == 0.5
    assert state[1] == 0.3
    assert state[2] == 0.0


def test_adapt_state_clamped():
    sa = StateAdapter()
    state = sa.adapt(EncoderInput(state_21d=[5.0] * 21))
    assert all(v == 1.0 for v in state)


def test_adapt_code_text():
    sa = StateAdapter()
    code = "import os\ndef hello():\n    return 42"
    state = sa.adapt(EncoderInput(code_text=code))
    assert len(state) == 21
    assert all(-1.0 <= v <= 1.0 for v in state)


def test_tongue_classification():
    sa = StateAdapter()
    scores = sa._classify_tongue("import from return yield export send")
    # AV keywords should score highest
    assert scores[1] > 0  # AV is index 1


def test_tongue_index():
    assert StateAdapter._tongue_index("KO") == 0
    assert StateAdapter._tongue_index("DR") == 5
    assert StateAdapter._tongue_index(None) == 0
    assert StateAdapter._tongue_index("INVALID") == 0
