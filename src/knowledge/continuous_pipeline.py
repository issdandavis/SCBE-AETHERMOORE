"""
Continuous Knowledge Pipeline — never-repeating, rate-limited, auto-uploading.

Runs on a loop:
  1. Check dedup registry (skip anything already scraped)
  2. Pull from all sources at safe rate limits
  3. Funnel through antivirus + 6D tongue coords
  4. Deposit to basin + build Fibonacci sphere grid
  5. Analyze connections from multiple angles
  6. Push datasets to HuggingFace by category
  7. Sleep, repeat

Usage:
    python -m src.knowledge.continuous_pipeline              # One cycle
    python -m src.knowledge.continuous_pipeline --daemon      # Loop forever
    python -m src.knowledge.continuous_pipeline --push-hf     # Push to HF after
    python -m src.knowledge.continuous_pipeline --export-web  # Export for Firebase
"""

import os
import sys
import json
import math
import time
import hashlib
import argparse
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.knowledge.funnel import KnowledgeFunnel, KnowledgeChunk, BASIN_ROOT
from src.knowledge.tokenizer_graph.memory_chain import (
    TokenizerGraph,
    TONGUE_WEIGHTS,
    TONGUE_NAMES,
    PHI,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEDUP_REGISTRY = BASIN_ROOT / "dedup_registry.json"
SPHERE_GRID_PATH = BASIN_ROOT / "fibonacci_sphere_grid.json"
CYCLE_INTERVAL = 330  # 5.5 minutes between cycles (S2 rate = 100/5min)
MAX_REQUESTS_PER_CYCLE = 85  # stay under 89/5min for S2, safe margin

EXPORT_ROOT = PROJECT_ROOT / "public" / "data"
HF_DATASET = "issdandavis/scbe-aethermoore-knowledge-base"


# ---------------------------------------------------------------------------
# Dedup Registry — never scrape the same thing twice
# ---------------------------------------------------------------------------


class DedupRegistry:
    """Tracks every query+source combo we've already run."""

    def __init__(self, path: Path = DEDUP_REGISTRY):
        self.path = path
        self.seen: dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            self.seen = json.loads(self.path.read_text())

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.seen, indent=2))

    def key(self, source: str, query: str) -> str:
        return hashlib.sha256(f"{source}:{query}".encode()).hexdigest()[:16]

    def is_done(self, source: str, query: str) -> bool:
        return self.key(source, query) in self.seen

    def mark_done(self, source: str, query: str, count: int):
        k = self.key(source, query)
        self.seen[k] = {
            "source": source,
            "query": query,
            "count": count,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        }
        self._save()

    def total_scraped(self) -> int:
        return sum(v.get("count", 0) for v in self.seen.values())

    def sources_done(self) -> dict[str, int]:
        counts = {}
        for v in self.seen.values():
            src = v.get("source", "unknown")
            counts[src] = counts.get(src, 0) + v.get("count", 0)
        return counts


# ---------------------------------------------------------------------------
# Fibonacci Sphere Grid — 6D node placement
# ---------------------------------------------------------------------------


