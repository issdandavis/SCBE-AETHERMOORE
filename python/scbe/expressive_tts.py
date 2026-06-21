"""expressive_tts: a custom TTS with an INFLECTION NOTATION for voice expression.

Plain tts_backend says words flat. This adds a compact inline notation that compiles to SAPI XML so the
voice gets real inflection -- pitch, emphasis, volume, pauses. Verified objectively by the L14 audio axis
(audio_field_observables.analyze_wav): pitched markup raises the measured spectral centroid, a faster rate
shortens the duration -- so the notation provably changes the sound, it is not cosmetic.

INFLECTION NOTATION (delimiters chosen to be rare in normal prose):
    *word*   strong emphasis            -> <emph>
    ^word^   pitch UP                   -> <pitch absmiddle="+N">
    ~word~   pitch DOWN                 -> <pitch absmiddle="-N">
    +word+   LOUDER                     -> <volume level="100">
    =word=   softer                     -> <volume level="55">
    |        short pause (250ms)        -> <silence msec="250"/>
    ||       long pause (600ms)         -> <silence msec="600"/>
Spans may nest (e.g. *^urgent^*). Global speed is the `rate` arg (-10 slow .. +10 fast).

    from python.scbe.expressive_tts import speak_expressive
    speak_expressive("the number 91 is *composite* | ^are you sure?^", out_path="reply.wav")

Honest: needs Windows SAPI (pywin32) for true inflection; with no SAPI it falls back to plain speech on
the stripped text (words still spoken, inflection dropped) or raises if no TTS at all. Nothing faked.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional
from xml.sax.saxutils import escape

# how strong the inline pitch shift is, in SAPI's -10..10 scale
_PITCH_STEP = 8


def to_ssml(marked: str) -> str:
    """Compile the inflection notation to a SAPI XML fragment. XML-escapes the prose first, so a literal
    & or < in the text is safe; the notation delimiters then become real tags."""
    s = escape(marked)  # & < > in the spoken text -> entities, before we insert real tags
    s = s.replace("||", '<silence msec="600"/>').replace("|", '<silence msec="250"/>')
    s = re.sub(r"\*([^*]+)\*", r"<emph>\1</emph>", s)
    s = re.sub(r"\^([^^]+)\^", r'<pitch absmiddle="%d">\1</pitch>' % _PITCH_STEP, s)
    s = re.sub(r"~([^~]+)~", r'<pitch absmiddle="-%d">\1</pitch>' % _PITCH_STEP, s)
    s = re.sub(r"\+([^+]+)\+", r'<volume level="100">\1</volume>', s)
    s = re.sub(r"=([^=]+)=", r'<volume level="55">\1</volume>', s)
    return s


def strip_notation(marked: str) -> str:
    """The plain spoken text with the notation removed (fallback engines + transcript comparison)."""
    s = marked.replace("||", " ").replace("|", " ")
    for ch in "*^~+=":
        s = s.replace(ch, "")
    return re.sub(r"\s+", " ", s).strip()


def _sapi_available() -> bool:
    try:
        import win32com.client  # noqa: F401

        return True
    except Exception:
        return False


def _sapi_speak_xml(ssml: str, out_path: Optional[str], rate: Optional[int], voice: Optional[str]) -> str:
    import win32com.client as w

    sp = w.Dispatch("SAPI.SpVoice")
    if rate is not None:
        sp.Rate = int(rate)
    if voice:
        for v in sp.GetVoices():
            if voice.lower() in v.GetDescription().lower():
                sp.Voice = v
                break
    if out_path:
        stream = w.Dispatch("SAPI.SpFileStream")
        stream.Open(out_path, 3)  # SSFMCreateForWrite
        sp.AudioOutputStream = stream
        sp.Speak(ssml, 8)  # 8 = SVSFIsXML -> interpret the inflection tags
        stream.Close()
        return out_path
    sp.Speak(ssml, 8)
    return "spoke to device"


def speak_expressive(
    marked: str,
    out_path: Optional[str] = None,
    rate: Optional[int] = None,
    voice: Optional[str] = None,
) -> str:
    """Speak text with inflection notation. SAPI renders the tags; without SAPI, falls back to plain
    speech on the stripped text (inflection lost but words still spoken) or raises if no TTS at all."""
    if _sapi_available():
        return _sapi_speak_xml(to_ssml(marked), out_path, rate, voice)
    try:
        from .tts_backend import speak  # plain fallback (inflection dropped, speech preserved)
    except Exception as exc:
        raise RuntimeError("expressive TTS needs Windows SAPI (pywin32); no fallback TTS: %s" % exc)
    return speak(strip_notation(marked), out_path=out_path, rate=rate, voice=voice)


def make_expressive_tool() -> Callable[[Dict[str, Any]], str]:
    """Governed-tool handler for UniversalPort.register_tool: params {text, out_path?, rate?} -> speak with
    inflection. The expressive OUTPUT leg, sealed like any tool call."""

    def handler(params: Dict[str, Any]) -> str:
        marked = str(params.get("text", "")).strip()
        if not marked:
            return "tts error: no text"
        rate = params.get("rate")
        return speak_expressive(marked, out_path=params.get("out_path"), rate=int(rate) if rate is not None else None)

    return handler
