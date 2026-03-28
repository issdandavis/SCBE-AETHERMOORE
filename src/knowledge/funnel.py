"""
Knowledge Funnel — All rivers flow to the basin.

Pulls from: Notion, arXiv, GitHub, web research, MIT OpenCourseWare, NSA/NIST,
            Semantic Scholar, Wikipedia, HuggingFace papers
Processes:  Antivirus membrane scan -> categorize -> tokenizer graph -> store
Pushes to:  Local intake, Dropbox backup, HuggingFace datasets

Architecture:
    Source -> Scraper -> AntiVirus Gate -> Basin Deposit -> TokenizerGraph -> HF Push

The 6D DNA blockchain memory:
    Each knowledge chunk gets a 6D coordinate from the Sacred Tongues tokenizer.
    Chunks link via semantic hypercords (edges weighted by tongue-distance).
    The graph IS the memory — traversal = recall, proximity = relevance.
"""

import os
import json
import hashlib
import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASIN_ROOT = Path("C:/Users/issda/SCBE-AETHERMOORE/training/intake")
BACKUP_ROOT = Path("C:/Users/issda/Dropbox/SCBE/knowledge")
HF_DATASET = "issdandavis/scbe-aethermoore-knowledge-base"
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# ---------------------------------------------------------------------------
# Knowledge Chunk — the atomic unit of the funnel
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeChunk:
    """A single piece of knowledge flowing through the funnel."""

    id: str
    source: str  # arxiv, notion, github, mit, nist, wikipedia, etc.
    category: str  # math, security, ai, physics, governance, lore, etc.
    title: str
    content: str
    url: str = ""
    timestamp: str = ""
    tongue_coords: list = field(
        default_factory=lambda: [0.0] * 6
    )  # 6D Sacred Tongue position
    trust_score: float = 0.5
    governance_zone: str = "YELLOW"  # GREEN/YELLOW/RED
    chain_hash: str = ""
    parent_hash: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.datetime.utcnow().isoformat()
        if not self.id:
            self.id = hashlib.sha256(
                f"{self.source}:{self.title}:{self.timestamp}".encode()
            ).hexdigest()[:16]
        if not self.chain_hash:
            self.chain_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = f"{self.parent_hash}:{self.id}:{self.content[:256]}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Source Registry — every knowledge river
# ---------------------------------------------------------------------------

KNOWLEDGE_SOURCES = {
    # Academic
    "arxiv": {
        "name": "arXiv",
        "base_url": "https://export.arxiv.org/api/query",
        "zone": "GREEN",
        "categories": ["cs.AI", "cs.CR", "cs.CL", "cs.LG", "math.DG", "quant-ph"],
        "rate_limit": 3,  # seconds between requests
    },
    "semantic_scholar": {
        "name": "Semantic Scholar",
        "base_url": "https://api.semanticscholar.org/graph/v1",
        "zone": "GREEN",
        "categories": ["ai-safety", "cryptography", "hyperbolic-geometry", "nlp"],
        "rate_limit": 1,
    },
    # Government / Standards
    "nist": {
        "name": "NIST",
        "base_url": "https://csrc.nist.gov",
        "zone": "GREEN",
        "categories": ["post-quantum", "cryptography", "standards"],
        "rate_limit": 5,
    },
    # Educational
    "mit_ocw": {
        "name": "MIT OpenCourseWare",
        "base_url": "https://ocw.mit.edu",
        "zone": "GREEN",
        "categories": ["mathematics", "computer-science", "physics"],
        "rate_limit": 5,
    },
    # Internal
    "notion": {
        "name": "Notion Workspace",
        "base_url": "https://api.notion.com/v1",
        "zone": "GREEN",
        "categories": ["scbe", "geoseed", "sacred-eggs", "governance", "lore"],
        "rate_limit": 0.3,
    },
    "github": {
        "name": "GitHub Repos",
        "base_url": "https://api.github.com",
        "zone": "GREEN",
        "categories": ["code", "docs", "issues", "discussions"],
        "rate_limit": 1,
    },
    "huggingface": {
        "name": "HuggingFace Hub",
        "base_url": "https://huggingface.co/api",
        "zone": "GREEN",
        "categories": ["papers", "models", "datasets"],
        "rate_limit": 1,
    },
    # Reference
    "wikipedia": {
        "name": "Wikipedia",
        "base_url": "https://en.wikipedia.org/api/rest_v1",
        "zone": "YELLOW",
        "categories": ["reference"],
        "rate_limit": 1,
    },
}


# ---------------------------------------------------------------------------
# Antivirus Gate — scan before deposit
# ---------------------------------------------------------------------------