class FibonacciSphereGrid:
    """
    6D Fibonacci sphere grid. Each knowledge chunk gets placed on a point
    on a 6D hypersphere using a Fibonacci-like distribution, then linked
    to nearby nodes. Each surface node leads to a depth tree of related content.

    Like Fibonacci on a 2D sphere gives even coverage, we extend to 6D
    using the Sacred Tongue coordinates as the basis dimensions.
    """

    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.depth_trees: dict[str, list] = {}  # node_id -> [child_ids]
        self.n = 0

    def fibonacci_6d_point(self, index: int) -> list[float]:
        """Generate the i-th point on a 6D Fibonacci hypersphere."""
        # Golden angle generalized to 6D
        angles = []
        for dim in range(5):  # 5 angles for 6D sphere
            angle = 2 * math.pi * index * (PHI ** (dim + 1))
            angles.append(angle % (2 * math.pi))

        # Convert to 6D Cartesian on unit sphere
        coords = [0.0] * 6
        r = 0.95  # Stay inside Poincare ball

        # Nested sine/cosine for hyperspherical coordinates
        coords[0] = r * math.cos(angles[0])
        coords[1] = r * math.sin(angles[0]) * math.cos(angles[1])
        coords[2] = r * math.sin(angles[0]) * math.sin(angles[1]) * math.cos(angles[2])
        coords[3] = r * math.sin(angles[0]) * math.sin(angles[1]) * math.sin(angles[2]) * math.cos(angles[3])
        coords[4] = (
            r
            * math.sin(angles[0])
            * math.sin(angles[1])
            * math.sin(angles[2])
            * math.sin(angles[3])
            * math.cos(angles[4])
        )
        coords[5] = (
            r
            * math.sin(angles[0])
            * math.sin(angles[1])
            * math.sin(angles[2])
            * math.sin(angles[3])
            * math.sin(angles[4])
        )

        return coords

    def add_node(
        self,
        chunk_id: str,
        title: str,
        category: str,
        tongue_coords: list[float],
        content_hash: str,
        depth: int = 0,
        parent_id: str = "",
    ) -> dict:
        """Place a knowledge chunk on the grid."""
        fib_coords = self.fibonacci_6d_point(self.n)

        # Blend Fibonacci placement with tongue coords (content-aware placement)
        blended = [0.6 * f + 0.4 * t for f, t in zip(fib_coords, tongue_coords)]

        # Normalize back to ball
        norm = math.sqrt(sum(c**2 for c in blended))
        if norm > 0:
            blended = [c / norm * 0.95 for c in blended]

        node = {
            "id": chunk_id,
            "index": self.n,
            "title": title,
            "category": category,
            "coords_6d": blended,
            "fib_coords": fib_coords,
            "tongue_coords": tongue_coords,
            "content_hash": content_hash,
            "depth": depth,
            "parent_id": parent_id,
            "children": [],
            "connections": [],
        }

        self.nodes[chunk_id] = node
        self.n += 1

        # Link to parent if exists
        if parent_id and parent_id in self.nodes:
            self.nodes[parent_id]["children"].append(chunk_id)
            if parent_id not in self.depth_trees:
                self.depth_trees[parent_id] = []
            self.depth_trees[parent_id].append(chunk_id)

        # Auto-connect to nearby nodes
        self._connect_nearby(chunk_id, max_connections=5)

        return node

    def _connect_nearby(self, node_id: str, max_connections: int = 5):
        """Find and link to nearest nodes on the grid."""
        node = self.nodes[node_id]
        distances = []

        for other_id, other in self.nodes.items():
            if other_id == node_id:
                continue
            dist = self._distance(node["coords_6d"], other["coords_6d"])
            distances.append((other_id, dist))

        distances.sort(key=lambda x: x[1])
        for target_id, dist in distances[:max_connections]:
            if dist < 0.5:  # Only connect if reasonably close
                node["connections"].append(
                    {
                        "target": target_id,
                        "distance": round(dist, 4),
                        "tongue": self._dominant_dimension(node["coords_6d"], self.nodes[target_id]["coords_6d"]),
                    }
                )

    @staticmethod
    def _distance(a: list, b: list) -> float:
        return math.sqrt(sum((ai - bi) ** 2 * TONGUE_WEIGHTS[i] for i, (ai, bi) in enumerate(zip(a, b)))) / sum(
            TONGUE_WEIGHTS
        )

    @staticmethod
    def _dominant_dimension(a: list, b: list) -> str:
        diffs = [abs(ai - bi) * TONGUE_WEIGHTS[i] for i, (ai, bi) in enumerate(zip(a, b))]
        min_idx = diffs.index(min(diffs))
        return TONGUE_NAMES[min_idx]

    def export(self, path: str = None) -> str:
        if path is None:
            path = str(SPHERE_GRID_PATH)
        data = {
            "total_nodes": len(self.nodes),
            "dimensions": 6,
            "tongue_names": TONGUE_NAMES,
            "tongue_weights": TONGUE_WEIGHTS,
            "nodes": self.nodes,
            "depth_trees": self.depth_trees,
            "stats": {
                "categories": {},
                "max_depth": 0,
                "total_connections": 0,
            },
        }

        # Compute stats
        for node in self.nodes.values():
            cat = node["category"]
            data["stats"]["categories"][cat] = data["stats"]["categories"].get(cat, 0) + 1
            data["stats"]["max_depth"] = max(data["stats"]["max_depth"], node["depth"])
            data["stats"]["total_connections"] += len(node["connections"])

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=2))
        return path


