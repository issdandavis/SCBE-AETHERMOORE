"""vision_backend: a local, $0 OCR backend for the universal port's visual modality.

Image -> text, the visual analog of whisper (audio->text). Preferred engine is the BUILT-IN Windows OCR
(Windows.Media.Ocr via winsdk -- no model download, no binary, like SAPI for TTS), then tesseract
(pytesseract + the tesseract binary), then easyocr (pip + torch). Pluggable exactly like whisper:

    from python.scbe.universal_port import UniversalPort, Envelope, VISUAL
    from python.scbe.vision_backend import make_visual_backend
    port = UniversalPort()
    port.register_backend(VISUAL, make_visual_backend())
    port.handle(Envelope(VISUAL, "screenshot.png"))   # -> OCR text -> gate -> route

Honest: with no OCR engine, ocr_image() raises with an install hint and available() reports None -- no
fabricated text. Accepts a file path (str/Path), raw image bytes, or a PIL Image.
"""

from __future__ import annotations

import asyncio
import io
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional, Tuple


def available() -> Optional[str]:
    """Which local OCR engine is usable: 'winocr' | 'tesseract' | 'easyocr' | None. No recognition."""
    try:
        import winsdk.windows.media.ocr  # noqa: F401

        return "winocr"
    except Exception:
        pass
    try:
        import shutil

        import pytesseract  # noqa: F401

        if shutil.which("tesseract"):
            return "tesseract"
    except Exception:
        pass
    try:
        import easyocr  # noqa: F401

        return "easyocr"
    except Exception:
        pass
    return None


def _to_png_path(image: Any) -> Tuple[str, bool]:
    """Return (path, is_temp). A path passes through; raw bytes / a PIL Image are written to a temp PNG."""
    if isinstance(image, (str, Path)):
        return os.path.abspath(str(image)), False
    from PIL import Image as _Img

    handle = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    handle.close()
    if isinstance(image, (bytes, bytearray)):
        _Img.open(io.BytesIO(bytes(image))).save(handle.name)
    else:  # assume a PIL Image
        image.save(handle.name)
    return handle.name, True


async def _winocr_async(path: str) -> str:
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.storage import FileAccessMode, StorageFile

    f = await StorageFile.get_file_from_path_async(path)
    stream = await f.open_async(FileAccessMode.READ)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise RuntimeError("no Windows OCR language pack installed")
    result = await engine.recognize_async(bitmap)
    return result.text


def _winocr(image: Any) -> str:
    path, is_temp = _to_png_path(image)
    try:
        return asyncio.run(_winocr_async(path)).strip()
    finally:
        if is_temp:
            try:
                os.unlink(path)
            except OSError:
                pass


def _tesseract(image: Any, lang: Optional[str]) -> str:
    import pytesseract
    from PIL import Image as _Img

    if isinstance(image, (str, Path)):
        im = _Img.open(str(image))
    elif isinstance(image, (bytes, bytearray)):
        im = _Img.open(io.BytesIO(bytes(image)))
    else:
        im = image
    return pytesseract.image_to_string(im, lang=lang or "eng").strip()


def _easyocr(image: Any) -> str:
    import easyocr

    path, is_temp = _to_png_path(image)
    try:
        reader = easyocr.Reader(["en"], gpu=False)
        return " ".join(reader.readtext(path, detail=0)).strip()
    finally:
        if is_temp:
            try:
                os.unlink(path)
            except OSError:
                pass


def ocr_image(image: Any, *, lang: Optional[str] = None, engine: Optional[str] = None) -> str:
    """OCR an image to text with a LOCAL engine. Raises (does not fabricate) if none is available."""
    eng = engine or available()
    if eng == "winocr":
        return _winocr(image)
    if eng == "tesseract":
        return _tesseract(image, lang)
    if eng == "easyocr":
        return _easyocr(image)
    raise RuntimeError(
        "no local OCR engine -- on Windows `pip install winsdk` (built-in OCR, no model); "
        "else install tesseract + `pip install pytesseract`, or `pip install easyocr`"
    )


def make_visual_backend(lang: Optional[str] = None) -> Callable[[Any], str]:
    """Return an OCR callable for UniversalPort.register_backend(VISUAL, ...) -- the visual analog of
    whisper's make_audio_backend. Lazy: the engine is touched only when an image actually arrives."""

    def backend(image: Any) -> str:
        return ocr_image(image, lang=lang)

    return backend
