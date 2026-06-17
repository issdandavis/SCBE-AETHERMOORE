"""Tests for the parallel corpus encoder (serial path — multiprocessing is env-flaky in CI)."""
import os
from python.scbe.encode_corpus import encode_file, encode_corpus, find_python_files


def test_encode_file_ok(tmp_path):
    p = tmp_path / "m.py"
    p.write_text("def f(x):\n    return x + 1\n", encoding="utf-8")
    r = encode_file(str(p))
    assert r["ok"] and r["nodes"] > 3 and len(r["sha256"]) == 64


def test_encode_file_bad_syntax(tmp_path):
    p = tmp_path / "bad.py"
    p.write_text("def (:\n", encoding="utf-8")
    r = encode_file(str(p))
    assert not r["ok"] and r["error"] == "parse"


def test_encode_corpus_serial(tmp_path):
    for i in range(5):
        (tmp_path / f"f{i}.py").write_text(f"a{i} = {i}\n", encoding="utf-8")
    paths = [str(p) for p in tmp_path.glob("*.py")]
    res = encode_corpus(paths, workers=1)
    assert len(res) == 5 and all(r["ok"] for r in res)


def test_find_python_files():
    fs = find_python_files("python/scbe")
    assert any(f.endswith("ast_cube_encoder.py") for f in fs)
