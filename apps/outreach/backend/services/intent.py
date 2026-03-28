"""
Aethermoor Outreach -- Intent classification service.
Keyword + pattern matching for v1. Upgradeable to ML classification later.
"""

import re
from typing import Dict, List, Tuple

# Intent patterns: (intent_key, keywords, description)
INTENT_PATTERNS: List[Tuple[str, List[str], str]] = [
    (
        "start_business",
        ["business", "start", "llc", "company", "incorporate", "sole prop", "corporation", "startup", "open a shop", "entrepreneur"],
        "Start or register a business",
    ),
    (
        "permit_inquiry",
        ["permit", "zone", "zoning", "build", "develop", "construction", "remodel", "land use", "site plan", "variance"],
        "Building permits and zoning inquiries",
    ),
    (
        "grant_discovery",
        ["grant", "fund", "funding", "loan", "support", "financial assistance", "subsidy", "incentive", "economic development"],
        "Grants, loans, and financial assistance",
    ),
    (
        "patent_filing",
        ["patent", "ip", "intellectual property", "invention", "trademark", "copyright", "provisional"],
        "Patent and intellectual property filing",
    ),
]


def classify_intent(text: str) -> Dict:
    """
    Classify freeform intent text into a structured category.

    Returns:
        dict with keys: intent, confidence, description, keywords_matched
    """
    if not text or not text.strip():
        return {
            "intent": "general_inquiry",
            "confidence": 0.0,
            "description": "General inquiry -- could not determine specific intent",
            "keywords_matched": [],
        }

    text_lower = text.lower().strip()

    best_intent = "general_inquiry"
    best_score = 0
    best_description = "General inquiry"
    best_keywords: List[str] = []

    for intent_key, keywords, description in INTENT_PATTERNS:
        matched = []
        for kw in keywords:
            # Use word boundary matching for single words, substring for phrases
            if " " in kw:
                if kw in text_lower:
                    matched.append(kw)
            else:
                if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                    matched.append(kw)

        score = len(matched)
        if score > best_score:
            best_score = score
            best_intent = intent_key
            best_description = description
            best_keywords = matched

    # Confidence: rough heuristic based on keyword hits
    if best_score == 0:
        confidence = 0.1
    elif best_score == 1:
        confidence = 0.6
    elif best_score == 2:
        confidence = 0.8
    else:
        confidence = 0.95

    return {
        "intent": best_intent,
        "confidence": confidence,
        "description": best_description,
        "keywords_matched": best_keywords,
    }


def get_all_intents() -> List[Dict]:
    """Return all known intent categories for UI suggestion chips."""
    return [
        {"intent": key, "description": desc, "example_keywords": kws[:3]}
        for key, kws, desc in INTENT_PATTERNS
    ] + [
        {
            "intent": "general_inquiry",
            "description": "General civic or business inquiry",
            "example_keywords": ["question", "help", "information"],
        }
    ]
