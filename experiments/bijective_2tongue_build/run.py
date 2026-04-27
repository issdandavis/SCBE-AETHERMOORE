"""Bijective 2-tongue small build test.

Operation: Euclid's GCD, written in two languages (Python=KO, Rust=RU).
For each language:
  source.bytes -> encode(tongue) -> tokens -> decode -> bytes  (must be identical)
Then both implementations are executed on the same input pair and outputs
are compared (semantic bijection: same algorithm, two surface forms).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from crypto.sacred_tongues import SacredTongueTokenizer  # noqa: E402

HERE = Path(__file__).parent

PY_SRC = '''def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


if __name__ == "__main__":
    print(gcd(462, 1071))
'''

RUST_SRC = '''fn gcd(mut a: u64, mut b: u64) -> u64 {
    while b != 0 {
        let t = b;
        b = a % b;
        a = t;
    }
    a
}

fn main() {
    println!("{}", gcd(462, 1071));
}
'''


def round_trip(tok: SacredTongueTokenizer, tongue: str, source: str) -> tuple[bool, int, str]:
    raw = source.encode("utf-8")
    tokens = tok.encode_bytes(tongue, raw)
    back = tok.decode_tokens(tongue, tokens)
    return back == raw, len(tokens), tokens[0]


def run_python(src_path: Path) -> str:
    out = subprocess.run(
        [sys.executable, str(src_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def run_rust(src_path: Path) -> str | None:
    rustc = shutil.which("rustc")
    if not rustc:
        return None
    bin_path = src_path.with_suffix(".exe" if sys.platform == "win32" else ".bin")
    subprocess.run(
        [rustc, str(src_path), "-O", "-o", str(bin_path)],
        capture_output=True,
        check=True,
    )
    out = subprocess.run([str(bin_path)], capture_output=True, text=True, check=True)
    return out.stdout.strip()


def main() -> int:
    HERE.mkdir(parents=True, exist_ok=True)
    py_path = HERE / "gcd.py"
    rs_path = HERE / "gcd.rs"
    py_path.write_text(PY_SRC, encoding="utf-8")
    rs_path.write_text(RUST_SRC, encoding="utf-8")

    tok = SacredTongueTokenizer()

    print("== Bijective round-trip ==")
    py_ok, py_n, py_first = round_trip(tok, "ko", PY_SRC)
    rs_ok, rs_n, rs_first = round_trip(tok, "ru", RUST_SRC)
    print(f"  KO (Python): {py_n} tokens, first={py_first!r}, round_trip_ok={py_ok}")
    print(f"  RU (Rust)  : {rs_n} tokens, first={rs_first!r}, round_trip_ok={rs_ok}")
    if not (py_ok and rs_ok):
        print("FAIL: byte-level bijection broke")
        return 1

    print("\n== Cross-tongue (re-key the same bytes through a second tongue) ==")
    py_via_ru = tok.decode_tokens("ru", tok.encode_bytes("ru", PY_SRC.encode("utf-8")))
    cross_ok = py_via_ru.decode("utf-8") == PY_SRC
    print(f"  Python source re-encoded as RU and decoded: identical={cross_ok}")
    if not cross_ok:
        print("FAIL: cross-tongue round-trip broke")
        return 2

    print("\n== Semantic bijection (run both, expect equal output) ==")
    py_out = run_python(py_path)
    rs_out = run_rust(rs_path)
    print(f"  Python output: {py_out}")
    print(f"  Rust output  : {rs_out if rs_out is not None else '(rustc not on PATH; skipped)'}")

    if rs_out is None:
        print("\nSKIP: rustc not installed; bijective layer verified, exec layer unconfirmed.")
        return 0

    if py_out != rs_out:
        print("FAIL: Python and Rust gave different answers")
        return 3

    expected = "21"  # gcd(462, 1071) = 21
    if py_out != expected:
        print(f"FAIL: expected {expected}, got {py_out}")
        return 4

    print(f"\nALL GREEN: bijection holds at bytes, cross-tongue, and semantic layers (gcd=21).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
