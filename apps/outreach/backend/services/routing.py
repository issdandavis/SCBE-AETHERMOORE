"""
Aethermoor Outreach -- Routing target service.
Real agencies, real contact information for Port Angeles, WA.
"""

from typing import Dict, List, Optional

# Routing targets with real contact information for Port Angeles
ROUTING_TARGETS: List[Dict] = [
    {
        "name": "WA Secretary of State -- Corporations",
        "agency": "Washington Secretary of State",
        "contact_info": "corps@sos.wa.gov",
        "phone": "360-725-0377",
        "hours": "Mon-Fri 8:00 AM - 5:00 PM PT",
        "website": "https://sos.wa.gov",
        "notes": "Business registration, LLC formation, trade names. Online filing available 24/7 at sos.wa.gov/corps.",
        "serves_intents": ["start_business"],
    },
    {
        "name": "City of PA -- Planning & Community Development",
        "agency": "City of Port Angeles",
        "contact_info": "planning@cityofpa.us",
        "phone": "360-417-4751",
        "hours": "Mon-Fri 8:00 AM - 5:00 PM PT",
        "website": "https://www.cityofpa.us",
        "notes": "Building permits, zoning questions, land use, pre-application conferences (free). Located at 321 E 5th St.",
        "serves_intents": ["permit_inquiry", "start_business"],
    },
    {
        "name": "Peninsula SBDC",
        "agency": "Peninsula Small Business Development Center",
        "contact_info": "sbdc@pencol.edu",
        "phone": "360-417-6540",
        "hours": "Mon-Fri 8:30 AM - 4:30 PM PT",
        "website": "https://wsbdc.org",
        "notes": "Free one-on-one business advising. Help with business plans, funding applications, marketing. At Peninsula College.",
        "serves_intents": ["start_business", "grant_discovery"],
    },
    {
        "name": "Port of Port Angeles",
        "agency": "Port of Port Angeles",
        "contact_info": "info@portofpa.com",
        "phone": "360-457-8527",
        "hours": "Mon-Fri 8:00 AM - 5:00 PM PT",
        "website": "https://www.portofpa.com",
        "notes": "Economic development, industrial sites, maritime facilities, infrastructure. Airport (CLM) operations.",
        "serves_intents": ["start_business", "grant_discovery", "permit_inquiry"],
    },
    {
        "name": "NODC / NICE",
        "agency": "North Olympic Development Council",
        "contact_info": "info@nodc.us",
        "phone": "360-457-7793",
        "hours": "Mon-Fri 8:00 AM - 5:00 PM PT",
        "website": "https://www.nodc.us",
        "notes": "Regional economic development for Clallam County. Administers revolving loan funds, CDBG, technical assistance.",
        "serves_intents": ["grant_discovery", "start_business"],
    },
    {
        "name": "USPTO -- Patent Assistance",
        "agency": "United States Patent and Trademark Office",
        "contact_info": None,
        "phone": "800-786-9199",
        "hours": "Mon-Fri 8:30 AM - 8:00 PM ET",
        "website": "https://www.uspto.gov",
        "notes": "Patent filing, trademark registration, pro se assistance. Provisional patent: $160 micro entity. Online filing at EFS-Web.",
        "serves_intents": ["patent_filing"],
    },
    {
        "name": "IRS -- EIN Assignment",
        "agency": "Internal Revenue Service",
        "contact_info": None,
        "phone": "800-829-4933",
        "hours": "Mon-Fri 7:00 AM - 7:00 PM local time",
        "website": "https://www.irs.gov",
        "notes": "Employer Identification Number (EIN) available free and instant online at irs.gov/ein. Phone for questions only.",
        "serves_intents": ["start_business"],
    },
    {
        "name": "SBA -- Small Business Administration",
        "agency": "U.S. Small Business Administration",
        "contact_info": None,
        "phone": "800-827-5722",
        "hours": "Mon-Fri 8:00 AM - 8:00 PM ET",
        "website": "https://www.sba.gov",
        "notes": "7(a) loans, microloans, disaster loans, government contracting. Find local resources at sba.gov/local.",
        "serves_intents": ["grant_discovery", "start_business"],
    },
    {
        "name": "USDA Rural Development -- WA",
        "agency": "USDA Rural Development",
        "contact_info": None,
        "phone": "360-704-7740",
        "hours": "Mon-Fri 8:00 AM - 4:30 PM PT",
        "website": "https://www.rd.usda.gov/wa",
        "notes": "Rural business grants, B&I loan guarantees, rural energy programs. Port Angeles qualifies as rural for most programs.",
        "serves_intents": ["grant_discovery"],
    },
    {
        "name": "WA Dept of Commerce",
        "agency": "Washington State Department of Commerce",
        "contact_info": None,
        "phone": "360-725-4000",
        "hours": "Mon-Fri 8:00 AM - 5:00 PM PT",
        "website": "https://www.commerce.wa.gov",
        "notes": "State grants, Community Development Block Grants, economic development programs. Check commerce.wa.gov/grants.",
        "serves_intents": ["grant_discovery"],
    },
    {
        "name": "WA Bar Association -- Patent Pro Bono",
        "agency": "Washington State Bar Association",
        "contact_info": None,
        "phone": "206-443-9722",
        "hours": "Mon-Fri 8:00 AM - 5:00 PM PT",
        "website": "https://www.wsba.org",
        "notes": "Patent pro bono program connects qualifying inventors with volunteer patent attorneys. Income qualification required.",
        "serves_intents": ["patent_filing"],
    },
]


def get_routing_targets(intent: Optional[str] = None) -> List[Dict]:
    """
    Get routing targets, optionally filtered by intent.

    Args:
        intent: If provided, filter to targets that serve this intent.

    Returns:
        List of routing target dicts (without serves_intents field for API output).
    """
    targets = ROUTING_TARGETS
    if intent:
        targets = [t for t in targets if intent in t.get("serves_intents", [])]

    # Strip internal serves_intents field from output
    return [
        {k: v for k, v in t.items() if k != "serves_intents"}
        for t in targets
    ]


def seed_routing_targets_to_db(session) -> int:
    """
    Seed routing targets into the database.
    Returns count of records inserted.
    """
    from apps.outreach.backend.models import RoutingTarget

    count = 0
    for t in ROUTING_TARGETS:
        existing = session.query(RoutingTarget).filter_by(name=t["name"]).first()
        if not existing:
            rt = RoutingTarget(
                name=t["name"],
                agency=t["agency"],
                contact_info=t.get("contact_info", ""),
                phone=t.get("phone", ""),
                hours=t.get("hours", ""),
                website=t.get("website", ""),
                notes=t.get("notes", ""),
            )
            session.add(rt)
            count += 1

    if count > 0:
        session.commit()
    return count
