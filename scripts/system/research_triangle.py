#!/usr/bin/env python3
"""
research_triangle.py

Three-source research ingestion pipeline:
  SAM.gov  ─┐
  DARPA    ─┼─► synthesis ─► training pairs (SFT + sections)
  arXiv    ─┘

Flow:
  1. Pull SAM.gov opportunities filtered to AI/governance/math keywords
     (DARPA BAAs/solicitations live on SAM.gov — same key, tag=DARPA)
  2. Pull arXiv abstracts matching the opportunity keywords
  3. Cross-reference: which papers are most relevant to which opportunities
  4. Emit training records:
       - SFT pairs:    {"text": "...", "instruction": "...", "response": "..."}
       - Section pairs: INTENT / MENTAL_MODEL / EXEC_TRACE / WHY_WORKS / SCBE_LAYER
         (compatible with BloodSplatterCallback section tags)

Usage:
  python scripts/system/research_triangle.py
  python scripts/system/research_triangle.py --max-opps 20 --max-papers 50
  python scripts/system/research_triangle.py --dry-run   # fetch only, no file write

Output:
  training-data/research_bridge/research_triangle_<date>.jsonl
  training-data/research_bridge/research_triangle_<date>_sections.jsonl

Environment:
  SAM_GOV_API_KEY   — required for SAM.gov + DARPA solicitations
  DATA_GOV_API_KEY  — optional, used for data.gov supplemental feeds
  (arXiv is free, no key needed)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple
from urllib.parse import quote_plus
from urllib.request import urlopen, Request
from urllib.error import URLError
import xml.etree.ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    from src.training.tongue_scorer import TongueScorer, get_layer_alignment
    _SCORER = TongueScorer()
    TONGUE_SCORING = True
except ImportError as _e:
    TONGUE_SCORING = False
    print(f"[WARN] tongue_scorer not available: {_e} — running without L2 orientation headers")

# Load env from connector oauth if running locally
_ENV_PATH = REPO_ROOT / "config" / "connector_oauth" / ".env.connector.oauth"
if _ENV_PATH.exists():
    for _line in _ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip("\"'"))


# =============================================================================
# QUERY KEYWORDS — what we're hunting across all three sources
# Mapped to SCBE concern areas
# =============================================================================

RESEARCH_QUERIES = [
    # Core architecture alignment — arXiv only (SAM.gov not relevant)
    {"label": "hyperbolic_geometry_safety",  "arxiv": "hyperbolic geometry neural network safety",      "sam": None},
    {"label": "agentic_governance",          "arxiv": "agentic AI governance multi-agent safety",       "sam": None},
    {"label": "formal_verification_ml",      "arxiv": "formal verification neural network verification", "sam": None},
    {"label": "adversarial_robustness",      "arxiv": "adversarial robustness certified defense",       "sam": None},
    {"label": "energy_based_training",       "arxiv": "energy based models training dynamics",          "sam": None},
    # DARPA-specific — fetch SAM.gov with DARPA org filter
    {"label": "darpa_math_agentic",          "arxiv": "multi-agent communication protocol formal",      "sam": "mathematical agentic communication",  "darpa": True},
    {"label": "darpa_trustworthy_ai",        "arxiv": "trustworthy AI interpretability alignment",      "sam": "trustworthy AI steerable",           "darpa": True},
    # General queries — arXiv only
    {"label": "composable_reasoning",        "arxiv": "compositional reasoning neural symbolic",        "sam": None},
    {"label": "curriculum_learning",         "arxiv": "curriculum learning training dynamics convergence", "sam": None},
    {"label": "geometric_deep_learning",     "arxiv": "geometric deep learning equivariant networks",   "sam": None},
]

# SAM.gov NAICS codes relevant to SCBE work
SAM_NAICS = ["541715", "541511", "541512", "541519"]  # R&D + software

# DARPA organization code on SAM.gov
DARPA_ORG_ID = "97AS"


# =============================================================================
# SAM.GOV CLIENT
# =============================================================================

class SamGovClient:
    BASE = "https://api.sam.gov/opportunities/v2/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch(
        self,
        keywords: str,
        days_back: int = 180,
        limit: int = 10,
        darpa_only: bool = False,
    ) -> List[dict]:
        now = datetime.now(timezone.utc)
        since = (now - timedelta(days=days_back)).strftime("%m/%d/%Y")
        until = now.strftime("%m/%d/%Y")
        params = {
            "api_key":    self.api_key,
            "q":          keywords,
            "postedFrom": since,
            "postedTo":   until,
            "limit":      str(limit),
            "offset":     "0",
            # R&D-relevant notice types only:
            # p=Presolicitation, k=Combined Synopsis, r=Sources Sought, s=Special Notice
            "ptype":      "p,k,r,s",
            # R&D and software NAICS codes
            "naicscode":  ",".join(SAM_NAICS),
        }
        if darpa_only:
            params["organizationId"] = DARPA_ORG_ID

        qs = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        url = f"{self.BASE}?{qs}"

        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode())
            return data.get("opportunitiesData", [])
        except URLError as e:
            print(f"  [SAM] fetch error for '{keywords}': {e}")
            return []

    @staticmethod
    def extract_fields(opp: dict) -> dict:
        return {
            "id":           opp.get("noticeId", ""),
            "title":        opp.get("title", ""),
            "agency":       opp.get("fullParentPathName", ""),
            "type":         opp.get("type", ""),
            "posted":       opp.get("postedDate", ""),
            "deadline":     opp.get("responseDeadLine", ""),
            "description":  (opp.get("description") or "")[:800],
            "sol_number":   opp.get("solicitationNumber", ""),
            "url":          opp.get("uiLink", ""),
        }


# =============================================================================
# ARXIV CLIENT
# =============================================================================

class ArxivClient:
    BASE = "https://export.arxiv.org/api/query"
    NS   = {"atom": "http://www.w3.org/2005/Atom"}

    def fetch(self, query: str, max_results: int = 10, days_back: int = 180) -> List[dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y%m%d")
        # arXiv search: title+abstract, restrict to cs.AI cs.LG cs.CR stat.ML
        full_q = f"({query}) AND (cat:cs.AI OR cat:cs.LG OR cat:cs.CR OR cat:stat.ML)"
        qs = f"search_query={quote_plus(full_q)}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
        url = f"{self.BASE}?{qs}"

        try:
            with urlopen(url, timeout=20) as r:
                raw = r.read()
            root = ET.fromstring(raw)
        except (URLError, ET.ParseError) as e:
            print(f"  [arXiv] fetch error for '{query}': {e}")
            return []

        def _clean(s: str) -> str:
            # Normalize whitespace and fix mojibake from mixed encoding
            s = s.replace("\n", " ").strip()
            repaired = s.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore").strip()
            return repaired or s

        papers = []
        for entry in root.findall("atom:entry", self.NS):
            title   = _clean(entry.findtext("atom:title",   "", self.NS) or "")
            summary = _clean(entry.findtext("atom:summary", "", self.NS) or "")
            arxiv_id = ""
            id_el = entry.find("atom:id", self.NS)
            if id_el is not None and id_el.text:
                arxiv_id = id_el.text.split("/abs/")[-1].strip()
            published = entry.findtext("atom:published", "", self.NS)
            authors = [
                a.findtext("atom:name", "", self.NS)
                for a in entry.findall("atom:author", self.NS)
            ]
            papers.append({
                "arxiv_id":  arxiv_id,
                "title":     title,
                "abstract":  summary[:600],
                "authors":   authors[:5],
                "published": published[:10],
                "url":       f"https://arxiv.org/abs/{arxiv_id}",
            })
            time.sleep(0.3)   # arXiv rate limit: 3 req/s

        return papers


# =============================================================================
# RELEVANCE SCORING — lightweight keyword overlap, no model needed
# =============================================================================

def keyword_overlap(text_a: str, text_b: str) -> float:
    """Normalized unigram overlap between two texts."""
    def tokens(t):
        return set(re.findall(r"\b[a-z]{4,}\b", t.lower()))
    a, b = tokens(text_a), tokens(text_b)
    if not a or not b:
        return 0.0
    return len(a & b) / math.sqrt(len(a) * len(b))


def score_paper_vs_opp(paper: dict, opp: dict) -> float:
    title_score    = keyword_overlap(paper["title"],    opp["title"])
    abstract_score = keyword_overlap(paper["abstract"], opp["description"])
    return round(0.4 * title_score + 0.6 * abstract_score, 4)


# =============================================================================
# TRAINING PAIR GENERATOR
# Emits two formats:
#   SFT pair:      instruction / response
#   Section pair:  INTENT / MENTAL_MODEL / EXEC_TRACE / WHY_WORKS / SCBE_LAYER
# =============================================================================

@dataclass
class ResearchMatch:
    query_label:  str
    opportunity:  dict
    paper:        dict
    score:        float


def _truncate(text: str, n: int = 400) -> str:
    return text[:n].rsplit(" ", 1)[0] + "…" if len(text) > n else text


def _orientation_header(text: str, query_label: str) -> str:
    """Build L2 orientation packet header from text + query label."""
    if not TONGUE_SCORING:
        return ""
    profile = _SCORER.score(text, domain_hint=query_label)
    return profile.to_header() + "\n\n"


def _orientation_meta(text: str, query_label: str, instruction: str = "", response: str = "") -> dict:
    """
    Return full orientation metadata for JSONL fields.

    Includes:
      - L2 orientation packet fields (from to_dict)
      - L0/L1 binary fields: bytes_b64, ss1_encoded (full bijection), ss1_tokens, tongue_profile vec, null_pattern vec
      - ss1_instruction / ss1_response: per-field SS1 encoding for training use
    """
    if not TONGUE_SCORING:
        return {}
    # Score combined text for the orientation packet
    profile = _SCORER.score(text, domain_hint=query_label)
    meta = profile.to_dict()
    # L0/L1 fields — encode the full combined text
    meta.update(profile.to_binary_fields(text))
    # Per-field SS1 encodings (lossless L1 layer for instruction and response separately)
    if instruction and _TONGUE_SCORING_SS1_AVAILABLE():
        meta["ss1_instruction"] = _encode_ss1(instruction, profile.primary)
    if response and _TONGUE_SCORING_SS1_AVAILABLE():
        meta["ss1_response"] = _encode_ss1(response, profile.primary)
    return meta


def _TONGUE_SCORING_SS1_AVAILABLE() -> bool:
    """Check if SS1 encoding is available (sixtongues package imported)."""
    try:
        from packages.sixtongues.sixtongues import encode_bytes  # noqa: F401
        return True
    except ImportError:
        return False


def _encode_ss1(text: str, primary_tongue: str) -> str:
    """Encode text as SS1 tongue tokens using the primary tongue's bijection."""
    try:
        from packages.sixtongues.sixtongues import encode_bytes
        raw = text.encode("utf-8", errors="replace")
        return encode_bytes(raw, tongue_code=primary_tongue.lower())
    except (ImportError, LookupError, UnicodeError, ValueError) as exc:
        print(f"[WARN] SS1 encoding unavailable for {primary_tongue}: {exc}", file=sys.stderr)
        return ""