# ---------------------------------------------------------------------------
# Multi-Angle Analyzer — find connections from different perspectives
# ---------------------------------------------------------------------------


class MultiAngleAnalyzer:
    """Analyze the knowledge graph from multiple perspectives to find connections."""

    ANGLES = [
        ("security_vs_math", ["security", "math", "quantum"], "Where does security meet mathematics?"),
        (
            "ai_vs_governance",
            ["ai", "governance", "swarm"],
            "How does AI governance intersect with swarm intelligence?",
        ),
        ("nlp_vs_geometry", ["nlp", "geometry", "math"], "Language models and geometric embeddings"),
        ("lore_vs_research", ["lore", "research", "tongues"], "Narrative patterns in research structures"),
        ("cross_domain", None, "Highest-connected nodes across all categories"),
    ]

    def analyze(self, grid: FibonacciSphereGrid) -> list[dict]:
        """Run all analysis angles, return connection reports."""
        reports = []

        for angle_name, categories, description in self.ANGLES:
            if categories:
                relevant = {nid: n for nid, n in grid.nodes.items() if n["category"] in categories}
            else:
                # Cross-domain: top connected nodes
                relevant = dict(
                    sorted(
                        grid.nodes.items(),
                        key=lambda x: len(x[1]["connections"]),
                        reverse=True,
                    )[:20]
                )

            # Find bridges: nodes connected to multiple categories
            bridges = []
            for nid, node in relevant.items():
                connected_cats = set()
                for conn in node["connections"]:
                    target = grid.nodes.get(conn["target"])
                    if target:
                        connected_cats.add(target["category"])
                if len(connected_cats) >= 2:
                    bridges.append(
                        {
                            "id": nid,
                            "title": node["title"],
                            "category": node["category"],
                            "bridges_to": list(connected_cats),
                            "connection_count": len(node["connections"]),
                        }
                    )

            reports.append(
                {
                    "angle": angle_name,
                    "description": description,
                    "nodes_analyzed": len(relevant),
                    "bridges_found": len(bridges),
                    "top_bridges": sorted(bridges, key=lambda x: x["connection_count"], reverse=True)[:5],
                }
            )

        return reports


# ---------------------------------------------------------------------------
# Category Exporter — split datasets for different website backends
# ---------------------------------------------------------------------------


class CategoryExporter:
    """Export datasets split by category for different website backends."""

    SITE_MAP = {
        "science": ["quantum", "math", "geometry", "research"],
        "ai": ["ai", "machine-learning", "nlp"],
        "security": ["security"],
        "governance": ["governance", "swarm", "multi-agent"],
        "culture": ["lore", "tongues", "sacred-eggs"],
        "data": ["research", "distributed"],
    }

    def export_for_web(self, chunks: list[KnowledgeChunk], grid: FibonacciSphereGrid) -> dict[str, str]:
        """Export categorized datasets for website backends."""
        paths = {}

        for site_name, categories in self.SITE_MAP.items():
            site_dir = EXPORT_ROOT / site_name
            site_dir.mkdir(parents=True, exist_ok=True)

            site_chunks = [c for c in chunks if c.category in categories]
            site_nodes = {nid: n for nid, n in grid.nodes.items() if n["category"] in categories}

            # Dataset JSON
            dataset_path = site_dir / "dataset.json"
            dataset_path.write_text(
                json.dumps(
                    [
                        {
                            "id": c.id,
                            "title": c.title,
                            "category": c.category,
                            "source": c.source,
                            "url": c.url,
                            "content_preview": c.content[:500],
                            "trust_score": c.trust_score,
                        }
                        for c in site_chunks
                    ],
                    indent=2,
                )
            )

            # Grid nodes JSON (for 3D visualization)
            grid_path = site_dir / "grid_nodes.json"
            grid_path.write_text(json.dumps(site_nodes, indent=2))

            # Index HTML snippet
            index_path = site_dir / "index.json"
            index_path.write_text(
                json.dumps(
                    {
                        "site": site_name,
                        "total_items": len(site_chunks),
                        "categories": categories,
                        "grid_nodes": len(site_nodes),
                        "updated": datetime.datetime.now(datetime.UTC).isoformat(),
                    },
                    indent=2,
                )
            )

            paths[site_name] = str(site_dir)
            print(f"  {site_name}: {len(site_chunks)} chunks, {len(site_nodes)} grid nodes")

        return paths


