"""
Patent AI — Responses API wrapper for USPTO non-provisional workbench.

Design rules:
  - Model is never the "lawyer." It is the drafting engine, issue spotter,
    examiner simulator, and citation organizer.
  - All control: official USPTO sources, claim support matrix, prior-art log,
    readiness checklist, and DOCX validation owned by this workbench.
  - Structured Outputs enforce JSON schema so every response is parseable
    and slots directly into checklist / manifest updates.

Requires: openai>=1.68.0, OPENAI_API_KEY in environment.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from openai import OpenAI

# ---------------------------------------------------------------------------
# Model constants
# ---------------------------------------------------------------------------

DEFAULT_PRIMARY_MODEL = "gpt-5"  # conservative public default; verify before live runs
DEFAULT_DRAFT_MODEL = "gpt-5"    # swap via env to a lower-cost available model


def primary_model() -> str:
    return os.environ.get("SCBE_PATENT_PRIMARY_MODEL", DEFAULT_PRIMARY_MODEL).strip() or DEFAULT_PRIMARY_MODEL


def draft_model() -> str:
    return os.environ.get("SCBE_PATENT_DRAFT_MODEL", DEFAULT_DRAFT_MODEL).strip() or DEFAULT_DRAFT_MODEL

REASONING_HIGH: dict = {"effort": "high"}
REASONING_MEDIUM: dict = {"effort": "medium"}

# ---------------------------------------------------------------------------
# Structured output schemas
# ---------------------------------------------------------------------------

ISSUE_SCHEMA = {
    "type": "json_schema",
    "name": "patent_issue_report",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "issue_type": {
                            "type": "string",
                            "enum": ["101", "102", "103", "112_a", "112_b", "misc"],
                        },
                        "claim_number": {"type": ["integer", "null"]},
                        "legal_basis": {"type": "string"},
                        "evidence_needed": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["blocking", "high", "medium", "low"],
                        },
                        "suggested_fix": {"type": "string"},
                    },
                    "required": [
                        "issue_type",
                        "claim_number",
                        "legal_basis",
                        "evidence_needed",
                        "severity",
                        "suggested_fix",
                    ],
                    "additionalProperties": False,
                },
            },
            "overall_risk": {
                "type": "string",
                "enum": ["blocking", "high", "medium", "low"],
            },
            "summary": {"type": "string"},
        },
        "required": ["issues", "overall_risk", "summary"],
        "additionalProperties": False,
    },
}

CROWD_SCHEMA = {
    "type": "json_schema",
    "name": "crowd_flags",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "flags": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "flag_type": {
                            "type": "string",
                            "enum": [
                                "confusing_term",
                                "undefined_term",
                                "missing_antecedent",
                                "figure_caption_mismatch",
                                "summary_mismatch",
                                "other",
                            ],
                        },
                        "excerpt": {"type": "string"},
                        "suggestion": {"type": "string"},
                    },
                    "required": ["location", "flag_type", "excerpt", "suggestion"],
                    "additionalProperties": False,
                },
            },
            "total_flags": {"type": "integer"},
        },
        "required": ["flags", "total_flags"],
        "additionalProperties": False,
    },
}

# ---------------------------------------------------------------------------
# System prompts — role-specific, not legal advice
# ---------------------------------------------------------------------------

EXAMINER_PROMPT = """\
You are simulating a USPTO patent examiner conducting a first-action examination.
Your role: surface every arguable rejection under 35 USC 101, 102, 103, and 112.
You are adversarial — find weaknesses, not strengths.
Rules:
- Cite specific claim language when raising each issue.
- For 102/103, name the closest prior-art reference you know of (be specific).
- For 112(a), identify which limitation lacks written-description support.
- For 112(b), identify which term is indefinite and why.
- Do not give legal advice. Return structured output only.
"""

APPLICANT_PROMPT = """\
You are simulating a patent applicant's counsel preparing a response to office actions.
Your role: identify the strongest arguments for patentability and propose amendments.
Rules:
- For each examiner issue, provide the best counter-argument.
- Propose specific claim amendments that preserve the broadest scope while
  overcoming the rejection.
