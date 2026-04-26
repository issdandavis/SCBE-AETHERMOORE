"""Lexicon Dimension Report — drift detector for the six-tongue coding lexicon.

Reads the three places the tongue->language pairing currently lives:

  1. docs/TONGUE_CODING_LANGUAGE_MAP.md           (canonical lexicon)
  2. training-data/sft/*_manifest.json (primaries) (training-data anchor)
  3. experiments/bijective_2tongue_build/run_full_braid.py:OPERATIONAL
     and the 'Spirit' column in its module docstring          (operational/spirit maps)

Emits a phase/weight/bridge table as JSON + MD and exits non-zero if the
canon doc, SFT manifests, or embedded canonical reference disagree without
an explicit --allow-drift override.

Operational and spirit maps are EXPECTED to differ from canon; those
differences are reported but do not fail the gate.

Usage:
    python scripts/eval/lexicon_dimension_report.py
    python scripts/eval/lexicon_dimension_report.py --allow-drift
    python scripts/eval/lexicon_dimension_report.py --output-root artifacts/lexicon_reports
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CANON_DOC = ROOT / "docs" / "TONGUE_CODING_LANGUAGE_MAP.md"
BRAID_FILE = ROOT / "experiments" / "bijective_2tongue_build" / "run_full_braid.py"
SFT_DIR = ROOT / "training-data" / "sft"

TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")

# Embedded canonical reference. If the canon doc edits drift away from this
# the gate fails — bump this constant deliberately when the canon truly moves.
CANON_REFERENCE = {
    "KO": {"language": "python", "phase_deg": 0, "phi_index": 0, "role": "intent_command"},
    "AV": {"language": "typescript", "phase_deg": 60, "phi_index": 1, "role": "wisdom_knowledge"},
    "RU": {"language": "rust", "phase_deg": 120, "phi_index": 2, "role": "governance_entropy"},
    "CA": {"language": "c", "phase_deg": 180, "phi_index": 3, "role": "compute_logic"},
    "UM": {"language": "julia", "phase_deg": 240, "phi_index": 4, "role": "security_defense"},
    "DR": {"language": "haskell", "phase_deg": 300, "phi_index": 5, "role": "structure_architecture"},
}

PHI = (1 + 5**0.5) / 2


@dataclass
class TongueRow:
    tongue: str
    canon_language: str
    operational_language: str | None = None
    operational_role: str | None = None
    spirit_language: str | None = None
    sft_languages: dict[str, str] = field(default_factory=dict)  # manifest_path -> language
    bridge_label: str | None = None
    bridge_note: str | None = None
    phase_deg: int = 0
    phi_weight: float = 1.0


@dataclass
class DriftFinding:
    severity: str  # 'fail' | 'warn' | 'info'
    source: str  # e.g. 'canon_doc', 'sft_manifest', 'braid_operational'
    tongue: str
    expected: str
    found: str
    detail: str = ""


# ---------- parsers ----------

CANON_ROW_RE = re.compile(
    r"^\|\s*\*\*(?P<tongue>[A-Z]{2})\*\*\s*" r"\|\s*(?P<conlang>[^|]+?)\s*" r"\|\s*\*\*(?P<lang>[A-Za-z+#0-9]+)\*\*"
)


def parse_canon_doc(path: Path) -> dict[str, str]:
    """Pull the Core Mapping table out of the canon doc as {tongue: language_lower}."""
    if not path.exists():
        raise FileNotFoundError(f"canon doc missing: {path}")
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = CANON_ROW_RE.match(line.strip())
        if m:
            out[m.group("tongue")] = m.group("lang").strip().lower()
    return out


OPERATIONAL_ENTRY_RE = re.compile(
    r'"(?P<tongue>ko|av|ru|ca|um|dr)"\s*:\s*\{\s*'
    r'"role"\s*:\s*"(?P<role>[^"]+)"\s*,\s*'
    r'"lang"\s*:\s*"(?P<lang>[^"]+)"',
    re.MULTILINE,
)
BRIDGE_RE = re.compile(
    r'"(?P<tongue>ko|av|ru|ca|um|dr)"\s*:\s*\{[^}]*?'
    r'"bridge_from_python"\s*:\s*"(?P<bridge>[^"]+)"[^}]*?'
    r'"bridge_note"\s*:\s*"(?P<note>[^"]*)"',
    re.DOTALL,
)
SPIRIT_TABLE_RE = re.compile(
    r"^\s*(?P<tongue>KO|AV|RU|CA|UM|DR)\s{2,}"
    r"(?P<spirit>[A-Za-z][A-Za-z ]*?)\s{2,}"
    r"(?P<role>[a-z]+)\s{2,}"
    r"(?P<oplang>[A-Za-z][A-Za-z+#]+)\s*$"
)


def parse_braid(path: Path) -> tuple[dict[str, dict], dict[str, str]]:
    """Return (operational_entries, spirit_map).

    operational_entries: {tongue_lower: {role, lang, bridge_label, bridge_note}}
    spirit_map:          {TONGUE: spirit_language_lower}
    """
    if not path.exists():
        raise FileNotFoundError(f"braid file missing: {path}")
    text = path.read_text(encoding="utf-8")

    operational: dict[str, dict] = {}
    for m in OPERATIONAL_ENTRY_RE.finditer(text):
        operational[m.group("tongue")] = {
            "role": m.group("role"),
            "lang": m.group("lang").strip().lower(),
        }
    for m in BRIDGE_RE.finditer(text):
        t = m.group("tongue")
        if t in operational:
            operational[t]["bridge_label"] = m.group("bridge").strip()
            operational[t]["bridge_note"] = m.group("note").strip()

    spirit: dict[str, str] = {}
    for line in text.splitlines():
        m = SPIRIT_TABLE_RE.match(line)
        if m:
            spirit[m.group("tongue")] = m.group("spirit").strip().lower()
    return operational, spirit


def parse_sft_manifests(sft_dir: Path) -> list[tuple[Path, dict[str, str]]]:
    """Pull tongue->language from any SFT manifest that carries a 'primaries' block."""
    found: list[tuple[Path, dict[str, str]]] = []
    if not sft_dir.exists():
        return found
    for manifest in sorted(sft_dir.glob("*_manifest.json")):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            continue
        primaries = data.get("primaries")
        if not isinstance(primaries, dict):
            continue
        mapping: dict[str, str] = {}
        for tongue, info in primaries.items():
            if isinstance(info, dict) and "language" in info:
                mapping[tongue] = str(info["language"]).strip().lower()
        if mapping:
            found.append((manifest, mapping))
    return found


# ---------- diff ----------


def diff_against_canon(
    label: str,
    candidate: dict[str, str],
    severity: str,
    findings: list[DriftFinding],
) -> None:
    for tongue in TONGUES:
        expected = CANON_REFERENCE[tongue]["language"]
        found = candidate.get(tongue) or candidate.get(tongue.lower())
        if found is None:
            findings.append(
                DriftFinding(
                    severity=severity,
                    source=label,
                    tongue=tongue,
                    expected=expected,
                    found="<missing>",
                    detail=f"{label} has no entry for {tongue}",
                )
            )
        elif found != expected:
            findings.append(
                DriftFinding(
                    severity=severity,
                    source=label,
                    tongue=tongue,
                    expected=expected,
                    found=found,
                )
            )


# ---------- report assembly ----------


def build_rows(
    operational: dict[str, dict],
    spirit: dict[str, str],
    sft_manifests: list[tuple[Path, dict[str, str]]],
) -> list[TongueRow]:
    rows: list[TongueRow] = []
    for tongue in TONGUES:
        ref = CANON_REFERENCE[tongue]
        op = operational.get(tongue.lower(), {})
        sft_pairs = {str(p): m.get(tongue) for p, m in sft_manifests if tongue in m}
        rows.append(
            TongueRow(
                tongue=tongue,
                canon_language=ref["language"],
                operational_language=op.get("lang"),
                operational_role=op.get("role"),
                spirit_language=spirit.get(tongue),
                sft_languages=sft_pairs,
                bridge_label=op.get("bridge_label"),
                bridge_note=op.get("bridge_note"),
                phase_deg=int(ref["phase_deg"]),
                phi_weight=PHI ** int(ref["phi_index"]),
            )
        )
    return rows


def render_json(rows: list[TongueRow], findings: list[DriftFinding]) -> dict:
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "canon_reference_source": str(CANON_DOC.relative_to(ROOT)),
        "operational_source": str(BRAID_FILE.relative_to(ROOT)),
        "sft_manifest_dir": str(SFT_DIR.relative_to(ROOT)),
        "rows": [
            {
                "tongue": r.tongue,
                "phase_deg": r.phase_deg,
                "phi_weight": round(r.phi_weight, 6),
                "canon_language": r.canon_language,
                "operational_language": r.operational_language,
                "operational_role": r.operational_role,
                "spirit_language": r.spirit_language,
                "bridge_label": r.bridge_label,
                "bridge_note": r.bridge_note,
                "sft_languages": r.sft_languages,
            }
            for r in rows
        ],
        "drift": [
            {
                "severity": f.severity,
                "source": f.source,
                "tongue": f.tongue,
                "expected": f.expected,
                "found": f.found,
                "detail": f.detail,
            }
            for f in findings
        ],
        "fail_count": sum(1 for f in findings if f.severity == "fail"),
        "warn_count": sum(1 for f in findings if f.severity == "warn"),
    }


def render_md(payload: dict) -> str:
    lines: list[str] = []
    lines.append("# Lexicon Dimension Report")
    lines.append("")
    lines.append(f"Generated: {payload['generated_at_utc']}")
    lines.append("")
    lines.append("## Phase / weight / bridge table")
    lines.append("")
    lines.append("| Tongue | Phase | phi-weight | Canon | Operational | Op role | Spirit | Bridge |")
    lines.append("|---|---:|---:|---|---|---|---|---|")
    for r in payload["rows"]:
        lines.append(
            f"| **{r['tongue']}** | {r['phase_deg']}° | {r['phi_weight']:.3f} | "
            f"{r['canon_language']} | {r['operational_language'] or '-'} | "
            f"{r['operational_role'] or '-'} | {r['spirit_language'] or '-'} | "
            f"{r['bridge_label'] or '-'} |"
        )
    lines.append("")
    fail = payload["fail_count"]
    warn = payload["warn_count"]
    lines.append(f"**Drift findings**: {fail} fail, {warn} warn")
    lines.append("")
    if payload["drift"]:
        lines.append("| Severity | Source | Tongue | Expected | Found | Detail |")
        lines.append("|---|---|---|---|---|---|")
        for f in payload["drift"]:
            lines.append(
                f"| {f['severity']} | {f['source']} | {f['tongue']} | "
                f"{f['expected']} | {f['found']} | {f['detail']} |"
            )
    else:
        lines.append("No drift detected.")
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------- main ----------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--allow-drift",
        action="store_true",
        help="Treat hard drift as warn instead of fail (use only with explicit human review)",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "artifacts" / "lexicon_reports",
        help="Where to write report.json and report.md",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress stdout summary table",
    )
    args = parser.parse_args()

    findings: list[DriftFinding] = []

    canon_doc_map = parse_canon_doc(CANON_DOC)
    diff_against_canon("canon_doc", canon_doc_map, "fail", findings)

    operational, spirit = parse_braid(BRAID_FILE)
    op_for_diff = {t.upper(): v["lang"] for t, v in operational.items()}
    diff_against_canon("braid_operational", op_for_diff, "info", findings)
    diff_against_canon("braid_spirit", spirit, "info", findings)

    sft_manifests = parse_sft_manifests(SFT_DIR)
    for path, mapping in sft_manifests:
        rel = path.relative_to(ROOT).as_posix()
        diff_against_canon(f"sft:{rel}", mapping, "fail", findings)

    rows = build_rows(operational, spirit, sft_manifests)
    payload = render_json(rows, findings)

    out_dir = args.output_root
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"dimension_report_{stamp}.json"
    md_path = out_dir / f"dimension_report_{stamp}.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(render_md(payload), encoding="utf-8")

    fail_count = payload["fail_count"]
    warn_count = payload["warn_count"]

    if not args.quiet:
        print("=== Lexicon Dimension Report ===")
        print(f"Canon doc:    {CANON_DOC.relative_to(ROOT)}")
        print(f"Operational:  {BRAID_FILE.relative_to(ROOT)}")
        print(f"SFT manifests checked: {len(sft_manifests)}")
        print()
        print(
            f"{'Tongue':<7}{'Phase':>7}{'phi-w':>10}  Canon            Op-lang          Op-role        Spirit           Bridge"
        )
        for r in rows:
            print(
                f"{r.tongue:<7}{str(r.phase_deg)+'d':>7}{r.phi_weight:>10.3f}  "
                f"{r.canon_language:<16} {r.operational_language or '-':<16} "
                f"{r.operational_role or '-':<14} {r.spirit_language or '-':<16} "
                f"{r.bridge_label or '-'}"
            )
        print()
        print(f"Drift: {fail_count} fail, {warn_count} warn, {sum(1 for f in findings if f.severity=='info')} info")
        for f in findings:
            print(f"  [{f.severity}] {f.source}: {f.tongue} expected={f.expected} found={f.found}")
        print()
        print(f"JSON: {json_path.relative_to(ROOT)}")
        print(f"MD:   {md_path.relative_to(ROOT)}")

    if fail_count > 0 and not args.allow_drift:
        print(f"FAIL: {fail_count} hard-drift findings (rerun with --allow-drift to override)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
