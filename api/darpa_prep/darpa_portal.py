from __future__ import annotations

import re
from typing import List

from .models import Citation, DarpaPortalOpportunityRecord


SOLICITATION_LINE_RE = re.compile(
    r"^(?P<solicitation_number>[A-Z0-9-]+): (?P<header_title>.+) \((?P<office_code>[A-Z0-9]+)\)$"
)

DEADLINE_PATTERNS = {
    "executive_summary_deadline": r"Executive Summary Deadline \(ET\)\s*([0-9/ :AMP]+)",
    "proposal_abstract_deadline": r"Proposal Abstract Deadline \(ET\)\s*([0-9/ :AMP]+)",
    "full_proposal_initial_close_deadline": r"Full Proposal Initial Close Deadline \(ET\)\s*([0-9/ :AMP]+)",
    "full_proposal_final_deadline": r"Full Proposal Final Deadline \(ET\)\s*([0-9/ :AMP]+)",
}


def _clean_deadline(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\s+", " ", value).strip()


def parse_darpa_start_submissions(
    raw_text: str,
    *,
    source_ref: str | None = None,
) -> tuple[List[DarpaPortalOpportunityRecord], List[Citation]]:
    opportunities: List[DarpaPortalOpportunityRecord] = []
    citations: List[Citation] = []
    source_ref = source_ref or "https://baa.darpa.mil/Submissions/StartSubmissions.aspx"

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    blocks: List[tuple[str, List[str]]] = []
    current_header: str | None = None
    current_lines: List[str] = []

    for line in lines:
        if SOLICITATION_LINE_RE.match(line):
            if current_header:
                blocks.append((current_header, current_lines))
            current_header = line
            current_lines = []
            continue
        if current_header:
            current_lines.append(line)

    if current_header:
        blocks.append((current_header, current_lines))

    for index, (header_line, block_lines) in enumerate(blocks, start=1):
        header_match = SOLICITATION_LINE_RE.match(header_line)
        if not header_match:
            continue
        solicitation_number = header_match.group("solicitation_number").strip()
        office_code = header_match.group("office_code").strip()
        display_title = block_lines[0] if block_lines else header_match.group("header_title").strip()
        body = re.sub(r"\s+", " ", " ".join(block_lines[1:] if len(block_lines) > 1 else block_lines)).strip()

        fields = {
            key: _clean_deadline(re.search(pattern, body).group(1) if re.search(pattern, body) else None)
            for key, pattern in DEADLINE_PATTERNS.items()
        }

        available_submission_types: List[str] = []
        if fields["executive_summary_deadline"]:
            available_submission_types.append("executive_summary")
        if fields["proposal_abstract_deadline"]:
            available_submission_types.append("proposal_abstract")
        if fields["full_proposal_initial_close_deadline"] or fields["full_proposal_final_deadline"]:
            available_submission_types.append("full_proposal")

        proposal_abstract_encouraged = "Requires an encouraged Proposal Abstract" in body
        proposal_abstract_required = bool(fields["proposal_abstract_deadline"]) and not proposal_abstract_encouraged

        excerpt_parts = [display_title]
        for field_name in (
            "executive_summary_deadline",
            "proposal_abstract_deadline",
            "full_proposal_initial_close_deadline",
            "full_proposal_final_deadline",
        ):
            if fields[field_name]:
                excerpt_parts.append(f"{field_name}={fields[field_name]}")
        if proposal_abstract_encouraged:
            excerpt_parts.append("proposal_abstract_encouraged=true")

        citation_id = f"cit_darpa_portal_{index:04d}"
        citations.append(
            Citation(
                citation_id=citation_id,
                source_type="agency_guidance",
                source_ref=source_ref,
                excerpt=" | ".join(excerpt_parts),
            )
        )

        opportunities.append(
            DarpaPortalOpportunityRecord(
                opportunity_id=f"darpa_portal_{solicitation_number.lower()}",
                title=display_title,
                solicitation_number=solicitation_number,
                office_code=office_code,
                submission_path=source_ref,
                solicitation_url=None,
                proposal_abstract_encouraged=proposal_abstract_encouraged,
                proposal_abstract_required=proposal_abstract_required,
                available_submission_types=available_submission_types,
                **fields,
            )
        )

    return opportunities, citations
