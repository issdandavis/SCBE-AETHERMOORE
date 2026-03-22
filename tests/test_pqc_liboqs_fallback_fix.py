import importlib
import sys


def test_mldsa_fallback_does_not_touch_oqs_when_skipped(monkeypatch):
    monkeypatch.setenv("SCBE_FORCE_SKIP_LIBOQS", "1")
    sys.modules.pop("src.crypto.pqc_liboqs", None)

    pqc_liboqs = importlib.import_module("src.crypto.pqc_liboqs")
    signer = pqc_liboqs.MLDSA65(seed=b"a" * 32)
    signature = signer.sign(b"ci-fallback")

    assert signer.verify(b"ci-fallback", signature) is True