def make_arxiv_sft_pair(paper: dict, query_label: str, query_keywords: str) -> dict:
    """SFT pair from arXiv paper — with layer-specific response and L2 orientation header."""
    layers = get_layer_alignment(query_label) if TONGUE_SCORING else [
        "L5 (hyperbolic distance d_H)", "L12 (harmonic wall)", "L13 (governance gate)"
    ]
    domain = query_label.replace("_", " ")

    instruction = (
        f"A research paper has been identified as relevant to SCBE-AETHERMOORE "
        f"({domain}):\n\n"
        f"PAPER: {paper['title']} ({paper['published']})\n"
        f"AUTHORS: {', '.join(paper['authors'][:3])}\n"
        f"ABSTRACT: {_truncate(paper['abstract'], 400)}\n\n"
        f"Explain the paper's core technical contribution and which SCBE-AETHERMOORE "
        f"pipeline layers it most directly validates or extends."
    )

    layer_bullets = "\n".join(f"• {l}" for l in layers)
    abstract_claim = _truncate(paper["abstract"], 300)
    response = (
        f"{paper['title']} advances the {domain} domain by showing that {abstract_claim}\n\n"
        f"The most directly relevant SCBE pipeline layers are:\n"
        f"{layer_bullets}\n\n"
        f"This work strengthens the SCBE argument because the exponential cost structure "
        f"d_H = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²))) makes adversarial behavior "
        f"computationally infeasible — a claim this paper's approach either directly "
        f"demonstrates or provides additional formal grounding for.\n\n"
        f"arXiv: {paper['url']}"
    )

    combined = f"{instruction} {response}"
    kw_score = keyword_overlap(paper["title"] + " " + paper["abstract"], query_keywords)
    header = _orientation_header(combined, query_label)
    orientation = _orientation_meta(combined, query_label, instruction=instruction, response=response)

    return {
        "instruction": header + instruction,
        "response":    response,
        "query_label": query_label,
        "opp_id":      "",
        "arxiv_id":    paper["arxiv_id"],
        "score":       kw_score,
        "source":      "research_triangle_arxiv",
        "stage":       7,
        **orientation,
    }


