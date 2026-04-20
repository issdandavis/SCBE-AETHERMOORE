from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query

from .client import SamGovClient, extract_requirement_candidates
from .darpa_portal import parse_darpa_start_submissions
from .models import (
    Citation,
    DarpaPortalParseRequest,
    DarpaPortalParseResponse,
    NormalizeOpportunityRequest,
    NormalizeOpportunityResponse,
    RequirementRecord,
    SamGovSearchResponse,
    SamGovSearchResult,
)

router = APIRouter(prefix="/v1/opportunities", tags=["DARPA Prep"])


@router.get("/sam-gov/search", response_model=SamGovSearchResponse)
async def search_sam_gov_opportunities(
    query: str = Query(..., min_length=2, description="Search string for SAM.gov opportunities"),
    limit: int = Query(default=10, ge=1, le=50),
    active_only: bool = Query(default=True),
):
    client = SamGovClient()
    try:
        raw_results = client.search_opportunities(query=query, limit=limit, active_only=active_only)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - network/runtime guard
        raise HTTPException(status_code=502, detail=f"SAM.gov search failed: {exc}") from exc

    normalized = [
        SamGovSearchResult(opportunity=client.normalize_opportunity(item), source_payload=item)
        for item in raw_results
    ]
    return SamGovSearchResponse(query=query, count=len(normalized), opportunities=normalized)


@router.post("/normalize", response_model=NormalizeOpportunityResponse)
async def normalize_opportunity(request: NormalizeOpportunityRequest):
    if not request.raw_text and not request.source_payload:
        raise HTTPException(status_code=400, detail="Provide raw_text or source_payload")

    if request.source_payload:
        opportunity = SamGovClient.normalize_opportunity(request.source_payload)
        source_ref = request.source_ref or opportunity.submission_path
        base_text = "\n".join(
            str(value) for value in request.source_payload.values() if isinstance(value, (str, int, float))
        )
    else:
        source_ref = request.source_ref or "inline://raw_text"
        opportunity = SamGovClient.normalize_opportunity(
            {
                "noticeId": "inline",
                "title": "Inline opportunity draft",
                "organizationName": request.source_system,
                "solicitationNumber": "unknown",
                "url": source_ref,
            }
        )
        opportunity.source_system = request.source_system
        base_text = request.raw_text or ""

    requirements: List[RequirementRecord] = []
    citations: List[Citation] = [
        Citation(
            citation_id="cit_source_001",
            source_type="solicitation",
            source_ref=source_ref,
            excerpt=(base_text[:400] if base_text else opportunity.title),
        )
    ]

    for index, (category, text) in enumerate(extract_requirement_candidates(base_text), start=1):
        requirements.append(
            RequirementRecord(
                requirement_id=f"req_{category}_{index:04d}",
                category=category,
                priority="high" if category in {"eligibility", "submission"} else "medium",
                text=text,
                source_section="source_payload" if request.source_payload else "raw_text",
                citation_ids=["cit_source_001"],
            )
        )

    return NormalizeOpportunityResponse(opportunity=opportunity, requirements=requirements, citations=citations)


@router.post("/darpa-portal/parse", response_model=DarpaPortalParseResponse)
async def parse_darpa_portal(request: DarpaPortalParseRequest):
    if not request.raw_text.strip():
        raise HTTPException(status_code=400, detail="raw_text must be non-empty")
    opportunities, citations = parse_darpa_start_submissions(
        request.raw_text, source_ref=request.source_ref
    )
    return DarpaPortalParseResponse(
        count=len(opportunities),
        opportunities=opportunities,
        citations=citations,
    )

