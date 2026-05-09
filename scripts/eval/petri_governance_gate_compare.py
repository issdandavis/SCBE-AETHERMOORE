"""Compare two Petri governance-gate run artifacts and surface the delta.

Use cases:
  - v2 (no NONE escape hatch) vs v3 (with NONE) — measure mitigation efficacy
  - release N vs release N+1 — regression check
  - same model, two confidence floors — threshold tuning

Outputs:
  - Headline verdict deltas (ALLOW/QUARANTINE counts and ratios)
  - Per-tag false-allow change with directional labels
  - Per-seed flips (seeds that went ALLOW->QUARANTINE or QUARANTINE->ALLOW)
  - Markdown report or JSON

Usage:
    python scripts/eval/petri_governance_gate_compare.py \\
        --baseline artifacts/petri/governance_gate_v2_dummy_args.json \\
        --candidate artifacts/petri/governance_gate_v3_with_none.json \\
        --markdown-out artifacts/petri/v2_vs_v3.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def _index_by_seed(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {entry["seed_id"]: entry for entry in (report.get("per_seed") or [])}


def compare(baseline: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    base = _index_by_seed(baseline)
    cand = _index_by_seed(candidate)

    common = sorted(set(base) & set(cand))
    only_baseline = sorted(set(base) - set(cand))
    only_candidate = sorted(set(cand) - set(base))

    # Verdict transitions on the common set.
    transitions: Counter[str] = Counter()
    flipped_to_quarantine: List[Dict[str, Any]] = []
    flipped_to_allow: List[Dict[str, Any]] = []
    for seed_id in common:
        b_v = base[seed_id]["verdict"]
        c_v = cand[seed_id]["verdict"]
        transitions[f"{b_v}->{c_v}"] += 1
        if b_v == "ALLOW" and c_v == "QUARANTINE":
            flipped_to_quarantine.append({
                "seed_id": seed_id,
                "tags": base[seed_id].get("tags") or [],
                "baseline_op": base[seed_id].get("op_name"),
                "baseline_band": base[seed_id].get("op_band"),
                "baseline_conf": base[seed_id].get("confidence"),
                "candidate_error_type": cand[seed_id].get("error_type"),
                "candidate_error_message": (cand[seed_id].get("error_message") or "")[:200],
            })
        elif b_v == "QUARANTINE" and c_v == "ALLOW":
            flipped_to_allow.append({
                "seed_id": seed_id,
                "tags": cand[seed_id].get("tags") or [],
                "candidate_op": cand[seed_id].get("op_name"),
                "candidate_band": cand[seed_id].get("op_band"),
                "candidate_conf": cand[seed_id].get("confidence"),
                "baseline_error_type": base[seed_id].get("error_type"),
            })

    # Per-tag false-allow delta.
    def _per_tag_allow(report: Dict[str, Any]) -> Dict[str, Tuple[int, int]]:
        """Returns tag -> (n_allow, n_total)."""
        out: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
        for e in report.get("per_seed") or []:
            tags = e.get("tags") or ["__untagged__"]
            for t in tags:
                out[t][1] += 1
                if e.get("verdict") == "ALLOW":
                    out[t][0] += 1
        return {t: (v[0], v[1]) for t, v in out.items()}

    base_per_tag = _per_tag_allow(baseline)
    cand_per_tag = _per_tag_allow(candidate)
    all_tags = sorted(set(base_per_tag) | set(cand_per_tag))
    per_tag_delta: List[Dict[str, Any]] = []
    for t in all_tags:
        b_a, b_n = base_per_tag.get(t, (0, 0))
        c_a, c_n = cand_per_tag.get(t, (0, 0))
        b_ratio = (b_a / b_n) if b_n else 0.0
        c_ratio = (c_a / c_n) if c_n else 0.0
        per_tag_delta.append({
            "tag": t,
            "baseline_allow": b_a,
            "baseline_n": b_n,
            "baseline_ratio": round(b_ratio, 3),
            "candidate_allow": c_a,
            "candidate_n": c_n,
            "candidate_ratio": round(c_ratio, 3),
            "ratio_delta": round(c_ratio - b_ratio, 3),
        })
    # Sort: largest absolute reduction (improvement) first, then largest regression.
    per_tag_delta.sort(key=lambda r: (r["ratio_delta"], -r["baseline_n"]))

    base_summary = baseline.get("summary") or {}
    cand_summary = candidate.get("summary") or {}
    return {
        "baseline_model": baseline.get("ollama_model"),
        "candidate_model": candidate.get("ollama_model"),
        "baseline_args_mode": baseline.get("args_mode", "?"),
        "candidate_args_mode": candidate.get("args_mode", "?"),
        "headline": {
            "baseline_total": base_summary.get("total_seeds"),
            "candidate_total": cand_summary.get("total_seeds"),
            "baseline_allow": (base_summary.get("verdict_counts") or {}).get("ALLOW"),
            "candidate_allow": (cand_summary.get("verdict_counts") or {}).get("ALLOW"),
            "baseline_quarantine_ratio": base_summary.get("quarantine_ratio"),
            "candidate_quarantine_ratio": cand_summary.get("quarantine_ratio"),
        },
        "transitions": dict(transitions.most_common()),
        "common_seeds": len(common),
        "only_baseline": only_baseline,
        "only_candidate": only_candidate,
        "flipped_allow_to_quarantine": flipped_to_quarantine,
        "flipped_quarantine_to_allow": flipped_to_allow,
        "per_tag_delta": per_tag_delta,
    }


def render_markdown(d: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Petri governance-gate run — comparison")
    lines.append("")
    lines.append(f"- baseline: `{d['baseline_model']}` (args_mode={d['baseline_args_mode']})")
    lines.append(f"- candidate: `{d['candidate_model']}` (args_mode={d['candidate_args_mode']})")
    lines.append(f"- common seeds: {d['common_seeds']}")
    if d["only_baseline"]:
        lines.append(f"- baseline-only seeds: {len(d['only_baseline'])}")
    if d["only_candidate"]:
        lines.append(f"- candidate-only seeds: {len(d['only_candidate'])}")
    lines.append("")
    h = d["headline"]
    lines.append("## Headline")
    lines.append("| | baseline | candidate |")
    lines.append("|---|---:|---:|")
    lines.append(f"| total | {h['baseline_total']} | {h['candidate_total']} |")
    lines.append(f"| allow | {h['baseline_allow']} | {h['candidate_allow']} |")
    lines.append(
        f"| quar ratio | {h['baseline_quarantine_ratio']:.3f} | "
        f"{h['candidate_quarantine_ratio']:.3f} |"
    )
    lines.append("")
    lines.append("## Verdict transitions")
    lines.append("| transition | count |")
    lines.append("|---|---:|")
    for t, c in d["transitions"].items():
        lines.append(f"| `{t}` | {c} |")
    lines.append("")
    if d["flipped_allow_to_quarantine"]:
        lines.append(f"## Newly quarantined ({len(d['flipped_allow_to_quarantine'])})")
        lines.append("Seeds the baseline ALLOWed that the candidate refuses — the mitigation working.")
        lines.append("")
        lines.append("| seed | tags | was -> via | candidate refusal |")
        lines.append("|---|---|---|---|")
        for f in d["flipped_allow_to_quarantine"]:
            tags = ",".join(f.get("tags") or []) or "—"
            err = f.get("candidate_error_type") or "?"
            was = f"`{f.get('baseline_op')}` ({f.get('baseline_band')})"
            lines.append(f"| `{f['seed_id']}` | {tags} | {was} | `{err}` |")
        lines.append("")
    if d["flipped_quarantine_to_allow"]:
        lines.append(f"## Newly allowed ({len(d['flipped_quarantine_to_allow'])})")
        lines.append("Seeds the candidate ALLOWs that the baseline refused — mitigation regressions to investigate.")
        lines.append("")
        lines.append("| seed | tags | now -> | conf |")
        lines.append("|---|---|---|---:|")
        for f in d["flipped_quarantine_to_allow"]:
            tags = ",".join(f.get("tags") or []) or "—"
            now = f"`{f.get('candidate_op')}` ({f.get('candidate_band')})"
            lines.append(f"| `{f['seed_id']}` | {tags} | {now} | {f.get('candidate_conf', 0):.2f} |")
        lines.append("")
    lines.append("## Per-tag false-allow delta")
    lines.append("Sorted by ratio_delta ascending — biggest improvements first.")
    lines.append("")
    lines.append("| tag | baseline | candidate | Δ |")
    lines.append("|---|---|---|---:|")
    for r in d["per_tag_delta"]:
        b = f"{r['baseline_allow']}/{r['baseline_n']} ({r['baseline_ratio']:.2f})"
        c = f"{r['candidate_allow']}/{r['candidate_n']} ({r['candidate_ratio']:.2f})"
        delta = r["ratio_delta"]
        sign = "🠗" if delta < 0 else ("🠕" if delta > 0 else "·")
        lines.append(f"| `{r['tag']}` | {b} | {c} | {sign} {delta:+.3f} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--markdown-out", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.baseline.exists():
        print(f"baseline not found: {args.baseline}", file=sys.stderr)
        return 2
    if not args.candidate.exists():
        print(f"candidate not found: {args.candidate}", file=sys.stderr)
        return 2

    base = json.loads(args.baseline.read_text(encoding="utf-8"))
    cand = json.loads(args.candidate.read_text(encoding="utf-8"))
    diff = compare(base, cand)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(diff, indent=2, sort_keys=True), encoding="utf-8")
        print(f"wrote {args.json_out}", file=sys.stderr)

    md = render_markdown(diff)
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(md, encoding="utf-8")
        print(f"wrote {args.markdown_out}", file=sys.stderr)

    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
