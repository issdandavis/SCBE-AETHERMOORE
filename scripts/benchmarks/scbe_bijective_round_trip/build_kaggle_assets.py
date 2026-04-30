#!/usr/bin/env python3
"""Build the public Kaggle dataset for the SCBE Bijective Tongue Coder benchmark.

Reads the internal SFT holdout, strips system prompts (which leak format hints),
and emits a clean public bundle:

    artifacts/benchmarks/scbe_bijective_round_trip/
        holdout.jsonl              # one row: {id, prompt, reference, meta}
        sample_submission.csv      # id,prediction (empty predictions)
        baseline_echo_submission.csv  # baseline: echo the user's source code
        README.md                  # benchmark description
        score.py                   # copy of the public scorer
        DATASET_METADATA.json      # for `kaggle datasets create`
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = (
    REPO_ROOT
    / "artifacts"
    / "kaggle_datasets"
    / "scbe-coding-agent-stage6-repair-v7"
    / "bijective_codeflow_v1_holdout.sft.jsonl"
)
DEFAULT_OUT = REPO_ROOT / "artifacts" / "benchmarks" / "scbe_bijective_round_trip"

SCORER_SRC = Path(__file__).parent / "score.py"

CODEBLOCK_RE = re.compile(r"```([a-zA-Z0-9_+-]*)\n(.*?)```", re.DOTALL)


def _row_id(meta: dict[str, Any], idx: int) -> str:
    task = meta.get("task", "x")
    algo = meta.get("algorithm", "x")
    suffix = meta.get("tongue") or meta.get("src") or meta.get("dst") or "x"
    return f"row{idx:04d}__{task}__{algo}__{suffix}"


def _extract_user_codeblocks(user_content: str) -> list[str]:
    """Return all code snippets the user provided as inputs."""
    return [body for _, body in CODEBLOCK_RE.findall(user_content)]


def build_clean_rows(input_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with input_path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            messages = d.get("messages") or []
            if len(messages) < 3:
                continue
            user_msg = next((m for m in messages if m.get("role") == "user"), None)
            asst_msg = next((m for m in messages if m.get("role") == "assistant"), None)
            if not user_msg or not asst_msg:
                continue
            meta = d.get("meta", {})
            rid = _row_id(meta, idx)
            rows.append(
                {
                    "id": rid,
                    "prompt": user_msg["content"],
                    "reference": asst_msg["content"],
                    "meta": meta,
                    "_user_inputs": _extract_user_codeblocks(user_msg["content"]),
                }
            )
    return rows


def write_holdout(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            public = {k: r[k] for k in ("id", "prompt", "reference", "meta")}
            f.write(json.dumps(public, ensure_ascii=False) + "\n")


def write_sample_submission(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "prediction"])
        for r in rows:
            writer.writerow([r["id"], ""])


def write_baseline_echo(rows: list[dict[str, Any]], path: Path) -> None:
    """Baseline: echo the first user-provided code snippet inside a markdown block."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "prediction"])
        for r in rows:
            inputs = r["_user_inputs"]
            if inputs:
                pred = "```\n" + inputs[0].rstrip() + "\n```\n"
            else:
                pred = "```\n```\n"
            writer.writerow([r["id"], pred])


README_TEMPLATE = """# SCBE Bijective Tongue Coder Round-Trip

Round-trip evaluation for Sacred Tongue source-code encoders.

Submissions take input code in one of six tongues (KO, AV, RU, CA, UM, DR)
and must encode → transmit → decode while preserving structural fidelity
and recovering the reference text token-for-token.

## Tongues
- KO = Kor'aelin (Python)        phi=1.00
- AV = Avali (JavaScript)        phi=1.62
- RU = Runethic (Rust)           phi=2.62
- CA = Cassisivadan (Mathematica) phi=4.24
- UM = Umbroth (Haskell)         phi=6.85
- DR = Draumric (Markdown)       phi=11.09

## Tasks ({n_tasks})
Eight task families covering the bijective code-translation surface:
identify, multiline_edit, translate_one, translate_all, align,
governance_tag, edit_slot_all, edit_slot_one.

## Files
- `holdout.jsonl` — {n_rows} eval rows, schema:
  `{{id, prompt, reference, meta}}`
- `sample_submission.csv` — empty submission template, columns: `id,prediction`
- `baseline_echo_submission.csv` — trivial baseline (echo the input snippet)
- `score.py` — self-contained scorer (no external deps)

## Scoring
Per row:
```
row_score = token_recall * structural_preservation
row_score = 0   if hard_fail (empty / DECODE_ERROR / unparseable)
```

- `token_recall` is order-aware: |LCS(pred_tokens, ref_tokens)| / |ref_tokens|.
- `structural_preservation` averages the codeblock-count, slot-marker-count,
  and tongue-header-count ratios that appear in the reference.

Leaderboard score = unweighted mean of `row_score` across all {n_rows} rows.
Higher is better, max = 1.0.

## Reference
Built from the SCBE-AETHERMOORE bijective tongue coder v1 frozen holdout.
- Repo: https://github.com/issdandavis/SCBE-AETHERMOORE
- Generated UTC: {generated_utc}
"""


def write_readme(rows: list[dict[str, Any]], path: Path) -> None:
    path.write_text(
        README_TEMPLATE.format(
            n_rows=len(rows),
            n_tasks=len({r["meta"].get("task") for r in rows}),
            generated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
        encoding="utf-8",
    )


def write_dataset_metadata(out_dir: Path, kaggle_user: str, slug: str) -> None:
    meta = {
        "title": "SCBE Bijective Tongue Coder Round-Trip Holdout",
        "id": f"{kaggle_user}/{slug}",
        "licenses": [{"name": "CC0-1.0"}],
        "keywords": [
            "ai-safety",
            "code-translation",
            "tokenization",
            "benchmark",
            "scbe",
            "sacred-tongues",
        ],
    }
    (out_dir / "dataset-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--kaggle-user", type=str, default="issacizrealdavis")
    parser.add_argument("--dataset-slug", type=str, default="scbe-bijective-tongue-coder-holdout")
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"input not found: {args.input}", flush=True)
        return 2

    rows = build_clean_rows(args.input)
    if not rows:
        print("no rows extracted", flush=True)
        return 2

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    write_holdout(rows, out_dir / "holdout.jsonl")
    write_sample_submission(rows, out_dir / "sample_submission.csv")
    write_baseline_echo(rows, out_dir / "baseline_echo_submission.csv")
    write_readme(rows, out_dir / "README.md")
    write_dataset_metadata(out_dir, args.kaggle_user, args.dataset_slug)

    if SCORER_SRC.is_file():
        shutil.copyfile(SCORER_SRC, out_dir / "score.py")

    summary = {
        "schema": "scbe_bijective_round_trip_assets_v1",
        "n_rows": len(rows),
        "out_dir": str(out_dir.relative_to(REPO_ROOT)) if out_dir.is_relative_to(REPO_ROOT) else str(out_dir),
        "files": [p.name for p in sorted(out_dir.iterdir()) if p.is_file()],
    }
    (out_dir / "BUILD_SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
