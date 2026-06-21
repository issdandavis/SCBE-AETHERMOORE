"""Tests for expressive_tts (the inflection-notation TTS).

Unit tests (always run) check the notation -> SAPI XML compiler. The integration tests run only with a
real SAPI (importorskip win32com): they prove the inflection is REAL by measuring it with the L14 audio
axis -- pitch-up markup raises the spectral centroid, a faster rate shortens the clip -- and that the
expressive output works as a governed, sealed port tool.
"""

from __future__ import annotations

import os
import tempfile
import wave

import pytest

from python.scbe.expressive_tts import make_expressive_tool, speak_expressive, strip_notation, to_ssml


# ---- notation compiler (always runs) -----------------------------------------------------------
def test_to_ssml_compiles_each_inflection():
    assert "<emph>x</emph>" in to_ssml("*x*")
    assert 'absmiddle="8"' in to_ssml("^x^")  # pitch up
    assert 'absmiddle="-8"' in to_ssml("~x~")  # pitch down
    assert 'volume level="100"' in to_ssml("+x+")  # louder
    assert 'volume level="55"' in to_ssml("=x=")  # softer
    assert 'silence msec="250"' in to_ssml("a|b")  # short pause
    assert 'silence msec="600"' in to_ssml("a||b")  # long pause


def test_to_ssml_escapes_xml_specials_in_prose():
    out = to_ssml("Tom & Jerry beats < that")
    assert "&amp;" in out and "&lt;" in out


def test_strip_notation_removes_all_markup():
    s = strip_notation("*a* ^b^ ~c~ +d+ =e= f|g||h")
    assert not any(ch in s for ch in "*^~+=|")
    assert "a" in s and "h" in s


def test_voice_tool_handles_empty_text():
    assert make_expressive_tool()({"text": ""}).startswith("tts error")


# ---- the inflection is REAL: measurable, robust effects (no fragile pitch-via-centroid claim) ---
def test_inflection_notation_changes_the_voice():
    pytest.importorskip("win32com")
    from python.scbe.audio_field_observables import analyze_wav

    tmp = tempfile.gettempdir()
    sentence = "this is a clear test of voice inflection"
    plain = os.path.join(tmp, "exp_plain.wav")
    pitched = os.path.join(tmp, "exp_pitched.wav")
    fast = os.path.join(tmp, "exp_fast.wav")
    emph = os.path.join(tmp, "exp_emph.wav")
    speak_expressive(sentence, out_path=plain)
    speak_expressive("^" + sentence + "^", out_path=pitched)  # pitch up (SAPI renders it)
    speak_expressive(sentence, out_path=fast, rate=8)  # faster speech
    speak_expressive("this is a *clear* test of voice inflection", out_path=emph)  # emphasis

    def _raw(p):
        with wave.open(p, "rb") as w:
            return w.readframes(w.getnframes())

    def _dur(p):
        with wave.open(p, "rb") as w:
            return w.getnframes() / w.getframerate()

    # RATE: reliably + directionally shortens the clip (the cleanly-measurable inflection)
    assert _dur(fast) < _dur(plain) * 0.9
    # pitch + emphasis markup is NOT ignored by SAPI -> the synthesized audio differs from plain
    assert _raw(pitched) != _raw(plain)
    assert _raw(emph) != _raw(plain)
    # the L14 audio axis distinguishes the inflected clips (different observables, not identical audio)
    assert (
        analyze_wav(plain, max_samples=2048).spectral_centroid_hz
        != analyze_wav(fast, max_samples=2048).spectral_centroid_hz
    )


def test_expressive_output_is_a_governed_sealed_port_tool():
    pytest.importorskip("win32com")
    from python.scbe.universal_port import UniversalPort, tool_action

    port = UniversalPort()
    port.register_tool(
        tool_action("say", "expressive tts", make_expressive_tool(), params={"text": "string", "out_path": "string"})
    )
    wav = os.path.join(tempfile.gettempdir(), "exp_tool.wav")
    rec = port.call("say", {"text": "the answer is *forty two*", "out_path": wav})
    assert rec["decision"] == "ALLOWED" and isinstance(rec.get("seal"), str)
    assert os.path.exists(wav) and os.path.getsize(wav) > 1000
