#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from prototype.polly_eggs.src.polly_eggs.nonbinary_kernel import KarySimplexKernel, default_sequence, snapshots_to_rows


def maybe_plot(rows, out_png: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return

    t = [r["t"] for r in rows]
    E = [r["E"] for r in rows]
    J = [r["J"] for r in rows]
    R = [r["R"] for r in rows]

    plt.figure(figsize=(10, 5))
    plt.plot(t, E, label="E")
    plt.plot(t, J, label="J")
    plt.plot(t, R, label="R")
    plt.title("K-ary Kernel Trajectory")
    plt.xlabel("t")
    plt.legend()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--k", type=int, default=4)
    p.add_argument("--steps", type=int, default=30)
    p.add_argument("--out", default="artifacts/system-audit/nonbinary_kernel_run.json")
    p.add_argument("--plot", default="artifacts/system-audit/nonbinary_kernel_plot.png")
    args = p.parse_args()

    kernel = KarySimplexKernel(k=args.k)
    snaps = kernel.simulate(default_sequence(args.steps))
    rows = snapshots_to_rows(snaps)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    maybe_plot(rows, Path(args.plot))

    print(json.dumps({"k": args.k, "steps": args.steps, "out": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