def make_arxiv_section_pair(paper: dict, query_label: str, query_keywords: str) -> dict:
    """Section pair from arXiv paper — layer-specific, with L2 orientation header."""
    kw_score = keyword_overlap(paper["title"] + " " + paper["abstract"], query_keywords)
    layers = get_layer_alignment(query_label) if TONGUE_SCORING else [
        "L5 (d_H)", "L12 (harmonic wall)", "L13 (governance gate)"
    ]
    layer_list = " | ".join(layers)
    domain = query_label.replace("_", " ")

    # Pick the most specific axiom tie-in per layer set
    axiom_map = {
        "hyperbolic_geometry_safety":  "Symmetry (A4) — gauge invariance across tongue dimensions",
        "agentic_governance":          "Composition (A5) — pipeline integrity across multi-agent coordination",
        "formal_verification_ml":      "Unitarity (A1) — norm preservation through all transforms",
        "adversarial_robustness":      "Locality (A2) — spatial bounds confine adversarial drift",
        "energy_based_training":       "Causality (A3) — time-ordering of energy state transitions",
        "darpa_math_agentic":          "Composition (A5) — multi-tongue communication protocol integrity",
        "darpa_trustworthy_ai":        "Symmetry (A4) — interpretable bounded score H(d,pd) ∈ (0,1]",
        "composable_reasoning":        "Composition (A5) — composable pipeline from L1 context to L14 telemetry",
        "curriculum_learning":         "Causality (A3) — governance tier progression TRICKLE→BURST→ECHO",
        "geometric_deep_learning":     "Symmetry (A4) — equivariant phi-scaling across tongue dimensions",
    }
    axiom = axiom_map.get(query_label, "Symmetry (A4) — gauge invariance")

    body = (
        f"[INTENT]\n"
        f"Map research paper to SCBE pipeline layer — domain: {domain}.\n"
        f"Paper: {paper['title']} — {paper['published']}\n\n"

        f"[MENTAL_MODEL]\n"
        f"Core contribution: {_truncate(paper['abstract'], 280)}\n"
        f"Relevance score (keyword overlap): {kw_score:.3f}\n\n"

        f"[EXEC_TRACE]\n"
        f"Step 1: Identify the paper's primary technical claim from the abstract.\n"
        f"Step 2: Find the SCBE layer where this claim plugs in ({layer_list}).\n"
        f"Step 3: State which axiom the paper implicitly satisfies: {axiom}.\n"
        f"Step 4: Write one sentence on whether this strengthens or challenges SCBE.\n\n"

        f"[WHY_WORKS]\n"
        f"The Poincaré ball model makes adversarial drift exponentially costly: "
        f"distance grows as arcosh(1 + 2‖u-v‖²/…), not linearly. Any paper that "
        f"formalizes structure in this space — geometric, statistical, or governance — "
        f"directly validates the core SCBE claim. The harmonic wall H(d,pd) then "
        f"translates that distance into a bounded, auditable safety score.\n\n"

        f"[SCBE_LAYER]\n"
        f"Primary layers: {layer_list}\n"
        f"Axiom: {axiom}\n"
        f"Query: {query_label} | arXiv: {paper['arxiv_id']} | {paper['published']}\n"
        f"Authors: {', '.join(paper['authors'][:3])}\n"
    )

    orientation = _orientation_meta(body, query_label, instruction=body)
    header = _orientation_header(body, query_label)

    return {
        "text":        header + body,
        "query_label": query_label,
        "opp_id":      "",
        "arxiv_id":    paper["arxiv_id"],
        "score":       kw_score,
        "source":      "research_triangle_arxiv_sections",
        "stage":       7,
        **orientation,
    }


