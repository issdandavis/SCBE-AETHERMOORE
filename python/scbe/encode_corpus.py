"""
Parallel corpus encoder — turn a whole codebase into cube-matrices fast.

Files are independent, so encoding a corpus parallelizes near-linearly across
cores. This is the real workload: prepping AI training data from a code corpus.
Single-file speed lives in ast_cube_encoder.encode_matrix(); this layer fans it
out over a process pool.
"""

from __future__ import annotations

import os
from multiprocessing import Pool, cpu_count
from typing import Any, Dict, List, Optional

from python.scbe.ast_cube_encoder import encode_matrix


def encode_file(path: str) -> Dict[str, Any]:
    """Worker: encode one file to its cube-matrix (top-level so it's picklable)."""
    try:
        with open(path, encoding="utf-8") as f:
            src = f.read()
    except Exception as e:  # unreadable / binary
        return {"path": path, "ok": False, "error": f"read: {e}"}
    try:
        enc = encode_matrix(src)
    except SyntaxError:
        return {"path": path, "ok": False, "error": "parse"}
    except Exception as e:
        return {"path": path, "ok": False, "error": str(e)}
    return {
        "path": path,
        "ok": True,
        "nodes": enc["shape"][0],
        "width": enc["shape"][1],
        "sha256": enc["bijective"]["source_sha256"],
    }


def encode_corpus(paths: List[str], workers: Optional[int] = None) -> List[Dict[str, Any]]:
    """Encode many files in parallel. Returns one record per file."""
    workers = workers if workers is not None else max(1, cpu_count() - 1)
    if workers <= 1 or len(paths) < 4:
        return [encode_file(p) for p in paths]
    with Pool(workers) as pool:
        return pool.map(encode_file, paths, chunksize=8)


def find_python_files(root: str = ".") -> List[str]:
    junk = ("node_modules", "pytest_temp_root", "liboqs", "__pycache__", "artifacts", "external", ".git")
    out: List[str] = []
    for dp, _dn, fn in os.walk(root):
        low = dp.replace("\\", "/").lower()
        if any(j in low for j in junk):
            continue
        for f in fn:
            if f.endswith(".py"):
                out.append(os.path.join(dp, f))
    return out


def _bench() -> None:
    import time

    files = find_python_files(".")[:1500]
    print(f"corpus: {len(files)} python files, cores={cpu_count()}\n")
    # serial
    t0 = time.time()
    s = encode_corpus(files, workers=1)
    ts = time.time() - t0
    n_serial = sum(r["nodes"] for r in s if r["ok"])
    # parallel
    t0 = time.time()
    p = encode_corpus(files, workers=max(1, cpu_count() - 1))
    tp = time.time() - t0
    ok = sum(1 for r in p if r["ok"])
    print(f"  serial   : {len(files)/ts:7.0f} files/s   {n_serial/ts:10,.0f} nodes/s")
    print(f"  parallel : {len(files)/tp:7.0f} files/s   {n_serial/tp:10,.0f} nodes/s " f"  ({ts/tp:.1f}x over serial)")
    print(f"  encoded ok: {ok}/{len(files)}   total nodes: {n_serial:,}")


if __name__ == "__main__":
    _bench()
