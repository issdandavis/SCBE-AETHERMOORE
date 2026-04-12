from __future__ import annotations

from api.darpa_prep.darpa_portal import parse_darpa_start_submissions

SAMPLE_PORTAL_TEXT = """
Begin a New Submission
The following is a list of open solicitations to which you may submit.

DARPA-PA-25-07-02: Compositional Learning-And-Reasoning for AI Complex Systems Engineering (CLARA) (DSO)
Compositional Learning-And-Reasoning for AI Complex Systems Engineering (CLARA)
Proposal Abstract Deadline (ET)
3/2/2026 4:00:00 PM Submission Deadline Passed Full Proposal Final Deadline (ET)
4/17/2026 4:00:00 PM

DARPA-PS-26-04: Cyber Physical Systems Executing in Real Time (CyPhER Forge) (TTO)
Cyber Physical Systems Executing in Real Time (CyPhER Forge)
Proposal Abstract Deadline (ET)
4/15/2026 4:00:00 PM  Full Proposal Initial Close Deadline (ET)
6/1/2026 1:00:00 PM Full Proposal Final Deadline (ET)
6/15/2026 1:00:00 PM

DARPA-PS-26-23: Fleetwood (BTO)
Fleetwood
Proposal Abstract Deadline (ET)
4/13/2026 5:00:00 PM  Full Proposal Final Deadline (ET)
6/4/2026 5:00:00 PM Requires an encouraged Proposal Abstract
"""


def test_parse_darpa_start_submissions_extracts_opportunities() -> None:
    opportunities, citations = parse_darpa_start_submissions(SAMPLE_PORTAL_TEXT)
    assert len(opportunities) == 3
    assert len(citations) == 3

    clara = next(item for item in opportunities if item.solicitation_number == "DARPA-PA-25-07-02")
    assert clara.office_code == "DSO"
    assert clara.proposal_abstract_deadline == "3/2/2026 4:00:00 PM"
    assert clara.full_proposal_final_deadline == "4/17/2026 4:00:00 PM"
    assert clara.available_submission_types == ["proposal_abstract", "full_proposal"]

    fleetwood = next(item for item in opportunities if item.solicitation_number == "DARPA-PS-26-23")
    assert fleetwood.proposal_abstract_encouraged is True
    assert fleetwood.proposal_abstract_required is False


def test_parse_darpa_start_submissions_uses_exact_portal_url_by_default() -> None:
    _, citations = parse_darpa_start_submissions(SAMPLE_PORTAL_TEXT)
    assert citations[0].source_ref == "https://baa.darpa.mil/Submissions/StartSubmissions.aspx"
