#!/usr/bin/env python3
"""Build the SCBE training hub manifest and static website page.

This is the operator-facing place where local, Colab, Kaggle, Hugging Face, and
publishable website surfaces meet. It does not launch paid jobs or upload data.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "training_hub"
DOCS_PAGE = REPO_ROOT / "docs" / "training-hub.html"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _existing(path: str) -> dict[str, Any]:
    p = REPO_ROOT / path
    return {
        "path": path,
        "exists": p.exists(),
        "bytes": p.stat().st_size if p.is_file() else None,
    }


def _latest_run_review() -> dict[str, Any]:
    data = (
        _safe_read_json(
            REPO_ROOT / "artifacts" / "training_reports" / "run_review_latest.json"
        )
        or {}
    )
    records = data.get("records") if isinstance(data.get("records"), list) else []
    top = []
    for row in records[:12]:
        if not isinstance(row, dict):
            continue
        top.append(
            {
                "id": row.get("id"),
                "triage": row.get("triage"),
                "platform": row.get("platform"),
                "lane": row.get("lane"),
                "path": row.get("path"),
                "next_step": row.get("recommended_next_step"),
            }
        )
    return {
        "source": "artifacts/training_reports/run_review_latest.json",
        "available": bool(data),
        "record_count": data.get("record_count"),
        "triage_counts": data.get("triage_counts") or {},
        "top_queue": top,
    }


def _evidence_links() -> list[dict[str, Any]]:
    return [
        _existing("artifacts/training_reports/run_review_latest.md"),
        _existing("artifacts/training_run_ledger/latest/ledger.md"),
        _existing("artifacts/training_evaluation_matrix/latest.md"),
        _existing("artifacts/adapter_registry/registry.md"),
        _existing("artifacts/adapter_registry/drift/latest/drift_report.md"),
        _existing("artifacts/ai_training_consolidation/latest/manifest.json"),
        _existing("artifacts/experiments/information_leakage_buffer/latest.json"),
        _existing("artifacts/training_hub/jupiter_ring_feedback_manifest.json"),
        _existing("training-data/agentic_coding/jupiter_ring_feedback.jsonl"),
    ]


def build_hub(*, run_preflight: bool) -> dict[str, Any]:
    surfaces_mod = _load_module(
        REPO_ROOT / "scripts" / "system" / "training_surfaces_connect.py",
        "training_surfaces_connect",
    )
    surfaces = surfaces_mod.build_manifest(run_preflight=run_preflight)
    run_review = _latest_run_review()
    return {
        "schema_version": "scbe_training_hub_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "principle": "local repo remains source of truth; Colab, Kaggle, Hugging Face, and Vercel are execution or publication surfaces",
        "surfaces": surfaces,
        "run_review": run_review,
        "evidence": _evidence_links(),
        "daily_stack": [
            {
                "step": "refresh consolidated local buckets",
                "command": "python scripts/system/consolidate_ai_training.py",
                "cost": "local",
            },
            {
                "step": "verify zero-cost profile inputs",
                "command": "npm run training:preflight:zero-cost",
                "cost": "local",
            },
            {
                "step": "open the safest remote compute lane",
                "command": "npm run training:surfaces -- --surface colab",
                "cost": "Colab or existing subscription",
            },
            {
                "step": "review current candidates before new GPU time",
                "command": "npm run training:eval-matrix && npm run training:run-ledger",
                "cost": "local",
            },
            {
                "step": "run reversible-buffer leakage tests",
                "command": "npm run experiment:info-leakage-buffer",
                "cost": "local",
            },
            {
                "step": "build Jupiter-ring feedback rows",
                "command": "npm run training:jupiter-ring",
                "cost": "local",
            },
            {
                "step": "publish this operator view",
                "command": "npm run training:hub",
                "cost": "local/Vercel static hosting",
            },
        ],
    }


def _css() -> str:
    return """
    :root { color-scheme: dark; --bg:#0b0d12; --panel:#141922; --line:#2c3542; --text:#f4f0e8; --muted:#aeb7c2; --accent:#d6a756; --ok:#69d391; --warn:#f1c45d; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:var(--bg); color:var(--text); line-height:1.55; }
    header, main { width:min(1120px, calc(100% - 32px)); margin:0 auto; }
    header { padding:42px 0 22px; border-bottom:1px solid var(--line); }
    h1 { margin:0 0 10px; font-size:clamp(32px, 6vw, 64px); line-height:.96; letter-spacing:0; }
    h2 { margin:34px 0 12px; font-size:22px; }
    p { color:var(--muted); max-width:78ch; }
    a { color:var(--accent); }
    .grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:12px; }
    .card { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; }
    .k { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }
    .v { font-size:24px; font-weight:700; margin-top:4px; }
    code { background:#0f131a; border:1px solid var(--line); border-radius:6px; padding:2px 5px; color:#f8dfaa; }
    table { width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden; }
    th, td { padding:10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:14px; }
    th { color:var(--accent); font-weight:700; }
    tr:last-child td { border-bottom:0; }
    .pill { display:inline-block; border:1px solid var(--line); border-radius:999px; padding:2px 8px; color:var(--muted); }
    footer { width:min(1120px, calc(100% - 32px)); margin:36px auto; color:var(--muted); font-size:13px; }
    """


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    return (
        f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"
    )


def render_html(hub: dict[str, Any]) -> str:
    surfaces = hub["surfaces"]
    review = hub["run_review"]
    colab = surfaces["colab"]
    hf = surfaces["huggingface"]["hub"]
    kaggle = surfaces["kaggle"]
    preflight = surfaces.get("local_preflight") or {}
    preflight_result = (
        preflight.get("result") if isinstance(preflight.get("result"), dict) else {}
    )

    top_rows = []
    for row in review.get("top_queue", []):
        top_rows.append(
            [
                f"<code>{html.escape(str(row.get('id') or ''))}</code>",
                html.escape(str(row.get("triage") or "")),
                html.escape(str(row.get("platform") or "")),
                html.escape(str(row.get("lane") or "")),
                html.escape(str(row.get("next_step") or "")),
            ]
        )

    notebook_rows = []
    for nb in colab.get("recommended_first", []):
        notebook_rows.append(
            [
                f"<a href=\"{html.escape(str(nb.get('colab_url') or '#'))}\">{html.escape(str(nb.get('name') or ''))}</a>",
                html.escape(str(nb.get("category") or "")),
                html.escape(str(nb.get("summary") or "")),
            ]
        )

    evidence_rows = []
    for ev in hub["evidence"]:
        label = html.escape(str(ev["path"]))
        link = f'<a href="../{label}">{label}</a>' if ev.get("exists") else label
        evidence_rows.append(
            [link, "yes" if ev.get("exists") else "no", str(ev.get("bytes") or "")]
        )

    daily_rows = [
        [
            html.escape(item["step"]),
            f"<code>{html.escape(item['command'])}</code>",
            html.escape(item["cost"]),
        ]
        for item in hub["daily_stack"]
    ]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SCBE Training Hub</title>
  <meta name="robots" content="noindex, nofollow">
  <style>{_css()}</style>
</head>
<body>
  <header>
    <div class="k">SCBE-AETHERMOORE Operator Surface</div>
    <h1>Training Hub</h1>
    <p>{html.escape(hub["principle"])}</p>
  </header>
  <main>
    <section class="grid" aria-label="status cards">
      <div class="card"><div class="k">Colab notebooks</div><div class="v">{colab.get("notebooks_total")}</div></div>
      <div class="card"><div class="k">Hugging Face token</div><div class="v">{"set" if hf.get("HF_TOKEN_set") else "not set"}</div></div>
      <div class="card"><div class="k">Kaggle credentials</div><div class="v">{"present" if kaggle["credentials_file"].get("present") else "missing"}</div></div>
      <div class="card"><div class="k">Zero-cost preflight</div><div class="v">{"ok" if preflight_result.get("ok") else "not run/blocked"}</div></div>
    </section>

    <h2>Daily Stack</h2>
    {_table(["Step", "Command", "Cost"], daily_rows)}

    <h2>Highest-Value Run Queue</h2>
    {_table(["Run", "Triage", "Platform", "Lane", "Next Step"], top_rows or [["", "", "", "", "Run npm run training:run-ledger first."]])}

    <h2>Remote Compute Lanes</h2>
    {_table(["Notebook", "Category", "Use"], notebook_rows)}

    <h2>Evidence Links</h2>
    {_table(["Path", "Exists", "Bytes"], evidence_rows)}
  </main>
  <footer>
    Generated {html.escape(str(hub["generated_utc"]))}. This page is an operator map, not a certification or performance claim.
  </footer>
</body>
</html>
"""


def write_outputs(hub: dict[str, Any]) -> dict[str, str]:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_PAGE.parent.mkdir(parents=True, exist_ok=True)
    json_path = ARTIFACT_DIR / "training_hub_latest.json"
    md_path = ARTIFACT_DIR / "training_hub_latest.md"
    html_path = ARTIFACT_DIR / "training_hub_latest.html"
    page = render_html(hub)
    json_path.write_text(json.dumps(hub, indent=2, ensure_ascii=True), encoding="utf-8")
    html_path.write_text(page, encoding="utf-8")
    DOCS_PAGE.write_text(page, encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# SCBE Training Hub",
                "",
                f"Generated: `{hub['generated_utc']}`",
                "",
                "## Commands",
                "",
                *[
                    f"- `{item['command']}` - {item['step']}"
                    for item in hub["daily_stack"]
                ],
                "",
                "## Outputs",
                "",
                f"- `{_rel(json_path)}`",
                f"- `{_rel(html_path)}`",
                f"- `{_rel(DOCS_PAGE)}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "json": _rel(json_path),
        "html": _rel(html_path),
        "docs_page": _rel(DOCS_PAGE),
        "markdown": _rel(md_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build SCBE training hub artifacts and docs page"
    )
    parser.add_argument("--json", action="store_true", help="Print hub JSON to stdout")
    parser.add_argument(
        "--no-preflight", action="store_true", help="Skip zero-cost preflight"
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write artifacts and docs/training-hub.html",
    )
    args = parser.parse_args()

    hub = build_hub(run_preflight=not args.no_preflight)
    outputs = write_outputs(hub) if args.write else {}
    if args.json:
        payload = dict(hub)
        if outputs:
            payload["outputs"] = outputs
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        if not outputs:
            print(
                json.dumps(
                    {"status": "preview", "generated_utc": hub["generated_utc"]},
                    indent=2,
                )
            )
        else:
            print(json.dumps({"status": "written", "outputs": outputs}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
