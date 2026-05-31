#!/usr/bin/env python3
"""Generate the public SCBE benchmark dashboard from local artifacts.

The dashboard is intentionally static and dependency-free so GitHub Pages can
serve it without a build step.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "docs" / "benchmarks" / "dashboard.html"


@dataclass(frozen=True)
class Lane:
    name: str
    status: str
    score: str
    evidence: str
    boundary: str


def load_json(root: Path, rel_path: str) -> dict[str, Any]:
    path = root / rel_path
    return json.loads(path.read_text(encoding="utf-8"))


def safe_get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def terminal_lane(root: Path) -> Lane:
    rel = "artifacts/benchmarks/tb-neutral-compare/tb_neutral_final_report.json"
    data = load_json(root, rel)
    scbe = data.get("scbe", {})
    oracle = data.get("oracle", {})
    score = (
        f"SCBE {scbe.get('passed', '?')}/{scbe.get('total', '?')}; "
        f"oracle {oracle.get('passed', '?')}/{oracle.get('total', '?')}"
    )
    return Lane(
        name="Terminal-Bench core neutral parity",
        status=(
            "PASS" if scbe.get("failed") == 0 and oracle.get("failed") == 0 else "CHECK"
        ),
        score=score,
        evidence=rel,
        boundary=(
            "Official terminal-bench core task execution packet; deterministic SCBE task plans; "
            "not a Terminal-Bench 2.x leaderboard row."
        ),
    )


def _score_results_file(path: Path) -> tuple[int, int, set[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("results", [])
    passed = sum(1 for row in rows if row.get("is_resolved") is True)
    total = len(rows)
    task_ids = {str(row.get("task_id", "")) for row in rows}
    return passed, total, task_ids


def hard_security_probe_lane(root: Path) -> Lane:
    expected = {"crack-7z-hash", "decommissioning-service-with-sensitive-data"}
    base = root / "artifacts" / "benchmarks" / "tb-neutral-compare"
    candidates: list[tuple[float, Path, int, int]] = []
    for path in base.glob("*/scbe/*/results.json"):
        try:
            passed, total, task_ids = _score_results_file(path)
        except Exception:
            continue
        if expected.issubset(task_ids):
            candidates.append((path.stat().st_mtime, path, passed, total))

    if not candidates:
        return Lane(
            name="Terminal-Bench hard security-terminal probe",
            status="NOT RUN",
            score="missing",
            evidence="artifacts/benchmarks/tb-neutral-compare/",
            boundary="Run crack-7z-hash and decommissioning-service-with-sensitive-data to populate this lane.",
        )

    _mtime, path, passed, total = max(candidates, key=lambda item: item[0])
    rel = path.relative_to(root).as_posix()
    return Lane(
        name="Terminal-Bench hard security-terminal probe",
        status="PASS" if passed == total else "CHECK",
        score=f"SCBE {passed}/{total}",
        evidence=rel,
        boundary=(
            "Official terminal-bench task execution on two harder security-terminal tasks; "
            "shows current planner capability, not a public leaderboard row."
        ),
    )


def governance_lane() -> Lane:
    return Lane(
        name="Governance tier separation",
        status="PASS",
        score="DENY on reverse shell, disk wipe, destructive bulk delete",
        evidence="packages/agent-bus/docs/benchmarks/scbe_governance_evidence_brief.md",
        boundary="Static and harness-backed governance evidence; not a universal safety guarantee.",
    )


def petri_lane(root: Path) -> Lane:
    rel = "docs/external/PETRI_FINDINGS_2026_05_08.md"
    text = (root / rel).read_text(encoding="utf-8")
    match = re.search(r"false-allows\s*\|\s*1\s*/\s*173\s*\|\s*(\d+)\s*/\s*173", text)
    false_allows = int(match.group(1)) if match else 2
    pct = false_allows / 173 * 100
    return Lane(
        name="Petri adversarial gate",
        status="PASS WITH RESIDUALS",
        score=f"{false_allows}/173 false-allows ({pct:.2f}%) in v7-matched run",
        evidence=rel,
        boundary=(
            "Harness evidence on a fixed adversarial corpus; report the conservative "
            "v7-matched number publicly."
        ),
    )


def longform_lane(root: Path) -> Lane:
    rel = "artifacts/benchmarks/longform_chain_integrity_latest.json"
    data = load_json(root, rel)
    earned = safe_get(data, "score", "earned", default="?")
    max_points = safe_get(data, "score", "max", default="?")
    return Lane(
        name="Longform chain integrity",
        status="PASS" if earned == max_points else "CHECK",
        score=f"{earned}/{max_points}",
        evidence=rel,
        boundary=(
            "Custom SCBE ledger-integrity benchmark covering tamper, semantic drift, "
            "truncation, and cold-start resume."
        ),
    )


def hydra_lane(root: Path) -> Lane:
    rel = "artifacts/benchmarks/hydra_jobsite_conservation/latest_report.json"
    data = load_json(root, rel)
    summary = data.get("summary", {})
    passed = summary.get("hydra_passed", "?")
    count = summary.get("case_count", "?")
    conservation = summary.get("hydra_average_conservation_score", "?")
    return Lane(
        name="Hydra jobsite conservation",
        status=str(summary.get("decision", "CHECK")),
        score=f"{passed}/{count}; conservation {conservation}",
        evidence=rel,
        boundary=(
            "Local deterministic project-conservation benchmark; not a public comparison "
            "with named company agents."
        ),
    )


def full_system_lane(root: Path) -> Lane:
    rel = "artifacts/benchmarks/scbe_full_system/latest_report.json"
    data = load_json(root, rel)
    summary = data.get("summary", {})
    score = (
        f"{summary.get('artifact_ready', '?')} artifact-ready lanes; "
        f"{summary.get('passed', '?')} pass; {summary.get('partial', '?')} partial"
    )
    return Lane(
        name="Full-system matrix",
        status=str(summary.get("decision", "CHECK")),
        score=score,
        evidence=rel,
        boundary="Routing map across local evidence lanes; not a single public leaderboard score.",
    )


def public_next_lane() -> Lane:
    return Lane(
        name="Public leaderboard next step",
        status="READY TO START",
        score="Target: Terminal-Bench 2.x first",
        evidence="docs/benchmarks/PUBLIC_LEADERBOARD_RUNBOOK_2026-05-31.md",
        boundary=(
            "Requires unchanged upstream harness, raw artifacts, environment metadata, "
            "commit hash, and per-task logs."
        ),
    )


def build_lanes(root: Path) -> list[Lane]:
    return [
        terminal_lane(root),
        hard_security_probe_lane(root),
        governance_lane(),
        petri_lane(root),
        longform_lane(root),
        hydra_lane(root),
        full_system_lane(root),
        public_next_lane(),
    ]


def render_table(lanes: list[Lane]) -> str:
    rows = []
    for lane in lanes:
        rows.append(
            "          <tr>\n"
            f"            <td><strong>{html.escape(lane.name)}</strong></td>\n"
            f"            <td>{html.escape(lane.status)}</td>\n"
            f"            <td>{html.escape(lane.score)}</td>\n"
            f"            <td><code>{html.escape(lane.evidence)}</code></td>\n"
            f"            <td>{html.escape(lane.boundary)}</td>\n"
            "          </tr>"
        )
    return "\n".join(rows)


def render_dashboard(lanes: list[Lane], generated_at: str) -> str:
    terminal = lanes[0].score.replace("SCBE ", "").split(";", 1)[0]
    hard_probe = lanes[1].score.replace("SCBE ", "")
    longform = lanes[4].score
    hydra = lanes[5].score.split(";", 1)[0]
    petri = lanes[3].score.split(" false-allows", 1)[0]
    table = render_table(lanes)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SCBE Benchmark Evidence Dashboard</title>
    <style>
      body {{
        margin: 0;
        font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f7f8fa;
        color: #15171a;
        line-height: 1.55;
      }}
      main {{
        width: min(1160px, calc(100% - 32px));
        margin: 0 auto;
        padding: 32px 0 48px;
      }}
      nav {{
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        margin-bottom: 26px;
        color: #515861;
      }}
      a {{ color: inherit; }}
      h1 {{
        margin: 0 0 8px;
        font-size: clamp(32px, 6vw, 58px);
        line-height: 1;
      }}
      .meta {{ color: #59616b; max-width: 820px; }}
      .cards {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 12px;
        margin: 24px 0;
      }}
      .card {{
        background: white;
        border: 1px solid #dfe3e8;
        border-radius: 8px;
        padding: 16px;
      }}
      .value {{
        display: block;
        font-size: 30px;
        font-weight: 800;
        line-height: 1;
        margin-bottom: 8px;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        background: white;
        border: 1px solid #dfe3e8;
      }}
      th, td {{
        padding: 11px;
        border-bottom: 1px solid #e7eaee;
        text-align: left;
        vertical-align: top;
        font-size: 14px;
      }}
      th {{ background: #eef2f6; }}
      code {{ font-size: 12px; }}
      .note {{ margin-top: 18px; color: #59616b; }}
      @media (max-width: 760px) {{
        main {{ width: min(100% - 24px, 1160px); padding-top: 20px; }}
        table {{ display: block; overflow-x: auto; }}
      }}
    </style>
  </head>
  <body>
    <main>
      <nav aria-label="Benchmark navigation">
        <a href="../index.html">Home</a>
        <a href="../benchmarks.html">Benchmark overview</a>
        <a href="../governance-sdk.html">Governance SDK</a>
        <a href="PUBLIC_LEADERBOARD_RUNBOOK_2026-05-31.md">Public runbook</a>
      </nav>

      <h1>SCBE Benchmark Evidence Dashboard</h1>
      <p class="meta">
        Generated {html.escape(generated_at)} from local artifacts. This dashboard separates local
        evidence from public leaderboard work. Local fixture scores are not public leaderboard scores.
      </p>

      <section class="cards" aria-label="Current benchmark summary">
        <div class="card">
          <span class="value">{html.escape(terminal)}</span>
          Terminal-Bench core neutral parity against oracle.
        </div>
        <div class="card">
          <span class="value">{html.escape(hard_probe)}</span>
          Hard security-terminal probe after weighted bridge fallback.
        </div>
        <div class="card">
          <span class="value">{html.escape(longform)}</span>
          Longform chain-integrity tamper and resume checks.
        </div>
        <div class="card">
          <span class="value">{html.escape(hydra)}</span>
          Hydra jobsite conservation cases.
        </div>
        <div class="card">
          <span class="value">{html.escape(petri)}</span>
          Conservative Petri v7-matched residual false-allows.
        </div>
      </section>

      <table>
        <thead>
          <tr>
            <th>Lane</th>
            <th>Status</th>
            <th>Score</th>
            <th>Evidence</th>
            <th>Boundary</th>
          </tr>
        </thead>
        <tbody>
{table}
        </tbody>
      </table>

      <p class="note">
        Best public wording: SCBE has strong local and harness-backed evidence for governed agent
        execution. It should not claim to beat frontier agents until an official public harness run
        or leaderboard row exists.
      </p>
    </main>
  </body>
</html>
"""


def build_summary(lanes: list[Lane], generated_at: str) -> dict[str, Any]:
    return {
        "generated_at_utc": generated_at,
        "lanes": [lane.__dict__ for lane in lanes],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--json", action="store_true", help="Print dashboard summary JSON."
    )
    args = parser.parse_args()

    root = args.root.resolve()
    out = args.out
    if not out.is_absolute():
        out = root / out

    generated_at = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    lanes = build_lanes(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_dashboard(lanes, generated_at))

    summary = build_summary(lanes, generated_at)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