- Flag any amendment that risks new-matter (37 CFR 1.121) or disclaimer.
- Do not give legal advice. Return structured output only.
"""

DRAFTER_PROMPT = """\
You are a patent drafter assisting with a non-provisional utility application.
Your role: improve claim language, find missing definitions, and check consistency
between claims, specification, and figures.
Rules:
- Prefer functional language (means-plus-function) only when explicitly requested.
- Flag every technical term that appears in the claims but is not defined in
  the specification's definitions section.
- Check that every figure cited in the Brief Description of Drawings is also
  referenced in the Detailed Description.
- Do not give legal advice. Return structured output only.
"""

CROWD_PROMPT = """\
You are one reviewer in a crowd-review pass. Your task is narrow and fast:
flag confusing words, missing definitions, figure-caption mismatches, and
antecedent-basis problems. Do not do full legal analysis — just flag items
a non-expert would find unclear or inconsistent.
"""

# ---------------------------------------------------------------------------
# Core call
# ---------------------------------------------------------------------------

def _call(
    instructions: str,
    content: str,
    schema: dict,
    reasoning: dict = REASONING_HIGH,
    model: str | None = None,
) -> dict:
    """
    Single Responses API call returning parsed JSON matching schema.
    Raises on API error; caller handles retry / logging.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set; run `python patent_ai.py check` before live examination.")
    selected_model = model or primary_model()
    client = OpenAI(api_key=api_key)
    resp = client.responses.create(
        model=selected_model,
        reasoning=reasoning,
        instructions=instructions,
        input=[{"role": "user", "content": content}],
        text={"format": schema},
    )
    return json.loads(resp.output_text)


def check_openai_config(verify_models: bool = False) -> dict:
    """Return safe preflight metadata without printing secrets."""
    payload = {
        "ok": True,
        "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
        "primary_model": primary_model(),
        "draft_model": draft_model(),
        "verified_against_api": False,
        "available": None,
        "error": None,
    }
    if verify_models:
        if not payload["openai_api_key_present"]:
            payload["ok"] = False
            payload["error"] = "OPENAI_API_KEY missing; cannot verify model IDs against the API."
            return payload
        try:
            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            ids = {model.id for model in client.models.list().data}
            missing = [model_id for model_id in (primary_model(), draft_model()) if model_id not in ids]
            payload["verified_against_api"] = True
            payload["available"] = not missing
            if missing:
                payload["ok"] = False
                payload["error"] = f"Model id(s) not available to this key: {', '.join(missing)}"
        except Exception as exc:  # pragma: no cover - network/API dependent
            payload["ok"] = False
            payload["error"] = f"{type(exc).__name__}: {exc}"
    return payload


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def examine(claims_text: str, spec_excerpt: str | None = None) -> dict:
    """
    Simulate USPTO first-action examination. Returns IssueReport JSON.

    claims_text : full claims section as plain text
    spec_excerpt: relevant spec sections for 112 analysis (optional)
    """
    content = f"CLAIMS:\n{claims_text}"
    if spec_excerpt:
        content += f"\n\nSPECIFICATION EXCERPT:\n{spec_excerpt}"
    return _call(EXAMINER_PROMPT, content, ISSUE_SCHEMA, REASONING_HIGH)


def respond(claims_text: str, examination_report: dict) -> dict:
    """
    Simulate applicant response to an IssueReport. Returns IssueReport JSON
    with suggested amendments and counter-arguments in suggested_fix fields.
    """
    content = (
        f"CLAIMS:\n{claims_text}\n\n"
        f"EXAMINER ISSUES:\n{json.dumps(examination_report, indent=2)}"
    )
    return _call(APPLICANT_PROMPT, content, ISSUE_SCHEMA, REASONING_HIGH)


def draft_review(claims_text: str, spec_text: str, figure_captions: list[str]) -> dict:
    """
    Drafter pass: consistency check between claims, spec, and figures.
    Returns IssueReport JSON.
    """
    fig_block = "\n".join(f"- {c}" for c in figure_captions)
    content = (
        f"CLAIMS:\n{claims_text}\n\n"
        f"SPECIFICATION (condensed):\n{spec_text}\n\n"
        f"FIGURE CAPTIONS:\n{fig_block}"
    )
    return _call(DRAFTER_PROMPT, content, ISSUE_SCHEMA, REASONING_MEDIUM)