def make_sft_pair(match: ResearchMatch) -> dict:
    """Enriched SFT pair: SAM opportunity × arXiv paper, with layer routing + orientation."""
    opp   = match.opportunity
    paper = match.paper
    layers = get_layer_alignment(match.query_label) if TONGUE_SCORING else [
        "L5 (hyperbolic distance d_H)", "L12 (harmonic wall)", "L13 (governance gate)"
    ]
    layer_bullets = "\n".join(f"• {l}" for l in layers)

    instruction = (
        f"A government research opportunity has been matched to a relevant paper.\n\n"
        f"OPPORTUNITY: {opp['title']}\n"
        f"AGENCY: {opp['agency']}\n"
        f"SOLICITATION: {opp['sol_number']}\n\n"
        f"PAPER: {paper['title']} ({paper['published']})\n"
        f"AUTHORS: {', '.join(paper['authors'][:3])}\n"
        f"ABSTRACT: {_truncate(paper['abstract'], 300)}\n\n"
        f"Describe a technical approach using SCBE-AETHERMOORE that addresses both the "
        f"opportunity's requirements and the paper's findings."
    )
    response = (
        f"{paper['title']} demonstrates {_truncate(paper['abstract'], 200)}\n\n"
        f"This directly maps to the solicitation's requirements through SCBE's:\n"
        f"{layer_bullets}\n\n"
        f"Technical approach: apply the Poincaré ball hyperbolic geometry pipeline "
        f"(L4-L5) to embed the problem space, then score safety posture continuously "
        f"via H(d,pd) = 1/(1+d_H+2·pd) ∈ (0,1] (L12). The governance tier gate (L13) "
        f"then provides the auditable ALLOW/QUARANTINE/ESCALATE/DENY classification "
        f"the solicitation requires, with exponential cost scaling making adversarial "
        f"manipulation computationally infeasible.\n\n"
        f"Alignment score: {match.score:.3f} | arXiv: {paper['url']}"
    )

    combined = f"{instruction} {response}"
    header = _orientation_header(combined, match.query_label)
    orientation = _orientation_meta(combined, match.query_label, instruction=instruction, response=response)

    return {
        "instruction": header + instruction,
        "response":    response,
        "query_label": match.query_label,
        "opp_id":      opp["id"],
        "arxiv_id":    paper["arxiv_id"],
        "score":       match.score,
        "source":      "research_triangle",
        "stage":       7,
        **orientation,
    }


