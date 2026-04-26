"""Cross-Tongue SFT Emitter.

Reads a sealed cross-tongue bundle (produced by `build_cross_tongue_project.py`)
and emits SFT pairs in the `bijective_codeflow_v1` schema:

  {"messages": [
      {"role": "system",    "content": "..."},
      {"role": "user",      "content": "..."},
      {"role": "assistant", "content": "..."}
   ],
   "meta": {"task": "translate_one"|"identify",
            "algorithm": "...",
            "src": "KO"|..., "dst": "..."}|"tongue": "..."}

For each algorithm in the bundle:
  - emits one `translate_one` pair for every ordered (src, dst) tongue pair
    with src != dst (6 tongues -> 30 ordered pairs per algorithm),
  - emits one `identify` pair per tongue (6 per algorithm).

The bundle is treated as the canonical source: bytes that round-trip in the
bundle round-trip in the SFT, so every emitted pair inherits the L1+L2+L3
proofs from the bundle without re-asserting them here.

Usage:
    python scripts/emit_cross_tongue_sft.py
    python scripts/emit_cross_tongue_sft.py --bundle artifacts/cross_tongue_projects/arithmetic_basics/bundle.json
    python scripts/emit_cross_tongue_sft.py --out training-data/sft/cross_tongue_arithmetic_basics.sft.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]

TONGUE_LABEL = {
    "ko": "Kor'aelin",
    "av": "Avali",
    "ru": "Runethic",
    "ca": "Cassisivadan",
    "um": "Umbroth",
    "dr": "Draumric",
}
TONGUE_PHI = {
    "ko": 1.00,
    "av": 1.62,
    "ru": 2.62,
    "ca": 4.24,
    "um": 6.85,
    "dr": 11.09,
}
LANG_FENCE = {
    "Python": "py",
    "JavaScript": "js",
    "Rust": "rs",
    "Mathematica": "wl",
    "Haskell": "hs",
    "Markdown": "md",
}

SYSTEM_PROMPT = (
    "You are the SCBE bijective coding agent. The Sacred Tongues map to code "
    "languages: KO=Kor'aelin/Python (phi=1.00), AV=Avali/JavaScript (phi=1.62), "
    "RU=Runethic/Rust (phi=2.62), CA=Cassisivadan/Mathematica (phi=4.24), "
    "UM=Umbroth/Haskell (phi=6.85), DR=Draumric/Markdown (phi=11.09). "
    "Each algorithm decomposes into named SLOTS that hold the same semantic "
    "role across all six tongues. An edit at slot k in any tongue must "
    "propagate to slot k in every other tongue (bijective edit propagation)."
)


def _fence(language: str) -> str:
    return LANG_FENCE.get(language, "txt")


def _slot_breakdown(slots: Dict[str, str]) -> str:
    lines = []
    for name, body in slots.items():
        n = body.count("\n") if body.endswith("\n") else body.count("\n") + 1
        lines.append(f"  {name}: {n} line(s)")
    return "\n".join(lines)


def _translate_pair(algo: Dict, src: str, dst: str) -> Dict:
    src_impl = algo["implementations"][src]
    dst_impl = algo["implementations"][dst]
    src_lang = src_impl["language"]
    dst_lang = dst_impl["language"]
    slot_order = algo["slot_order"]
    slot_csv = ", ".join(slot_order)
    description = algo.get("description", "")

    user = (
        f"Algorithm: {algo['name']}"
        + (f" ({description})" if description else "")
        + f"\nSource tongue: {src.upper()} ({src_lang})\n\n"
        f"```{_fence(src_lang)}\n{src_impl['rendered']}```\n\n"
        f"Translate to tongue {dst.upper()} ({dst_lang}), preserving slot "
        f"alignment ({slot_csv})."
    )
    assistant = (
        f"```{_fence(dst_lang)}\n{dst_impl['rendered']}```\n\n"
        f"Slot map: {slot_csv}"
    )
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {
            "task": "translate_one",
            "algorithm": algo["name"],
            "src": src.upper(),
            "dst": dst.upper(),
        },
    }


def _identify_pair(algo: Dict, tongue: str) -> Dict:
    impl = algo["implementations"][tongue]
    lang = impl["language"]
    description = algo.get("description", "")
    label = TONGUE_LABEL[tongue]
    phi = TONGUE_PHI[tongue]
    slot_csv = ", ".join(algo["slot_order"])

    user = (
        f"Identify the algorithm and its slot structure from this snippet "
        f"({tongue.upper()}, {lang}):\n\n"
        f"```{_fence(lang)}\n{impl['rendered']}```"
    )
    assistant = (
        f"algorithm: {algo['name']}\n"
        f"description: {description}\n"
        f"tongue: {tongue.upper()} ({label}, phi={phi:.2f})\n"
        f"slots: {slot_csv}\n\n"
        f"slot breakdown:\n{_slot_breakdown(impl['slots'])}"
    )
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {
            "task": "identify",
            "algorithm": algo["name"],
            "tongue": tongue.upper(),
        },
    }


def emit_pairs(bundle: Dict) -> List[Dict]:
    if not bundle.get("summary", {}).get("all_green"):
        raise ValueError("bundle is not all-green; refusing to emit SFT from a broken seal")

    tongues = bundle["tongue_order"]
    rows: List[Dict] = []
    for algo in bundle["algorithms"]:
        for src in tongues:
            for dst in tongues:
                if src == dst:
                    continue
                rows.append(_translate_pair(algo, src, dst))
        for code in tongues:
            rows.append(_identify_pair(algo, code))
    return rows


def write_jsonl(rows: Iterable[Dict], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False))
            fh.write("\n")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--bundle",
        default=str(ROOT / "artifacts" / "cross_tongue_projects" / "arithmetic_basics" / "bundle.json"),
    )
    ap.add_argument("--out", default=None, help="Output JSONL path")
    args = ap.parse_args()

    bundle_path = Path(args.bundle)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    rows = emit_pairs(bundle)

    out_path = Path(args.out) if args.out else (
        ROOT / "training-data" / "sft" / f"cross_tongue_{bundle['project']}.sft.jsonl"
    )
    write_jsonl(rows, out_path)

    n_translate = sum(1 for r in rows if r["meta"]["task"] == "translate_one")
    n_identify = sum(1 for r in rows if r["meta"]["task"] == "identify")
    print(f"== Cross-Tongue SFT Emit: {bundle['project']} ==")
    print(f"  algorithms: {len(bundle['algorithms'])}, tongues: {len(bundle['tongue_order'])}")
    print(f"  translate_one rows: {n_translate}")
    print(f"  identify rows:      {n_identify}")
    print(f"  total rows:         {len(rows)}")
    print(f"  out: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
