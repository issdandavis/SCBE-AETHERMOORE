"""Tests for whisper_backend (the local audio STT backend for the universal port).

The unit tests run everywhere (no whisper needed): they check availability reporting, the honest
raise-don't-fabricate behavior, and the callable factory. The integration test runs ONLY where a real
faster-whisper + the sample WAV are present (importorskip) -- it proves a real spoken clip transcribes
and routes through the governed port.
"""

from __future__ import annotations

import os

import pytest

from python.scbe.whisper_backend import available, make_audio_backend, transcribe

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "whisper_sample.wav")


# ---- unit (no whisper required) ----------------------------------------------------------------
def test_available_reports_a_known_state():
    assert available() in (None, "faster-whisper", "openai-whisper")


def test_unknown_backend_raises_with_install_hint_not_fabrication():
    with pytest.raises(RuntimeError, match="whisper"):
        transcribe(b"not audio", backend="does-not-exist")


def test_make_audio_backend_returns_a_lazy_callable():
    # building the backend must NOT load a model (cheap to wire even if audio is never sent)
    assert callable(make_audio_backend(model_size="tiny"))


# ---- integration (real local whisper + sample clip) -------------------------------------------
def test_real_clip_transcribes_and_routes_through_the_port():
    pytest.importorskip("faster_whisper")
    if not os.path.exists(_FIXTURE):
        pytest.skip("no sample wav fixture")
    from python.scbe.universal_port import AUDIO, Envelope, UniversalPort

    port = UniversalPort()
    port.register_backend(AUDIO, make_audio_backend(model_size="tiny"))
    out = port.handle(Envelope(AUDIO, _FIXTURE))
    assert out["decision"] in ("ROUTED", "OK")  # transcribed -> gated -> routed (not NEEDS_BACKEND)
    assert "classify" in out["normalized"].lower()  # the spoken words came through
