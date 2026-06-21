"""tts_backend: local, $0 TEXT-TO-VOICE -- the output leg of the universal port (complement to whisper).

whisper_backend is voice->text (the ears); this is text->voice (the mouth). Together they close the loop:
audio in -> transcript -> gate -> route -> result -> SPEAK. All local + free: Windows SAPI via pywin32
(preferred, built in -- no install), then pyttsx3, then espeak / macOS `say`. Writes a WAV (composable +
round-trip verifiable) or speaks to the default device. Nothing faked: with no engine, speak() raises with
a hint and available() reports None.

Wire the output side as a governed tool on the port (sealed like any tool):

    from python.scbe.universal_port import UniversalPort
    from python.scbe.tts_backend import make_voice_tool
    port = UniversalPort()
    port.register_tool(tool_action("speak", "text to speech", make_voice_tool(),
                                   params={"text": "string", "out_path": "string"}))
    port.call("speak", {"text": "the number 91 is composite", "out_path": "reply.wav"})  # -> WAV
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from typing import Any, Callable, Dict, Optional


def available() -> Optional[str]:
    """Which local TTS engine is usable: 'sapi' | 'pyttsx3' | 'espeak' | 'say' | None. No synthesis."""
    try:
        import win32com.client  # noqa: F401

        return "sapi"
    except Exception:
        pass
    try:
        import pyttsx3  # noqa: F401

        return "pyttsx3"
    except Exception:
        pass
    if shutil.which("espeak-ng") or shutil.which("espeak"):
        return "espeak"
    if platform.system() == "Darwin" and shutil.which("say"):
        return "say"
    return None


def _sapi(text: str, out_path: Optional[str], rate: Optional[int], voice: Optional[str]) -> str:
    import win32com.client as w

    sp = w.Dispatch("SAPI.SpVoice")
    if rate is not None:
        sp.Rate = int(rate)  # -10 (slow) .. 10 (fast)
    if voice:
        for v in sp.GetVoices():
            if voice.lower() in v.GetDescription().lower():
                sp.Voice = v
                break
    if out_path:
        stream = w.Dispatch("SAPI.SpFileStream")
        stream.Open(out_path, 3)  # 3 = SSFMCreateForWrite
        sp.AudioOutputStream = stream
        sp.Speak(text)
        stream.Close()
        return out_path
    sp.Speak(text)
    return "spoke to device"


def _pyttsx3(text: str, out_path: Optional[str], rate: Optional[int], voice: Optional[str]) -> str:
    import pyttsx3

    eng = pyttsx3.init()
    if rate is not None:
        eng.setProperty("rate", int(eng.getProperty("rate")) + int(rate) * 10)
    if out_path:
        eng.save_to_file(text, out_path)
        eng.runAndWait()
        return out_path
    eng.say(text)
    eng.runAndWait()
    return "spoke to device"


def _cli_tts(exe: str, to_file_flag: str, text: str, out_path: Optional[str]) -> str:
    args = [exe]
    if out_path:
        args += [to_file_flag, out_path]
    args += [text]
    subprocess.run(args, check=True, capture_output=True)
    return out_path if out_path else "spoke to device"


def speak(
    text: str,
    out_path: Optional[str] = None,
    rate: Optional[int] = None,
    voice: Optional[str] = None,
    engine: Optional[str] = None,
) -> str:
    """Synthesize speech with a LOCAL engine. Writes a WAV if out_path is given, else speaks to the device.
    Raises (does not fabricate) if no engine is available."""
    eng = engine or available()
    if eng == "sapi":
        return _sapi(text, out_path, rate, voice)
    if eng == "pyttsx3":
        return _pyttsx3(text, out_path, rate, voice)
    if eng == "espeak":
        return _cli_tts(shutil.which("espeak-ng") or shutil.which("espeak"), "-w", text, out_path)
    if eng == "say":
        return _cli_tts("say", "-o", text, out_path)
    raise RuntimeError(
        "no local TTS engine -- on Windows pywin32 is built in; else `pip install pyttsx3` or install espeak"
    )


def make_voice_tool() -> Callable[[Dict[str, Any]], str]:
    """Handler for UniversalPort.register_tool: params {text, out_path?, rate?} -> speak -> path|status.
    The OUTPUT leg as a governed tool, so every spoken reply is gate-checked + sealed like any tool call."""

    def handler(params: Dict[str, Any]) -> str:
        text = str(params.get("text", "")).strip()
        if not text:
            return "tts error: no text"
        rate = params.get("rate")
        return speak(text, out_path=params.get("out_path"), rate=int(rate) if rate is not None else None)

    return handler