# ---------------------------------------------------------------------------
# HuggingFace Pusher — upload categorized datasets
# ---------------------------------------------------------------------------


def push_datasets_to_hf(chunks: list[KnowledgeChunk], grid: FibonacciSphereGrid):
    """Push categorized datasets to HuggingFace."""
    hf_token = os.environ.get("HF_TOKEN", "")
    if not hf_token:
        print("  HF_TOKEN not set, skipping")
        return

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("  huggingface_hub not installed")
        return

    api = HfApi(token=hf_token)
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M")

    # Group by category
    by_category: dict[str, list] = {}
    for chunk in chunks:
        by_category.setdefault(chunk.category, []).append(chunk.to_dict())

    for category, records in by_category.items():
        # Write JSONL
        filename = f"knowledge/{category}/{category}_{timestamp}.jsonl"
        local_path = BASIN_ROOT / "hf_staging" / category / f"{category}_{timestamp}.jsonl"
        local_path.parent.mkdir(parents=True, exist_ok=True)

        with open(local_path, "w") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")

        try:
            api.upload_file(
                path_or_fileobj=str(local_path),
                path_in_repo=filename,
                repo_id=HF_DATASET,
                repo_type="dataset",
            )
            print(f"  HF: pushed {len(records)} records to {category}/")
        except Exception as e:
            print(f"  HF push error for {category}: {e}")

    # Push grid
    grid_path = grid.export()
    try:
        api.upload_file(
            path_or_fileobj=grid_path,
            path_in_repo=f"knowledge/sphere_grid_{timestamp}.json",
            repo_id=HF_DATASET,
            repo_type="dataset",
        )
        print(f"  HF: pushed sphere grid ({len(grid.nodes)} nodes)")
    except Exception as e:
        print(f"  HF grid push error: {e}")


# ---------------------------------------------------------------------------
# HYDRA Integration — feed HYDRA research output into pipeline
# ---------------------------------------------------------------------------


def hydra_research_to_chunks(topic: str, max_subtasks: int = 3) -> list[KnowledgeChunk]:
    """Run HYDRA research on a topic and convert results to KnowledgeChunks."""
    import subprocess

    chunks = []

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "hydra",
                "research",
                topic,
                "--mode",
                "httpx",
                "--max-subtasks",
                str(max_subtasks),
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(PROJECT_ROOT),
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
        )
        if result.returncode != 0:
            print(f"    HYDRA research error: {result.stderr[:200]}")
            return chunks

        # Parse HYDRA JSON output
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            # HYDRA may print banner before JSON — try to find JSON block
            for line in result.stdout.split("\n"):
                line = line.strip()
                if line.startswith("{") or line.startswith("["):
                    try:
                        data = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
            else:
                return chunks

        # Convert research findings to chunks
        findings = data if isinstance(data, list) else data.get("findings", data.get("results", []))
        if isinstance(findings, dict):
            findings = [findings]

        for i, finding in enumerate(findings):
            title = finding.get("title", finding.get("query", f"HYDRA research: {topic}"))
            content = finding.get("content", finding.get("summary", finding.get("text", str(finding))))
            url = finding.get("url", finding.get("source", ""))

            chunk = KnowledgeChunk(
                id=f"hydra-{hashlib.sha256(f'{topic}:{i}:{title}'.encode()).hexdigest()[:12]}",
                title=str(title)[:256],
                content=str(content)[:4000],
                source="hydra",
                category=_categorize_hydra(topic),
                url=str(url),
                timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
            )
            chunks.append(chunk)

    except subprocess.TimeoutExpired:
        print(f"    HYDRA research timed out for '{topic}'")
    except Exception as e:
        print(f"    HYDRA research error: {e}")

    return chunks


