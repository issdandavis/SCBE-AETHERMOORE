from __future__ import annotations

import re
from typing import Any, Dict, Iterable

from .models import OpportunityRecord
from .sam_public import SamGovPublicClient


class SamGovClient(SamGovPublicClient):
    """Public SAM transport plus SCBE's proposal-domain normalization."""

    @staticmethod
    def normalize_opportunity(payload: Dict[str, Any]) -> OpportunityRecord:
        notice_id = str(
            payload.get("noticeId")
            or payload.get("opportunityId")
            or payload.get("id")
            or payload.get("solicitationNumber")
            or "unknown"
        ).strip()

        solicitation_number = str(
            payload.get("solicitationNumber")
            or payload.get("solicitation_number")
            or payload.get("solNumber")
            or notice_id
        ).strip()

        title = str(payload.get("title") or payload.get("opportunityTitle") or "Untitled opportunity").strip()
        agency = str(
            payload.get("fullParentPathName")
            or payload.get("organizationName")
            or payload.get("department")
            or payload.get("agency")
            or "Unknown agency"
        ).strip()

        submission_path = str(
            payload.get("uiLink")
            or payload.get("link")
            or payload.get("url")
            or payload.get("samUrl")
            or f"https://sam.gov/opp/{notice_id}/view"
        ).strip()

        deadline = (
            payload.get("responseDeadLine")
            or payload.get("responseDeadline")
            or payload.get("closeDate")
            or payload.get("archiveDate")
        )

        topic_area = (
            str(
                payload.get("naicsDescription")
                or payload.get("naicsCode")
                or payload.get("classification")
                or payload.get("classificationCode")
                or ""
            ).strip()
            or None
        )

        notice_type = str(
            payload.get("type") or payload.get("noticeType") or payload.get("instrumentType") or ""
        ).lower()
        if "grant" in notice_type:
            instrument_type = "grant"
        elif "cooperative" in notice_type:
            instrument_type = "cooperative_agreement"
        elif "transaction" in notice_type:
            instrument_type = "other_transaction"
        elif notice_type:
            instrument_type = "contract"
        else:
            instrument_type = "unknown"

        return OpportunityRecord(
            opportunity_id=f"sam_gov_{notice_id}",
            source_system="SAM.gov",
            instrument_type=instrument_type,
            title=title,
            agency=agency,
            solicitation_number=solicitation_number,
            submission_path=submission_path,
            deadline=str(deadline).strip() if deadline else None,
            topic_area=topic_area,
        )


def extract_requirement_candidates(text: str) -> Iterable[tuple[str, str]]:
    for raw_line in text.splitlines():
        for chunk in re.split(r"(?<=[.!?])\s+", raw_line):
            line = chunk.strip(" -*\t")
            lowered = line.lower()
            if len(line) < 20:
                continue
            if any(
                token in lowered
                for token in ("shall", "must", "required", "deadline", "eligib", "evaluate", "registration", "submit")
            ):
                if "eligib" in lowered or "sam.gov" in lowered or "uei" in lowered or "register" in lowered:
                    category = "eligibility"
                elif "deadline" in lowered or "submit" in lowered:
                    category = "submission"
                elif "evaluate" in lowered:
                    category = "evaluation"
                elif "budget" in lowered or "cost" in lowered:
                    category = "budget"
                else:
                    category = "technical"
                yield category, line
