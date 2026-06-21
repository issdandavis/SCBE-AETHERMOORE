"""Tests for tts_backend (the local text-to-voice OUTPUT leg of the universal port).

Unit tests run everywhere (no engine needed). The round-trip integration test runs only where a real
TTS engine + faster-whisper exist (importorskip): it speaks text to a WAV through the GOVERNED port tool,
then transcribes it back and checks the words survived -- text -> voice -> text, fully local.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from python.scbe.tts_backend import available, make_voice_tool, speak


# ---- unit (no engine required) -----------------------------------------------------------------
def test_available_reports_a_known_state():
    assert available() in (None, "sapi", "pyttsx3", "espeak", "say")


def test_unknown_engine_raises_with_hint_not_fabrication():
    with pytest.raises(RuntimeError, match="TTS"):
        speak("hello", engine="does-not-exist")


def test_voice_tool_handles_empty_text_gracefully():
    handler = make_voice_tool()
    assert handler({"text": ""}).startswith("tts error")


# ---- integration: text -> voice -> text round-trip THROUGH the governed port -------------------
def test_voice_round_trip_through_the_port():
    pytest.importorskip("win32com")  # SAPI on Windows; the integration is platform-local
    pytest.importorskip("faster_whisper")
    if available() is None:
        pytest.skip("no local TTS engine")
    wb = pytest.importorskip("python.scbe.whisper_backend")  # resilient if whisper leg not present yet
    from python.scbe.universal_port import AUDIO, Envelope, UniversalPort, tool_action

    port = UniversalPort()
    port.register_tool(
        tool_action("speak", "text to speech", make_voice_tool(), params={"text": "string", "out_path": "string"})
    )
    port.register_backend(AUDIO, wb.make_audio_backend("tiny"))

    wav = os.path.join(tempfile.gettempdir(), "scbe_tts_roundtrip.wav")
    # text -> voice (the OUTPUT leg, as a governed + sealed tool call)
    rec = port.call("speak", {"text": "the number ninety one is composite", "out_path": wav})
    assert rec["decision"] == "ALLOWED" and isinstance(rec.get("seal"), str)
    assert os.path.exists(wav) and os.path.getsize(wav) > 1000

    # voice -> text (back in through the audio modality) -- the loop closed
    out = port.handle(Envelope(AUDIO, wav))
    low = out["normalized"].lower()
    assert "composite" in low or "91" in low
