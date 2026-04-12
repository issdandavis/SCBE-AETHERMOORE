from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


def test_darpa_prep_schema_accepts_minimal_analysis_record() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    schema = json.loads(
        (repo_root / "schemas" / "darpa_prep_opportunity_analysis.schema.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)

    record = {
        "schema_version": "scbe_darpa_prep_opportunity_analysis_v1",
        "opportunity": {
            "opportunity_id": "opp_darpa_clara_0001",
            "source_system": "DARPA",
            "instrument_type": "contract",
            "title": "Compositional Lifelong Adaptive Resilient Autonomy",
            "agency": "DARPA",
            "solicitation_number": "DARPA-PA-25-07-02",
            "submission_path": "https://sam.gov/opportunity/example",
            "deadline": "2026-04-17T23:59:59Z",
            "topic_area": "AI compositional reasoning",
        },
        "requirements": [
            {
                "requirement_id": "req_technical_0001",
                "category": "technical",
                "priority": "critical",
                "text": "Describe the technical approach and milestones.",
                "source_section": "Section 3.2",
                "citation_ids": ["cit_001"],
            }
        ],
        "compliance_matrix": [
            {
                "requirement_id": "req_technical_0001",
                "status": "weak",
                "evidence_section_ids": ["sec_exec_summary"],
                "confidence": 0.61,
                "review_required": True,
                "notes": "Milestones are implied but not explicit.",
            }
        ],
        "readiness_scores": {
            "technical_fit": {
                "value": 0.72,
                "explanation": "Technical approach aligns with the solicitation scope.",
                "citation_ids": ["cit_001"],
            },
            "completeness": {
                "value": 0.50,
                "explanation": "Several required sections are incomplete.",
                "citation_ids": ["cit_001"],
            },
            "compliance": {
                "value": 0.58,
                "explanation": "One critical requirement is weakly addressed.",
                "citation_ids": ["cit_001"],
            },
            "transition_alignment": {
                "value": 0.66,
                "explanation": "Transition path is present but underspecified.",
                "citation_ids": ["cit_001"],
            },
            "teaming_readiness": {
                "value": 0.40,
                "explanation": "Teaming evidence is limited.",
                "citation_ids": ["cit_001"],
            },
            "submission_readiness": {
                "value": 0.55,
                "explanation": "Submission prerequisites still need review.",
                "citation_ids": ["cit_001"],
            },
            "overall": {
                "value": 0.57,
                "explanation": "Draft is usable for review, not for submission.",
                "citation_ids": ["cit_001"],
            },
        },
        "citations": [
            {
                "citation_id": "cit_001",
                "source_type": "solicitation",
                "source_ref": "DARPA-PA-25-07-02 Section 3.2",
                "excerpt": "Offerors shall describe the technical approach and milestones.",
            }
        ],
    }

    validator.validate(record)
