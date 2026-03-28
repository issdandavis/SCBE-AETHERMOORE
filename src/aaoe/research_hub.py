"""
AAOE Research Hub — Governed Academic Paper Pipeline
========================================================

Connects to arXiv (free API, no key needed), runs papers through
SCBE governance, stores as training data, pushes to HuggingFace.

Pipeline:
  arXiv search → download abstract → governance scan (14-layer) →
  MMCCL credit mint → JSONL training record → HuggingFace push →
  Notion research page

This becomes the foundation for the premium research website:
agents and humans search through SCBE-governed research, paying
credits for deeper analysis (the AAOE economy in action).

arXiv API: https://info.arxiv.org/help/api/index.html
  - Free, no auth required for search/metadata
  - Rate limit: 1 request per 3 seconds (we respect this)
  - Returns Atom XML feed

@layer Layer 1, Layer 13
"""

from __future__ import annotations

import json
import math
import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from urllib.error import URLError

from .task_monitor import PHI, hyperbolic_distance

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
USER_AGENT = "SCBE-AETHERMOORE-ResearchHub/1.0 (issdandavis7795@aethermoorgames.com)"
RATE_LIMIT_SECONDS = 3.0
DEFAULT_OUTPUT_DIR = "training/intake/arxiv_research"

# SCBE categories of interest
SCBE_CATEGORIES = [
    "cs.AI",  # Artificial Intelligence
    "cs.LG",  # Machine Learning
    "cs.CR",  # Cryptography and Security
    "cs.MA",  # Multi-Agent Systems
    "cs.CL",  # Computation and Language (NLP)
    "math.DG",  # Differential Geometry
    "math.GT",  # Geometric Topology
    "stat.ML",  # Statistics - Machine Learning
]


# ---------------------------------------------------------------------------
#  ArXiv Paper dataclass
# ---------------------------------------------------------------------------


