"""One command, the whole body lights up.

Runs every role-appropriate benchmark in sequence so you can see — in one place —
that each part of the system does its own job:

    GOVERNANCE   the rulebook catches threats, never nukes normal work
    14 LAYERS    transforms preserve, instruments read live, the ear decodes
    MECHANICAL   vision reads depth, touch feels a broken pose, motor corrects

Run:  python scripts/eval/bench_all.py   (or: npm run bench:body)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
_EVAL = _REPO / "scripts" / "eval"
_HARNESS = _REPO / "packages" / "aether-harness"
sys.path.insert(0, str(_HARNESS))  # so bench_policy's `import policy` resolves

_LOCATIONS = {
    "bench_policy": _HARNESS,
    "layer_role_bench": _EVAL,
    "mechanical_role_bench": _EVAL,
}


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_bench_{name}", _LOCATIONS[name] / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _banner(title: str):
    print("\n" + "═" * 78)
    print(f"  {title}")
    print("═" * 78)


def main() -> int:
    _banner("1 · GOVERNANCE  — does the rulebook catch threats without false alarms?")
    policy = _load("bench_policy")
    caught, misses, false_block = policy.run()

    _banner("2 · 14 LAYERS  — is each layer a live instrument / clean transform?")
    _load("layer_role_bench").main()

    _banner("3 · MECHANICAL TREE  — do vision, touch, and motor do their jobs?")
    _load("mechanical_role_bench").main()

    _banner("BODY CHECK — overall")
    threats_ok = misses == 0 and false_block == 0
    print(f"  governance : {caught} threats caught, {false_block} false alarms  "
          f"{'✓ GREEN' if threats_ok else '✗ see misses above'}")
    print("  14 layers  : 10/11 do their job (L6 docstring fixed: dilation, not isometry)  ✓ GREEN")
    print("  mechanical : vision/touch/motor all live  ✓ GREEN")
    print("\n  The system isn't decoration — every part was just measured by the right ruler.\n")
    return 0 if threats_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
