import importlib
import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_scbe_cli_module_can_expose_package_submodules(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO_ROOT))

    scbe_spec = importlib.util.spec_from_file_location("scbe", REPO_ROOT / "scbe.py")
    scbe_module = importlib.util.module_from_spec(scbe_spec)
    sys.modules["scbe"] = scbe_module
    assert scbe_spec.loader is not None
    scbe_spec.loader.exec_module(scbe_module)

    context_module = importlib.import_module("scbe.context_encoder")
    assert hasattr(context_module, "SCBE_CONTEXT_ENCODER")


def test_root_patent_math_module_is_importable(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO_ROOT))
    patent_math = importlib.import_module("aethermoore_patent_math")
    assert patent_math.harmonic_security_scaling(2, 1.5) == 1.5 ** 4
