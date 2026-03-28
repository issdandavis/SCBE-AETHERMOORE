"""
Aethermoor Outreach -- Opportunity profile service.
Real location profiles for Port Angeles, WA neighborhoods/areas.
"""

from typing import Dict, List, Optional

OPPORTUNITY_PROFILES: Dict[str, Dict] = {
    "downtown": {
        "area": "Downtown Port Angeles",
        "description": "The commercial heart of Port Angeles. First Street corridor with established retail, restaurants, and services. High foot traffic from tourists heading to/from the Coho Ferry (Victoria, BC) and Olympic National Park.",
        "walkability": "High",
        "opportunity_types": ["Retail", "Food service", "Professional services", "Tourism", "Arts and culture"],
        "competition_level": "Moderate",
        "avg_commercial_rent": "$12-18/sq ft/year (varies widely)",
        "highlights": [
            "Vision 2045 downtown investment zone -- city actively investing in streetscape improvements",
            "Coho Ferry terminal brings Canadian day-trippers with strong currency spending",
            "First Street has some vacancies -- opportunity for new tenants",
            "Port Angeles Downtown Association supports new businesses with events and marketing",
            "Walking distance to courthouse, library, and transit center",
        ],
        "challenges": [
            "Seasonal tourist fluctuations (peak: June-September)",
            "Limited parking in core blocks",
            "Some storefronts need renovation",
        ],
        "key_contacts": [
            "Port Angeles Downtown Association: 360-452-2363",
            "City Economic Development: 360-417-4500",
        ],
    },
    "waterfront": {
        "area": "Waterfront / Port Area",
        "description": "The industrial and maritime corridor along the harbor. Includes the Port of Port Angeles facilities, log yards, marine terminals, and the waterfront trail. Major redevelopment potential as timber industry transitions.",
        "walkability": "Low to moderate",
        "opportunity_types": ["Maritime services", "Light industrial", "Manufacturing", "Warehousing", "Marine tourism"],
        "competition_level": "Low",
        "avg_commercial_rent": "$8-14/sq ft/year (industrial)",
        "highlights": [
            "Port of Port Angeles actively recruiting new tenants and businesses",
            "Infrastructure already built -- water, sewer, power, heavy-load roads",
            "William R. Fairchild International Airport (CLM) adjacent for air freight",
            "Access to deep-water port for import/export",
            "Enterprise Zone tax incentives may apply",
        ],
        "challenges": [
            "Environmental review required for some sites (former industrial use)",
            "Shoreline Management Act restrictions near water",
            "Limited retail foot traffic (industrial character)",
        ],
        "key_contacts": [
            "Port of Port Angeles: 360-457-8527",
            "Clallam County Economic Development: 360-417-2421",
        ],
    },
    "east_side": {
        "area": "East Side (East of Race Street)",
        "description": "Growing residential area with increasing commercial activity along East Front Street and Highway 101 East corridor. Mix of established neighborhoods and newer development. Gateway to Sequim.",
        "walkability": "Moderate (along main corridors)",
        "opportunity_types": ["Neighborhood services", "Healthcare", "Automotive", "Convenience retail", "Professional offices"],
        "competition_level": "Low to moderate",
        "avg_commercial_rent": "$10-15/sq ft/year",
        "highlights": [
            "Growing residential population creating demand for local services",
            "Lower commercial density means less competition",
            "Highway 101 frontage gives good visibility",
            "Olympic Medical Center nearby drives healthcare-adjacent demand",
            "More affordable lease rates than downtown",
        ],
        "challenges": [
            "Car-dependent for most trips",
            "Less established commercial identity than downtown",
            "Some zoning is residential -- verify commercial use allowed",
        ],
        "key_contacts": [
            "City Planning (zoning questions): 360-417-4751",
            "Olympic Medical Center (partnership): 360-417-7000",
        ],
    },
    "west_end": {
        "area": "West End (West of Lincoln Street)",
        "description": "Tourism-adjacent area closest to Olympic National Park visitor facilities. Includes lodging, outdoor recreation services, and the Highway 101 West corridor toward Lake Crescent and the Hoh Rainforest.",
        "walkability": "Low (car-dependent, scenic)",
        "opportunity_types": ["Tourism services", "Outdoor recreation", "Lodging", "Guide services", "Artisan/craft"],
        "competition_level": "Low to moderate (seasonal)",
        "avg_commercial_rent": "$10-16/sq ft/year",
        "highlights": [
            "Over 3 million visitors to Olympic National Park annually (pre-pandemic peak)",
            "Gateway position -- travelers pass through on way to park attractions",
            "Strong seasonal revenue potential (June-September peak)",
            "Growing shoulder-season tourism (storm watching, mushroom foraging, whale watching)",
            "Hurricane Ridge is 17 miles from downtown -- day-trippers return through west side",
        ],
        "challenges": [
            "Highly seasonal -- must plan for winter slowdown",
            "Competition from lodging/services inside the park and in Forks",
            "Limited commercial zoning in some areas",
        ],
        "key_contacts": [
            "Olympic National Park Visitor Center: 360-565-3130",
            "Olympic Peninsula Visitor Bureau: 360-452-8552",
        ],
    },
}


def get_opportunity_profile(location: str) -> Optional[Dict]:
    """
    Get the opportunity profile for a location area.

    Args:
        location: Area key (downtown, waterfront, east_side, west_end) or
                  human-readable name (case insensitive, spaces/underscores flexible).

    Returns:
        Opportunity profile dict, or None if not found.
    """
    # Normalize key
    key = location.lower().strip().replace(" ", "_").replace("-", "_")

    # Direct match
    if key in OPPORTUNITY_PROFILES:
        return OPPORTUNITY_PROFILES[key]

    # Fuzzy match on area name
    for k, v in OPPORTUNITY_PROFILES.items():
        if key in v["area"].lower().replace(" ", "_"):
            return v

    return None


def get_all_locations() -> List[Dict]:
    """Return summary of all available location profiles."""
    return [
        {
            "key": k,
            "area": v["area"],
            "opportunity_types": v["opportunity_types"],
            "competition_level": v["competition_level"],
        }
        for k, v in OPPORTUNITY_PROFILES.items()
    ]


def seed_opportunity_summary() -> str:
    """Return a printable summary of all opportunity profiles for seeding confirmation."""
    lines = ["Opportunity profiles loaded:"]
    for k, v in OPPORTUNITY_PROFILES.items():
        lines.append(f"  - {v['area']} ({v['competition_level']} competition, {len(v['highlights'])} highlights)")
    return "\n".join(lines)
