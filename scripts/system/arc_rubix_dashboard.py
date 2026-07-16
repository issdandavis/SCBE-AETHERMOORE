#!/usr/bin/env python3
"""Render a small static ARC Rubix dashboard for AI/human visual inspection."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(r"C:\Users\issda\kaggle\arc_agi2_2026")
DEFAULT_COMP = ROOT / "competition"
PALETTE = [
    "#111827", "#2563eb", "#dc2626", "#16a34a", "#facc15", "#6b7280", "#d946ef", "#f97316", "#06b6d4", "#7c3aed"
]


def grid_html(grid):
    rows = []
    for row in grid:
        cells = []
        for v in row:
            color = PALETTE[int(v) % len(PALETTE)]
            cells.append(f'<td title="{v}" style="background:{color}"></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return '<table class="grid">' + "".join(rows) + "</table>"


def main() -> None:
    ap = argparse.ArgumentParser(description="Build ARC Rubix static dashboard HTML.")
    ap.add_argument("--challenges", default=str(DEFAULT_COMP / "arc-agi_evaluation_challenges.json"))
    ap.add_argument("--submission", default=str(ROOT / "eval_submission.json"))
    ap.add_argument("--report", default=str(ROOT / "arc_rubix_report.json"))
    ap.add_argument("--out", default=str(ROOT / "arc_rubix_dashboard.html"))
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    challenges = json.loads(Path(args.challenges).read_text(encoding="utf-8"))
    submission = json.loads(Path(args.submission).read_text(encoding="utf-8")) if Path(args.submission).exists() else {}
    report = json.loads(Path(args.report).read_text(encoding="utf-8")) if Path(args.report).exists() else {"tasks": {}, "summary": {}}
    cards = []
    for idx, (task_id, task) in enumerate(challenges.items()):
        if idx >= args.limit:
            break
        task_report = report.get("tasks", {}).get(task_id, {})
        learned = ", ".join(task_report.get("learned_rules", [])[:8]) or "none"
        parts = [f'<section class="card"><h2>{html.escape(task_id)}</h2><p><b>rules:</b> {html.escape(learned)}</p>']
        parts.append('<div class="row"><div><h3>Train</h3>')
        for pair in task.get("train", [])[:3]:
            parts.append('<div class="pair"><div>' + grid_html(pair["input"]) + '</div><span>-></span><div>' + grid_html(pair["output"]) + '</div></div>')
        parts.append('</div><div><h3>Test / attempts</h3>')
        preds = submission.get(task_id, [])
        for j, test_case in enumerate(task.get("test", [])[:3]):
            parts.append('<div class="pair"><div>' + grid_html(test_case["input"]) + '</div>')
            if j < len(preds):
                parts.append('<span>a1</span><div>' + grid_html(preds[j].get("attempt_1", [])) + '</div>')
                parts.append('<span>a2</span><div>' + grid_html(preds[j].get("attempt_2", [])) + '</div>')
            parts.append('</div>')
        parts.append('</div></div></section>')
        cards.append("".join(parts))
    summary = html.escape(json.dumps(report.get("summary", {}), indent=2)[:4000])
    doc = f'''<!doctype html><html><head><meta charset="utf-8"><title>ARC Rubix Dashboard</title>
<style>
body{{font-family:Georgia,serif;background:#f5efe2;color:#1f2937;margin:24px}}h1{{font-size:34px}}.card{{background:#fffaf0;border:2px solid #111827;box-shadow:6px 6px 0 #111827;margin:18px 0;padding:16px}}.row{{display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap}}.pair{{display:flex;gap:8px;align-items:center;margin:8px 0;flex-wrap:wrap}}.grid{{border-collapse:collapse;background:#ddd}}.grid td{{width:13px;height:13px;border:1px solid rgba(255,255,255,.35);padding:0}}pre{{background:#111827;color:#f9fafb;padding:12px;overflow:auto}}
</style></head><body><h1>ARC Rubix Dashboard</h1><p>Static AI-eyes board for rule reading, attempts, and ledger review.</p><h2>Rule summary</h2><pre>{summary}</pre>{''.join(cards)}</body></html>'''
    Path(args.out).write_text(doc, encoding="utf-8")
    payload = {"ok": True, "out": args.out, "tasks_rendered": len(cards)}
    print(json.dumps(payload, indent=2) if args.json else f"Wrote {args.out}")


if __name__ == "__main__":
    main()