def crowd_flag(section_text: str, section_label: str = "unknown") -> dict:
    """
    Cheap crowd pass on a single section. Returns CrowdFlags JSON.
    Use for Background, Summary, or individual claim groups.
    """
    content = f"SECTION: {section_label}\n\n{section_text}"
    return _call(CROWD_PROMPT, content, CROWD_SCHEMA, REASONING_MEDIUM, model=draft_model())


# ---------------------------------------------------------------------------
# Workbench helpers — read from assembled/ and write results to workbench/
# ---------------------------------------------------------------------------

HERE = Path(__file__).parent
ASSEMBLED = HERE / "assembled"
SPEC_DOCX_MD = ASSEMBLED / "SCBE_NONPROVISIONAL_SPEC_DRAFT_v1.md"


def _load_md_section(md_text: str, header: str) -> str:
    """Extract a section from the assembled markdown spec."""
    lines = md_text.splitlines()
    out, capturing = [], False
    for line in lines:
        stripped = line.strip()
        low = stripped.lower()
        if header.lower() in low and stripped.startswith("## "):
            capturing = True
            continue
        if capturing and stripped.startswith("## "):
            break
        if capturing:
            out.append(line)
    return "\n".join(out).strip()


def run_examination_round(round_label: str = "auto") -> Path:
    """
    Full examination round against the assembled spec MD.
    Writes JSON and MD results to workbench/rounds/.
    Returns path to the JSON output.
    """
    if not SPEC_DOCX_MD.exists():
        raise FileNotFoundError(f"Assembled spec MD not found: {SPEC_DOCX_MD}")

    md_text = SPEC_DOCX_MD.read_text(encoding="utf-8")
    claims_text = _load_md_section(md_text, "CLAIMS")
    spec_excerpt = _load_md_section(md_text, "DETAILED DESCRIPTION")[:6000]

    if not claims_text:
        raise ValueError("Could not extract CLAIMS section from assembled MD")

    report = examine(claims_text, spec_excerpt)

    rounds_dir = HERE / "rounds"
    rounds_dir.mkdir(exist_ok=True)

    # Auto-number rounds
    if round_label == "auto":
        existing = sorted(rounds_dir.glob("examination_round_*.json"))
        n = len(existing) + 1
        round_label = f"{n:03d}"

    json_out = rounds_dir / f"examination_round_{round_label}.json"
    md_out = rounds_dir / f"examination_round_{round_label}.md"

    json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        f"# Examination Round {round_label}",
        f"",
        f"**Overall risk:** {report['overall_risk']}",
        f"",
        f"**Summary:** {report['summary']}",
        f"",
        f"## Issues ({len(report['issues'])} total)",
        f"",
    ]
    for iss in report["issues"]:
        lines += [
            f"### [{iss['issue_type'].upper()}] Claim {iss['claim_number']} — {iss['severity']}",
            f"",
            f"**Legal basis:** {iss['legal_basis']}",
            f"",
            f"**Evidence needed:** {iss['evidence_needed']}",
            f"",
            f"**Suggested fix:** {iss['suggested_fix']}",
            f"",
        ]
    md_out.write_text("\n".join(lines), encoding="utf-8")

    print(f"Examination round {round_label}: {len(report['issues'])} issues, "
          f"overall_risk={report['overall_risk']}")
    print(f"  JSON: {json_out}")
    print(f"  MD:   {md_out}")
    return json_out


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "examine"
    if cmd == "examine":
        run_examination_round()
    elif cmd == "check":
        verify = "--verify" in sys.argv[2:]
        payload = check_openai_config(verify_models=verify)
        print(json.dumps(payload, indent=2))
        if not payload["ok"]:
            sys.exit(2)
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python patent_ai.py [check [--verify] | examine]")
        sys.exit(1)
