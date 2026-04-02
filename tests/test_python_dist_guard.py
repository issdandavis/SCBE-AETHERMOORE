from __future__ import annotations

import importlib.util
import io
import tarfile
import zipfile
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


guard = _load_module("test_python_dist_guard", ROOT / "scripts" / "python_dist_guard.py")


def test_evaluate_archive_accepts_clean_wheel(tmp_path) -> None:
    wheel = tmp_path / "scbe_aethermoore-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr("spiralverse/__init__.py", "__version__ = '1.0.0'\n")
        zf.writestr("spiralverse/cli.py", "def main():\n    return 0\n")
        zf.writestr("code_prism/__init__.py", "__version__ = '1.0.0'\n")
        zf.writestr("scbe_aethermoore-1.0.0.dist-info/METADATA", "Name: scbe-aethermoore\n")
        zf.writestr("scbe_aethermoore-1.0.0.dist-info/licenses/LICENSE", "MIT\n")

    result = guard.evaluate_archive(wheel)
    assert result["metadata_ok"] is True
    assert result["violations"] == []


def test_evaluate_archive_flags_repo_surface_in_sdist(tmp_path) -> None:
    sdist = tmp_path / "scbe-aethermoore-1.0.0.tar.gz"
    with tarfile.open(sdist, "w:gz") as tf:
        pkg_info = b"Metadata-Version: 2.1\nName: scbe-aethermoore\n"
        info = tarfile.TarInfo("scbe-aethermoore-1.0.0/PKG-INFO")
        info.size = len(pkg_info)
        tf.addfile(info, io.BytesIO(pkg_info))

        docs_payload = b"# leaked docs\n"
        docs_info = tarfile.TarInfo("scbe-aethermoore-1.0.0/docs/leak.md")
        docs_info.size = len(docs_payload)
        tf.addfile(docs_info, io.BytesIO(docs_payload))

    result = guard.evaluate_archive(sdist)
    assert result["metadata_ok"] is True
    assert result["violations"] == [
        {"file": "scbe-aethermoore-1.0.0/docs/leak.md", "reason": "repo-only surface shipped in public dist"}
    ]


def test_evaluate_archive_flags_unexpected_public_root_in_wheel(tmp_path) -> None:
    wheel = tmp_path / "scbe_aethermoore-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr("browser/main.py", "print('nope')\n")
        zf.writestr("scbe_aethermoore-1.0.0.dist-info/METADATA", "Name: scbe-aethermoore\n")

    result = guard.evaluate_archive(wheel)
    assert result["metadata_ok"] is True
    assert result["violations"] == [
        {"file": "browser/main.py", "reason": "unexpected file outside public wheel surface"}
    ]
