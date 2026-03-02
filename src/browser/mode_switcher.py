# src/browser/mode_switcher.py
"""phi-weight gating for Octopus Browser Kernel operating modes."""
from __future__ import annotations

# Sacred Tongue phi-weight scale: actions cost exponentially more at higher tiers
PHI = 1.618033988749895

ACTION_WEIGHTS: dict[str, float] = {
    "read": 0.1,
    "navigate": 0.2,
    "click": 0.3,
    "scroll": 0.15,
    "type": 0.5,
    "select": 0.4,
    "submit": 0.7,
    "upload": 0.6,
    "download": 0.5,
    "execute_script": 0.8,
    "pay": 0.9,
}

SENSITIVE_DOMAINS: dict[str, float] = {
    # Banking / Finance
    "chase.com": 0.9, "bankofamerica.com": 0.9, "wellsfargo.com": 0.9,
    "paypal.com": 0.8, "venmo.com": 0.8, "stripe.com": 0.7,
    # Shopping / Transactions
    "amazon.com": 0.6, "shopify.com": 0.5, "gumroad.com": 0.4,
    # Social (auth-heavy)
    "twitter.com": 0.4, "x.com": 0.4, "linkedin.com": 0.4,
    # Low-sensitivity
    "google.com": 0.2, "wikipedia.org": 0.1, "github.com": 0.3,
    "notion.so": 0.3, "huggingface.co": 0.2,
}


def domain_sensitivity(domain: str) -> float:
    domain = domain.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return SENSITIVE_DOMAINS.get(domain, 0.5)


def compute_phi_weight(
    domain_sensitivity: float,
    action_type: str,
    data_sensitivity: float = 0.1,
    auth_required: bool = False,
) -> float:
    action_weight = ACTION_WEIGHTS.get(action_type, 0.5)
    auth_factor = 0.5 if auth_required else 0.0
    raw = domain_sensitivity + action_weight + data_sensitivity + auth_factor
    # Scale to phi-weight range using golden ratio exponential curve
    # Low raw → sightless (<5), medium → visual (5-10),
    # high → full_octopus (10-20), critical → governed_critical (>=20)
    return PHI ** (raw * 2.2)


def select_mode(phi_weight: float) -> str:
    if phi_weight < 5.0:
        return "sightless"
    elif phi_weight < 10.0:
        return "visual"
    elif phi_weight < 20.0:
        return "full_octopus"
    else:
        return "governed_critical"