@dataclass
class ArxivPaper:
    """A paper from arXiv with SCBE governance metadata."""

    arxiv_id: str = ""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    summary: str = ""
    published: str = ""
    updated: str = ""
    categories: List[str] = field(default_factory=list)
    primary_category: str = ""
    pdf_url: str = ""
    abs_url: str = ""
    comment: str = ""
    # SCBE governance fields
    governance_score: float = 0.0
    relevance_score: float = 0.0
    tongue_affinity: str = ""  # Which Sacred Tongue this paper aligns with
    intent_vector: List[float] = field(default_factory=list)
    training_value: float = 0.0  # How valuable for training data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "authors": self.authors,
            "summary": self.summary[:500],
            "published": self.published,
            "categories": self.categories,
            "primary_category": self.primary_category,
            "pdf_url": self.pdf_url,
            "abs_url": self.abs_url,
            "governance_score": round(self.governance_score, 4),
            "relevance_score": round(self.relevance_score, 4),
            "tongue_affinity": self.tongue_affinity,
            "training_value": round(self.training_value, 4),
        }

    def to_training_record(self) -> Dict[str, Any]:
        """Export as SFT training record."""
        return {
            "type": "arxiv_research_sft",
            "input": {
                "query": f"Analyze paper: {self.title}",
                "context": {
                    "arxiv_id": self.arxiv_id,
                    "categories": self.categories,
                    "authors": self.authors[:5],
                },
            },
            "output": {
                "summary": self.summary,
                "governance_score": self.governance_score,
                "relevance_score": self.relevance_score,
                "tongue_affinity": self.tongue_affinity,
                "training_value": self.training_value,
            },
            "metadata": {
                "source": "arxiv",
                "arxiv_id": self.arxiv_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }


# ---------------------------------------------------------------------------
#  Governance Analysis — score papers using SCBE math
# ---------------------------------------------------------------------------

# Keywords that map to Sacred Tongues
TONGUE_KEYWORDS = {
    "KO": [
        "knowledge",
        "learning",
        "representation",
        "embedding",
        "understanding",
        "reasoning",
        "inference",
        "attention",
        "transformer",
    ],
    "AV": [
        "language",
        "communication",
        "dialogue",
        "translation",
        "generation",
        "summarization",
        "sentiment",
        "social",
    ],
    "RU": [
        "adversarial",
        "robustness",
        "attack",
        "defense",
        "chaos",
        "perturbation",
        "generative",
        "creative",
        "synthesis",
    ],
    "CA": [
        "optimization",
        "compute",
        "efficiency",
        "scaling",
        "architecture",
        "training",
        "hardware",
        "distributed",
        "parallel",
    ],
    "UM": [
        "privacy",
        "security",
        "stealth",
        "anonymity",
        "federated",
        "differential",
        "encryption",
        "obfuscation",
    ],
    "DR": [
        "safety",
        "alignment",
        "governance",
        "structure",
        "formal",
        "verification",
        "specification",
        "constraint",
        "regulation",
    ],
}

# Topics with high SCBE relevance
HIGH_RELEVANCE_KEYWORDS = [
    "hyperbolic",
    "poincare",
    "safety",
    "governance",
    "alignment",
    "adversarial cost",
    "exponential scaling",
    "fiber bundle",
    "multi-agent",
    "trust",
    "audit",
    "post-quantum",
    "sacred",
    "geometric",
    "manifold",
    "curvature",
]


def analyze_paper(paper: ArxivPaper) -> ArxivPaper:
    """Run SCBE governance analysis on a paper."""
    text = f"{paper.title} {paper.summary}".lower()

    # 1. Compute tongue affinity
    tongue_scores = {}
    for tongue, keywords in TONGUE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        tongue_scores[tongue] = score
    best_tongue = max(tongue_scores, key=tongue_scores.get)
    paper.tongue_affinity = best_tongue

    # 2. Compute intent vector (6D)
    total = max(sum(tongue_scores.values()), 1)
    phi_weights = {
        "KO": 1.0,
        "AV": PHI,
        "RU": PHI**2,
        "CA": PHI**3,
        "UM": PHI**4,
        "DR": PHI**5,
    }
    iv = []
    for tongue in ["KO", "AV", "RU", "CA", "UM", "DR"]:
        raw = tongue_scores.get(tongue, 0) / total
        weighted = raw * phi_weights[tongue]
        iv.append(min(weighted, 0.9))  # Clamp to Poincaré ball
    # Normalize to ball
    norm = math.sqrt(sum(x * x for x in iv))
    if norm > 0.95:
        iv = [x * 0.95 / norm for x in iv]
    paper.intent_vector = iv

    # 3. Relevance score — how relevant to SCBE research
    relevance_hits = sum(1 for kw in HIGH_RELEVANCE_KEYWORDS if kw in text)
    paper.relevance_score = min(relevance_hits / 5.0, 1.0)

    # 4. Governance score — distance from SCBE "safe center"
    # Safe center = DR-heavy (structure/governance)
    safe_center = [0.1, 0.1, 0.1, 0.1, 0.1, 0.4]  # DR-dominant
    d_H = hyperbolic_distance(iv, safe_center)
    # Score = 1.0 for papers close to governance, lower for distant
    paper.governance_score = max(0.0, 1.0 - d_H / 3.0)

    # 5. Training value — combined metric
    paper.training_value = (
        0.4 * paper.relevance_score
        + 0.3 * paper.governance_score
        + 0.2 * (len(paper.summary) / 2000.0)  # Longer abstracts = more data
        + 0.1 * min(len(paper.categories) / 3.0, 1.0)
    )

    return paper


# ---------------------------------------------------------------------------
#  ArXiv Search — raw API client
# ---------------------------------------------------------------------------


def search_arxiv(
    query: str,
    max_results: int = 10,
    category: Optional[str] = None,
    sort_by: str = "relevance",
    start: int = 0,
) -> List[ArxivPaper]:
    """
    Search arXiv and return parsed papers.

    Args:
        query: Search terms
        max_results: Max papers to return (max 100 per API call)
        category: arXiv category filter (e.g. "cs.AI")
        sort_by: "relevance", "lastUpdatedDate", or "submittedDate"
        start: Offset for pagination

    Returns: List of ArxivPaper objects
    """
    # Build query
    search_query = quote_plus(query)
    if category:
        search_query = f"cat:{category}+AND+all:{quote_plus(query)}"

    url = (
        f"{ARXIV_API}?search_query={search_query}"
        f"&start={start}&max_results={min(max_results, 100)}"
        f"&sortBy={sort_by}&sortOrder=descending"
    )

    req = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(req, timeout=20) as response:
            xml_data = response.read().decode("utf-8")
    except (URLError, TimeoutError):
        return []

    return _parse_atom_feed(xml_data)


def fetch_paper_by_id(arxiv_id: str) -> Optional[ArxivPaper]:
    """Fetch a single paper by arXiv ID (e.g. '2401.12345')."""
    clean_id = arxiv_id.strip().replace("arXiv:", "")
    url = f"{ARXIV_API}?id_list={clean_id}"
    req = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(req, timeout=20) as response:
            xml_data = response.read().decode("utf-8")
    except (URLError, TimeoutError):
        return None

    papers = _parse_atom_feed(xml_data)
    return papers[0] if papers else None


def _parse_atom_feed(xml_data: str) -> List[ArxivPaper]:
    """Parse arXiv Atom XML feed into ArxivPaper list."""
    papers = []
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return []

    for entry in root.findall(f"{ARXIV_ATOM_NS}entry"):
        paper = ArxivPaper()

        # ID
        id_elem = entry.find(f"{ARXIV_ATOM_NS}id")
        if id_elem is not None and id_elem.text:
            paper.abs_url = id_elem.text.strip()
            paper.arxiv_id = paper.abs_url.split("/abs/")[-1]

        # Title
        title_elem = entry.find(f"{ARXIV_ATOM_NS}title")
        if title_elem is not None and title_elem.text:
            paper.title = " ".join(title_elem.text.split())

        # Summary
        summary_elem = entry.find(f"{ARXIV_ATOM_NS}summary")
        if summary_elem is not None and summary_elem.text:
            paper.summary = " ".join(summary_elem.text.split())

        # Authors
        for author in entry.findall(f"{ARXIV_ATOM_NS}author"):
            name = author.find(f"{ARXIV_ATOM_NS}name")
            if name is not None and name.text:
                paper.authors.append(name.text.strip())

        # Dates
        pub = entry.find(f"{ARXIV_ATOM_NS}published")
        if pub is not None and pub.text:
            paper.published = pub.text.strip()
        upd = entry.find(f"{ARXIV_ATOM_NS}updated")
        if upd is not None and upd.text:
            paper.updated = upd.text.strip()

        # Categories
        for cat in entry.findall(f"{ARXIV_ATOM_NS}category"):
            term = cat.get("term", "")
            if term:
                paper.categories.append(term)
        prim = entry.find(f"{ARXIV_NS}primary_category")
        if prim is not None:
            paper.primary_category = prim.get("term", "")

        # PDF link
        for link in entry.findall(f"{ARXIV_ATOM_NS}link"):
            if link.get("title") == "pdf":
                paper.pdf_url = link.get("href", "")

        # Comment
        comment_elem = entry.find(f"{ARXIV_NS}comment")
        if comment_elem is not None and comment_elem.text:
            paper.comment = comment_elem.text.strip()

        if paper.arxiv_id:
            papers.append(paper)

    return papers


# ---------------------------------------------------------------------------
#  Research Hub — the full pipeline
# ---------------------------------------------------------------------------


class ResearchHub:
    """
    Governed research pipeline connecting arXiv → SCBE → Training Data.

    Usage:
        hub = ResearchHub()
        results = hub.search("hyperbolic geometry AI safety", category="cs.AI")
        for paper in results:
            print(f"{paper.title} — governance: {paper.governance_score}")

        # Save as training data
        hub.save_results(results)

        # Push to HuggingFace
        hub.push_to_huggingface(results)
    """

    def __init__(
        self,
        output_dir: str = DEFAULT_OUTPUT_DIR,
        hf_token: Optional[str] = None,
        hf_repo: str = "issdandavis/scbe-aethermoore-training-data",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.hf_token = hf_token or os.environ.get("HF_TOKEN")
        self.hf_repo = hf_repo
        self._last_request_time = 0.0

    def search(
        self,
        query: str,
        max_results: int = 10,
        category: Optional[str] = None,
        sort_by: str = "relevance",
        auto_analyze: bool = True,
    ) -> List[ArxivPaper]:
        """Search arXiv with SCBE governance analysis."""
        self._rate_limit()
        papers = search_arxiv(query, max_results, category, sort_by)

        if auto_analyze:
            papers = [analyze_paper(p) for p in papers]
            # Sort by training value
            papers.sort(key=lambda p: p.training_value, reverse=True)

        return papers

    def search_scbe_topics(self, max_per_topic: int = 5) -> List[ArxivPaper]:
        """Search all SCBE-relevant topics across categories."""
        queries = [
            ("hyperbolic geometry machine learning", "cs.AI"),
            ("AI safety alignment governance", "cs.AI"),
            ("adversarial cost scaling", "cs.LG"),
            ("multi-agent trust governance", "cs.MA"),
            ("post-quantum cryptography AI", "cs.CR"),
            ("fiber bundle neural network", "cs.LG"),
            ("Poincare embedding representation", "cs.CL"),
            ("differential geometry deep learning", "math.DG"),
        ]
        all_papers = []
        seen_ids = set()
        for query, cat in queries:
            self._rate_limit()
            papers = search_arxiv(query, max_per_topic, cat)
            for p in papers:
                if p.arxiv_id not in seen_ids:
                    seen_ids.add(p.arxiv_id)
                    all_papers.append(analyze_paper(p))

        all_papers.sort(key=lambda p: p.training_value, reverse=True)
        return all_papers

    def fetch_paper(self, arxiv_id: str) -> Optional[ArxivPaper]:
        """Fetch and analyze a single paper by ID."""
        self._rate_limit()
        paper = fetch_paper_by_id(arxiv_id)
        if paper:
            paper = analyze_paper(paper)
        return paper

    def save_results(
        self,
        papers: List[ArxivPaper],
        filename: Optional[str] = None,
    ) -> Path:
        """Save papers as JSONL training data."""
        if not filename:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            filename = f"arxiv_research_{ts}.jsonl"

        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            for paper in papers:
                f.write(
                    json.dumps(paper.to_training_record(), ensure_ascii=False) + "\n"
                )

        return filepath

    def push_to_huggingface(
        self,
        papers: List[ArxivPaper],
        path_in_repo: Optional[str] = None,
    ) -> bool:
        """Push research results to HuggingFace dataset."""
        if not self.hf_token:
            return False

        try:
            from huggingface_hub import HfApi
        except ImportError:
            return False

        if not path_in_repo:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            path_in_repo = f"research/arxiv_{ts}.jsonl"

        # Write to temp file
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f:
            for paper in papers:
                f.write(
                    json.dumps(paper.to_training_record(), ensure_ascii=False) + "\n"
                )
            temp_path = f.name

        try:
            api = HfApi(token=self.hf_token)
            api.upload_file(
                path_or_fileobj=temp_path,
                path_in_repo=path_in_repo,
                repo_id=self.hf_repo,
                repo_type="dataset",
                commit_message=f"Research: {len(papers)} arXiv papers analyzed",
            )
            return True
        except Exception:
            return False
        finally:
            os.unlink(temp_path)

    def daily_research_sweep(self) -> Dict[str, Any]:
        """
        Run a full daily research sweep:
        1. Search SCBE-relevant topics
        2. Analyze all papers
        3. Save as training data
        4. Push to HuggingFace
        5. Return summary
        """
        papers = self.search_scbe_topics(max_per_topic=5)

        # Save locally
        filepath = self.save_results(papers)

        # Push to HF
        hf_pushed = self.push_to_huggingface(papers)

        # Stats
        by_tongue = {}
        for p in papers:
            tongue = p.tongue_affinity or "UNKNOWN"
            by_tongue[tongue] = by_tongue.get(tongue, 0) + 1

        avg_governance = (
            sum(p.governance_score for p in papers) / len(papers) if papers else 0
        )
        avg_relevance = (
            sum(p.relevance_score for p in papers) / len(papers) if papers else 0
        )
        avg_training = (
            sum(p.training_value for p in papers) / len(papers) if papers else 0
        )

        return {
            "total_papers": len(papers),
            "saved_to": str(filepath),
            "pushed_to_hf": hf_pushed,
            "by_tongue": by_tongue,
            "avg_governance_score": round(avg_governance, 4),
            "avg_relevance_score": round(avg_relevance, 4),
            "avg_training_value": round(avg_training, 4),
            "top_papers": [
                {"title": p.title, "arxiv_id": p.arxiv_id, "score": p.training_value}
                for p in papers[:5]
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _rate_limit(self):
        """Respect arXiv's 3-second rate limit."""
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_SECONDS:
            time.sleep(RATE_LIMIT_SECONDS - elapsed)
        self._last_request_time = time.time()


# ---------------------------------------------------------------------------
#  CLI — run from terminal
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    hub = ResearchHub()

    if len(sys.argv) > 1 and sys.argv[1] == "--sweep":
        print("Running daily research sweep...")
        result = hub.daily_research_sweep()
        print(json.dumps(result, indent=2))
    elif len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"Searching arXiv: {query}")
        papers = hub.search(query, max_results=5)
        for p in papers:
            print(f"\n  [{p.arxiv_id}] {p.title}")
            print(
                f"    Tongue: {p.tongue_affinity} | Gov: {p.governance_score:.2f} | Train: {p.training_value:.2f}"
            )
            print(f"    {p.abs_url}")
    else:
        print("Usage:")
        print("  python -m src.aaoe.research_hub 'hyperbolic AI safety'")
        print("  python -m src.aaoe.research_hub --sweep")