def make_section_pair(match: ResearchMatch) -> dict:
    """Section-tagged DARPA×arXiv pair — layer-specific, with L2 orientation header."""
    opp   = match.opportunity
    paper = match.paper
    layers = get_layer_alignment(match.query_label) if TONGUE_SCORING else [
        "L5 (d_H)", "L12 (harmonic wall)", "L13 (governance gate)"
    ]
    layer_list = " | ".join(layers)
    domain = match.query_label.replace("_", " ")

    body = (
        f"[INTENT]\n"
        f"Map DARPA opportunity to SCBE technical approach via aligned research.\n"
        f"Opportunity: {opp['title']} ({_truncate(opp['agency'], 60)})\n"
        f"Paper: {paper['title']} — {paper['published']}\n\n"

        f"[MENTAL_MODEL]\n"
        f"The opportunity's domain ({domain}) requires: {_truncate(opp['description'], 180)}\n"
        f"The paper demonstrates: {_truncate(paper['abstract'], 200)}\n"
        f"Alignment score: {match.score:.3f}\n\n"

        f"[EXEC_TRACE]\n"
        f"Step 1: Extract the solicitation's core technical requirement.\n"
        f"Step 2: Match to paper's technical contribution.\n"
        f"Step 3: Map the combined approach to SCBE layers: {layer_list}\n"
        f"Step 4: Identify the governance posture this solution provides (L13 tier).\n\n"

        f"[WHY_WORKS]\n"
        f"SCBE's hyperbolic geometry provides exponential cost scaling — adversarial "
        f"drift costs grow as arcosh(1 + 2‖u-v‖²/…), not linearly. This geometric "
        f"guarantee satisfies formal verifiability requirements without exhaustive "
        f"enumeration of attack vectors. The paper's approach plugs into this framework "
        f"at the identified layers, strengthening the total system claim.\n\n"

        f"[SCBE_LAYER]\n"
        f"Layers: {layer_list}\n"
        f"SAM ID: {opp['id']} | arXiv: {paper['arxiv_id']} | {paper['published']}\n"
        f"Query: {match.query_label} | Score: {match.score:.3f}\n"
        f"Authors: {', '.join(paper['authors'][:3])}\n"
    )

    orientation = _orientation_meta(body, match.query_label, instruction=body)
    header = _orientation_header(body, match.query_label)

    return {
        "text":        header + body,
        "query_label": match.query_label,
        "opp_id":      opp["id"],
        "arxiv_id":    paper["arxiv_id"],
        "score":       match.score,
        "source":      "research_triangle_sections",
        "stage":       7,
        **orientation,
    }


