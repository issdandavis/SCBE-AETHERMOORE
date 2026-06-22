"""whisper_backend: a local, $0 speech-to-text backend for the universal port's audio modality.

Wires a LOCAL whisper into the universal port so the audio modality stops being a stub. Preferred backend
is faster-whisper (no ffmpeg, no torch -- PyAV bundles the codecs, ctranslate2 runs the model); falls
back to openai-whisper (needs ffmpeg on PATH). The model is downloaded once from HF and cached; every
transcription after that is fully local and offline. Nothing is faked: with no whisper installed,
make_audio_backend()/transcribe() raise at call time with an install hint, and available() reports None.

    from python.scbe.universal_port import UniversalPort, Envelope, AUDIO
    from python.scbe.whisper_backend import make_audio_backend
    port = UniversalPort()
    port.register_backend(AUDIO, make_audio_backend(model_size="tiny"))
    port.handle(Envelope(AUDIO, "clip.wav"))   # -> whisper transcript -> gate -> route

Accepts a file path (str / Path), raw bytes (e.g. an uploaded clip), or a numpy float32 mono array.
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

# one loaded model per (backend, size) -- loading is the slow part, transcription is cheap
_MODEL_CACHE: Dict[Tuple[str, str], Any] = {}


def available() -> Optional[str]:
    """Which local whisper is importable: 'faster-whisper' | 'openai-whisper' | None. No model load."""
    try:
        import faster_whisper  # noqa: F401

        return "faster-whisper"
    except Exception:
        pass
    try:
        import whisper  # noqa: F401

        return "openai-whisper"
    except Exception:
        return None


def _fw_input(audio: Any) -> Any:
    """faster-whisper accepts a path, a file-like, or an ndarray. Wrap raw bytes in BytesIO (PyAV reads it)."""
    if isinstance(audio, (bytes, bytearray)):
        return io.BytesIO(bytes(audio))
    if isinstance(audio, Path):
        return str(audio)
    return audio


def _transcribe_faster(audio: Any, model_size: str, language: Optional[str]) -> str:
    from faster_whisper import WhisperModel

    key = ("faster-whisper", model_size)
    model = _MODEL_CACHE.get(key)
    if model is None:
        # int8 on CPU: small + fast, no CUDA needed (local torch here is CPU-only anyway)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        _MODEL_CACHE[key] = model
    segments, _info = model.transcribe(_fw_input(audio), language=language)
    return " ".join(seg.text for seg in segments).strip()


def _transcribe_openai(audio: Any, model_size: str, language: Optional[str]) -> str:
    import whisper  # needs ffmpeg on PATH

    key = ("openai-whisper", model_size)
    model = _MODEL_CACHE.get(key)
    if model is None:
        model = whisper.load_model(model_size)
        _MODEL_CACHE[key] = model
    tmp = None
    try:
        if isinstance(audio, (bytes, bytearray)):
            tmp = tempfile.NamedTemporaryFile("wb", suffix=".wav", delete=False)
            tmp.write(bytes(audio))
            tmp.close()
            path: Any = tmp.name
        else:
            path = str(audio) if isinstance(audio, Path) else audio
        return str(whisper.transcribe(model, path, language=language)["text"]).strip()
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass


def transcribe(
    audio: Any, model_size: str = "tiny", language: Optional[str] = None, backend: Optional[str] = None
) -> str:
    """Transcribe audio to text with a LOCAL whisper. Raises (does not fabricate) if none is installed."""
    be = backend or available()
    if be == "faster-whisper":
        return _transcribe_faster(audio, model_size, language)
    if be == "openai-whisper":
        return _transcribe_openai(audio, model_size, language)
    raise RuntimeError(
        "no local whisper installed -- `pip install faster-whisper` (preferred, no ffmpeg) "
        "or `pip install openai-whisper` + ffmpeg on PATH"
    )


def make_audio_backend(model_size: str = "tiny", language: Optional[str] = None) -> Callable[[Any], str]:
    """Return a transcriber callable for UniversalPort.register_backend(AUDIO, ...). Lazy: the model loads
    on first call, so wiring the backend is cheap even if audio is never sent."""

    def backend(audio: Any) -> str:
        return transcribe(audio, model_size=model_size, language=language)

    return backend