def _categorize_hydra(topic: str) -> str:
    """Categorize a HYDRA research topic."""
    topic_lower = topic.lower()
    if any(w in topic_lower for w in ["security", "crypto", "attack", "vulnerability"]):
        return "security"
    if any(w in topic_lower for w in ["governance", "consensus", "agent", "coordination"]):
        return "governance"
    if any(w in topic_lower for w in ["ai", "neural", "learning", "model", "training"]):
        return "ai"
    if any(w in topic_lower for w in ["geometry", "manifold", "topology", "quasicrystal"]):
        return "math"
    return "research"


def hydra_arxiv_expand(query: str, max_results: int = 5) -> list[str]:
    """Use HYDRA arXiv search to discover new related queries."""
    import subprocess

    new_queries = []

    try:
        result = subprocess.run(
            [sys.executable, "-m", "hydra", "arxiv", "search", query, "--max", str(max_results)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
        )
        if result.returncode != 0:
            return new_queries

        # Extract paper titles as new query seeds
        for line in result.stdout.split("\n"):
            if "::" in line and line.strip().startswith(("1.", "2.", "3.", "4.", "5.")):
                # Format: "1. arxiv_id :: Title"
                title = line.split("::", 1)[1].strip() if "::" in line else ""
                if title and len(title) > 10:
                    # Extract key phrases (first 5 words)
                    words = title.split()[:5]
                    new_queries.append(" ".join(words))

    except Exception:
        pass

    return new_queries


# HYDRA research topics for the pipeline
HYDRA_RESEARCH_TOPICS = [
    "quasicrystal data storage resonance-gated access control",
    "chiral symmetry breaking data security cryptographic",
    "Poincare ball embedding governance decision multi-agent",
    "Sacred geometry tokenization language model",
    "hyperbolic neural network exponential cost adversarial",
    "Chladni pattern vibration mode storage addressing",
    "federated learning geometric aggregation",
    "Byzantine fault tolerance Poincare metric",
    "lore-seeded tokenizer narrative corpus",
    "multi-modal AI safety evaluation framework",
]


# ---------------------------------------------------------------------------
# Query Generator — expand queries so we never run out of new things to search
# ---------------------------------------------------------------------------

SEED_QUERIES = {
    "arxiv": [
        # Core SCBE domains
        "hyperbolic geometry AI safety",
        "Poincare ball embedding",
        "post-quantum cryptography lattice",
        "multi-agent governance consensus",
        "geometric deep learning",
        "adversarial robustness exponential cost",
        "knowledge graph retrieval augmented",
        "federated learning privacy",
        "homomorphic encryption neural",
        "topological data analysis",
        "graph neural network security",
        "differential privacy machine learning",
        "zero knowledge proof blockchain",
        "swarm intelligence optimization",
        "manifold learning dimensionality reduction",
        "causal inference deep learning",
        "quantum error correction",
        "Byzantine fault tolerance distributed",
        "attention mechanism transformer geometry",
        "information theoretic security",
        # Chladni / quasicrystal / resonance storage
        "quasicrystal aperiodic tiling data structure",
        "Chladni pattern vibration mode nodal",
        "chiral symmetry breaking information theory",
        "resonance gated access control",
        "icosahedral symmetry projection higher dimensional",
        "Penrose tiling computational properties",
        # Agent coordination / governance
        "multi-agent reinforcement learning cooperative",
        "constitutional AI alignment training",
        "language model safety evaluation benchmark",
        "autonomous agent tool use planning",
        "reward hacking specification gaming",
        # Geometric / topological ML
        "hyperbolic neural network hierarchical",
        "Riemannian optimization manifold",
        "persistent homology machine learning",
        "equivariant neural network symmetry",
        "fiber bundle gauge neural network",
    ],
    "s2": [
        "hyperbolic geometry AI safety",
        "Poincare ball embedding neural network",
        "post-quantum cryptography lattice",
        "multi-agent governance consensus",
        "sacred geometry tokenization",
        "geometric deep learning hyperbolic",
        "adversarial robustness exponential cost",
        "blockchain memory distributed ledger AI",
        "RAG retrieval augmented generation security",
        "autonomous agent containment",
        "differential geometry machine learning",
        "topological deep learning",
        "cryptographic hash function neural",
        "swarm robotics consensus",
        "manifold optimization gradient",
        # New
        "quasicrystal lattice computation",
        "Chladni vibration pattern analysis",
        "chirality data security",
        "resonance-based authentication",
        "Sacred Egg cryptographic container",
    ],
    "loc": [
        "cryptography history",
        "hyperbolic geometry",
        "artificial intelligence",
        "quantum computing",
        "sacred geometry mathematics",
        "distributed systems",
        "network security",
        "machine learning",
        "blockchain technology",
        "computational complexity",
        # New
        "quasicrystals aperiodic",
        "Chladni acoustics vibration",
        "chirality chemistry physics",
        "resonance engineering",
        "game theory governance",
    ],
    "ia": [
        "hyperbolic geometry",
        "post-quantum cryptography",
        "AI safety alignment",
        "sacred geometry",
        "distributed consensus protocols",
        "tokenization natural language",
        "neural network security",
        "blockchain memory",
        "graph theory applications",
        "information security",
        # New
        "quasicrystal mathematics",
        "Chladni plate acoustics",
        "chirality symmetry breaking",
        "resonance structures",
        "agent coordination systems",
    ],
    "wikidata": [
        "hyperbolic geometry",
        "Poincare disk model",
        "post-quantum cryptography",
        "AI alignment",
        "sacred geometry",
        "golden ratio",
        "blockchain consensus",
        "multi-agent system",
        "lattice-based cryptography",
        "retrieval-augmented generation",
        # New
        "quasicrystal",
        "Chladni figure",
        "chirality",
        "Penrose tiling",
        "icosahedral symmetry",
    ],
    "nist": [
        "cryptographic",
        "post-quantum",
        "machine learning adversarial",
        "browser remote code execution",
        "authentication bypass",
        "blockchain vulnerability",
        "AI model injection",
        "supply chain",
        # New
        "multi-factor authentication",
        "key management",
        "side-channel attack",
        "firmware integrity",
    ],
    "dataverse": [
        "cryptography",
        "machine learning security",
        "hyperbolic embedding",
        "graph neural network",
        "natural language processing",
        "quantum computing",
        "blockchain",
        "adversarial machine learning",
        # New
        "quasicrystal structure",
        "acoustic resonance",
        "multi-agent simulation",
        "geometric deep learning",
    ],
}


# ---------------------------------------------------------------------------
# Main Pipeline Cycle
# ---------------------------------------------------------------------------


def run_cycle(
    dedup: DedupRegistry,
    funnel: KnowledgeFunnel,
    graph: TokenizerGraph,
    grid: FibonacciSphereGrid,
    push_hf: bool = False,
    export_web: bool = False,
) -> dict:
    """Run one cycle of the continuous pipeline."""
    now = datetime.datetime.now(datetime.UTC)
    print(f"\n{'=' * 60}")
    print(f"CYCLE START: {now.isoformat()}")
    print(f"Previously scraped: {dedup.total_scraped()} items")
    print(f"{'=' * 60}")

    request_count = 0
    all_allowed: list[KnowledgeChunk] = []

    # Import scrapers
    from src.knowledge.scrapers.arxiv_scraper import search_arxiv, CATEGORIES as ARXIV_CATS
    from src.knowledge.scrapers.semantic_scholar_scraper import search_papers
    from src.knowledge.scrapers.loc_scraper import search_loc
    from src.knowledge.scrapers.internet_archive_scraper import search_archive
    from src.knowledge.scrapers.wikidata_scraper import search_entities
    from src.knowledge.scrapers.nist_nvd_scraper import search_cves
    from src.knowledge.scrapers.harvard_dataverse_scraper import search_datasets

    scraper_map = {
        "arxiv": lambda q: _scrape_arxiv_all_cats(search_arxiv, ARXIV_CATS, q),
        "s2": lambda q: search_papers(q, limit=10),
        "loc": lambda q: search_loc(q, limit=10),
        "ia": lambda q: search_archive(q, limit=10),
        "wikidata": lambda q: search_entities(q, limit=10),
        "nist": lambda q: search_cves(q, limit=10),
        "dataverse": lambda q: search_datasets(q, limit=10),
    }

    # Process each source
    for source, queries in SEED_QUERIES.items():
        if request_count >= MAX_REQUESTS_PER_CYCLE:
            print(f"  Hit request cap ({MAX_REQUESTS_PER_CYCLE}), stopping cycle")
            break

        scrape_fn = scraper_map.get(source)
        if not scrape_fn:
            continue

        for query in queries:
            if request_count >= MAX_REQUESTS_PER_CYCLE:
                break
            if dedup.is_done(source, query):
                continue

            print(f"  [{source}] '{query}'...")
            try:
                chunks = scrape_fn(query)
                request_count += 1

                # Funnel each chunk
                for chunk in chunks:
                    result = funnel.ingest(chunk)
                    if result["decision"] == "ALLOW":
                        graph.add_chunk(
                            chunk.id,
                            chunk.title,
                            chunk.category,
                            chunk.content,
                            chunk.source,
                            chunk.chain_hash,
                            chunk.parent_hash,
                        )
                        # Add to Fibonacci grid
                        node_in_graph = graph.nodes.get(chunk.id)
                        coords = node_in_graph.coords if node_in_graph else [0.0] * 6
                        grid.add_node(
                            chunk.id,
                            chunk.title,
                            chunk.category,
                            coords,
                            chunk.chain_hash[:12],
                        )
                        all_allowed.append(chunk)

                dedup.mark_done(source, query, len(chunks))
                print(f"    -> {len(chunks)} chunks")

            except Exception as e:
                print(f"    ERROR: {e}")
                if "429" in str(e):
                    print(f"    Rate limited on {source}, skipping rest")
                    break

            # Rate limit: space requests ~3.4 seconds apart (89 per 5 min)
            time.sleep(3.4)

    # HYDRA research phase — use HYDRA CLI for deeper research
    if request_count < MAX_REQUESTS_PER_CYCLE:
        print("\n  --- HYDRA Research Phase ---")
        for topic in HYDRA_RESEARCH_TOPICS:
            if request_count >= MAX_REQUESTS_PER_CYCLE:
                break
            if dedup.is_done("hydra", topic):
                continue

            print(f"  [hydra] '{topic}'...")
            try:
                chunks = hydra_research_to_chunks(topic, max_subtasks=2)
                request_count += 1

                for chunk in chunks:
                    result = funnel.ingest(chunk)
                    if result["decision"] == "ALLOW":
                        graph.add_chunk(
                            chunk.id,
                            chunk.title,
                            chunk.category,
                            chunk.content,
                            chunk.source,
                            chunk.chain_hash,
                            chunk.parent_hash,
                        )
                        node_in_graph = graph.nodes.get(chunk.id)
                        coords = node_in_graph.coords if node_in_graph else [0.0] * 6
                        grid.add_node(
                            chunk.id,
                            chunk.title,
                            chunk.category,
                            coords,
                            chunk.chain_hash[:12],
                        )
                        all_allowed.append(chunk)

                dedup.mark_done("hydra", topic, len(chunks))
                print(f"    -> {len(chunks)} chunks")
            except Exception as e:
                print(f"    HYDRA error: {e}")

    # Export grid
    grid_path = grid.export()
    print(f"\nSphere grid: {len(grid.nodes)} nodes -> {grid_path}")

    # Multi-angle analysis
    analyzer = MultiAngleAnalyzer()
    reports = analyzer.analyze(grid)
    analysis_path = BASIN_ROOT / "analysis_report.json"
    analysis_path.write_text(json.dumps(reports, indent=2))
    print(f"Analysis: {len(reports)} angles")
    for r in reports:
        print(f"  {r['angle']}: {r['bridges_found']} bridges found")

    # Category export for web
    if export_web:
        print("\nExporting for web backends...")
        exporter = CategoryExporter()
        exporter.export_for_web(all_allowed, grid)

    # Push to HuggingFace
    if push_hf:
        print("\nPushing to HuggingFace...")
        push_datasets_to_hf(all_allowed, grid)

    # Stats
    stats = funnel.get_stats()
    cycle_report = {
        "cycle_time": now.isoformat(),
        "requests_made": request_count,
        "chunks_allowed": len(all_allowed),
        "total_ever_scraped": dedup.total_scraped(),
        "grid_nodes": len(grid.nodes),
        "graph_nodes": len(graph.nodes),
        "graph_cords": len(graph.cords),
        "funnel_stats": stats,
        "analysis_angles": len(reports),
    }

    print(f"\n{'=' * 60}")
    print("CYCLE COMPLETE")
    print(f"  Requests this cycle: {request_count}")
    print(f"  New chunks allowed:  {len(all_allowed)}")
    print(f"  Total ever scraped:  {dedup.total_scraped()}")
    print(f"  Grid nodes:          {len(grid.nodes)}")
    print(f"  Graph cords:         {len(graph.cords)}")
    print(f"{'=' * 60}")

    return cycle_report


def _scrape_arxiv_all_cats(search_fn, cats, query, max_per_cat=5):
    """Scrape one query across all arXiv categories."""
    all_chunks = []
    for cat in cats:
        chunks = search_fn(query, category=cat, max_results=max_per_cat)
        all_chunks.extend(chunks)
        time.sleep(3)  # arXiv rate limit
    return all_chunks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Continuous Knowledge Pipeline")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode (loop forever)")
    parser.add_argument("--push-hf", action="store_true", help="Push to HuggingFace after each cycle")
    parser.add_argument("--export-web", action="store_true", help="Export for Firebase/web backends")
    parser.add_argument("--interval", type=int, default=CYCLE_INTERVAL, help="Seconds between cycles")
    args = parser.parse_args()

    dedup = DedupRegistry()
    funnel = KnowledgeFunnel()
    graph = TokenizerGraph()
    grid = FibonacciSphereGrid()

    print("=" * 60)
    print("SCBE Continuous Knowledge Pipeline")
    print(f"Daemon: {args.daemon} | Push HF: {args.push_hf} | Export Web: {args.export_web}")
    print(f"Interval: {args.interval}s | Max req/cycle: {MAX_REQUESTS_PER_CYCLE}")
    print(f"Previously scraped: {dedup.total_scraped()}")
    print("=" * 60)

    cycle = 0
    while True:
        cycle += 1
        print(f"\n{'#' * 60}")
        print(f"CYCLE {cycle}")
        print(f"{'#' * 60}")

        report = run_cycle(
            dedup,
            funnel,
            graph,
            grid,
            push_hf=args.push_hf,
            export_web=args.export_web,
        )

        # Save cycle report
        report_path = BASIN_ROOT / f"cycle_report_{cycle}.json"
        report_path.write_text(json.dumps(report, indent=2))

        if not args.daemon:
            break

        # Check if we've exhausted all queries
        if report["requests_made"] == 0:
            print("\nAll queries exhausted! Pipeline complete.")
            break

        print(f"\nSleeping {args.interval}s until next cycle...")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
