"""
Generate a visual formatting report for the KDP DOCX.

This is a lightweight local substitute for a full book-design tool. It checks
the Word document's trim, margins, dominant fonts, heading spacing, and sample
paragraph rhythm, then emits JSON plus a Markdown checklist for human review.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_DOCX = REPO / "content" / "book" / "the-six-tongues-protocol-kdp.docx"
DEFAULT_OUT_DIR = REPO / "artifacts" / "book" / "kdp"
EXPECTED = {
    "page_width_in": 5.5,
    "page_height_in": 8.5,
    "top_margin_in": 0.75,
    "bottom_margin_in": 0.75,
    "inside_margin_in": 0.75,
    "outside_margin_in": 0.5,
    "body_font": "Garamond",
}


def emu_to_inches(value: Any) -> float:
    return round(float(value.inches), 3)


def pt_value(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value.pt), 2)


def run_report(docx_path: Path) -> dict[str, Any]:
    try:
        from docx import Document
    except ImportError as exc:
        raise SystemExit("python-docx is required for visual format reports") from exc

    if not docx_path.exists():
        raise SystemExit(f"DOCX not found: {docx_path}")

    doc = Document(str(docx_path))
    section = doc.sections[0]
    page = {
        "page_width_in": emu_to_inches(section.page_width),
        "page_height_in": emu_to_inches(section.page_height),
        "top_margin_in": emu_to_inches(section.top_margin),
        "bottom_margin_in": emu_to_inches(section.bottom_margin),
        "inside_margin_in": emu_to_inches(section.left_margin),
        "outside_margin_in": emu_to_inches(section.right_margin),
    }

    font_counter: Counter[str] = Counter()
    size_counter: Counter[str] = Counter()
    heading_samples: list[dict[str, Any]] = []
    paragraph_samples: list[dict[str, Any]] = []
    non_empty = 0

    for idx, para in enumerate(doc.paragraphs):
        text = (para.text or "").strip()
        if not text:
            continue
        non_empty += 1
        pf = para.paragraph_format
        run_fonts = [r.font.name for r in para.runs if r.font.name]
        run_sizes = [pt_value(r.font.size) for r in para.runs if r.font.size is not None]
        for font in run_fonts:
            font_counter[font] += 1
        for size in run_sizes:
            size_counter[str(size)] += 1

        sample = {
            "index": idx,
            "text": text[:140],
            "style": para.style.name if para.style else "",
            "alignment": str(pf.alignment),
            "space_before_pt": pt_value(pf.space_before),
            "space_after_pt": pt_value(pf.space_after),
            "line_spacing_pt": pt_value(pf.line_spacing),
            "first_line_indent_in": emu_to_inches(pf.first_line_indent) if pf.first_line_indent else 0,
            "fonts": sorted(set(run_fonts)),
            "sizes_pt": sorted(set(s for s in run_sizes if s is not None)),
        }
        if len(text) < 90 and ("Chapter" in text or "Interlude" in text or text in {"About the Author", "Coming Soon"}):
            heading_samples.append(sample)
        elif len(paragraph_samples) < 12:
            paragraph_samples.append(sample)

    checks = []

    def check(name: str, ok: bool, evidence: dict[str, Any]) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "HOLD", "evidence": evidence})

    check("trim_size", page["page_width_in"] == EXPECTED["page_width_in"] and page["page_height_in"] == EXPECTED["page_height_in"], page)
    check(
        "margins",
        page["top_margin_in"] == EXPECTED["top_margin_in"]
        and page["bottom_margin_in"] == EXPECTED["bottom_margin_in"]
        and page["inside_margin_in"] == EXPECTED["inside_margin_in"]
        and page["outside_margin_in"] == EXPECTED["outside_margin_in"],
        page,
    )
    dominant_fonts = font_counter.most_common(5)
    check("dominant_body_font", any(font == EXPECTED["body_font"] for font, _ in dominant_fonts), {"dominant_fonts": dominant_fonts})
    check("paragraph_samples", len(paragraph_samples) >= 6, {"sample_count": len(paragraph_samples)})
    check("heading_samples", len(heading_samples) >= 10, {"sample_count": len(heading_samples)})

    decision = "PASS" if all(c["status"] == "PASS" for c in checks) else "HOLD"
    return {
        "schema_version": "scbe_kdp_visual_format_report_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "docx_path": str(docx_path),
        "page": page,
        "dominant_fonts": dominant_fonts,
        "dominant_sizes_pt": size_counter.most_common(8),
        "non_empty_paragraphs": non_empty,
        "heading_samples": heading_samples[:18],
        "paragraph_samples": paragraph_samples,
        "checks": checks,
    }


def write_markdown(report: dict[str, Any], out_path: Path) -> None:
    lines = [
        "# KDP Visual Format Report",
        "",
        f"- Decision: **{report['decision']}**",
        f"- DOCX: `{report['docx_path']}`",
        f"- Generated: `{report['generated_at']}`",
        "",
        "## Checks",
        "",
    ]
    for check in report["checks"]:
        lines.append(f"- {check['status']} `{check['name']}`")
    lines.extend(["", "## Page", "", "```json", json.dumps(report["page"], indent=2), "```", ""])
    lines.extend(["## Heading Samples", ""])
    for sample in report["heading_samples"][:12]:
        lines.append(f"- `{sample['text']}` | space before {sample['space_before_pt']}pt | fonts {sample['fonts']}")
    lines.extend(["", "## Body Samples", ""])
    for sample in report["paragraph_samples"][:8]:
        lines.append(f"- `{sample['text']}`")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a KDP DOCX visual formatting report.")
    parser.add_argument("--docx", default=str(DEFAULT_DOCX))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = run_report(Path(args.docx).resolve())
    json_path = out_dir / "visual-format-report.json"
    md_path = out_dir / "visual-format-report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, md_path)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"[kdp-visual] decision={report['decision']}")
        print(f"[kdp-visual] json={json_path}")
        print(f"[kdp-visual] markdown={md_path}")
        for check in report["checks"]:
            print(f"  {check['status']} {check['name']}")
    return 0 if report["decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
