"""Tests for vision_backend (the local OCR backend for the universal port's visual modality).

Unit tests run everywhere (no engine needed). The integration test runs only where a real OCR engine +
the sample image exist (importorskip winsdk) -- it proves a real image is read and routed through the port.
"""

from __future__ import annotations

import os

import pytest

from python.scbe.vision_backend import available, make_visual_backend, ocr_image

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ocr_sample.png")


# ---- unit (no OCR engine required) -------------------------------------------------------------
def test_available_reports_a_known_state():
    assert available() in (None, "winocr", "tesseract", "easyocr")


def test_unknown_engine_raises_with_hint_not_fabrication():
    with pytest.raises(RuntimeError, match="OCR"):
        ocr_image(b"not an image", engine="does-not-exist")


def test_make_visual_backend_returns_a_lazy_callable():
    assert callable(make_visual_backend())


# ---- integration: real image -> OCR -> routed through the port ---------------------------------
def test_real_image_ocrs_and_routes_through_the_port():
    pytest.importorskip("winsdk")
    if available() is None or not os.path.exists(_FIXTURE):
        pytest.skip("no OCR engine or no sample image")
    from python.scbe.universal_port import VISUAL, Envelope, UniversalPort

    text = ocr_image(_FIXTURE)
    assert "CLASSIFY" in text.upper() and "91" in text  # the image text was read, not fabricated

    port = UniversalPort()
    port.register_backend(VISUAL, make_visual_backend())
    out = port.handle(Envelope(VISUAL, _FIXTURE))
    assert out["decision"] in ("ROUTED", "OK")  # OCR text -> gated -> routed (not NEEDS_BACKEND)
    assert "classify" in out["normalized"].lower()