# =============================================================================
# MAIN PIPELINE
# =============================================================================

import math   # placed here to avoid top-level import before we know it's needed


def run(
    max_opps:    int  = 10,
    max_papers:  int  = 20,
    days_back:   int  = 180,
    min_score:   float = 0.02,
    darpa_only:  bool = False,
    dry_run:     bool = False,
) -> Tuple[List[dict], List[dict]]:

    sam_key = os.environ.get("SAM_GOV_API_KEY", "")
    if not sam_key:
        print("[WARN] SAM_GOV_API_KEY not set — skipping SAM.gov/DARPA fetch")

    sam    = SamGovClient(sam_key) if sam_key else None
    arxiv  = ArxivClient()

    sft_records:     List[dict] = []
    section_records: List[dict] = []
    sam_matches:     List[ResearchMatch] = []

    for q in RESEARCH_QUERIES:
        label       = q["label"]
        sam_kw      = q.get("sam")
        is_darpa    = q.get("darpa", False)
        print(f"\n[{label}]")

        # --- arXiv papers (primary for all queries) ---
        papers = arxiv.fetch(q["arxiv"], max_results=max_papers, days_back=days_back)
        print(f"  arXiv: {len(papers)} papers")

        # arXiv-only training pairs — filter out zero-score papers
        kept = 0
        for paper in papers:
            kw = keyword_overlap(paper["title"] + " " + paper["abstract"], q["arxiv"])
            if kw < min_score:
                continue   # skip papers with no keyword overlap — they're noise
            sft_records.append(make_arxiv_sft_pair(paper, label, q["arxiv"]))
            section_records.append(make_arxiv_section_pair(paper, label, q["arxiv"]))
            kept += 1
        if kept < len(papers):
            print(f"  Filtered: {len(papers) - kept} low-relevance papers (kept {kept})")

        # --- SAM.gov / DARPA opportunities (only for darpa-tagged queries) ---
        if sam and sam_kw and (is_darpa or darpa_only):
            raw_opps = sam.fetch(sam_kw, days_back=days_back, limit=max_opps, darpa_only=True)
            opps = [sam.extract_fields(o) for o in raw_opps]
            print(f"  DARPA: {len(opps)} opportunities")
            time.sleep(0.5)

            # Cross-reference DARPA opps with arXiv papers
            for opp in opps:
                for paper in papers:
                    score = score_paper_vs_opp(paper, opp)
                    if score >= min_score:
                        sam_matches.append(ResearchMatch(
                            query_label=label,
                            opportunity=opp,
                            paper=paper,
                            score=score,
                        ))
        elif sam_kw is None:
            print(f"  SAM:   skipped (arXiv-only query)")

    # Add enriched SAM×arXiv pairs (deduped)
    sam_matches.sort(key=lambda m: m.score, reverse=True)
    seen_pairs: set = set()
    for m in sam_matches:
        key = (m.opportunity["id"], m.paper["arxiv_id"])
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        sft_records.append(make_sft_pair(m))
        section_records.append(make_section_pair(m))

    print(f"\nTotal arXiv pairs:   {len([r for r in sft_records if r['source'] == 'research_triangle_arxiv'])}")
    print(f"Total DARPA matches: {len(sam_matches)}")
    print(f"Total SFT records:   {len(sft_records)}")
    print(f"Total section recs:  {len(section_records)}")

    if not dry_run:
        out_dir = REPO_ROOT / "training-data" / "research_bridge"
        out_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

        sft_path = out_dir / f"research_triangle_{date_str}.jsonl"
        sec_path = out_dir / f"research_triangle_{date_str}_sections.jsonl"

        sft_path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in sft_records),
            encoding="utf-8",
        )
        sec_path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in section_records),
            encoding="utf-8",
        )
        print(f"\nWrote: {sft_path}")
        print(f"Wrote: {sec_path}")

    return sft_records, section_records


