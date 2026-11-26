"""probability_cloud: multi-point "inference" for a NON-inference model -- a belief cloud convolved with a
gate-topography, read by gradient flow. The continuous substrate under the discrete skill-check.

Issac's idea: a rule-based / physics-style system can get the multi-OPTION resilience of a neural net's
probability distribution WITHOUT running a network -- by treating the option space as a fluid field instead
of a sequence of hard picks:

  1. DIFFUSE  -- the input isn't a single point; it's a Gaussian cloud over the option positions (sigma =
     uncertainty). One precise coordinate becomes a density.
  2. TOPOGRAPHY -- the environment is a landscape: desirable actions are gravity WELLS (deep), pitfalls /
     soft-locked gates are PEAKS (repelling, clip the cloud to zero).
  3. CONVOLVE -- overlay the cloud on the landscape (a tensor product): mass pools into the wells, is
     clipped at the peaks. No inference loop -- one instantaneous field operation.
  4. FLOW     -- read the modified field by gradient: the cloud flows to the deepest ACCESSIBLE well; that
     site is the action. Because it integrates the WHOLE cloud, a locked top choice doesn't stall the
     system -- the flow routes around it to the next well (multi-option resilience), and an all-peaks field
     yields no flow (stuck -> escalate), all from fast deterministic calculus.

This is exactly the discrete skill-check ([[skillcheck]]) made continuous: option confidence -> well depth,
a locked gate -> a peak, choose() -> the gradient flow. It also composes with the safety gates (a DENY is a
peak) and the dimensional lift (the field can live in the lifted, separable space).

    from python.scbe.probability_cloud import Site, resolve
    sites = [Site("login", 0.0, appeal=0.9, locked=True), Site("search", 1.0, appeal=0.7)]
    resolve(sites, belief=0.0, sigma=0.6)   # belief sits on the LOCKED login -> flows to search
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

_LOCKED = -1e9


@dataclass
class Site:
    """One option in the field: a position, an appeal (-> well depth), and whether it's a locked gate (peak)."""

    name: str
    pos: float  # position in the option/state space (1-D here; generalizes to n-D by vector distance)
    appeal: float = 0.5  # 0..1 desirability / confidence -> the depth of its gravity well
    locked: bool = False  # a gate peak: repels the cloud, clips its mass to zero


def gaussian(x: float, mu: float, sigma: float) -> float:
    s = max(sigma, 1e-6)
    return math.exp(-((x - mu) ** 2) / (2 * s * s))


def diffuse(sites: List[Site], belief: float, sigma: float) -> Dict[str, float]:
    """The input cloud: a Gaussian over the option positions, centered at the current belief (sigma =
    uncertainty). A single coordinate becomes a probability density across the options."""
    return {s.name: gaussian(s.pos, belief, sigma) for s in sites}


def topography(sites: List[Site]) -> Dict[str, float]:
    """The landscape potential per site: a well (its appeal) or a locked PEAK (repelling)."""
    return {s.name: (_LOCKED if s.locked else s.appeal) for s in sites}


def convolve(cloud: Dict[str, float], topo: Dict[str, float]) -> Dict[str, float]:
    """Overlay the cloud on the landscape: density = cloud_mass * exp(well_depth), clipped to 0 at peaks.
    Mass pools into the wells; locked peaks erase it. One field op -- no inference loop."""
    return {n: (0.0 if topo[n] <= _LOCKED / 2 else cloud[n] * math.exp(topo[n])) for n in cloud}


def flow(density: Dict[str, float]) -> Optional[str]:
    """Gradient flow: the cloud pools into the deepest ACCESSIBLE well -> that site is the action. No
    accessible mass anywhere -> None (the field is all peaks: stuck, escalate)."""
    if not density or max(density.values()) <= 0:
        return None
    return max(density, key=lambda k: density[k])


def resolve(sites: List[Site], belief: float, sigma: float = 0.6) -> Dict[str, object]:
    """Run the full multi-point field: diffuse -> topography -> convolve -> flow. Returns the chosen site
    (or None if the field is all peaks) plus the field for inspection."""
    cloud = diffuse(sites, belief, sigma)
    topo = topography(sites)
    density = convolve(cloud, topo)
    choice = flow(density)
    return {
        "choice": choice,
        "density": {n: round(v, 4) for n, v in density.items()},
        "stuck": choice is None,
    }


def from_skill_menu(options, belief_ref: Optional[str] = None) -> List[Site]:
    """Build the field from a skillcheck menu: each option becomes a Site at an evenly-spaced position, its
    confidence -> appeal, a locked gate -> a peak. So the continuous cloud runs over the SAME options the
    discrete skill-check shows -- the cloud is the skill-check's smooth substrate."""
    sites = []
    for i, o in enumerate(options):
        sites.append(
            Site(
                name="%s:%s" % (o.kind, o.ref or ""),
                pos=float(i),
                appeal=float(o.confidence),
                locked=(o.gate == "locked"),
            )
        )
    return sites
