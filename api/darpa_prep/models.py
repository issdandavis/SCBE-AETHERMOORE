from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


SourceSystem = Literal["DARPA", "SAM.gov", "Grants.gov", "agency_portal"]
InstrumentType = Literal["contract", "grant", "cooperative_agreement", "other_transaction", "unknown"]


class Citation(BaseModel):
    citation_id: str
    source_type: str
    source_ref: str
    excerpt: str


class OpportunityRecord(BaseModel):
    opportunity_id: str
    source_system: SourceSystem
    instrument_type: InstrumentType
    title: str
    agency: str
    solicitation_number: str
    submission_path: str
    deadline: Optional[str] = None
    topic_area: Optional[str] = None


class RequirementRecord(BaseModel):
    requirement_id: str
    category: Literal[
        "eligibility",
        "format",
        "technical",
        "evaluation",
        "registration",
        "budget",
        "security",
        "export_control",
        "submission",
    ]
    priority: Literal["critical", "high", "medium", "low"]
    text: str
    source_section: str
    citation_ids: List[str]


class NormalizeOpportunityRequest(BaseModel):
    raw_text: Optional[str] = Field(default=None, description="Raw solicitation or guidance text")
    source_payload: Optional[Dict[str, Any]] = Field(default=None, description="Raw opportunity payload from a source API")
    source_system: SourceSystem = "SAM.gov"
    source_ref: Optional[str] = None


class NormalizeOpportunityResponse(BaseModel):
    opportunity: OpportunityRecord
    requirements: List[RequirementRecord]
    citations: List[Citation]


class SamGovSearchResult(BaseModel):
    opportunity: OpportunityRecord
    source_payload: Dict[str, Any]


class SamGovSearchResponse(BaseModel):
    query: str
    count: int
    opportunities: List[SamGovSearchResult]


class DarpaPortalOpportunityRecord(BaseModel):
    opportunity_id: str
    title: str
    solicitation_number: str
    office_code: str
    submission_path: str
    solicitation_url: Optional[str] = None
    proposal_abstract_encouraged: bool = False
    proposal_abstract_required: bool = False
    available_submission_types: List[str] = Field(default_factory=list)
    executive_summary_deadline: Optional[str] = None
    proposal_abstract_deadline: Optional[str] = None
    full_proposal_initial_close_deadline: Optional[str] = None
    full_proposal_final_deadline: Optional[str] = None


class DarpaPortalParseRequest(BaseModel):
    raw_text: str = Field(..., description="Raw Start Submissions page text")
    source_ref: Optional[str] = Field(
        default=None, description="Canonical URL for the solicitation source"
    )


class DarpaPortalParseResponse(BaseModel):
    count: int
    opportunities: List[DarpaPortalOpportunityRecord]
    citations: List[Citation]