def main():
    parser = argparse.ArgumentParser(description="Research triangle: SAM + DARPA + arXiv → training pairs")
    parser.add_argument("--max-opps",   type=int,   default=10,   help="Max SAM opportunities per query")
    parser.add_argument("--max-papers", type=int,   default=20,   help="Max arXiv papers per query")
    parser.add_argument("--days-back",  type=int,   default=180,  help="How far back to search (days)")
    parser.add_argument("--min-score",  type=float, default=0.02, help="Minimum relevance score to include")
    parser.add_argument("--darpa-only", action="store_true",       help="SAM.gov: DARPA opportunities only")
    parser.add_argument("--dry-run",    action="store_true",       help="Fetch and score but don't write files")
    args = parser.parse_args()

    sft, sections = run(
        max_opps=args.max_opps,
        max_papers=args.max_papers,
        days_back=args.days_back,
        min_score=args.min_score,
        darpa_only=args.darpa_only,
        dry_run=args.dry_run,
    )

    if sft:
        print(f"\n--- Top 3 by score ---")
        for r in sorted(sft, key=lambda x: x["score"], reverse=True)[:3]:
            src = r["source"].replace("research_triangle_", "")
            print(f"  [{r['query_label']}] score={r['score']:.3f}  arXiv:{r['arxiv_id']}  ({src})")


if __name__ == "__main__":
    main()