class AntivirusGate:
    """
    Scans knowledge chunks before they enter the basin.
    Uses the same ALLOW/DENY/QUARANTINE model as the browser.
    """

    BLOCKED_PATTERNS = [
        "prompt injection",
        "ignore previous",
        "system prompt",
        "jailbreak",
        "DAN mode",
        "bypass safety",
    ]

    def scan(self, chunk: KnowledgeChunk) -> tuple[str, str]:
        """Returns (decision, reason)."""
        content_lower = chunk.content.lower()

        # Check for injection patterns
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in content_lower:
                return "DENY", f"Blocked pattern detected: {pattern}"

        # Check content length (too short = spam, too long = dump)
        if len(chunk.content) < 50:
            return "QUARANTINE", "Content too short — possible spam"
        if len(chunk.content) > 500_000:
            return "QUARANTINE", "Content too large — needs chunking"

        # Source zone check
        source_config = KNOWLEDGE_SOURCES.get(chunk.source, {})
        zone = source_config.get("zone", "RED")
        if zone == "RED":
            return "QUARANTINE", f"Unknown source: {chunk.source}"

        return "ALLOW", "Passed antivirus scan"


# ---------------------------------------------------------------------------
# Basin Deposit — where chunks land
# ---------------------------------------------------------------------------


class BasinDeposit:
    """Deposits knowledge chunks into the local basin and backup."""

    def __init__(self, basin_root: Path = BASIN_ROOT, backup_root: Path = BACKUP_ROOT):
        self.basin_root = basin_root
        self.backup_root = backup_root

    def deposit(self, chunk: KnowledgeChunk) -> str:
        """Write chunk to basin. Returns file path."""
        # Local deposit
        deposit_dir = self.basin_root / chunk.source / chunk.category
        deposit_dir.mkdir(parents=True, exist_ok=True)
        filepath = deposit_dir / f"{chunk.id}.json"
        filepath.write_text(json.dumps(chunk.to_dict(), indent=2))

        # Backup to Dropbox
        backup_dir = self.backup_root / chunk.source / chunk.category
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{chunk.id}.json"
        backup_path.write_text(json.dumps(chunk.to_dict(), indent=2))

        return str(filepath)


# ---------------------------------------------------------------------------
# Knowledge Funnel — the main pipeline
# ---------------------------------------------------------------------------


class KnowledgeFunnel:
    """
    Main pipeline: Source -> AntiVirus -> Basin -> TokenizerGraph -> HF

    All rivers flow here. The funnel:
    1. Accepts chunks from any scraper
    2. Scans with antivirus membrane
    3. Deposits to basin (local + Dropbox backup)
    4. Chains into 6D memory blockchain
    5. Pushes to HuggingFace dataset on schedule
    """

    def __init__(self):
        self.antivirus = AntivirusGate()
        self.basin = BasinDeposit()
        self.chain: list[KnowledgeChunk] = []
        self.stats = {
            "total": 0,
            "allowed": 0,
            "quarantined": 0,
            "denied": 0,
        }

    def ingest(self, chunk: KnowledgeChunk) -> dict:
        """Process a single chunk through the funnel."""
        self.stats["total"] += 1

        # 1. Antivirus scan
        decision, reason = self.antivirus.scan(chunk)
        chunk.governance_zone = (
            "GREEN"
            if decision == "ALLOW"
            else "RED" if decision == "DENY" else "YELLOW"
        )

        if decision == "DENY":
            self.stats["denied"] += 1
            return {"decision": decision, "reason": reason, "chunk_id": chunk.id}

        # 2. Chain hash (link to previous)
        if self.chain:
            chunk.parent_hash = self.chain[-1].chain_hash
            chunk.chain_hash = chunk._compute_hash()

        # 3. Deposit to basin
        if decision == "ALLOW":
            self.stats["allowed"] += 1
            path = self.basin.deposit(chunk)
            self.chain.append(chunk)
            return {
                "decision": decision,
                "reason": reason,
                "chunk_id": chunk.id,
                "path": path,
            }
        else:
            self.stats["quarantined"] += 1
            # Quarantined chunks go to a separate area
            chunk.category = f"quarantine/{chunk.category}"
            path = self.basin.deposit(chunk)
            return {
                "decision": decision,
                "reason": reason,
                "chunk_id": chunk.id,
                "path": path,
            }

    def ingest_batch(self, chunks: list[KnowledgeChunk]) -> list[dict]:
        """Process multiple chunks."""
        return [self.ingest(c) for c in chunks]

    def get_stats(self) -> dict:
        return {**self.stats, "chain_length": len(self.chain)}

    def export_chain_manifest(self, output_path: Optional[str] = None) -> str:
        """Export the chain as a JSONL manifest for HuggingFace."""
        if not output_path:
            output_path = str(BASIN_ROOT / "chain_manifest.jsonl")

        with open(output_path, "w") as f:
            for chunk in self.chain:
                f.write(json.dumps(chunk.to_dict()) + "\n")

        return output_path
