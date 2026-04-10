from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .models import OpportunityRecord


def _env_api_key() -> Optional[str]:
    for name in ("SAM_GOV_API_KEY", "DATA_GOV_API_KEY"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return None


@dataclass
class SamGovClient:
    api_key: Optional[str] = None
    base_url: str = "https://api.sam.gov/opportunities/v2/search"
    timeout_seconds: int = 20

    def __post_init__(self) -> None:
        self.api_key = (self.api_key or _env_api_key() or "").strip() or None
        override_url = os.getenv("SAM_GOV_OPPORTUNITIES_URL", "").strip()
        if override_url:
            self.base_url = override_url

    def search_opportunities(self, *, query: str, limit: int = 10, active_only: bool = True) -> List[Dict[str, Any]]:
        if not self.api_key:
            raise ValueError("SAM_GOV_API_KEY or DATA_GOV_API_KEY is not configured")

        today = datetime.now(UTC).date()
        posted_from = (today - timedelta(days=180)).strftime("%m/%d/%Y")
        posted_to = today.strftime("%m/%d/%Y")
        params = {
            "api_key": self.api_key,
            "title": query,
            "limit": max(1, min(int(limit), 50)),
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "offset": 0,
        }

        request = Request(f"{self.base_url}?{urlencode(params)}", method="GET")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"SAM.gov search failed with HTTP {exc.code}: {body}") from exc

        opportunities = payload.get("opportunitiesData") or payload.get("data") or payload.get("results") or []
        if isinstance(opportunities, dict):
            opportunities = [opportunities]
        if active_only:
            opportunities = [item for item in opportunities if str(item.get("active", "")).strip().lower() in {"yes", "true", "active"}]
        return list(opportunities)

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

        topic_area = str(
            payload.get("naicsDescription")
            or payload.get("description")
            or payload.get("classification")
            or ""
        ).strip() or None

        notice_type = str(payload.get("noticeType") or payload.get("instrumentType") or "").lower()
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
            if any(token in lowered for token in ("shall", "must", "required", "deadline", "eligib", "evaluate", "registration", "submit")):
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
