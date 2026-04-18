"""Axiom convergence zone extractor for the memory palace vault.

The user's thesis: terms that appear on every layer of the system — by
coincidence — are consistency indicators for what is flowing through the
system. We lattice the knowledge by extracting keyword sets per bucket
(SCBE/PHDM/HYDRA/Spiralverse/...), intersect them across buckets, and
call the intersection the axiom set. The axioms become mesh joints —
bridge nodes connecting dense clusters of notes in a knowledge graph.

No external dependencies: stdlib only, graph is an adjacency dict.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from src.mempalace.vault_link import VaultIndex

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")

STOPWORDS: frozenset[str] = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "are",
        "but",
        "not",
        "you",
        "all",
        "any",
        "can",
        "has",
        "have",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "how",
        "one",
        "two",
        "three",
        "out",
        "use",
        "used",
        "using",
        "its",
        "their",
        "there",
        "then",
        "than",
        "into",
        "over",
        "some",
        "also",
        "just",
        "like",
        "only",
        "such",
        "more",
        "most",
        "been",
        "being",
        "those",
        "these",
        "would",
        "could",
        "should",
        "about",
        "after",
        "before",
        "because",
        "each",
        "every",
        "get",
        "got",
        "had",
        "here",
        "let",
        "make",
        "made",
        "many",
        "may",
        "might",
        "much",
        "must",
        "need",
        "now",
        "off",
        "our",
        "own",
        "per",
        "see",
        "set",
        "shall",
        "them",
        "they",
        "thus",
        "too",
        "via",
        "way",
        "will",
        "yet",
        "your",
        "new",
        "non",
        "true",
        "false",
        "none",
        "null",
        "src",
        "test",
        "tests",
        "file",
        "files",
        "path",
        "paths",
        "line",
        "lines",
        "note",
        "notes",
        "doc",
        "docs",
        "code",
        "text",
        "list",
        "dict",
        "set",
        "type",
        "types",
        "data",
        "value",
        "values",
        "name",
        "names",
        "page",
        "pages",
        "item",
        "items",
    }
)


@dataclass
class BucketProfile:
    """Per-bucket term statistics."""

    name: str
    notes: List[Path] = field(default_factory=list)
    term_counts: Counter = field(default_factory=Counter)
    note_count: int = 0

    def top_terms(self, k: int = 40) -> List[Tuple[str, int]]:
        return self.term_counts.most_common(k)

    def term_set(self, k: int = 40) -> Set[str]:
        return {term for term, _ in self.top_terms(k)}


@dataclass
class AxiomMesh:
    """A graph whose nodes are notes, edges are shared-axiom links,
    and joints are terms that bridge dense clusters."""

    buckets: Dict[str, BucketProfile] = field(default_factory=dict)
    axioms: List[str] = field(default_factory=list)
    edges: Dict[Tuple[Path, Path], float] = field(default_factory=dict)
    joint_terms: List[Tuple[str, int]] = field(default_factory=list)

    def nodes(self) -> Set[Path]:
        out: Set[Path] = set()
        for profile in self.buckets.values():
            out.update(profile.notes)
        return out

    def neighbors(self, node: Path) -> Dict[Path, float]:
        out: Dict[Path, float] = {}
        for (a, b), w in self.edges.items():
            if a == node:
                out[b] = w
            elif b == node:
                out[a] = w
        return out


def tokenize(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text) if w.lower() not in STOPWORDS]


def build_buckets(
    index: VaultIndex,
    bucket_rules: Optional[Dict[str, Iterable[str]]] = None,
    top_k_per_note: int = 30,
) -> Dict[str, BucketProfile]:
    """Split notes into buckets by path substring.

    `bucket_rules` maps bucket_name -> list of substrings. A note lands
    in a bucket if ANY substring is present in its path (lowercased).
    """
    if bucket_rules is None:
        bucket_rules = {
            "SCBE": ["scbe", "harmonic", "poincare", "hyperbolic"],
            "PHDM": ["phdm", "polyhedral", "21d"],
            "HYDRA": ["hydra", "swarm", "spine"],
            "Spiralverse": ["spiralverse", "spiral", "lore", "aethermoor"],
            "SacredEggs": ["egg", "mother", "avion"],
            "Governance": ["governance", "axiom", "compliance", "ledger"],
            "Training": ["training", "sft", "dataset", "dpo"],
        }

    buckets: Dict[str, BucketProfile] = {name: BucketProfile(name=name) for name in bucket_rules}

    for path, _rec in index.records.items():
        path_str = str(path).lower()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        tokens = tokenize(text)
        if not tokens:
            continue
        term_freq = Counter(tokens)
        top_terms = [t for t, _ in term_freq.most_common(top_k_per_note)]
        hit = False
        for bucket_name, needles in bucket_rules.items():
            if any(needle in path_str for needle in needles):
                profile = buckets[bucket_name]
                profile.notes.append(path)
                profile.note_count += 1
                for term in top_terms:
                    profile.term_counts[term] += 1
                hit = True
        if not hit:
            continue

    return buckets


def find_convergence_zones(
    buckets: Dict[str, BucketProfile],
    top_k: int = 40,
    min_buckets: int = 3,
) -> List[str]:
    """Terms present in the top-K of at least `min_buckets` buckets."""
    term_bucket_count: Counter = Counter()
    for profile in buckets.values():
        for term in profile.term_set(top_k):
            term_bucket_count[term] += 1
    axioms = [term for term, count in term_bucket_count.most_common() if count >= min_buckets]
    return axioms


def build_mesh_graph(
    buckets: Dict[str, BucketProfile],
    axioms: Iterable[str],
    max_edges_per_bucket: int = 200,
) -> Dict[Tuple[Path, Path], float]:
    """Edges weighted by count of shared axioms between two notes in the
    same bucket. Capped per bucket to keep the graph tractable on 35k files."""
    axiom_set = set(axioms)
    edges: Dict[Tuple[Path, Path], float] = {}
    for profile in buckets.values():
        note_terms: Dict[Path, Set[str]] = {}
        for path in profile.notes:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            tokens = set(tokenize(text))
            shared = tokens & axiom_set
            if shared:
                note_terms[path] = shared
        items = list(note_terms.items())
        added = 0
        for i, (a, ta) in enumerate(items):
            if added >= max_edges_per_bucket:
                break
            for b, tb in items[i + 1 :]:
                if added >= max_edges_per_bucket:
                    break
                weight = float(len(ta & tb))
                if weight <= 0:
                    continue
                key = (a, b) if str(a) < str(b) else (b, a)
                edges[key] = max(edges.get(key, 0.0), weight)
                added += 1
    return edges


def bridge_joints(
    buckets: Dict[str, BucketProfile],
    axioms: Iterable[str],
) -> List[Tuple[str, int]]:
    """Rank axiom terms by how many buckets they span (higher = stronger joint)."""
    ranks: Counter = Counter()
    axiom_set = set(axioms)
    for profile in buckets.values():
        top = profile.term_set(80)
        for term in top & axiom_set:
            ranks[term] += 1
    return ranks.most_common()


def build_axiom_mesh(
    index: VaultIndex,
    bucket_rules: Optional[Dict[str, Iterable[str]]] = None,
    top_k_per_note: int = 30,
    convergence_top_k: int = 40,
    convergence_min_buckets: int = 3,
    max_edges_per_bucket: int = 200,
) -> AxiomMesh:
    buckets = build_buckets(
        index,
        bucket_rules=bucket_rules,
        top_k_per_note=top_k_per_note,
    )
    axioms = find_convergence_zones(
        buckets,
        top_k=convergence_top_k,
        min_buckets=convergence_min_buckets,
    )
    edges = build_mesh_graph(
        buckets,
        axioms,
        max_edges_per_bucket=max_edges_per_bucket,
    )
    joints = bridge_joints(buckets, axioms)
    return AxiomMesh(buckets=buckets, axioms=axioms, edges=edges, joint_terms=joints)
